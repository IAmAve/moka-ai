# MOKA AI - Main Application Entry Point

import os
import sys
from pathlib import Path

# Core imports
from config import Config
from core.logger import Logger
from core.di_container import DIContainer
from core.event_bus import EventBus
from core.plugin_manager import PluginManager
from core.service_manager import ServiceManager

class MokaAI:
    def __init__(self):
        """Initialize the MOKA AI system"""
        self.config = Config()
        self.logger = Logger()
        self.event_bus = EventBus()
        self.service_manager = ServiceManager()
        self.plugin_manager = PluginManager()
        self.workers = {}

    def initialize(self):
        """Initialize the MOKA system"""
        # Load configuration
        self.config.load()

        # Initialize logging
        self.logger.initialize(self.config.get("log_level", "INFO"))

        # Setup plugin system
        self._init_plugins()

        # Run startup validation
        self._validate_startup()

    def _init_plugins(self):
        """Initialize plugin system"""
        # Setup plugin manager
        self.plugin_manager = PluginManager(self.config)
        self.plugin_manager.initialize()

        # Run startup validation
        self._validate_startup()

        # Start the system
        self._start_services()