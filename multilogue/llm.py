"""Model clients and the resumable stage runner.

Every model call goes through a client with ``complete()`` / ``embed()``.
Every stage goes through :class:`StageRunner`, which keeps an append-only
checkpoint per stage, skips finished items on a rerun, and starts a stage
afresh if its prompt or model fingerprint changes. In *replay* mode nothing
is sent to a model.
"""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from .text import sha

QUOTA_MARKERS = ("insufficient_quota", "credit_balance", "billing_hard_limit")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReplayMiss(RuntimeError):
    pass


class ReplayClient:
    """Refuses every call: used to reproduce a run purely from its checkpoints."""

    def complete(self, stage, *a, **k):
        raise ReplayMiss(f"replay mode: no saved result for an item in stage '{stage}'")

    def embed(self, texts, model):
        raise ReplayMiss(f"replay mode: {len(texts)} phrases have no saved embedding")


class LogClient:
    """Answers each call from a saved llm_calls.jsonl, matching on prompt hash and model."""

    def __init__(self, log_path: Path):
        self.answers: dict[tuple, list[str]] = {}
        for line in Path(log_path).read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            self.answers.setdefault((r["input_hash"], r["model"]), []).append(r["response"])
        self._used: dict[tuple, int] = {}
        self._lock = threading.Lock()
        self.misses = 0

    def complete(self, stage, system, user, model, json_mode=False):
        key = (sha(system + "\n" + user), model)
        with self._lock:
            got = self.answers.get(key)
            if not got:
                self.misses += 1
                raise ReplayMiss(f"log replay: prompt not in the log (stage '{stage}')")
            i = self._used.get(key, 0)
            self._used[key] = i + 1
            return got[min(i, len(got) - 1)]

    def embed(self, texts, model):
        raise ReplayMiss(f"log replay: {len(texts)} phrases have no saved embedding")


class StageRunner:
    def __init__(
        self,
        checkpoint_dir: Path,
        log_dir: Path,
        max_workers: int = 8,
        replay: bool = False,
        allow_incomplete: bool = False,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.ckpt, self.logs = Path(checkpoint_dir), Path(log_dir)
        self.ckpt.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.replay = replay
        self.allow_incomplete = allow_incomplete
        self.sleep = sleep
        self.status: dict[str, dict] = {}

    def run(
        self,
        stage: str,
        items: Iterable,
        key_fn: Callable,
        work_fn: Callable,
        fingerprint_text: str,
        quiet: bool = False,
    ) -> dict:
        items = list(items)
        data_path, meta_path = self.ckpt / f"{stage}.jsonl", self.ckpt / f"{stage}.meta.json"
        fp = sha(fingerprint_text)
        if meta_path.exists() and json.loads(meta_path.read_text()).get("fingerprint") != fp:
            if self.replay:
                raise RuntimeError(
                    f"replay mode: the prompt/model for '{stage}' differs from the saved run "
                    "(fingerprint mismatch)."
                )
            stamp = int(time.time())
            for p in (data_path, meta_path):
                if p.exists():
                    p.rename(p.with_name(p.stem + f"_superseded_{stamp}" + p.suffix))
            if not quiet:
                print(
                    f"{stage}: prompt or model changed — starting afresh "
                    f"(old results kept as *_superseded_{stamp})."
                )
        if not self.replay:
            meta_path.write_text(json.dumps({"fingerprint": fp}))
        done: dict = {}
        if data_path.exists():
            for line in data_path.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                    done[r["key"]] = r["result"]
                except Exception:
                    pass
        pending = [u for u in items if key_fn(u) not in done]
        if not quiet:
            print(
                f"{stage}: {len(items)} items — {len(items) - len(pending)} already done, "
                f"{len(pending)} to run."
            )
        errors: list[dict] = []
        stop = threading.Event()
        if pending and not self.replay:
            lock = threading.Lock()

            def one(u):
                k = key_fn(u)
                for attempt in range(4):
                    if stop.is_set():
                        return k, None, "skipped"
                    try:
                        return k, work_fn(u), None
                    except ReplayMiss as e:
                        return k, None, str(e)
                    except Exception as e:  # noqa: BLE001
                        msg = str(e)
                        if any(m in msg for m in QUOTA_MARKERS):
                            stop.set()
                            return k, None, "OUT OF CREDIT: " + msg[:300]
                        if attempt < 3:
                            self.sleep(3 * 3**attempt)
                        else:
                            return k, None, msg[:400]

            with ThreadPoolExecutor(max_workers=self.max_workers) as ex, open(
                data_path, "a", encoding="utf-8"
            ) as fh:
                futs = [ex.submit(one, u) for u in pending]
                for i, f in enumerate(as_completed(futs), 1):
                    k, res, err = f.result()
                    with lock:
                        if res is not None:
                            done[k] = res
                            fh.write(
                                json.dumps({"key": k, "result": res}, ensure_ascii=False) + "\n"
                            )
                            fh.flush()
                        elif err != "skipped":
                            errors.append({"item": k, "error": err})
                    if not quiet and (i % 200 == 0 or i == len(pending)):
                        print(f"  {i}/{len(pending)}")
        missing = [key_fn(u) for u in items if key_fn(u) not in done]
        self.status[stage] = {
            "total": len(items),
            "complete": len(items) - len(missing),
            "missing": missing,
        }
        (self.logs / f"{stage}_errors.json").write_text(
            json.dumps(errors, indent=2, ensure_ascii=False)
        )
        if stop.is_set() and not quiet:
            print(f"{stage} STOPPED: the API account has run out of credit. Add credit and rerun.")
        if missing and not quiet:
            how = (
                "replay found no saved result for them"
                if self.replay
                else f"rerun (errors in logs/{stage}_errors.json)"
            )
            print(f"{stage} INCOMPLETE: {len(missing)}/{len(items)} still to do — {how}.")
        elif not quiet:
            print(f"{stage} COMPLETE.")
        return {k: done[k] for k in (key_fn(u) for u in items) if k in done}

    def require_complete(self, *stages: str) -> None:
        for s in stages:
            st = self.status.get(s)
            if st is None:
                raise RuntimeError(f"Stage '{s}' has not been run yet.")
            if st["missing"]:
                msg = f"{s} is incomplete ({st['complete']}/{st['total']})."
                if not self.allow_incomplete:
                    raise RuntimeError(
                        msg + " Rerun it, or set allow_incomplete=True for a preview only."
                    )
                print("WARNING:", msg, "Preview only — do not report these results.")
