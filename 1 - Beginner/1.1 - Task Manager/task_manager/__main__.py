"""Entry point for running as a module: python -m task_manager"""

import sys

from task_manager.cli import main

if __name__ == "__main__":
    sys.exit(main())
