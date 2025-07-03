"""
Prompt templates and engineering for Claude AI integration.

This module contains optimized prompts for various game situations
and decision types.
"""

from .prompt_templates import (
    BATCH_DECISION_PROMPT,
    META_ANALYSIS_PROMPT,
    STRATEGY_PROMPT,
    SYSTEM_PROMPT,
)

__all__ = [
    "SYSTEM_PROMPT",
    "STRATEGY_PROMPT",
    "META_ANALYSIS_PROMPT",
    "BATCH_DECISION_PROMPT",
]
