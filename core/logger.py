import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(log_dir="core/logs", log_level=logging.INFO):
    """
    Sets up the application logger with rotating file handlers.
    """
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    logger = logging.getLogger("VisionTrackAI")
    logger.setLevel(log_level)

    # Avoid adding handlers multiple times
    if not logger.handlers:
        # File handler (10 MB max size, keep 5 backups)
        file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger

# Global instance for easy import
app_logger = setup_logger()
