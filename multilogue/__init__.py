"""multilogue — reusable Access→Assess→Address dialogue methodology."""

from . import access
from .access import list_sources, load, load_units
from .dummy import FakeClient, make_units
from .experiment import run_validation_experiment
from .llm import LogClient, ReplayClient, ReplayMiss, StageRunner
from .multiverse import enumerate_configurations, run_multiverse, variance_decomposition
from .protocols import LLMClient, Phrase, Unit
from .text import get_list, parse_json, quote_support, sha
from .weight import doc_profile, group_compare, kappa, soft_doc_profiles, soft_group_compare

__version__ = "0.1.0"

__all__ = [
    "FakeClient",
    "LLMClient",
    "LogClient",
    "Phrase",
    "ReplayClient",
    "ReplayMiss",
    "StageRunner",
    "Unit",
    "access",
    "doc_profile",
    "enumerate_configurations",
    "get_list",
    "group_compare",
    "kappa",
    "list_sources",
    "load",
    "load_units",
    "make_units",
    "parse_json",
    "quote_support",
    "run_multiverse",
    "run_validation_experiment",
    "sha",
    "soft_doc_profiles",
    "soft_group_compare",
    "variance_decomposition",
    "__version__",
]
