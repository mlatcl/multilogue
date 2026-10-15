from pathlib import Path

import numpy as np
import pandas as pd

from multilogue.cluster import Embedder, frozen_or_new_assignments, resolve_lenses


class FakeEmbedClient:
    def embed(self, texts, model):
        # deterministic unit vectors from hash of text
        out = []
        for t in texts:
            rng = np.random.default_rng(abs(hash(t)) % (2**32))
            v = rng.normal(size=8).astype(np.float32)
            v /= np.linalg.norm(v)
            out.append(v.tolist())
        return out


def test_frozen_assignments_roundtrip(tmp_path: Path):
    phrases = pd.DataFrame(
        {
            "phrase_id": [f"p{i}" for i in range(20)],
            "phrase": [f"theme {i % 3} item {i}" for i in range(20)],
        }
    )
    emb = Embedder(tmp_path, FakeEmbedClient(), "fake-embed")
    E = emb(phrases.phrase.tolist())
    labels1, C1, frozen1 = frozen_or_new_assignments(phrases, E, k=3, seed=0, checkpoint_dir=tmp_path)
    assert not frozen1
    labels2, C2, frozen2 = frozen_or_new_assignments(phrases, E, k=3, seed=0, checkpoint_dir=tmp_path)
    assert frozen2
    assert np.array_equal(labels1, labels2)


def test_resolve_lenses_default():
    lens_runs = {"1": {"mapping": {"0": "A", "1": "B"}}}
    lens_of, edited = resolve_lenses(3, lens_runs)
    assert not edited
    assert lens_of[0] == "A"
    assert lens_of[2] == "Other"
