"""
Logging module for MOKA AI system
"""

import logging
import os
from datetime import datetime

class Logger:
    def __init__(self, name="moka_ai"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Create logs directory if it doesn't exist
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # Set up file handler
        file_handler = logging.FileHandler(f"logs/moka_{datetime.now().strftime('%Y%m%d')}.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.propagate = False

    def initialize(self, log_level="INFO"):
        """Initialize the logger with the specified level"""
        level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger.setLevel(level)

    def info(self, message):
        """Log info level message"""
        self.logger.info(message)

    def error(self, message):
        """Log error level message"""
        self.logger.error(message)

    def warning(self, message):
        """Log warning level message"""
        self.logger.warning(message)

    def debug(self, message):
        """Log debug level message"""
        self.logger.debug(message)

    def critical(self, message):
        """Log critical level message"""
        self.logger.critical(message)