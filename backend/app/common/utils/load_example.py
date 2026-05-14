import json
import logging
from pathlib import Path

from config import FilesLocationConstants

logger = logging.getLogger(__name__)


def _load_prompt_examples(
    file: str, path: Path = FilesLocationConstants.EXAMPLE_PROMPT_DIR
) -> dict:
    """Load JSON examples for strategies nodes."""
    result = []
    json_path = path / f"{file}.json"
    if file and json_path.exists():
        with open(json_path, "r") as f:
            result = json.load(f)

    return result


def _examples(schema: dict, model_type: type) -> dict:
    schema.setdefault("examples", [])
    schema["examples"].extend(_load_prompt_examples(file=model_type.__qualname__))
    logger.info(
        f"📋 Loaded {len(schema['examples']):>3} prompt examples from {model_type.__qualname__}"
    )

    return schema
