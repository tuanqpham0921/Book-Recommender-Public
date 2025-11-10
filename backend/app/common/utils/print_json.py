import json

from enum import Enum
from typing import Any
from pydantic import BaseModel


def to_jsonable(obj: Any):
    """Recursively convert objects (Pydantic, Enum, dataclass, etc.) to JSON-friendly types."""
    if isinstance(obj, BaseModel):
        return {k: to_jsonable(v) for k, v in obj.model_dump().items()}
    elif isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, list):
        return [to_jsonable(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    elif hasattr(obj, "__dict__") and not isinstance(obj, type):
        # Fallback for arbitrary classes
        return {k: to_jsonable(v) for k, v in vars(obj).items()}
    else:
        return obj

def print_json(data: Any, name: str | None = None, indent: int = 2, color: bool = True):
    """Pretty-print JSON data with an optional label."""
    serializable = to_jsonable(data)
    output = json.dumps(serializable, indent=indent, ensure_ascii=False)

    if name:
        print(f"\n********** {name} **************")

    if color:
        try:
            from pygments import highlight, lexers, formatters
            output = highlight(output, lexers.JsonLexer(), formatters.TerminalFormatter())
        except ImportError:
            pass

    print(output)
    if name:
        print("******************************\n")
        
