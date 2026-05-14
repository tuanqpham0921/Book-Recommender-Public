import json
import logging
from pathlib import Path

from config import FilesLocationConstants

logger = logging.getLogger(__name__)

def save_file(
    data,
    file_name: str = "log",
    path: Path | str = FilesLocationConstants.EXPORT_DIR,
):
    """JSON logging utility for debugging and exports.

    Args:
        data: Any JSON-serializable data structure
        file_name: Filename (without extension)
        path: Directory path for the log file
    """
    
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)

    json_str = json.dumps(data, indent=2, default=str)
    filepath = path / f"{file_name}.json"

    with open(filepath, "w") as f:
        f.write(json_str)

    logger.info(f"📋 log written to {filepath}")