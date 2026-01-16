"""Config handler for web scraper"""

from __future__ import annotations

import yaml

class ConfigManager:
    """Config Manager
    
    This class handles the YAML Config.
    """
    
    def __init__(self, path) -> None:
        """Initialize Config Manager"""
        self.path = path
        
    def load_config(self):
        """Load YAML Config"""
        with open(self.path, "r") as fp:
            config = yaml.safe_load(fp)
            
        return dict(config)