"""
Stress test and benchmark suite for the ETL pipeline.

Generates large datasets and measures pipeline performance under load.

Usage:
    python -m etl_pipeline.stress_test --records 100000
    python -m etl_pipeline.stress_test --benchmark
"""

from __future__ import annotations

import asyncio
import random
import string
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite
import polars as pl

from etl_pipeline.config import get_project_root, get_settings
from etl_pipeline.loaders import SQLiteLoader
from etl_pipeline.models import (
    GitHubRepository,
)
from etl_pipeline.orchestration.pipeline import Pipeline
from etl_pipeline.transformers import DataCleaner, DataNormalizer, DataValidator, TransformerChain
from etl_pipeline.utils.logging import get_logger, setup_logging
from etl_pipeline.utils.metrics import reset_metrics

logger = get_logger("stress_test")


class DataGenerator:
    """
    Generates large synthetic datasets for stress testing.

    Supports generating:
    - Weather records (CSV)
    - Book records (SQLite)
    - GitHub repository records (in-memory)
    """

    def __init__(self, seed: int = 42) -> None:
        """Initialize with reproducible seed."""
        self.seed = seed
        random.seed(seed)

    def generate_weather_csv(
        self,
        output_path: Path,
        num_records: int = 10000,
        start_date: datetime | None = None,
    ) -> Path:
        """
        Generate a large weather CSV file.

        Args:
            output_path: Where to write the CSV
            num_records: Number of weather records to generate
            start_date: Starting date for records

        Returns:
            Path to generated CSV file
        """
        start_date = start_date or datetime(2020, 1, 1)
        locations = [
            "Berlin",
            "Munich",
            "Hamburg",
            "Frankfurt",
            "Cologne",
            "Stuttgart",
            "Düsseldorf",
            "Leipzig",
            "Dortmund",
            "Essen",
            "Bremen",
            "Dresden",
            "Hanover",
            "Nuremberg",
            "Duisburg",
        ]
        conditions = [
            "Sunny",
            "Cloudy",
            "Rainy",
            "Partly Cloudy",
            "Stormy",
            "Foggy",
            "Snowy",
            "Windy",
            "Clear",
            "Overcast",
        ]

        logger.info(f"Generating {num_records:,} weather records...")

        rows = []
        for i in range(num_records):
            # Distribute records across time and locations
            date = start_date + timedelta(hours=i)
            location = random.choice(locations)

            # Generate realistic-ish values with some variation
            base_temp = 10 + 15 * random.random()  # 10-25°C base
            seasonal_variation = 10 * (0.5 - abs((date.month - 6) / 6))  # Seasonal
            temp = base_temp + seasonal_variation + random.uniform(-5, 5)

            rows.append(
                {
                    "date": date.strftime("%Y-%m-%d %H:%M:%S"),
                    "location": location,
                    "temperature": round(temp, 1),
                    "humidity": round(random.uniform(30, 95), 1),
                    "precipitation": round(random.uniform(0, 20), 1)
                    if random.random() > 0.6
                    else 0,
                    "wind_speed": round(random.uniform(0, 60), 1),
                    "conditions": random.choice(conditions),
                }
            )

        df = pl.DataFrame(rows)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.write_csv(output_path)

        logger.info(f"Generated weather CSV: {output_path} ({num_records:,} records)")
        return output_path

    async def generate_books_db(
        self,
        output_path: Path,
        num_records: int = 10000,
    ) -> Path:
        """
        Generate a large books SQLite database.

        Args:
            output_path: Where to create the database
            num_records: Number of book records to generate

        Returns:
            Path to generated database
        """
        logger.info(f"Generating {num_records:,} book records...")

        # Book generation helpers
        adjectives = [
            "Great",
            "Amazing",
            "Incredible",
            "Mysterious",
            "Lost",
            "Secret",
            "Hidden",
            "Eternal",
            "Dark",
            "Bright",
        ]
        nouns = [
            "Journey",
            "Adventure",
            "Mystery",
            "Legacy",
            "Crown",
            "Shadow",
            "Light",
            "Truth",
            "World",
            "Dream",
        ]
        authors_first = [
            "John",
            "Jane",
            "Michael",
            "Sarah",
            "David",
            "Emily",
            "Robert",
            "Emma",
            "William",
            "Olivia",
        ]
        authors_last = [
            "Smith",
            "Johnson",
            "Brown",
            "Jones",
            "Garcia",
            "Miller",
            "Davis",
            "Wilson",
            "Moore",
            "Taylor",
        ]

        def generate_title() -> str:
            pattern = random.choice(
                [
                    f"The {random.choice(adjectives)} {random.choice(nouns)}",
                    f"{random.choice(nouns)} of {random.choice(nouns)}",
                    f"A {random.choice(adjectives)} {random.choice(nouns)}",
                    f"The {random.choice(nouns)}'s {random.choice(nouns)}",
                ]
            )
            return pattern

        def generate_author() -> str:
            return f"{random.choice(authors_first)} {random.choice(authors_last)}"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing database
        if output_path.exists():
            output_path.unlink()

        async with aiosqlite.connect(output_path) as db:
            await db.execute("""
                CREATE TABLE books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT,
                    price REAL,
                    rating INTEGER,
                    availability TEXT,
                    url TEXT,
                    upc TEXT UNIQUE,
                    category TEXT,
                    description TEXT
                )
            """)

            # Generate in batches for efficiency
            batch_size = 1000
            for batch_start in range(0, num_records, batch_size):
                batch_end = min(batch_start + batch_size, num_records)
                batch = []

                for i in range(batch_start, batch_end):
                    upc = f"UPC{i:08d}"
                    title = generate_title()
                    author = generate_author()
                    price = round(random.uniform(5.99, 49.99), 2)
                    rating = random.randint(1, 5)
                    availability = random.choice(["In Stock", "Low Stock", "Out of Stock"])
                    url = f"https://books.example.com/book/{upc.lower()}"
                    category = random.choice(
                        [
                            "Fiction",
                            "Non-Fiction",
                            "Science",
                            "History",
                            "Biography",
                            "Fantasy",
                            "Romance",
                        ]
                    )
                    desc = f"A {random.choice(adjectives).lower()} book about {random.choice(nouns).lower()}."

                    batch.append(
                        (title, author, price, rating, availability, url, upc, category, desc)
                    )

                await db.executemany(
                    """INSERT INTO books
                       (title, author, price, rating, availability, url, upc, category, description)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    batch,
                )

                if (batch_end) % 10000 == 0:
                    logger.debug(f"Generated {batch_end:,} book records...")

            await db.commit()

        logger.info(f"Generated books database: {output_path} ({num_records:,} records)")
        return output_path

    def generate_github_repos(self, num_records: int = 1000) -> list[GitHubRepository]:
        """
        Generate synthetic GitHub repository records in memory.

        Args:
            num_records: Number of repos to generate

        Returns:
            List of GitHubRepository records
        """
        logger.info(f"Generating {num_records:,} GitHub repository records...")

        languages = [
            "Python",
            "JavaScript",
            "TypeScript",
            "Go",
            "Rust",
            "Java",
            "C++",
            "Ruby",
            "PHP",
            "Swift",
        ]
        topics = [
            "api",
            "web",
            "cli",
            "library",
            "framework",
            "tool",
            "database",
            "ml",
            "devops",
            "testing",
        ]
        users = [
            "alice",
            "bob",
            "charlie",
            "diana",
            "eve",
            "frank",
            "grace",
            "henry",
            "ivy",
            "jack",
        ]

        repos = []
        base_date = datetime(2020, 1, 1)

        for i in range(num_records):
            user = random.choice(users)
            name = f"project-{i:05d}-{''.join(random.choices(string.ascii_lowercase, k=5))}"
            created = base_date + timedelta(days=random.randint(0, 1800))
            updated = created + timedelta(days=random.randint(0, 365))

            repos.append(
                GitHubRepository(
                    repo_id=i + 1000000,
                    name=name,
                    full_name=f"{user}/{name}",
                    description=f"A sample repository for testing - {name}",
                    html_url=f"https://github.com/{user}/{name}",
                    language=random.choice(languages),
                    stargazers_count=random.randint(0, 50000),
                    forks_count=random.randint(0, 5000),
                    open_issues_count=random.randint(0, 500),
                    created_at=created,
                    updated_at=updated,
                    topics=random.sample(topics, k=random.randint(1, 5)),
                    owner_login=user,
                    raw_data={},
                )
            )

        logger.info(f"Generated {len(repos):,} GitHub repository records")
        return repos


class BenchmarkRunner:
    """
    Runs benchmarks on pipeline components.

    Measures:
    - Transformation throughput
    - Loading throughput
    - Full pipeline performance
    - Memory usage
    """

    def __init__(self) -> None:
        """Initialize benchmark runner."""
        self.results: dict[str, Any] = {}
        self.generator = DataGenerator()

    async def benchmark_transformation(
        self,
        num_records: int = 10000,
    ) -> dict[str, Any]:
        """
        Benchmark transformation stage throughput.

        Args:
            num_records: Number of records to transform

        Returns:
            Benchmark results
        """
        logger.info(f"Benchmarking transformation with {num_records:,} records...")

        # Generate test data
        repos = self.generator.generate_github_repos(num_records)

        # Create transformer chain
        chain = TransformerChain(
            [
                DataCleaner(missing_strategy="fill_default"),
                DataNormalizer(deduplicate=True),
                DataValidator(min_completeness=0.5),
            ]
        )

        # Run benchmark
        start = time.perf_counter()
        result = chain.execute(repos)
        duration = time.perf_counter() - start

        throughput = num_records / duration

        results = {
            "stage": "transformation",
            "input_records": num_records,
            "output_records": result.output_count,
            "dropped_records": result.dropped_count,
            "duration_seconds": round(duration, 4),
            "throughput_records_per_second": round(throughput, 2),
        }

        logger.info(
            f"Transformation benchmark: {throughput:,.0f} records/sec "
            f"({num_records:,} records in {duration:.2f}s)"
        )

        return results

    async def benchmark_loading(
        self,
        num_records: int = 10000,
        batch_size: int = 1000,
    ) -> dict[str, Any]:
        """
        Benchmark loading stage throughput.

        Args:
            num_records: Number of records to load
            batch_size: Batch size for loading

        Returns:
            Benchmark results
        """
        logger.info(f"Benchmarking loading with {num_records:,} records...")

        # Generate and transform test data
        repos = self.generator.generate_github_repos(num_records)

        chain = TransformerChain(
            [
                DataCleaner(missing_strategy="fill_default"),
                DataNormalizer(deduplicate=False),  # No dedup to test raw throughput
            ]
        )
        transform_result = chain.execute(repos)

        # Create loader with temp database
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            loader = SQLiteLoader(
                database_path=db_path,
                batch_size=batch_size,
                enable_history=False,  # Faster without history
            )

            # Run benchmark
            start = time.perf_counter()
            result = await loader.load(transform_result.records)
            duration = time.perf_counter() - start

            throughput = result.total_processed / duration

            results = {
                "stage": "loading",
                "input_records": len(transform_result.records),
                "inserted_records": result.records_inserted,
                "updated_records": result.records_updated,
                "batch_size": batch_size,
                "duration_seconds": round(duration, 4),
                "throughput_records_per_second": round(throughput, 2),
            }

            logger.info(
                f"Loading benchmark: {throughput:,.0f} records/sec "
                f"({result.total_processed:,} records in {duration:.2f}s)"
            )

            return results

        finally:
            # Cleanup
            if db_path.exists():
                db_path.unlink()

    async def benchmark_full_pipeline(
        self,
        num_weather_records: int = 10000,
        num_book_records: int = 5000,
    ) -> dict[str, Any]:
        """
        Benchmark full E2E pipeline execution.

        Args:
            num_weather_records: Weather records to generate
            num_book_records: Book records to generate

        Returns:
            Benchmark results
        """
        logger.info(
            f"Benchmarking full pipeline: {num_weather_records:,} weather + "
            f"{num_book_records:,} book records..."
        )

        # Generate test data
        data_dir = get_project_root() / "data" / "stress_test"
        data_dir.mkdir(parents=True, exist_ok=True)

        weather_path = data_dir / "weather_stress.csv"
        books_path = data_dir / "books_stress.db"
        output_path = data_dir / "output_stress.db"

        # Remove old output
        if output_path.exists():
            output_path.unlink()

        # Generate data
        self.generator.generate_weather_csv(weather_path, num_weather_records)
        await self.generator.generate_books_db(books_path, num_book_records)

        # Configure pipeline with generated data
        settings = get_settings()
        settings.sources.github.enabled = False
        settings.sources.weather.path = str(weather_path)
        settings.sources.books.database_path = str(books_path)
        settings.sources.books.fallback_path = ""
        settings.loading.sqlite.path = str(output_path)

        # Reset metrics
        reset_metrics()

        # Run pipeline
        pipeline = Pipeline(settings)

        start = time.perf_counter()
        job = await pipeline.run()
        duration = time.perf_counter() - start

        total_input = num_weather_records + num_book_records
        throughput = job.total_loaded / duration if job.total_loaded > 0 else 0

        results = {
            "stage": "full_pipeline",
            "weather_records": num_weather_records,
            "book_records": num_book_records,
            "total_input": total_input,
            "extracted": job.total_extracted,
            "transformed": job.total_transformed,
            "loaded": job.total_loaded,
            "status": job.status.value,
            "duration_seconds": round(duration, 4),
            "throughput_records_per_second": round(throughput, 2),
            "stages": [
                {
                    "stage": s.stage.value,
                    "status": s.status.value,
                    "records": s.record_count,
                    "duration_seconds": (s.completed_at - s.started_at).total_seconds()
                    if s.completed_at
                    else None,
                }
                for s in job.stages
            ],
        }

        logger.info(
            f"Full pipeline benchmark: {throughput:,.0f} records/sec "
            f"({job.total_loaded:,} loaded in {duration:.2f}s)"
        )

        return results

    async def run_all_benchmarks(
        self,
        sizes: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Run all benchmarks at multiple data sizes.

        Args:
            sizes: List of record counts to test (default: [1000, 10000, 50000])

        Returns:
            Complete benchmark results
        """
        sizes = sizes or [1000, 10000, 50000]

        all_results = {
            "started_at": datetime.utcnow().isoformat() + "Z",
            "benchmarks": [],
        }

        for size in sizes:
            logger.info(f"\n{'=' * 60}\nRunning benchmarks at size {size:,}\n{'=' * 60}")

            # Transformation benchmark
            trans_result = await self.benchmark_transformation(size)
            trans_result["size_tier"] = size
            all_results["benchmarks"].append(trans_result)

            # Loading benchmark
            load_result = await self.benchmark_loading(size)
            load_result["size_tier"] = size
            all_results["benchmarks"].append(load_result)

            # Full pipeline benchmark (scaled down for book records)
            full_result = await self.benchmark_full_pipeline(
                num_weather_records=size,
                num_book_records=size // 2,
            )
            full_result["size_tier"] = size
            all_results["benchmarks"].append(full_result)

        all_results["completed_at"] = datetime.utcnow().isoformat() + "Z"

        # Summary
        all_results["summary"] = self._compute_summary(all_results["benchmarks"])

        return all_results

    def _compute_summary(self, benchmarks: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute summary statistics from benchmarks."""
        by_stage: dict[str, list[float]] = {}

        for b in benchmarks:
            stage = b.get("stage", "unknown")
            throughput = b.get("throughput_records_per_second", 0)
            if stage not in by_stage:
                by_stage[stage] = []
            by_stage[stage].append(throughput)

        summary = {}
        for stage, throughputs in by_stage.items():
            summary[stage] = {
                "min_throughput": round(min(throughputs), 2),
                "max_throughput": round(max(throughputs), 2),
                "avg_throughput": round(sum(throughputs) / len(throughputs), 2),
            }

        return summary


async def run_stress_test(
    num_records: int = 50000,
    run_benchmark: bool = True,
) -> dict[str, Any]:
    """
    Main stress test entry point.

    Args:
        num_records: Base number of records to generate
        run_benchmark: Whether to run full benchmarks

    Returns:
        Stress test results
    """
    setup_logging(level="INFO", log_format="simple")

    logger.info(f"\n{'=' * 60}")
    logger.info("ETL Pipeline Stress Test")
    logger.info(f"{'=' * 60}\n")

    results: dict[str, Any] = {
        "started_at": datetime.utcnow().isoformat() + "Z",
        "configuration": {
            "num_records": num_records,
            "run_benchmark": run_benchmark,
        },
    }

    benchmark_runner = BenchmarkRunner()

    if run_benchmark:
        # Run comprehensive benchmarks
        sizes = [1000, num_records // 5, num_records]
        benchmark_results = await benchmark_runner.run_all_benchmarks(sizes)
        results["benchmarks"] = benchmark_results
    else:
        # Just run single full pipeline test
        full_result = await benchmark_runner.benchmark_full_pipeline(
            num_weather_records=num_records,
            num_book_records=num_records // 2,
        )
        results["pipeline_result"] = full_result

    results["completed_at"] = datetime.utcnow().isoformat() + "Z"

    # Print summary
    logger.info(f"\n{'=' * 60}")
    logger.info("Stress Test Complete")
    logger.info(f"{'=' * 60}")

    if "benchmarks" in results and "summary" in results["benchmarks"]:
        summary = results["benchmarks"]["summary"]
        for stage, stats in summary.items():
            logger.info(
                f"{stage}: {stats['avg_throughput']:,.0f} records/sec avg "
                f"(min: {stats['min_throughput']:,.0f}, max: {stats['max_throughput']:,.0f})"
            )

    return results


# CLI entry point
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="ETL Pipeline Stress Test")
    parser.add_argument(
        "--records",
        "-r",
        type=int,
        default=50000,
        help="Number of records to generate (default: 50000)",
    )
    parser.add_argument(
        "--benchmark",
        "-b",
        action="store_true",
        help="Run full benchmark suite",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file for results (JSON)",
    )

    args = parser.parse_args()

    results = asyncio.run(
        run_stress_test(
            num_records=args.records,
            run_benchmark=args.benchmark,
        )
    )

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(results, indent=2))
        print(f"\nResults written to: {output_path}")
