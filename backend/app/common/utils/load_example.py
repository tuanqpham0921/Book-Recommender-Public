import os
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def _load_prompt_examples(
    file: str, path: str = settings.app.EXAMPLE_PROMPT_DIR
) -> dict:
    """Load JSON examples for strategies nodes."""
    result = []
    json_path = os.path.join(path, file + ".json")
    if file and os.path.exists(json_path):
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
