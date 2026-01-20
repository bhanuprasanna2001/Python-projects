"""
SQLite loader implementation.

Loads transformed data to SQLite database with:
- Automatic schema creation
- Upsert support (insert or update)
- Batch processing
- Transaction management
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import aiosqlite

from etl_pipeline.config import get_project_root
from etl_pipeline.exceptions import LoadingError
from etl_pipeline.loaders.base import BaseLoader
from etl_pipeline.models import LoadingResult, TransformedRecord


class SQLiteLoader(BaseLoader):
    """
    Loads transformed records to SQLite database.

    Features:
    - Automatic table creation with proper schema
    - Upsert logic based on source_identifier
    - Batch processing for performance
    - Data versioning with history table
    """

    # Table schema for transformed records
    MAIN_TABLE = "etl_records"
    HISTORY_TABLE = "etl_records_history"

    def __init__(
        self,
        database_path: str | Path,
        on_conflict: Literal["skip", "update", "fail"] = "update",
        batch_size: int = 1000,
        enable_history: bool = True,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize SQLite loader.

        Args:
            database_path: Path to SQLite database file
            on_conflict: How to handle duplicates (skip, update, fail)
            batch_size: Records per batch
            enable_history: Whether to maintain history table
            config: Additional configuration
        """
        super().__init__("sqlite", on_conflict, batch_size, config)
        self.database_path = Path(database_path)
        self.enable_history = enable_history
        self._resolved_path: Path | None = None

    @property
    def name(self) -> str:
        return f"SQLite ({self.database_path.name})"

    def _resolve_path(self) -> Path:
        """Resolve database path."""
        if self._resolved_path:
            return self._resolved_path

        path = self.database_path
        if not path.is_absolute():
            path = get_project_root() / path

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        self._resolved_path = path
        return path

    async def validate_connection(self) -> bool:
        """Check if database is accessible."""
        try:
            path = self._resolve_path()

            async with aiosqlite.connect(path) as db:
                # Try a simple query
                cursor = await db.execute("SELECT 1")
                await cursor.fetchone()
                return True

        except Exception as e:
            self.logger.warning(f"SQLite connection validation failed: {e}")
            return False

    async def initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        path = self._resolve_path()

        async with aiosqlite.connect(path) as db:
            # Main records table
            await db.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.MAIN_TABLE} (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_identifier TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    url TEXT,
                    category TEXT,
                    numeric_value_1 REAL,
                    numeric_value_2 REAL,
                    source_created_at TEXT,
                    source_updated_at TEXT,
                    extracted_at TEXT NOT NULL,
                    transformed_at TEXT NOT NULL,
                    loaded_at TEXT NOT NULL,
                    tags TEXT,
                    extra_data TEXT,

                    -- Metadata for tracking
                    version INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Index on source_identifier for fast lookups
            await db.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.MAIN_TABLE}_source_identifier
                ON {self.MAIN_TABLE}(source_identifier)
            """)

            # Index on source for filtering
            await db.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.MAIN_TABLE}_source
                ON {self.MAIN_TABLE}(source)
            """)

            # History table for versioning
            if self.enable_history:
                await db.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.HISTORY_TABLE} (
                        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        record_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        source_id TEXT NOT NULL,
                        source_identifier TEXT NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        url TEXT,
                        category TEXT,
                        numeric_value_1 REAL,
                        numeric_value_2 REAL,
                        source_created_at TEXT,
                        source_updated_at TEXT,
                        extracted_at TEXT NOT NULL,
                        transformed_at TEXT NOT NULL,
                        loaded_at TEXT NOT NULL,
                        tags TEXT,
                        extra_data TEXT,
                        version INTEGER,
                        archived_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

            # Pipeline runs table for job tracking
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id TEXT PRIMARY KEY,
                    pipeline_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    total_extracted INTEGER DEFAULT 0,
                    total_transformed INTEGER DEFAULT 0,
                    total_loaded INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    config_snapshot TEXT
                )
            """)

            await db.commit()

            self.logger.info(
                "Schema initialized",
                extra={"tables": [self.MAIN_TABLE, self.HISTORY_TABLE, "pipeline_runs"]},
            )

    async def load(self, records: list[TransformedRecord]) -> LoadingResult:
        """
        Load transformed records to SQLite.

        Implements upsert logic based on on_conflict setting.
        """
        result = self._create_result()
        result.records_attempted = len(records)

        if not records:
            result.complete()
            return result

        path = self._resolve_path()

        try:
            self.logger.info(
                f"Loading {len(records)} records to SQLite",
                extra={"on_conflict": self.on_conflict},
            )

            # Ensure schema exists
            await self.initialize_schema()

            async with aiosqlite.connect(path) as db:
                # Process in batches
                for i in range(0, len(records), self.batch_size):
                    batch = records[i : i + self.batch_size]
                    await self._load_batch(db, batch, result)

                await db.commit()

        except Exception as e:
            self._handle_error(result, e)
            raise LoadingError(
                f"SQLite loading failed: {e}",
                target="sqlite",
                recoverable=False,
            ) from e
        finally:
            result.complete()

        self.logger.info(
            f"Loading complete: {result.records_inserted} inserted, "
            f"{result.records_updated} updated, {result.records_skipped} skipped",
            extra={
                "inserted": result.records_inserted,
                "updated": result.records_updated,
                "skipped": result.records_skipped,
                "failed": result.records_failed,
            },
        )

        return result

    async def _load_batch(
        self,
        db: aiosqlite.Connection,
        batch: list[TransformedRecord],
        result: LoadingResult,
    ) -> None:
        """Load a batch of records."""
        import json

        now = datetime.utcnow().isoformat()

        for record in batch:
            try:
                # Check if record exists
                cursor = await db.execute(
                    f"SELECT id, version FROM {self.MAIN_TABLE} WHERE source_identifier = ?",
                    (record.source_identifier,),
                )
                existing = await cursor.fetchone()

                # Prepare record data
                record_data = {
                    "id": str(record.id),
                    "source": record.source.value,
                    "source_id": record.source_id,
                    "source_identifier": record.source_identifier,
                    "title": record.title,
                    "description": record.description,
                    "url": record.url,
                    "category": record.category,
                    "numeric_value_1": record.numeric_value_1,
                    "numeric_value_2": record.numeric_value_2,
                    "source_created_at": record.source_created_at.isoformat()
                    if record.source_created_at
                    else None,
                    "source_updated_at": record.source_updated_at.isoformat()
                    if record.source_updated_at
                    else None,
                    "extracted_at": record.extracted_at.isoformat(),
                    "transformed_at": record.transformed_at.isoformat(),
                    "loaded_at": now,
                    "tags": json.dumps(record.tags),
                    "extra_data": json.dumps(record.extra_data),
                }

                if existing:
                    # Record exists - handle based on conflict strategy
                    if self.on_conflict == "skip":
                        result.records_skipped += 1
                        continue
                    elif self.on_conflict == "fail":
                        raise LoadingError(
                            f"Duplicate record: {record.source_identifier}",
                            target="sqlite",
                        )
                    else:  # update
                        existing_id, existing_version = existing

                        # Archive old version if history enabled
                        if self.enable_history:
                            await self._archive_record(db, existing_id)

                        # Update with incremented version
                        record_data["version"] = existing_version + 1
                        record_data["id"] = existing_id  # Keep original ID

                        await db.execute(
                            f"""
                            UPDATE {self.MAIN_TABLE}
                            SET source = :source,
                                source_id = :source_id,
                                title = :title,
                                description = :description,
                                url = :url,
                                category = :category,
                                numeric_value_1 = :numeric_value_1,
                                numeric_value_2 = :numeric_value_2,
                                source_created_at = :source_created_at,
                                source_updated_at = :source_updated_at,
                                extracted_at = :extracted_at,
                                transformed_at = :transformed_at,
                                loaded_at = :loaded_at,
                                tags = :tags,
                                extra_data = :extra_data,
                                version = :version,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE source_identifier = :source_identifier
                            """,
                            record_data,
                        )
                        result.records_updated += 1

                else:
                    # New record - insert
                    record_data["version"] = 1

                    await db.execute(
                        f"""
                        INSERT INTO {self.MAIN_TABLE}
                        (id, source, source_id, source_identifier, title, description,
                         url, category, numeric_value_1, numeric_value_2,
                         source_created_at, source_updated_at, extracted_at,
                         transformed_at, loaded_at, tags, extra_data, version)
                        VALUES
                        (:id, :source, :source_id, :source_identifier, :title, :description,
                         :url, :category, :numeric_value_1, :numeric_value_2,
                         :source_created_at, :source_updated_at, :extracted_at,
                         :transformed_at, :loaded_at, :tags, :extra_data, :version)
                        """,
                        record_data,
                    )
                    result.records_inserted += 1

            except LoadingError:
                raise
            except Exception as e:
                self.logger.warning(f"Failed to load record {record.source_identifier}: {e}")
                result.records_failed += 1
                result.errors.append(f"{record.source_identifier}: {e}")

    async def _archive_record(self, db: aiosqlite.Connection, record_id: str) -> None:
        """Archive a record to history table before update."""
        await db.execute(
            f"""
            INSERT INTO {self.HISTORY_TABLE}
            (record_id, source, source_id, source_identifier, title, description,
             url, category, numeric_value_1, numeric_value_2,
             source_created_at, source_updated_at, extracted_at,
             transformed_at, loaded_at, tags, extra_data, version)
            SELECT
             id, source, source_id, source_identifier, title, description,
             url, category, numeric_value_1, numeric_value_2,
             source_created_at, source_updated_at, extracted_at,
             transformed_at, loaded_at, tags, extra_data, version
            FROM {self.MAIN_TABLE}
            WHERE id = ?
            """,
            (record_id,),
        )

    async def get_record_count(self) -> int:
        """Get total number of records in the database."""
        path = self._resolve_path()

        async with aiosqlite.connect(path) as db:
            cursor = await db.execute(f"SELECT COUNT(*) FROM {self.MAIN_TABLE}")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_records_by_source(self, source: str) -> int:
        """Get count of records by source."""
        path = self._resolve_path()

        async with aiosqlite.connect(path) as db:
            cursor = await db.execute(
                f"SELECT COUNT(*) FROM {self.MAIN_TABLE} WHERE source = ?",
                (source,),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_summary(self) -> dict[str, Any]:
        """Get summary statistics of loaded data."""
        path = self._resolve_path()

        if not path.exists():
            return {"error": "Database not found"}

        async with aiosqlite.connect(path) as db:
            summary: dict[str, Any] = {}

            # Total records
            cursor = await db.execute(f"SELECT COUNT(*) FROM {self.MAIN_TABLE}")
            row = await cursor.fetchone()
            summary["total_records"] = row[0] if row else 0

            # Records by source
            cursor = await db.execute(
                f"SELECT source, COUNT(*) FROM {self.MAIN_TABLE} GROUP BY source"
            )
            rows = await cursor.fetchall()
            summary["by_source"] = {row[0]: row[1] for row in rows}

            # Latest load time
            cursor = await db.execute(f"SELECT MAX(loaded_at) FROM {self.MAIN_TABLE}")
            row = await cursor.fetchone()
            summary["last_loaded_at"] = row[0] if row and row[0] else None

            # History records (if enabled)
            if self.enable_history:
                cursor = await db.execute(f"SELECT COUNT(*) FROM {self.HISTORY_TABLE}")
                row = await cursor.fetchone()
                summary["history_records"] = row[0] if row else 0

            return summary
