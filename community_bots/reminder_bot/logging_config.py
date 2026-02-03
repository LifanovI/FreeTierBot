import json
import logging
import sys

class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        })

def setup_logging():
    """Configure structured JSON logging for Cloud Functions."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]

# Setup logging when module is imported
setup_logging()

# Create a logger for this module
logger = logging.getLogger(__name__)