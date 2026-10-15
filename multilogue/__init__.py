"""multilogue — reusable Access→Assess→Address dialogue methodology."""

from .llm import LogClient, ReplayClient, ReplayMiss, StageRunner
from .protocols import LLMClient, Phrase, Unit
from .text import get_list, parse_json, quote_support, sha

__version__ = "0.1.0"

__all__ = [
    "LLMClient",
    "LogClient",
    "Phrase",
    "ReplayClient",
    "ReplayMiss",
    "StageRunner",
    "Unit",
    "get_list",
    "parse_json",
    "quote_support",
    "sha",
    "__version__",
]
