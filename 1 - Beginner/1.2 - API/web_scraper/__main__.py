"""Entry point for running as a module: python -m web_scraper"""

import sys

from web_scraper.cli import main

if __name__ == "__main__":
    sys.exit(main())