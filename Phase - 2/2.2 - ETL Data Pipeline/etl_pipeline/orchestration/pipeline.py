"""
Pipeline orchestrator.

Coordinates the execution of Extract, Transform, Load stages.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from etl_pipeline.config import Settings, get_settings
from etl_pipeline.exceptions import PipelineError
from etl_pipeline.extractors import CSVExtractor, GitHubExtractor, SQLiteExtractor
from etl_pipeline.extractors.base import BaseExtractor
from etl_pipeline.loaders import SQLiteLoader
from etl_pipeline.loaders.base import BaseLoader
from etl_pipeline.models import (
    DataSource,
    ExtractedRecord,
    ExtractionResult,
    JobStatus,
    LoadingResult,
    PipelineJob,
    Stage,
    StageResult,
    TransformationResult,
    TransformedRecord,
)
from etl_pipeline.orchestration.job_store import get_job_store
from etl_pipeline.transformers import DataCleaner, DataNormalizer, DataValidator
from etl_pipeline.transformers.base import TransformerChain
from etl_pipeline.utils.logging import get_logger, setup_logging


class Pipeline:
    """
    Orchestrates the ETL pipeline execution.

    Coordinates:
    - Multiple extractors (GitHub, CSV, SQLite)
    - Transformer chain (Clean → Normalize → Validate)
    - Loader (SQLite)

    Tracks execution metrics and handles failures gracefully.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        extractors: list[BaseExtractor[Any]] | None = None,
        loader: BaseLoader | None = None,
    ) -> None:
        """
        Initialize pipeline.

        Args:
            settings: Pipeline configuration (uses default if not provided)
            extractors: Custom extractors (created from config if not provided)
            loader: Custom loader (created from config if not provided)
        """
        self.settings = settings or get_settings()
        self.logger = get_logger("pipeline")

        # Setup logging
        setup_logging(
            level=self.settings.log_level,
            log_format=self.settings.logging.format,
        )

        # Initialize components
        self.extractors = extractors or self._create_extractors()
        self.transformer_chain = self._create_transformer_chain()
        self.loader = loader or self._create_loader()

        # Job tracking
        self.current_job: PipelineJob | None = None

    def _create_extractors(self) -> list[BaseExtractor[Any]]:
        """Create extractors from configuration."""
        extractors: list[BaseExtractor[Any]] = []
        sources = self.settings.sources

        # GitHub extractor
        if sources.github.enabled:
            extractors.append(
                GitHubExtractor(
                    username=sources.github.username,
                    max_items=sources.github.max_items,
                    rate_limit_delay=sources.github.rate_limit_delay,
                    token=self.settings.github_token,
                )
            )
            self.logger.info(f"GitHub extractor configured for user '{sources.github.username}'")

        # CSV extractor
        if sources.weather.enabled:
            extractors.append(CSVExtractor(file_path=sources.weather.path))
            self.logger.info(f"CSV extractor configured for '{sources.weather.path}'")

        # SQLite extractor
        if sources.books.enabled:
            extractors.append(
                SQLiteExtractor(
                    database_path=sources.books.database_path,
                    query=sources.books.query,
                    fallback_path=sources.books.fallback_path,
                )
            )
            self.logger.info("SQLite extractor configured")

        if not extractors:
            self.logger.warning("No extractors enabled in configuration")

        return extractors

    def _create_transformer_chain(self) -> TransformerChain:
        """Create transformer chain from configuration."""
        config = self.settings.transformations

        transformers = [
            DataCleaner(missing_strategy=config.handle_missing),
            DataNormalizer(
                deduplicate=config.deduplicate,
                normalize_dates=config.normalize_dates,
            ),
            DataValidator(
                min_completeness=config.quality.min_completeness,
                fail_on_quality_error=False,
            ),
        ]

        return TransformerChain(transformers)

    def _create_loader(self) -> BaseLoader:
        """Create loader from configuration."""
        config = self.settings.loading

        if config.target == "sqlite":
            return SQLiteLoader(
                database_path=config.sqlite.path,
                on_conflict=config.on_conflict,
                batch_size=config.batch_size,
            )
        else:
            # PostgreSQL loader would go here
            raise PipelineError(
                f"Unsupported loader target: {config.target}",
                stage="initialization",
            )

    async def run(
        self,
        stages: list[Stage] | None = None,
        sources: list[DataSource] | None = None,
    ) -> PipelineJob:
        """
        Run the complete ETL pipeline.

        Args:
            stages: Specific stages to run (default: all)
            sources: Specific sources to extract from (default: all enabled)

        Returns:
            PipelineJob with execution results
        """
        stages = stages or [Stage.EXTRACT, Stage.TRANSFORM, Stage.LOAD]

        # Create job
        self.current_job = PipelineJob(
            pipeline_name=self.settings.pipeline.name,
            config_snapshot={
                "sources": [e.source.value for e in self.extractors],
                "stages": [s.value for s in stages],
            },
        )
        self.current_job.start()

        self.logger.info(
            f"Starting pipeline '{self.settings.pipeline.name}'",
            extra={
                "job_id": str(self.current_job.job_id),
                "stages": [s.value for s in stages],
            },
        )

        extracted_records: list[ExtractedRecord] = []
        transformed_records: list[TransformedRecord] = []

        try:
            # EXTRACT
            if Stage.EXTRACT in stages:
                extraction_results = await self._run_extraction(sources)
                extracted_records = []
                for result in extraction_results:
                    extracted_records.extend(result.records)
                self.current_job.total_extracted = len(extracted_records)

            # TRANSFORM
            if Stage.TRANSFORM in stages:
                if not extracted_records and Stage.EXTRACT not in stages:
                    raise PipelineError(
                        "No records to transform. Run extraction first.",
                        stage="transform",
                    )
                transform_result = await self._run_transformation(extracted_records)
                transformed_records = transform_result.records
                self.current_job.total_transformed = len(transformed_records)

            # LOAD
            if Stage.LOAD in stages:
                if not transformed_records and Stage.TRANSFORM not in stages:
                    raise PipelineError(
                        "No records to load. Run transformation first.",
                        stage="load",
                    )
                load_result = await self._run_loading(transformed_records)
                self.current_job.total_loaded = load_result.total_processed

            # Determine final status
            if self.current_job.error_count > 0:
                self.current_job.complete(JobStatus.PARTIAL)
            else:
                self.current_job.complete(JobStatus.COMPLETED)

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.current_job.complete(JobStatus.FAILED)
            raise

        self.logger.info(
            f"Pipeline completed with status '{self.current_job.status.value}'",
            extra={
                "job_id": str(self.current_job.job_id),
                "duration_seconds": self.current_job.duration_seconds,
                "extracted": self.current_job.total_extracted,
                "transformed": self.current_job.total_transformed,
                "loaded": self.current_job.total_loaded,
            },
        )

        # Persist job to job store
        try:
            job_store = get_job_store()
            await job_store.save_job(self.current_job)
            self.logger.debug(f"Job {self.current_job.job_id} persisted to job store")
        except Exception as e:
            self.logger.warning(f"Failed to persist job to store: {e}")

        return self.current_job

    async def _run_extraction(
        self, sources: list[DataSource] | None = None
    ) -> list[ExtractionResult]:
        """Run extraction stage."""
        stage_start = datetime.utcnow()
        results: list[ExtractionResult] = []

        self.logger.info("Starting extraction stage")

        # Filter extractors by source if specified
        extractors = self.extractors
        if sources:
            extractors = [e for e in extractors if e.source in sources]

        # Run extractors concurrently
        tasks = [self._extract_from_source(e) for e in extractors]
        extraction_results = await asyncio.gather(*tasks, return_exceptions=True)

        total_records = 0
        error_count = 0

        for extractor, result in zip(extractors, extraction_results, strict=True):
            if isinstance(result, BaseException):
                self.logger.error(
                    f"Extractor {extractor.name} failed: {result}",
                    extra={"source": extractor.source.value},
                )
                error_count += 1
            elif isinstance(result, ExtractionResult):
                results.append(result)
                total_records += len(result.records)

        # Record stage result
        stage_result = StageResult(
            stage=Stage.EXTRACT,
            status=JobStatus.COMPLETED if error_count == 0 else JobStatus.PARTIAL,
            started_at=stage_start,
            completed_at=datetime.utcnow(),
            record_count=total_records,
            error_message=f"{error_count} extractors failed" if error_count > 0 else None,
            metrics={
                "sources_attempted": len(extractors),
                "sources_succeeded": len(extractors) - error_count,
                "total_records": total_records,
            },
        )
        if self.current_job:
            self.current_job.add_stage_result(stage_result)

        self.logger.info(
            f"Extraction complete: {total_records} records from {len(results)} sources"
        )

        return results

    async def _extract_from_source(self, extractor: BaseExtractor[Any]) -> ExtractionResult:
        """Extract from a single source."""
        self.logger.info(f"Extracting from {extractor.name}")

        async with extractor:
            result = await extractor.extract()

        self.logger.info(
            f"Extracted {len(result.records)} records from {extractor.name}",
            extra={
                "source": extractor.source.value,
                "record_count": len(result.records),
                "error_count": result.error_count,
            },
        )

        return result

    async def _run_transformation(self, records: list[ExtractedRecord]) -> TransformationResult:
        """Run transformation stage."""
        stage_start = datetime.utcnow()

        self.logger.info(f"Starting transformation of {len(records)} records")

        result = self.transformer_chain.execute(records)

        # Get quality report from validator
        validator = self.transformer_chain.transformers[-1]
        quality_report = {}
        if isinstance(validator, DataValidator) and validator.metrics:
            quality_report = validator.get_quality_report()

        # Record stage result
        stage_result = StageResult(
            stage=Stage.TRANSFORM,
            status=JobStatus.COMPLETED if result.success else JobStatus.FAILED,
            started_at=stage_start,
            completed_at=datetime.utcnow(),
            record_count=result.output_count,
            metrics={
                "input_count": result.input_count,
                "output_count": result.output_count,
                "dropped_count": result.dropped_count,
                "completeness_ratio": result.completeness_ratio,
                **quality_report,
            },
        )
        if self.current_job:
            self.current_job.add_stage_result(stage_result)

        self.logger.info(
            f"Transformation complete: {result.input_count} → {result.output_count} records"
        )

        return result

    async def _run_loading(self, records: list[TransformedRecord]) -> LoadingResult:
        """Run loading stage."""
        stage_start = datetime.utcnow()

        self.logger.info(f"Starting loading of {len(records)} records")

        async with self.loader:
            result = await self.loader.load(records)

        # Record stage result
        stage_result = StageResult(
            stage=Stage.LOAD,
            status=JobStatus.COMPLETED if result.success else JobStatus.PARTIAL,
            started_at=stage_start,
            completed_at=datetime.utcnow(),
            record_count=result.total_processed,
            error_message=f"{result.records_failed} records failed"
            if result.records_failed > 0
            else None,
            metrics={
                "records_attempted": result.records_attempted,
                "records_inserted": result.records_inserted,
                "records_updated": result.records_updated,
                "records_skipped": result.records_skipped,
                "records_failed": result.records_failed,
            },
        )
        if self.current_job:
            self.current_job.add_stage_result(stage_result)

        self.logger.info(
            f"Loading complete: {result.records_inserted} inserted, "
            f"{result.records_updated} updated"
        )

        return result

    async def validate_sources(self) -> dict[str, bool]:
        """Validate connectivity to all data sources."""
        results = {}

        for extractor in self.extractors:
            try:
                is_valid = await extractor.validate_connection()
                results[extractor.name] = is_valid
            except Exception as e:
                self.logger.warning(f"Validation failed for {extractor.name}: {e}")
                results[extractor.name] = False

        return results

    async def get_status(self) -> dict[str, Any]:
        """Get current pipeline status and statistics."""
        # Get loader summary
        loader_summary = {}
        if isinstance(self.loader, SQLiteLoader):
            loader_summary = await self.loader.get_summary()

        return {
            "pipeline_name": self.settings.pipeline.name,
            "sources": {
                "configured": len(self.extractors),
                "names": [e.name for e in self.extractors],
            },
            "database": loader_summary,
            "last_job": {
                "job_id": str(self.current_job.job_id) if self.current_job else None,
                "status": self.current_job.status.value if self.current_job else None,
                "duration_seconds": self.current_job.duration_seconds if self.current_job else None,
            }
            if self.current_job
            else None,
        }
