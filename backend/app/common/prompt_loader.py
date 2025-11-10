"""
Prompt loading utilities for managing external prompt templates.
"""

import os
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class PromptLoader:
    """Utility for loading and formatting prompt templates from files."""

    def __init__(self, prompts_dir: Optional[Path] = None):
        """Initialize with prompts directory."""
        if prompts_dir is None:
            # Default to prompts directory relative to app root
            current_dir = Path(__file__).parent.parent  # Go up to app/
            prompts_dir = current_dir / "prompts"

        self.prompts_dir = Path(prompts_dir)
        self._cache: Dict[str, str] = {}

    def load_prompt(self, prompt_path: str, use_cache: bool = True) -> str:
        """
        Load a prompt template from file.

        Args:
            prompt_path: Path relative to prompts directory
            use_cache: Whether to cache the loaded prompt

        Returns:
            The raw prompt template string

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        if use_cache and prompt_path in self._cache:
            return self._cache[prompt_path]

        full_path = self.prompts_dir / prompt_path

        if not full_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {full_path}")

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if use_cache:
                self._cache[prompt_path] = content

            logger.debug(f"📄 Loaded prompt: {prompt_path}")
            return content

        except Exception as e:
            logger.error(f"❌ Failed to load prompt {prompt_path}: {e}")
            raise

    def format_prompt(self, prompt_path: str, **kwargs) -> str:
        """
        Load and format a prompt template with provided variables.

        Args:
            prompt_path: Path to prompt file
            **kwargs: Variables to substitute in the template

        Returns:
            Formatted prompt string
        """
        template = self.load_prompt(prompt_path)

        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"❌ Missing variable for prompt {prompt_path}: {e}")
            raise ValueError(f"Missing required variable: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to format prompt {prompt_path}: {e}")
            raise

    def clear_cache(self):
        """Clear the prompt cache."""
        self._cache.clear()
        logger.debug("🗑️ Prompt cache cleared")

    def list_prompts(self, pattern: str = "*.txt") -> list[Path]:
        """List available prompt files matching pattern."""
        if not self.prompts_dir.exists():
            return []

        return list(self.prompts_dir.rglob(pattern))


# Global prompt loader instance
prompt_loader = PromptLoader()


def load_prompt(prompt_path: str) -> str:
    """Convenience function to load a prompt."""
    return prompt_loader.load_prompt(prompt_path)


def format_prompt(prompt_path: str, **kwargs) -> str:
    """Convenience function to load and format a prompt."""
    return prompt_loader.format_prompt(prompt_path, **kwargs)
