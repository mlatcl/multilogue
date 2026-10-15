"""multilogue — reusable Access→Assess→Address dialogue methodology."""

from .llm import LogClient, ReplayClient, ReplayMiss, StageRunner
from .multiverse import enumerate_configurations, run_multiverse, variance_decomposition
from .protocols import LLMClient, Phrase, Unit
from .text import get_list, parse_json, quote_support, sha
from .weight import doc_profile, group_compare, kappa

__version__ = "0.1.0"

__all__ = [
    "LLMClient",
    "LogClient",
    "Phrase",
    "ReplayClient",
    "ReplayMiss",
    "StageRunner",
    "Unit",
    "doc_profile",
    "enumerate_configurations",
    "get_list",
    "group_compare",
    "kappa",
    "parse_json",
    "quote_support",
    "run_multiverse",
    "sha",
    "variance_decomposition",
    "__version__",
]
