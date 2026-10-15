"""Access: switchable public-corpus loaders → Unit lists (pods-style).

Example::

    from multilogue.access import load, list_sources

    for name in list_sources():
        print(name)
    bundle = load("synthetic")
    # or: load("polis", conversation="vtaiwan.uberx", max_units=200)

Downloads are cached under ``MULTILOGUE_DATAPATH`` or ``~/.cache/multilogue``.
Set ``MULTILOGUE_ACCESS_YES=1`` to skip interactive licence prompts.
"""
from __future__ import annotations

from . import datasets
from .datasets import get_resource, list_sources, load, load_units
from .download import (
    DATAPATH,
    clear_cache,
    override_manual_authorize,
    set_datapath,
)

# Named loaders for direct import / discovery
synthetic = datasets.synthetic
polis = datasets.polis
gdn_cc = datasets.gdn_cc
cdcp = datasets.cdcp
cimt = datasets.cimt
decidim = datasets.decidim

__all__ = [
    "DATAPATH",
    "cdcp",
    "cimt",
    "clear_cache",
    "datasets",
    "decidim",
    "gdn_cc",
    "get_resource",
    "list_sources",
    "load",
    "load_units",
    "override_manual_authorize",
    "polis",
    "set_datapath",
    "synthetic",
]
