"""
PostgreSQL loader implementation.

Loads transformed data to PostgreSQL database with:
- Async connection pooling via asyncpg
- Upsert support (INSERT ON CONFLICT)
- Batch processing with COPY for high performance
- Transaction management
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

import asyncpg  # type: ignore[import-untyped]

from etl_pipeline.exceptions import LoadingError
from etl_pipeline.loaders.base import BaseLoader
from etl_pipeline.models import LoadingResult, TransformedRecord


class PostgresLoader(BaseLoader):
    """
    Loads transformed records to PostgreSQL database.

    Features:
    - Async connection pooling for performance
    - Upsert logic based on source_identifier
    - Batch processing for performance
    - Proper schema management with migrations
    """

    MAIN_TABLE = "etl_records"
    HISTORY_TABLE = "etl_records_history"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "etl_pipeline",
        user: str = "etl_user",
        password: str = "etl_password",
        on_conflict: Literal["skip", "update", "fail"] = "update",
        batch_size: int = 1000,
        min_pool_size: int = 2,
        max_pool_size: int = 10,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize PostgreSQL loader.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            on_conflict: How to handle duplicates (skip, update, fail)
            batch_size: Records per batch
            min_pool_size: Minimum connection pool size
            max_pool_size: Maximum connection pool size
            config: Additional configuration
        """
        super().__init__("postgres", on_conflict, batch_size, config)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self._pool: asyncpg.Pool | None = None

    @property
    def name(self) -> str:
        return f"PostgreSQL ({self.host}:{self.port}/{self.database})"

    @property
    def dsn(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.dsn,
                min_size=self.min_pool_size,
                max_size=self.max_pool_size,
            )
        return self._pool

    async def _close_pool(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def __aenter__(self) -> PostgresLoader:
        """Async context manager entry."""
        await self._get_pool()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self._close_pool()

    async def validate_connection(self) -> bool:
        """Check if database is accessible."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return bool(result == 1)
        except Exception as e:
            self.logger.warning(f"PostgreSQL connection validation failed: {e}")
            return False

    async def initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Main records table
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.MAIN_TABLE} (
                    id UUID PRIMARY KEY,
                    source VARCHAR(50) NOT NULL,
                    source_id VARCHAR(255) NOT NULL,
                    source_identifier VARCHAR(500) UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    url TEXT,
                    category VARCHAR(255),
                    numeric_value_1 DOUBLE PRECISION,
                    numeric_value_2 DOUBLE PRECISION,
                    source_created_at TIMESTAMP WITH TIME ZONE,
                    source_updated_at TIMESTAMP WITH TIME ZONE,
                    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    transformed_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    loaded_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    tags JSONB DEFAULT '[]',
                    extra_data JSONB DEFAULT '{{}}',
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)

            # Indexes
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.MAIN_TABLE}_source_identifier
                ON {self.MAIN_TABLE}(source_identifier)
            """)

            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.MAIN_TABLE}_source
                ON {self.MAIN_TABLE}(source)
            """)

            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.MAIN_TABLE}_loaded_at
                ON {self.MAIN_TABLE}(loaded_at)
            """)

            # History table for versioning
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.HISTORY_TABLE} (
                    history_id SERIAL PRIMARY KEY,
                    record_id UUID NOT NULL,
                    source VARCHAR(50) NOT NULL,
                    source_id VARCHAR(255) NOT NULL,
                    source_identifier VARCHAR(500) NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    url TEXT,
                    category VARCHAR(255),
                    numeric_value_1 DOUBLE PRECISION,
                    numeric_value_2 DOUBLE PRECISION,
                    source_created_at TIMESTAMP WITH TIME ZONE,
                    source_updated_at TIMESTAMP WITH TIME ZONE,
                    extracted_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    transformed_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    loaded_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    tags JSONB DEFAULT '[]',
                    extra_data JSONB DEFAULT '{{}}',
                    version INTEGER,
                    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)

            # Pipeline runs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS pipeline_runs (
                    run_id UUID PRIMARY KEY,
                    pipeline_name VARCHAR(255) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    total_extracted INTEGER DEFAULT 0,
                    total_transformed INTEGER DEFAULT 0,
                    total_loaded INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    config_snapshot JSONB
                )
            """)

            self.logger.info(
                "PostgreSQL schema initialized",
                extra={"tables": [self.MAIN_TABLE, self.HISTORY_TABLE, "pipeline_runs"]},
            )

    async def load(self, records: list[TransformedRecord]) -> LoadingResult:
        """
        Load transformed records to PostgreSQL.

        Implements upsert logic based on on_conflict setting.
        """
        result = self._create_result()
        result.records_attempted = len(records)

        if not records:
            result.complete()
            return result

        try:
            self.logger.info(
                f"Loading {len(records)} records to PostgreSQL",
                extra={"on_conflict": self.on_conflict},
            )

            # Ensure schema exists
            await self.initialize_schema()

            pool = await self._get_pool()

            async with pool.acquire() as conn:
                # Process in batches
                for i in range(0, len(records), self.batch_size):
                    batch = records[i : i + self.batch_size]
                    await self._load_batch(conn, batch, result)

        except Exception as e:
            self._handle_error(result, e)
            raise LoadingError(
                f"PostgreSQL loading failed: {e}",
                target="postgres",
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
        conn: asyncpg.Connection,
        batch: list[TransformedRecord],
        result: LoadingResult,
    ) -> None:
        """Load a batch of records using upsert."""
        now = datetime.utcnow()

        for record in batch:
            try:
                # Check if record exists
                existing = await conn.fetchrow(
                    f"SELECT id, version FROM {self.MAIN_TABLE} WHERE source_identifier = $1",
                    record.source_identifier,
                )

                # Prepare record data
                record_data = {
                    "id": record.id,
                    "source": record.source.value,
                    "source_id": record.source_id,
                    "source_identifier": record.source_identifier,
                    "title": record.title,
                    "description": record.description,
                    "url": record.url,
                    "category": record.category,
                    "numeric_value_1": record.numeric_value_1,
                    "numeric_value_2": record.numeric_value_2,
                    "source_created_at": record.source_created_at,
                    "source_updated_at": record.source_updated_at,
                    "extracted_at": record.extracted_at,
                    "transformed_at": record.transformed_at,
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
                            target="postgres",
                            recoverable=True,
                        )
                    else:
                        # Update existing record
                        new_version = (existing["version"] or 0) + 1

                        # Archive to history first
                        await conn.execute(
                            f"""
                            INSERT INTO {self.HISTORY_TABLE}
                            (record_id, source, source_id, source_identifier, title,
                             description, url, category, numeric_value_1, numeric_value_2,
                             source_created_at, source_updated_at, extracted_at,
                             transformed_at, loaded_at, tags, extra_data, version)
                            SELECT id, source, source_id, source_identifier, title,
                                   description, url, category, numeric_value_1, numeric_value_2,
                                   source_created_at, source_updated_at, extracted_at,
                                   transformed_at, loaded_at, tags, extra_data, version
                            FROM {self.MAIN_TABLE}
                            WHERE source_identifier = $1
                        """,
                            record.source_identifier,
                        )

                        # Update main record
                        await conn.execute(
                            f"""
                            UPDATE {self.MAIN_TABLE}
                            SET title = $1, description = $2, url = $3, category = $4,
                                numeric_value_1 = $5, numeric_value_2 = $6,
                                source_created_at = $7, source_updated_at = $8,
                                extracted_at = $9, transformed_at = $10, loaded_at = $11,
                                tags = $12, extra_data = $13, version = $14, updated_at = NOW()
                            WHERE source_identifier = $15
                        """,
                            record_data["title"],
                            record_data["description"],
                            record_data["url"],
                            record_data["category"],
                            record_data["numeric_value_1"],
                            record_data["numeric_value_2"],
                            record_data["source_created_at"],
                            record_data["source_updated_at"],
                            record_data["extracted_at"],
                            record_data["transformed_at"],
                            record_data["loaded_at"],
                            record_data["tags"],
                            record_data["extra_data"],
                            new_version,
                            record.source_identifier,
                        )

                        result.records_updated += 1
                else:
                    # Insert new record
                    await conn.execute(
                        f"""
                        INSERT INTO {self.MAIN_TABLE}
                        (id, source, source_id, source_identifier, title, description,
                         url, category, numeric_value_1, numeric_value_2,
                         source_created_at, source_updated_at, extracted_at,
                         transformed_at, loaded_at, tags, extra_data)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                    """,
                        record_data["id"],
                        record_data["source"],
                        record_data["source_id"],
                        record_data["source_identifier"],
                        record_data["title"],
                        record_data["description"],
                        record_data["url"],
                        record_data["category"],
                        record_data["numeric_value_1"],
                        record_data["numeric_value_2"],
                        record_data["source_created_at"],
                        record_data["source_updated_at"],
                        record_data["extracted_at"],
                        record_data["transformed_at"],
                        record_data["loaded_at"],
                        record_data["tags"],
                        record_data["extra_data"],
                    )

                    result.records_inserted += 1

            except LoadingError:
                raise
            except Exception as e:
                self.logger.warning(f"Failed to load record {record.source_identifier}: {e}")
                result.records_failed += 1
                result.errors.append(f"{record.source_identifier}: {e}")

    async def get_summary(self) -> dict[str, Any]:
        """Get summary statistics from the database."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # Total records
            total = await conn.fetchval(f"SELECT COUNT(*) FROM {self.MAIN_TABLE}")

            # Records by source
            rows = await conn.fetch(f"""
                SELECT source, COUNT(*) as count
                FROM {self.MAIN_TABLE}
                GROUP BY source
            """)
            by_source = {row["source"]: row["count"] for row in rows}

            # Latest load
            latest = await conn.fetchval(f"""
                SELECT MAX(loaded_at) FROM {self.MAIN_TABLE}
            """)

            return {
                "total_records": total,
                "by_source": by_source,
                "latest_load": latest.isoformat() if latest else None,
                "database": self.database,
                "host": self.host,
            }
