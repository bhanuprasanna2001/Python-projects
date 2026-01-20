"""
CLI for the ETL pipeline.

Provides commands for running, monitoring, and managing the pipeline.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from etl_pipeline.config import get_settings
from etl_pipeline.models import DataSource, JobStatus, PipelineJob, Stage
from etl_pipeline.orchestration.pipeline import Pipeline
from etl_pipeline.utils.logging import setup_logging

app = typer.Typer(
    name="etl_pipeline",
    help="Automated ETL Pipeline - Extract, Transform, Load data from multiple sources",
    no_args_is_help=True,
)

# Scheduler sub-app
scheduler_app = typer.Typer(
    name="scheduler",
    help="Scheduler commands for automated pipeline execution",
)
app.add_typer(scheduler_app, name="scheduler")

# Monitoring sub-app
monitor_app = typer.Typer(
    name="monitor",
    help="Monitoring and health check commands",
)
app.add_typer(monitor_app, name="monitor")

console = Console()


def _get_stage_list(stage: str | None) -> list[Stage] | None:
    """Convert stage string to Stage enum list.

    Accepts comma-separated stages like 'extract,transform,load' or single stage.
    """
    if stage is None:
        return None

    stage_map = {
        "extract": Stage.EXTRACT,
        "transform": Stage.TRANSFORM,
        "load": Stage.LOAD,
    }

    # Handle 'all' as special case
    if stage.lower() == "all":
        return None

    # Parse comma-separated stages
    result: list[Stage] = []
    for s in stage.split(","):
        s = s.strip().lower()
        if s not in stage_map:
            console.print(f"[red]Invalid stage: {s}[/red]")
            console.print(f"Valid stages: {', '.join(stage_map.keys())}, all")
            raise typer.Exit(1)
        result.append(stage_map[s])

    return result if result else None


def _get_source_list(sources: str | None) -> list[DataSource] | None:
    """Convert source string to DataSource enum list."""
    if sources is None:
        return None

    source_map = {
        "github": DataSource.GITHUB,
        "csv": DataSource.CSV,
        "sqlite": DataSource.SQLITE,
    }

    result = []
    for source in sources.split(","):
        source = source.strip().lower()
        if source not in source_map:
            console.print(f"[red]Invalid source: {source}[/red]")
            console.print(f"Valid sources: {', '.join(source_map.keys())}")
            raise typer.Exit(1)
        result.append(source_map[source])

    return result


@app.command()
def run(
    stage: str | None = typer.Option(
        None,
        "--stage",
        "-s",
        help="Comma-separated stages: extract,transform,load or 'all'",
    ),
    sources: str | None = typer.Option(
        None,
        "--sources",
        help="Comma-separated list of sources to extract from: github,csv,sqlite",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """
    Run the ETL pipeline.

    Examples:
        etl_pipeline run                              # Run full pipeline
        etl_pipeline run --stage extract              # Run extraction only
        etl_pipeline run --stage extract,transform    # Run extract + transform
        etl_pipeline run --sources github             # Extract from GitHub only
    """
    settings = get_settings()
    setup_logging(
        level="DEBUG" if verbose else settings.log_level,
        log_format="simple",
    )

    stages = _get_stage_list(stage)
    source_list = _get_source_list(sources)

    console.print(
        Panel(
            f"[bold blue]ETL Pipeline: {settings.pipeline.name}[/bold blue]",
            subtitle="Running pipeline...",
        )
    )

    pipeline = Pipeline(settings)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running pipeline...", total=None)

        try:
            job = asyncio.run(pipeline.run(stages=stages, sources=source_list))

            progress.update(task, completed=True)

            # Display results
            _display_job_results(job)

            if job.status == JobStatus.FAILED:
                raise typer.Exit(1)

        except Exception as e:
            progress.update(task, completed=True)
            console.print(f"[red]Pipeline failed: {e}[/red]")
            raise typer.Exit(1) from None


def _display_job_results(job: PipelineJob) -> None:
    """Display job results in a formatted table."""
    # Status color
    status_colors = {
        JobStatus.COMPLETED: "green",
        JobStatus.PARTIAL: "yellow",
        JobStatus.FAILED: "red",
        JobStatus.RUNNING: "blue",
        JobStatus.PENDING: "dim",
    }
    status_color = status_colors.get(job.status, "white")

    # Summary table
    table = Table(title="Pipeline Results", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Status", f"[{status_color}]{job.status.value}[/{status_color}]")
    table.add_row("Job ID", str(job.job_id)[:8] + "...")
    table.add_row("Duration", f"{job.duration_seconds:.2f}s" if job.duration_seconds else "N/A")
    table.add_row("Records Extracted", str(job.total_extracted))
    table.add_row("Records Transformed", str(job.total_transformed))
    table.add_row("Records Loaded", str(job.total_loaded))

    console.print(table)

    # Stage details
    if job.stages:
        stage_table = Table(title="Stage Details", show_header=True)
        stage_table.add_column("Stage", style="cyan")
        stage_table.add_column("Status", style="white")
        stage_table.add_column("Records", style="white")
        stage_table.add_column("Duration", style="white")

        for stage_result in job.stages:
            stage_status_color = status_colors.get(stage_result.status, "white")
            duration = (
                f"{(stage_result.completed_at - stage_result.started_at).total_seconds():.2f}s"
                if stage_result.completed_at
                else "N/A"
            )
            stage_table.add_row(
                stage_result.stage.value.upper(),
                f"[{stage_status_color}]{stage_result.status.value}[/{stage_status_color}]",
                str(stage_result.record_count),
                duration,
            )

        console.print(stage_table)


@app.command()
def status() -> None:
    """Show pipeline status and database statistics."""
    settings = get_settings()
    setup_logging(level="WARNING", log_format="simple")

    pipeline = Pipeline(settings)

    console.print(Panel("[bold blue]Pipeline Status[/bold blue]"))

    # Run async status check
    status_info = asyncio.run(pipeline.get_status())

    # Pipeline info
    table = Table(show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Pipeline Name", status_info["pipeline_name"])
    table.add_row("Configured Sources", str(status_info["sources"]["configured"]))
    table.add_row("Source Names", ", ".join(status_info["sources"]["names"]))

    console.print(table)

    # Database info
    if status_info.get("database"):
        db = status_info["database"]
        if "error" not in db:
            db_table = Table(title="Database Statistics", show_header=False)
            db_table.add_column("Key", style="cyan")
            db_table.add_column("Value", style="white")

            db_table.add_row("Total Records", str(db.get("total_records", 0)))
            db_table.add_row("Last Loaded", db.get("last_loaded_at", "Never"))

            if db.get("by_source"):
                for source, count in db["by_source"].items():
                    db_table.add_row(f"  {source}", str(count))

            console.print(db_table)


@app.command()
def validate() -> None:
    """Validate data source connections."""
    settings = get_settings()
    setup_logging(level="WARNING", log_format="simple")

    pipeline = Pipeline(settings)

    console.print(Panel("[bold blue]Validating Data Sources[/bold blue]"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Validating sources...", total=None)
        results = asyncio.run(pipeline.validate_sources())
        progress.update(task, completed=True)

    table = Table(title="Source Validation", show_header=True)
    table.add_column("Source", style="cyan")
    table.add_column("Status", style="white")

    for source, is_valid in results.items():
        status = "[green]✓ Connected[/green]" if is_valid else "[red]✗ Failed[/red]"
        table.add_row(source, status)

    console.print(table)

    # Exit with error if any failed
    if not all(results.values()):
        raise typer.Exit(1)


@app.command()
def sources() -> None:
    """List configured data sources."""
    settings = get_settings()

    console.print(Panel("[bold blue]Configured Data Sources[/bold blue]"))

    table = Table(show_header=True)
    table.add_column("Source", style="cyan")
    table.add_column("Type", style="white")
    table.add_column("Enabled", style="white")
    table.add_column("Details", style="dim")

    # GitHub
    gh = settings.sources.github
    table.add_row(
        "GitHub",
        "API",
        "[green]Yes[/green]" if gh.enabled else "[red]No[/red]",
        f"User: {gh.username}, Max: {gh.max_items}",
    )

    # CSV
    csv = settings.sources.weather
    table.add_row(
        "Weather CSV",
        "File",
        "[green]Yes[/green]" if csv.enabled else "[red]No[/red]",
        f"Path: {csv.path}",
    )

    # SQLite
    sqlite = settings.sources.books
    table.add_row(
        "Books SQLite",
        "Database",
        "[green]Yes[/green]" if sqlite.enabled else "[red]No[/red]",
        f"Path: {sqlite.database_path or sqlite.fallback_path}",
    )

    console.print(table)


@app.command()
def config() -> None:
    """Show current configuration."""
    settings = get_settings()

    console.print(Panel("[bold blue]Current Configuration[/bold blue]"))

    # Pipeline settings
    table = Table(title="Pipeline", show_header=False)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", settings.pipeline.name)
    table.add_row("Description", settings.pipeline.description)
    table.add_row("Log Level", settings.log_level)

    console.print(table)

    # Loading settings
    load_table = Table(title="Loading", show_header=False)
    load_table.add_column("Key", style="cyan")
    load_table.add_column("Value", style="white")

    load_table.add_row("Target", settings.loading.target)
    load_table.add_row("On Conflict", settings.loading.on_conflict)
    load_table.add_row("Batch Size", str(settings.loading.batch_size))

    if settings.loading.target == "sqlite":
        load_table.add_row("Database Path", settings.loading.sqlite.path)

    console.print(load_table)

    # Transformation settings
    trans_table = Table(title="Transformations", show_header=False)
    trans_table.add_column("Key", style="cyan")
    trans_table.add_column("Value", style="white")

    trans = settings.transformations
    trans_table.add_row("Normalize Dates", str(trans.normalize_dates))
    trans_table.add_row("Handle Missing", trans.handle_missing)
    trans_table.add_row("Deduplicate", str(trans.deduplicate))
    trans_table.add_row("Min Completeness", f"{trans.quality.min_completeness:.0%}")

    console.print(trans_table)


@app.command()
def version() -> None:
    """Show version information."""
    from etl_pipeline import __version__

    console.print(f"ETL Pipeline version [bold]{__version__}[/bold]")


# ============================================================================
# Scheduler Commands
# ============================================================================


@scheduler_app.command("start")
def scheduler_start(
    interval: int = typer.Option(
        60,
        "--interval",
        "-i",
        help="Run interval in minutes",
    ),
    sources: str | None = typer.Option(
        None,
        "--sources",
        help="Comma-separated list of sources to process",
    ),
    daemon: bool = typer.Option(
        False,
        "--daemon",
        "-d",
        help="Run in daemon mode (foreground)",
    ),
) -> None:
    """
    Start the pipeline scheduler.

    Examples:
        etl_pipeline scheduler start --interval 30
        etl_pipeline scheduler start --daemon
    """
    from etl_pipeline.orchestration.scheduler import (
        PipelineScheduler,
        ScheduleConfig,
        ScheduleType,
    )

    settings = get_settings()
    setup_logging(level=settings.log_level, log_format="simple")

    source_list = _get_source_list(sources) or [DataSource.CSV, DataSource.SQLITE]

    console.print(
        Panel(
            "[bold blue]Starting Pipeline Scheduler[/bold blue]",
            subtitle=f"Interval: {interval} minutes",
        )
    )

    scheduler = PipelineScheduler()

    # Add default schedule
    schedule = ScheduleConfig(
        job_id="main_pipeline",
        pipeline_name=settings.pipeline.name,
        sources=source_list,
        schedule_type=ScheduleType.INTERVAL,
        interval_minutes=interval,
    )
    scheduler.add_schedule(schedule)

    if daemon:
        console.print("[yellow]Running in foreground. Press Ctrl+C to stop.[/yellow]")
        asyncio.run(scheduler.run_forever())
    else:
        scheduler.start()
        console.print("[green]Scheduler started in background[/green]")
        console.print("Use 'etl_pipeline scheduler status' to check status")


@scheduler_app.command("stop")
def scheduler_stop() -> None:
    """Stop the running scheduler."""
    from etl_pipeline.orchestration.scheduler import get_scheduler

    scheduler = get_scheduler()
    scheduler.stop()
    console.print("[green]Scheduler stopped[/green]")


@scheduler_app.command("status")
def scheduler_status() -> None:
    """Show scheduler status and scheduled jobs."""
    from etl_pipeline.orchestration.scheduler import get_scheduler

    scheduler = get_scheduler()
    stats = scheduler.get_stats()
    schedules = scheduler.get_schedules()

    # Status info
    status_color = "green" if stats.running else "red"
    console.print(
        Panel(
            f"[bold {status_color}]Scheduler {'Running' if stats.running else 'Stopped'}[/bold {status_color}]"
        )
    )

    table = Table(title="Scheduler Statistics", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Jobs Scheduled", str(stats.jobs_scheduled))
    table.add_row("Jobs Executed", str(stats.jobs_executed))
    table.add_row("Jobs Failed", str(stats.jobs_failed))
    table.add_row(
        "Last Execution",
        stats.last_execution.isoformat() if stats.last_execution else "Never",
    )
    table.add_row("Uptime", f"{stats.uptime_seconds:.0f}s")

    console.print(table)

    # Scheduled jobs
    if schedules:
        jobs_table = Table(title="Scheduled Jobs", show_header=True)
        jobs_table.add_column("Job ID", style="cyan")
        jobs_table.add_column("Pipeline", style="white")
        jobs_table.add_column("Next Run", style="white")
        jobs_table.add_column("Trigger", style="dim")

        for job in schedules:
            jobs_table.add_row(
                job["job_id"],
                job["pipeline_name"] or "N/A",
                job["next_run"] or "Not scheduled",
                job["trigger"],
            )

        console.print(jobs_table)


@scheduler_app.command("run-now")
def scheduler_run_now(
    job_id: str = typer.Argument(..., help="Job ID to run immediately"),
) -> None:
    """Run a scheduled job immediately."""
    from etl_pipeline.orchestration.scheduler import get_scheduler

    scheduler = get_scheduler()

    if asyncio.run(scheduler.run_now(job_id)):
        console.print(f"[green]Job '{job_id}' triggered[/green]")
    else:
        console.print(f"[red]Failed to trigger job '{job_id}'[/red]")
        raise typer.Exit(1)


@scheduler_app.command("backfill")
def scheduler_backfill(
    start_date: str = typer.Argument(..., help="Start date (YYYY-MM-DD)"),
    end_date: str | None = typer.Option(
        None,
        "--end",
        "-e",
        help="End date (YYYY-MM-DD). Defaults to today.",
    ),
    interval_hours: int = typer.Option(
        24,
        "--interval",
        "-i",
        help="Hours between each backfill run",
    ),
    sources: str | None = typer.Option(
        None,
        "--sources",
        help="Comma-separated list of sources to process",
    ),
) -> None:
    """
    Run backfill for historical data.

    Examples:
        etl_pipeline scheduler backfill 2024-01-01
        etl_pipeline scheduler backfill 2024-01-01 --end 2024-01-31 --interval 12
    """
    from etl_pipeline.orchestration.scheduler import (
        PipelineScheduler,
        ScheduleConfig,
    )

    settings = get_settings()
    setup_logging(level=settings.log_level, log_format="simple")

    source_list = _get_source_list(sources) or [DataSource.CSV, DataSource.SQLITE]

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
    except ValueError as e:
        console.print(f"[red]Invalid date format: {e}[/red]")
        raise typer.Exit(1) from None

    console.print(
        Panel(
            f"[bold blue]Running Backfill[/bold blue]\n"
            f"Period: {start_date} to {end_date or 'now'}\n"
            f"Interval: {interval_hours} hours"
        )
    )

    scheduler = PipelineScheduler()
    config = ScheduleConfig(
        job_id="backfill",
        pipeline_name="Backfill Pipeline",
        sources=source_list,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Running backfill...", total=None)
        job_ids = asyncio.run(scheduler.backfill(config, start_dt, end_dt, interval_hours))
        progress.update(task, completed=True)

    console.print(f"[green]Backfill completed: {len(job_ids)} jobs executed[/green]")


# ============================================================================
# Monitoring Commands
# ============================================================================


@monitor_app.command("health")
def monitor_health() -> None:
    """Run health checks on all components."""
    from etl_pipeline.monitoring.health import HealthChecker, HealthStatus

    checker = HealthChecker()
    overall_health = asyncio.run(checker.check_all())

    # Show overall status
    overall_color = {
        HealthStatus.HEALTHY: "green",
        HealthStatus.DEGRADED: "yellow",
        HealthStatus.UNHEALTHY: "red",
        HealthStatus.UNKNOWN: "dim",
    }.get(overall_health.status, "white")

    console.print(
        Panel(
            f"[bold blue]Health Check Results[/bold blue]\n"
            f"Overall: [{overall_color}]{overall_health.status.value.upper()}[/{overall_color}]"
        )
    )

    table = Table(show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Latency", style="white")
    table.add_column("Message", style="dim")

    status_colors = {
        HealthStatus.HEALTHY: "green",
        HealthStatus.DEGRADED: "yellow",
        HealthStatus.UNHEALTHY: "red",
        HealthStatus.UNKNOWN: "dim",
    }

    for result in overall_health.checks:
        color = status_colors.get(result.status, "white")
        table.add_row(
            result.name,
            f"[{color}]{result.status.value}[/{color}]",
            f"{result.latency_ms:.1f}ms" if result.latency_ms else "N/A",
            result.message or "",
        )

    console.print(table)

    # Exit with error if overall unhealthy
    if overall_health.status == HealthStatus.UNHEALTHY:
        raise typer.Exit(1)


@monitor_app.command("metrics")
def monitor_metrics() -> None:
    """Show collected pipeline metrics."""
    from etl_pipeline.monitoring.metrics_collector import MetricsCollector

    collector = MetricsCollector()
    metrics = collector.collect()  # Synchronous method

    console.print(Panel("[bold blue]Pipeline Metrics[/bold blue]"))

    if not metrics:
        console.print("[yellow]No metrics collected yet[/yellow]")
        return

    # Show collected timestamp
    console.print(f"[dim]Collected at: {metrics.get('collected_at', 'N/A')}[/dim]\n")

    # Show pipeline summary
    pipeline_summary = metrics.get("pipeline", {})
    if pipeline_summary:
        table = Table(title="Pipeline Summary", show_header=False)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        for key, value in pipeline_summary.items():
            if isinstance(value, float):
                table.add_row(key, f"{value:.2f}")
            else:
                table.add_row(key, str(value))

        console.print(table)
        console.print()

    # Show registry metrics (counters, gauges, histograms)
    registry = metrics.get("registry", {})
    if registry:
        # Counters
        counters = registry.get("counters", {})
        if counters:
            counter_table = Table(title="Counters", show_header=True)
            counter_table.add_column("Name", style="cyan")
            counter_table.add_column("Value", style="green")
            for name, value in sorted(counters.items()):
                counter_table.add_row(name, str(value))
            console.print(counter_table)
            console.print()

        # Gauges
        gauges = registry.get("gauges", {})
        if gauges:
            gauge_table = Table(title="Gauges", show_header=True)
            gauge_table.add_column("Name", style="cyan")
            gauge_table.add_column("Value", style="yellow")
            for name, value in sorted(gauges.items()):
                gauge_table.add_row(
                    name, f"{value:.2f}" if isinstance(value, float) else str(value)
                )
            console.print(gauge_table)
            console.print()

        # Histograms summary
        histograms = registry.get("histograms", {})
        if histograms:
            hist_table = Table(title="Histograms", show_header=True)
            hist_table.add_column("Name", style="cyan")
            hist_table.add_column("Count", style="white")
            hist_table.add_column("Mean", style="white")
            hist_table.add_column("P95", style="white")
            for name, stats in sorted(histograms.items()):
                hist_table.add_row(
                    name,
                    str(stats.get("count", 0)),
                    f"{stats.get('mean', 0):.3f}s",
                    f"{stats.get('p95', 0):.3f}s",
                )
            console.print(hist_table)


@monitor_app.command("jobs")
def monitor_jobs(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of jobs to show"),
    status: str | None = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status: completed, failed, running",
    ),
) -> None:
    """Show recent pipeline job history."""
    from etl_pipeline.orchestration.job_store import get_job_store

    job_store = get_job_store()

    status_filter = None
    if status:
        try:
            status_filter = JobStatus(status.lower())
        except ValueError:
            console.print(f"[red]Invalid status: {status}[/red]")
            raise typer.Exit(1) from None

    jobs = asyncio.run(job_store.get_recent_jobs(limit=limit, status=status_filter))

    console.print(Panel("[bold blue]Recent Pipeline Jobs[/bold blue]"))

    if not jobs:
        console.print("[yellow]No jobs found[/yellow]")
        return

    table = Table(show_header=True)
    table.add_column("Job ID", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Started", style="white")
    table.add_column("Duration", style="white")
    table.add_column("Records", style="white")

    status_colors = {
        JobStatus.COMPLETED: "green",
        JobStatus.PARTIAL: "yellow",
        JobStatus.FAILED: "red",
        JobStatus.RUNNING: "blue",
    }

    for job in jobs:
        color = status_colors.get(job.status, "white")
        duration = f"{job.duration_seconds:.1f}s" if job.duration_seconds else "N/A"
        table.add_row(
            str(job.job_id)[:8] + "...",
            f"[{color}]{job.status.value}[/{color}]",
            job.started_at.strftime("%Y-%m-%d %H:%M"),
            duration,
            str(job.total_loaded),
        )

    console.print(table)


@monitor_app.command("stats")
def monitor_stats() -> None:
    """Show aggregated job statistics."""
    from etl_pipeline.orchestration.job_store import get_job_store

    job_store = get_job_store()
    stats = asyncio.run(job_store.get_job_stats())

    console.print(Panel("[bold blue]Job Statistics[/bold blue]"))

    table = Table(show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total Jobs", str(stats["total_jobs"]))
    table.add_row("Average Duration", f"{stats['avg_duration_seconds']:.1f}s")
    table.add_row("Recent Success Rate", f"{stats['recent_success_rate_percent']:.1f}%")

    # By status
    for status_name, count in stats.get("by_status", {}).items():
        table.add_row(f"  {status_name.title()}", str(count))

    # Total records
    records = stats.get("total_records", {})
    table.add_row("Total Extracted", str(records.get("extracted", 0)))
    table.add_row("Total Transformed", str(records.get("transformed", 0)))
    table.add_row("Total Loaded", str(records.get("loaded", 0)))

    console.print(table)


if __name__ == "__main__":
    app()
