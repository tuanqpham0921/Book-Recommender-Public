import os
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)

def save_file(data, file_name: str = "log", path: str = settings.app.EXPORT_DIR):
    """JSON logging utility for debugging and exports.

    Args:
        data: Any JSON-serializable data structure
        file_name: Filename (without extension)
        path: Directory path for the log file
    """
    
    # Ensure directory exists
    os.makedirs(path, exist_ok=True)

    json_str = json.dumps(data, indent=2, default=str)
    filepath = f"{path}{file_name}.json"

    with open(filepath, "w") as f:
        f.write(json_str)

    logger.info(f"📋 log written to {filepath}")