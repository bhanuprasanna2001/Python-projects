"""Config handler for web scraper"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigManager:
    """Config Manager

    This class handles the YAML Config.
    """

    def __init__(self, path: str | Path) -> None:
        """Initialize Config Manager."""
        self.path = Path(path)

    def load_config(self) -> dict[str, Any]:
        """Load YAML Config."""
        with self.path.open() as fp:
            config = yaml.safe_load(fp)

        return dict(config)
