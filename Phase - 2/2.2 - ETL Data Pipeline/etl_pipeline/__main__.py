"""Entry point for `python -m etl_pipeline`."""

from etl_pipeline.cli import app


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
