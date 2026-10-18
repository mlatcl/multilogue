"""Study client resolution and FakeClient human-readable labels."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from multilogue.clients import FAKE_MODELS, resolve_study_client
from multilogue.cluster import coerce_topic_label, make_label_work
from multilogue.config import load_dotenv
from multilogue.dummy import FakeClient


def test_resolve_study_client_force_fake(monkeypatch):
    monkeypatch.setenv("MULTILOGUE_FORCE_FAKE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-should-be-ignored")
    client, models, kind = resolve_study_client()
    assert kind == "fake"
    assert isinstance(client, FakeClient)
    assert models == FAKE_MODELS


def test_resolve_study_client_no_silent_fake(monkeypatch):
    monkeypatch.delenv("MULTILOGUE_FORCE_FAKE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        "multilogue.config.load_dotenv", lambda *a, **k: None
    )
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        resolve_study_client(prefer_openai=True, allow_fake=False)


def test_load_dotenv_walks_up_from_subdir(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    nested = root / "notebooks"
    nested.mkdir(parents=True)
    (root / ".env").write_text("OPENAI_API_KEY=sk-from-parent\n", encoding="utf-8")
    monkeypatch.chdir(nested)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("MULTILOGUE_ROOT", raising=False)
    found = load_dotenv(override=True)
    assert found is not None
    assert found.resolve() == (root / ".env").resolve()
    assert os.environ.get("OPENAI_API_KEY") == "sk-from-parent"


def test_fake_cluster_label_summarises_exemplars():
    c = FakeClient()
    out = c.complete(
        "cluster_label",
        "label",
        "Summarise this soft topic…\n"
        "- Mehr sichere Fahrradstellplätze in der Innenstadt\n"
        "- Wichtige Stellplätze — leidenschaftlich gefordert\n",
        model="fake-small",
        json_mode=True,
    )
    d = json.loads(out)
    assert "Stellplätze" in d["label"] or "Fahrrad" in d["label"]
    assert not d["label"].startswith("topic ")
    assert d["description"]


def test_coerce_topic_label_rejects_junk_and_lists():
    examples = ["Mehr Stellplätze für Fahrräder bitte"]
    assert coerce_topic_label("?", examples=examples, cluster_id=0) != "?"
    assert "Stellplätze" in coerce_topic_label("?", examples=examples, cluster_id=0)
    assert "Stellplätze" in coerce_topic_label(
        ["positive", "neutral"], examples=examples, cluster_id=1
    )
    assert "→ ?" not in coerce_topic_label(
        "«Parent» → ?", examples=examples, cluster_id=2
    )


def test_make_label_work_falls_back_from_sentiment_list():
    class _ListClient:
        def complete(self, *a, **k):
            return json.dumps(
                {"label": ["positive", "negative"], "description": "x"}
            )

    work = make_label_work(
        _ListClient(),
        system="s",
        prompt_template="<<PHRASES>>",
        model="m",
    )
    out = work({"cluster": 0, "examples": ["safe bike parking near the station"]})
    assert "bike" in out["label"].lower() or "parking" in out["label"].lower()
    assert out["label"] not in {"positive", "negative", "?"}
