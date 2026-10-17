"""Harden-view helpers for soft MPPCA topics (CIP-0017)."""

import numpy as np
import pytest

from multilogue.mppca import (
    example_phrases_for_soft_topics,
    responsibilities_to_labels,
)


def test_map_labels_match_argmax():
    R = np.array([[0.1, 0.7, 0.2], [0.9, 0.05, 0.05]])
    assert list(responsibilities_to_labels(R)) == [1, 0]


def test_degenerate_rows_get_empty_label():
    R = np.array(
        [
            [0.0, 0.0, 0.0],
            [np.nan, np.nan, np.nan],
            [0.2, 0.5, 0.3],
        ]
    )
    labels = responsibilities_to_labels(R)
    assert labels[0] == -1
    assert labels[1] == -1
    assert labels[2] == 1


def test_exemplars_deterministic_under_seed():
    phrases = [f"p{i}" for i in range(30)]
    rng = np.random.default_rng(0)
    logits = rng.normal(size=(30, 3))
    R = np.exp(logits - logits.max(axis=1, keepdims=True))
    R /= R.sum(axis=1, keepdims=True)
    a = example_phrases_for_soft_topics(phrases, R, n_top=5, n_sample=3, seed=7)
    b = example_phrases_for_soft_topics(phrases, R, n_top=5, n_sample=3, seed=7)
    assert a == b
    assert len(a) == 3
    for unit in a:
        assert "examples" in unit and "key" in unit
        assert unit["examples"]  # non-empty when mass present


def test_exemplars_empty_component():
    phrases = ["a", "b", "c"]
    R = np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
    units = example_phrases_for_soft_topics(phrases, R, n_top=2, n_sample=0, seed=0)
    assert units[1]["examples"] == []
    assert units[0]["examples"][0] in phrases


def test_exemplars_length_mismatch():
    with pytest.raises(ValueError, match="phrases length"):
        example_phrases_for_soft_topics(["a"], np.eye(2), seed=0)
