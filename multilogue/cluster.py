"""Embed phrases, freeze k-means assignments, blind labels, framing lenses."""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import yaml
from sklearn.cluster import KMeans

from .text import get_list, parse_json, sha


class Embedder:
    """Embeddings cached on disk by phrase (lower-cased, stripped)."""

    def __init__(self, checkpoint_dir: Path, client, model: str):
        self.client = client
        self.model = model
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.vec_path = self.checkpoint_dir / f"embeddings_{model}.npy"
        self.idx_path = self.checkpoint_dir / f"embeddings_{model}_index.json"
        if self.vec_path.exists():
            self.vecs = np.load(self.vec_path)
        else:
            self.vecs = np.zeros((0, 0), np.float32)
        self.idx = json.loads(self.idx_path.read_text()) if self.idx_path.exists() else []
        self.pos = {h: i for i, h in enumerate(self.idx)}

    def __call__(self, texts: list[str]) -> np.ndarray:
        texts = [str(t) for t in texts]
        hashes = [sha(t.lower().strip()) for t in texts]
        if len(self.idx) != len(self.vecs):
            self.vecs, self.idx, self.pos = np.zeros((0, 0), np.float32), [], {}
        todo: dict[str, str] = {}
        for h, t in zip(hashes, texts):
            if h not in self.pos and h not in todo:
                todo[h] = t
        items = sorted(todo.items())
        for i in range(0, len(items), 256):
            batch = items[i : i + 256]
            vecs = np.array(
                self.client.embed([t for _, t in batch], self.model), dtype=np.float32
            )
            if len(vecs) != len(batch):
                raise RuntimeError(
                    f"The embedding service returned {len(vecs)} vectors for {len(batch)} phrases."
                )
            self.vecs = vecs if self.vecs.size == 0 else np.vstack([self.vecs, vecs])
            for h, _ in batch:
                self.pos[h] = len(self.idx)
                self.idx.append(h)
            np.save(self.vec_path, self.vecs)
            self.idx_path.write_text(json.dumps(self.idx))
        missing = [h for h in hashes if h not in self.pos]
        if missing:
            raise RuntimeError(
                f"{len(missing)} phrases still have no embedding (first: {missing[0][:12]})."
            )
        m = self.vecs[[self.pos[h] for h in hashes]]
        return m / np.linalg.norm(m, axis=1, keepdims=True)


def kmeans(X: np.ndarray, k: int, seed: int):
    km = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(X)
    C = km.cluster_centers_ / np.linalg.norm(km.cluster_centers_, axis=1, keepdims=True)
    return km.labels_, C


