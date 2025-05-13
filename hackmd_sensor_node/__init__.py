import logging
from rich.logging import RichHandler

log_level_str = "DEBUG"

logger = logging.getLogger()
logger.setLevel(log_level_str.upper())

# Remove existing handlers to avoid duplicates if this module is reloaded
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Use stderr=True if you want logs to go to stderr instead of stdout
rich_handler = RichHandler(rich_tracebacks=True, show_path=False, log_time_format="%Y-%m-%d %H:%M:%S")
rich_handler.setLevel(log_level_str.upper()) # Set level for this handler
rich_handler.setFormatter(logging.Formatter(
    fmt="%(name)s - %(message)s", # Simplified format for console
    datefmt="[%X]" # Use RichHandler's default time format
))
logger.addHandler(rich_handler)

# Add file handler to write logs to node.sensor.log
file_handler = logging.FileHandler("node.sensor.log")
file_handler.setLevel(log_level_str.upper())
file_handler.setFormatter(logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
logger.addHandler(file_handler)

logger.info(f"Logging initialized for HackMD Sensor Node. Level: {log_level_str.upper()}.")
