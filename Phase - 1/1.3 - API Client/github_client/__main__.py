"""Entry point for running as a module: python -m github_client."""

import sys

from github_client.cli import main

if __name__ == "__main__":
    sys.exit(main())