def frozen_or_new_assignments(
    phrases: pd.DataFrame,
    E: np.ndarray,
    k: int,
    seed: int,
    checkpoint_dir: Path,
    *,
    phrase_id_col: str = "phrase_id",
    replay: bool = False,
) -> tuple[np.ndarray, np.ndarray, bool]:
    """Load saved cluster assignments when phrase ids match; otherwise cluster and save."""
    checkpoint_dir = Path(checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    path = checkpoint_dir / f"cluster_assignments_k{k}.csv"
    if path.exists():
        saved = pd.read_csv(path)
        if set(saved.phrase_id) == set(phrases[phrase_id_col]) and saved.cluster.nunique() == k:
            labels = (
                phrases[phrase_id_col]
                .map(dict(zip(saved.phrase_id, saved.cluster)))
                .to_numpy()
                .astype(int)
            )
            C = np.vstack([E[labels == c].mean(0) for c in range(k)])
            C = C / np.linalg.norm(C, axis=1, keepdims=True)
            return labels, C, True
    if replay:
        raise RuntimeError(
            f"replay mode: no saved cluster assignments matching these phrases ({path.name})."
        )
    labels, C = kmeans(E, k, seed)
    pd.DataFrame({"phrase_id": phrases[phrase_id_col], "cluster": labels}).to_csv(
        path, index=False
    )
    ex_path = checkpoint_dir / f"cluster_examples_k{k}.json"
    if ex_path.exists():
        ex_path.unlink()
    return labels, C, False


def example_phrases_for_clusters(
    phrases: pd.DataFrame,
    k: int,
    seed: int,
    *,
    phrase_col: str = "phrase",
    n_top: int = 12,
    n_sample: int = 6,
) -> list[dict[str, Any]]:
    """Build labelling units (examples + stable key) for each cluster."""
    cluster_units = []
    for c in range(k):
        sub = phrases[phrases.cluster == c].sort_values("centroid_sim", ascending=False)
        ex = sub[phrase_col].head(n_top).tolist()
        rest = sub[phrase_col].iloc[n_top:]
        if len(rest):
            ex += rest.sample(n=min(n_sample, len(rest)), random_state=seed).tolist()
        key = str(c) + "|" + sha("|".join(ex))[:10]
        cluster_units.append({"cluster": c, "examples": ex, "key": key})
    return cluster_units


def make_label_work(
    client,
    *,
    system: str,
    prompt_template: str,
    model: str,
    phrases_placeholder: str = "<<PHRASES>>",
) -> Callable[[dict], dict]:
    def work(cu: dict) -> dict:
        user = prompt_template.replace(
            phrases_placeholder, "\n".join(f"- {p}" for p in cu["examples"])
        )
        d = parse_json(
            client.complete("cluster_label", system, user, model=model, json_mode=True)
        )
        return {
            "label": str(d.get("label", f"cluster {cu['cluster']}"))[:80],
            "description": str(d.get("description", "")),
        }

    return work


def make_lens_work(
    client,
    *,
    system: str,
    prompt_template: str,
    cluster_description: str,
    model: str,
    k: int,
    clusters_placeholder: str = "<<CLUSTERS>>",
) -> Callable[[int], dict]:
    def work(run_number: int) -> dict:
        user = (
            prompt_template.replace(clusters_placeholder, cluster_description)
            + f"\n\n(run {run_number})"
        )
        d = parse_json(client.complete("lens", system, user, model=model, json_mode=True))
        mapping, descs = {}, {}
        for L in get_list(d, "lenses"):
            name = str(L.get("name", "")).strip() or "Unnamed"
            descs[name] = str(L.get("description", ""))
            for c in L.get("clusters", []) or []:
                m = re.search(r"\d+", str(c))
                if m and int(m.group()) < k:
                    mapping.setdefault(int(m.group()), name)
        for c in range(k):
            mapping.setdefault(c, "Other")
        return {"mapping": {str(a): b for a, b in mapping.items()}, "descriptions": descs}

    return work


def resolve_lenses(
    k: int,
    lens_runs: dict,
    *,
    edited_mapping_path: str | Path | None = None,
) -> tuple[dict[int, str], bool]:
    """Lens of each cluster: researcher-edited YAML if provided, else lens run 1."""
    if edited_mapping_path:
        edited = yaml.safe_load(Path(edited_mapping_path).read_text(encoding="utf-8"))
        lens_of = {int(c): L for L, cs in edited.items() for c in cs}
        is_edited = True
    else:
        proposed = lens_runs.get("1", {"mapping": {str(c): "Other" for c in range(k)}})
        lens_of = {int(c): L for c, L in proposed["mapping"].items()}
        is_edited = False
    for c in range(k):
        lens_of.setdefault(c, "Other")
    return lens_of, is_edited


def lens_proposal_yaml(lens_runs: dict, names: dict[int, str]) -> str:
    by: dict[str, list[int]] = defaultdict(list)
    for c, L in lens_runs.get("1", {}).get("mapping", {}).items():
        by[L].append(int(c))
    lines = ["# Edit and point clustering.lens_mapping at this file."]
    for L, cs in sorted(by.items()):
        lines.append(
            f"{json.dumps(L)}: {sorted(cs)}   # "
            + "; ".join(names[c] for c in sorted(cs))[:150]
        )
    return "\n".join(lines) + "\n"
