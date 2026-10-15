from pathlib import Path

import pytest

from multilogue.llm import ReplayClient, ReplayMiss, StageRunner


class FakeClient:
    def __init__(self):
        self.n = 0

    def complete(self, stage, system, user, model, json_mode=False):
        self.n += 1
        return f"ok-{user}"

    def embed(self, texts, model):
        return [[float(i)] * 3 for i, _ in enumerate(texts)]


def test_stage_runner_resume_and_fingerprint(tmp_path: Path):
    ckpt, logs = tmp_path / "ckpt", tmp_path / "logs"
    client = FakeClient()
    runner = StageRunner(ckpt, logs, max_workers=2, sleep=lambda _: None)
    items = [{"id": "a", "t": "one"}, {"id": "b", "t": "two"}]

    def work(u):
        return client.complete("s", "sys", u["t"], "m")

    r1 = runner.run("demo", items, lambda u: u["id"], work, "fp-v1", quiet=True)
    assert set(r1) == {"a", "b"}
    assert client.n == 2

    r2 = runner.run("demo", items, lambda u: u["id"], work, "fp-v1", quiet=True)
    assert client.n == 2  # resumed
    assert r2 == r1

    r3 = runner.run("demo", items, lambda u: u["id"], work, "fp-v2", quiet=True)
    assert client.n == 4  # superseded
    assert set(r3) == {"a", "b"}
    assert list(ckpt.glob("demo_superseded_*.jsonl"))


def test_replay_misses_without_checkpoint(tmp_path: Path):
    runner = StageRunner(tmp_path / "c", tmp_path / "l", replay=True, sleep=lambda _: None)
    with pytest.raises(RuntimeError, match="fingerprint|incomplete|no saved"):
        # no meta yet — run returns incomplete; require_complete raises
        runner.run(
            "x",
            [{"id": "1"}],
            lambda u: u["id"],
            lambda u: ReplayClient().complete("x", "", "", ""),
            "fp",
            quiet=True,
        )
        runner.require_complete("x")


def test_replay_client_raises():
    c = ReplayClient()
    with pytest.raises(ReplayMiss):
        c.complete("s", "a", "b", "m")
