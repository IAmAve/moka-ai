"""
Configuration module for MOKA AI system
"""

import json
import os
from pathlib import Path

class Config:
    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self.config = {}
        self.default_config = {
            "log_level": "INFO",
            "max_workers": 4,
            "voice_enabled": True,
            "memory_backend": "sqlite",
            "storage_path": "data/",
            "plugins_path": "plugins/",
            "models_path": "models/",
            "temp_path": "temp/"
        }

    def load(self):
        """Load configuration from file or use defaults"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            except FileNotFoundError:
                self.config = self.default_config
        else:
            self.config = self.default_config

    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)

    def set(self, key, value):
        """Set configuration value"""
        self.config[key] = value

    def save(self):
        """Save configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)