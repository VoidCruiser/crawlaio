import logging
import logging.handlers
import queue
import os

LOG_DIR = 'logs'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG').upper()

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Define log formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create a logging queue for thread-safe operations
log_queue = queue.Queue()
queue_handler = logging.handlers.QueueHandler(log_queue)

# File handler for ALL logs, including DEBUG
file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(LOG_DIR, 'combined.log'),
    maxBytes=1024 * 1024, backupCount=5, encoding='utf-8'
)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)  # Capture all logs

# Debug-specific file handler (Optional: Separate debug logs)
debug_handler = logging.handlers.RotatingFileHandler(
    os.path.join(LOG_DIR, 'debug.log'),
    maxBytes=1024 * 1024, backupCount=5, encoding='utf-8'
)
debug_handler.setFormatter(formatter)
debug_handler.setLevel(logging.DEBUG)  # Capture all logs

# Console handler (ONLY WARNING and above)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.WARNING)  # Ensures only WARNING+ in terminal

# Attach queue listener
queue_listener = logging.handlers.QueueListener(
    log_queue, file_handler, debug_handler  # Logs go to files
)
queue_listener.start()

def get_logger(name: str):
    """Returns a thread-safe logger instance."""
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logger.setLevel(logging.DEBUG)  # Capture everything
        logger.addHandler(queue_handler)  # Route through queue (to log files)
        logger.addHandler(console_handler)  # Route WARN+ to terminal
    return logger

# Configure httpx and httpcore to log everything but show only WARN in terminal
http_logger = logging.getLogger("httpx")
http_logger.setLevel(logging.DEBUG)  # Log everything to file
http_logger.addHandler(queue_handler)
http_logger.propagate = False

httpcore_logger = logging.getLogger("httpcore")
httpcore_logger.setLevel(logging.DEBUG)  # Log everything to file
httpcore_logger.addHandler(queue_handler)
httpcore_logger.propagate = False

# **FORCE Scrapy Logs to Follow This Rule**
logging.getLogger("scrapy").setLevel(logging.WARNING)  # Ensure Scrapy only prints WARN+ to terminal
logging.getLogger("twisted").setLevel(logging.WARNING)  # Ensure Twisted only prints WARN+ to terminal
