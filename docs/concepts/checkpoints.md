# Checkpoints and replay

Every model stage should go through [`StageRunner`](../api/llm.md).

## Behaviour

1. **Fingerprint** — a string you supply (prompt + model + version). Stored in stage meta.
2. **Resume** — items already keyed in the JSONL checkpoint are skipped.
3. **Supersede** — if the fingerprint changes, the stage starts clean.
4. **Replay** — `replay=True` refuses live calls; use checkpoints / logs only.

```python
from pathlib import Path
from multilogue.llm import StageRunner
from multilogue.dummy import FakeClient
from multilogue.extract import make_extract_work

client = FakeClient()
runner = StageRunner(Path("ckpt"), Path("logs"), max_workers=4, sleep=lambda _: None)
work = make_extract_work(
    client, kind="concern", system="s", user_for_unit=lambda u: u["text"],
    model="fake-small", sentinel="NO_CONCERN",
)
# results = runner.run("extract_concern", units, lambda u: u["unit_id"], work, "extract|concern|v1")
```

## Why this shape?

Dialogue pipelines are expensive and iterative. Append-only checkpoints make "rerun after lunch" and "CI without keys" the same mechanism. Consumers wrap their own clients (`OpenAIClient`, `LiteLLMClient`) behind the same `complete` / `embed` protocol.
