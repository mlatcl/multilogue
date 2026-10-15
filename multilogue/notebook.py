"""Colab / local notebook bootstrap for the pedagogical series."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def repo_root() -> Path:
    """Prefer the installed package location; else walk up for pyproject.toml."""
    try:
        import multilogue as _ml

        pkg = Path(_ml.__file__).resolve().parent.parent
        if (pkg / "pyproject.toml").is_file():
            return pkg
    except Exception:
        pass
    here = Path.cwd().resolve()
    for cand in (here, here.parent, *here.parents):
        if (cand / "pyproject.toml").is_file() and (cand / "multilogue").is_dir():
            return cand
    return here.parent if here.name == "notebooks" else here


def setup(*, figures_dir: str | Path = "outputs/notebook_figures") -> Path:
    """Prepare paths and matplotlib for notebooks; return figures directory.

    Call after installing / importing multilogue. Sets
    ``MULTILOGUE_ACCESS_YES=1`` so Access downloads do not block on stdin.
    Figures default under the *current working directory* when relative, so
    smoke tests and Colab keep outputs local to the session.
    """
    root = repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("MULTILOGUE_ACCESS_YES", "1")
    fig = Path(figures_dir)
    if not fig.is_absolute():
        fig = Path.cwd().resolve() / fig
    fig.mkdir(parents=True, exist_ok=True)
    try:
        import matplotlib

        matplotlib.rcParams.update(
            {
                "figure.facecolor": "white",
                "axes.facecolor": "white",
                "font.size": 10,
            }
        )
    except ImportError:
        pass
    return fig
