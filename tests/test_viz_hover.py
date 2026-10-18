"""Hover text helpers and optional Plotly Assess U_q path."""

from __future__ import annotations

import numpy as np
import pytest

from multilogue.mppca import mppca_fit
from multilogue.subject_grain_shell import SubjectGrainShell
from multilogue.viz import (
    hover_phrase_texts,
    plotly_available,
    topic_fit_view,
)


def test_hover_phrase_texts_truncates_and_escapes():
    texts = hover_phrase_texts(
        ["  hello   world  ", "a" * 300, "<b>x</b>"],
        max_chars=20,
    )
    assert texts[0] == "hello world"
    assert texts[1].endswith("…")
    assert len(texts[1]) == 20
    assert "&lt;b&gt;" in texts[2]
    assert hover_phrase_texts(None) == []


def test_topic_fit_view_matplotlib_export_ignores_plotly(tmp_path):
    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 8))
    fit = mppca_fit(X, k=2, sigma2=0.12, seed=0, max_iter=15)
    phrases = [f"phrase {i} about civic life" for i in range(len(X))]
    out = topic_fit_view(
        X,
        fit["responsibilities"],
        fit["means"],
        focus=0,
        component_fits=fit["component_fits"],
        sigma2=fit["sigma2"],
        phrases=phrases,
        interactive=True,
        path=tmp_path / "uq.png",
        show=False,
    )
    assert out == tmp_path / "uq.png"
    assert (tmp_path / "uq.png").exists()


@pytest.mark.skipif(not plotly_available(), reason="plotly not installed")
def test_topic_fit_view_plotly_hover_aligned():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(30, 6))
    fit = mppca_fit(X, k=2, sigma2=0.1, seed=1, max_iter=12)
    phrases = [f"paragraph number {i}" for i in range(len(X))]
    fig = topic_fit_view(
        X,
        fit["responsibilities"],
        fit["means"],
        focus=0,
        component_fits=fit["component_fits"],
        sigma2=fit["sigma2"],
        phrases=phrases,
        interactive=True,
        show=False,
    )
    assert fig is not None
    # First trace is the phrase scatter with hover text
    scatter = fig.data[0]
    assert len(scatter.text) == len(X)
    assert "paragraph number" in str(scatter.text[0])


@pytest.mark.skipif(not plotly_available(), reason="plotly not installed")
def test_shell_fit_view_plotly_uses_phrase_column():
    rng = np.random.default_rng(2)
    X = rng.normal(size=(25, 6))
    fit = mppca_fit(X, k=2, sigma2=0.1, seed=2, max_iter=12)
    phrases = [f"unit-{i}: longer civic paragraph text" for i in range(len(X))]
    shell = SubjectGrainShell(X, fit, phrases, seed=2)
    fig = shell.fit_view(focus=0, show=False, interactive=True)
    assert fig is not None
    assert "longer civic" in str(fig.data[0].text[0])
