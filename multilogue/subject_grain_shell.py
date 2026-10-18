"""ipywidgets subject-grain interaction shell (CIP-0009 Layer B).

``SubjectGrainShell`` is a pure state machine over Layer A helpers
(:mod:`multilogue.subject_grain`). The optional widget surface is built
only when ``ipywidgets`` is installed — importing this module (and the
rest of multilogue) must succeed without it.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import numpy as np
import pandas as pd

from .config import dump_json
from .mppca import example_phrases_for_soft_topics
from .subject_grain import (
    lock_subject_grain,
    propose_merge,
    propose_split,
    subject_grain_diagnostics,
    topic_catalogue,
)

LabelWork = Callable[[dict], dict]


def ipywidgets_available() -> bool:
    try:
        import ipywidgets  # noqa: F401
    except ImportError:
        return False
    return True


def _snapshot_fit(fit: dict[str, Any]) -> dict[str, Any]:
    """Deep-ish copy of an MPPCA-style fit dict (arrays duplicated)."""
    out: dict[str, Any] = {}
    for key, val in fit.items():
        if isinstance(val, np.ndarray):
            out[key] = val.copy()
        elif key == "component_fits" and isinstance(val, list):
            out[key] = deepcopy(val)
        else:
            out[key] = deepcopy(val) if isinstance(val, (dict, list)) else val
    return out


def is_placeholder_label(name: str | None, topic_id: int | None = None) -> bool:
    """True for unset / index-only names (not yet LLM-labelled)."""
    if name is None:
        return True
    s = str(name).strip()
    if not s or s == "unnamed / stale":
        return True
    if topic_id is not None and s == f"topic {int(topic_id)}":
        return True
    if s.endswith(" → ?") or " → ?" in s:
        return True
    if "→ (unnamed)" in s or s.endswith("(unnamed)"):
        return True
    if s in {"?", "…", "..."}:
        return True
    return False


class SubjectGrainShell:
    """Assess controller: merge / split / undo / name-dirty / lock.

    Geometry updates never call the LLM. Labelling runs only via
    :meth:`name_dirty` / :meth:`name_catalogue` (or when
    ``name_after_action=True`` / ``name_initial=True``).
    """

    def __init__(
        self,
        X: np.ndarray,
        fit: dict[str, Any],
        phrases: Sequence[Any] | pd.DataFrame,
        *,
        labels: Optional[dict[int, str]] = None,
        descriptions: Optional[dict[int, str]] = None,
        phrase_col: str = "phrase",
        seed: int = 0,
        label_work: LabelWork | None = None,
        label_client: Any | None = None,
        label_system: str | None = None,
        label_prompt: str | None = None,
        label_model: str | None = None,
        label_model_choices: Sequence[str] | None = None,
        name_after_action: bool = False,
        name_initial: bool = False,
        k_multiverse: str | Sequence[int] | None = "hold",
    ) -> None:
        from .clients import (
            LABEL_MODEL_CHOICES,
            TOPIC_LABEL_PROMPT,
            TOPIC_LABEL_SYSTEM,
        )

        self.X = np.asarray(X, dtype=float)
        self.fit = _snapshot_fit(fit)
        if self.X.shape[0] != self.fit["responsibilities"].shape[0]:
            raise ValueError("X rows must match responsibilities rows")
        if isinstance(phrases, pd.DataFrame):
            self._phrases_df = phrases
            self._phrase_list = phrases[phrase_col].astype(str).tolist()
        else:
            self._phrases_df = None
            self._phrase_list = [str(p) for p in phrases]
        if len(self._phrase_list) != self.X.shape[0]:
            raise ValueError("phrases length must match X rows")
        self.phrase_col = phrase_col
        self.seed = int(seed)
        self.label_client = label_client
        self.label_system = label_system or TOPIC_LABEL_SYSTEM
        self.label_prompt = label_prompt or TOPIC_LABEL_PROMPT
        self.label_model = label_model or "gpt-4.1-mini"
        self.label_model_choices = list(
            label_model_choices or LABEL_MODEL_CHOICES
        )
        if self.label_model not in self.label_model_choices:
            self.label_model_choices = [self.label_model, *self.label_model_choices]
        self.label_work = label_work
        if self.label_work is None and self.label_client is not None:
            self.rebuild_label_work()
        elif self.label_work is not None:
            # Mirror make_label_work.config onto shell fields (UI + rebuild)
            cfg = getattr(self.label_work, "config", None)
            if isinstance(cfg, dict):
                self.label_prompt = str(cfg.get("prompt_template") or self.label_prompt)
                self.label_model = str(cfg.get("model") or self.label_model)
                self.label_system = str(cfg.get("system") or self.label_system)
                if self.label_client is None:
                    self.label_client = getattr(self.label_work, "client", None)
            if self.label_model not in self.label_model_choices:
                self.label_model_choices = [
                    self.label_model,
                    *self.label_model_choices,
                ]
        self.name_after_action = bool(name_after_action)
        self.k_multiverse = k_multiverse
        k = int(self.fit["k"])
        self.labels: dict[int, str] = (
            {int(i): str(labels[i]) for i in labels} if labels else {}
        )
        self.descriptions: dict[int, str] = (
            {int(i): str(descriptions[i]) for i in descriptions}
            if descriptions
            else {}
        )
        self.dirty: set[int] = set()
        self.action_history: list[dict[str, Any]] = []
        self._undo_stack: list[dict[str, Any]] = []
        self.locked: dict[str, Any] | None = None
        # topic_id → original parent LLM label (lineage after a split)
        self.parent_of: dict[int, str] = {}
        # Pending split proposal (geometry applied; semantics not yet accepted)
        self.pending_proposal: dict[str, Any] | None = None
        self.last_naming_errors: list[str] = []
        # Ensure every leaf has a display name
        for j in range(k):
            self.labels.setdefault(j, f"topic {j}")
        # Placeholders start dirty so "Name dirty topics" / name_catalogue is obvious
        for j in range(k):
            if is_placeholder_label(self.labels.get(j), j):
                self.dirty.add(j)
        if name_initial:
            if self.label_work is None:
                raise ValueError(
                    "name_initial=True requires label_work= or label_client="
                )
            self.name_catalogue()

    def rebuild_label_work(
        self,
        *,
        prompt: str | None = None,
        model: str | None = None,
        system: str | None = None,
    ) -> LabelWork:
        """Update prompt / model on ``label_work`` (mutable config or rebuild)."""
        from .cluster import make_label_work

        if prompt is not None:
            self.label_prompt = str(prompt)
        if model is not None:
            self.label_model = str(model)
            if self.label_model not in self.label_model_choices:
                self.label_model_choices = [
                    self.label_model,
                    *self.label_model_choices,
                ]
        if system is not None:
            self.label_system = str(system)
        if "<<PHRASES>>" not in self.label_prompt:
            raise ValueError(
                "label prompt must contain the <<PHRASES>> placeholder"
            )
        # Prefer in-place update so an existing make_label_work closure
        # (even without label_client=) picks up the new prompt immediately.
        cfg = getattr(self.label_work, "config", None) if self.label_work else None
        if isinstance(cfg, dict):
            cfg["prompt_template"] = self.label_prompt
            cfg["model"] = self.label_model
            cfg["system"] = self.label_system
            client = getattr(self.label_work, "client", None)
            if client is not None and self.label_client is None:
                self.label_client = client
            return self.label_work  # type: ignore[return-value]
        client = self.label_client
        if client is None:
            raise ValueError(
                "rebuild_label_work requires label_client= at construction "
                "or a label_work built by make_label_work"
            )
        self.label_work = make_label_work(
            client,
            system=self.label_system,
            prompt_template=self.label_prompt,
            model=self.label_model,
        )
        return self.label_work

    def label_client_kind(self) -> str:
        """``openai`` / ``fake`` / ``unknown`` — for UI warnings."""
        c = self.label_client
        if c is None:
            c = getattr(self.label_work, "client", None)
        if c is None:
            return "none"
        name = type(c).__name__.lower()
        if "fake" in name:
            return "fake"
        if "openai" in name:
            return "openai"
        return name or "unknown"

    def label_config_summary(self) -> str:
        """Short status line: client + model + prompt fingerprint in use."""
        cfg = getattr(self.label_work, "config", None) if self.label_work else None
        prompt = (
            str(cfg.get("prompt_template", ""))
            if isinstance(cfg, dict)
            else self.label_prompt
        )
        model = (
            str(cfg.get("model", ""))
            if isinstance(cfg, dict)
            else self.label_model
        )
        flat = " ".join(prompt.split())
        preview = flat if len(flat) <= 72 else flat[:69] + "…"
        return (
            f"client={self.label_client_kind()} · model={model} · prompt=«{preview}»"
        )

    # ------------------------------------------------------------------ state
    @property
    def k(self) -> int:
        return int(self.fit["k"])

    @property
    def responsibilities(self) -> np.ndarray:
        return np.asarray(self.fit["responsibilities"], dtype=float)

    @property
    def means(self) -> np.ndarray:
        return np.asarray(self.fit["means"], dtype=float)

    def topic_ids(self) -> list[int]:
        return list(range(self.k))

    def proposed_topic_ids(self) -> list[int]:
        if not self.pending_proposal:
            return []
        return [int(c) for c in self.pending_proposal.get("children") or ()]

    def catalogue(self) -> pd.DataFrame:
        label_seq = [self.labels.get(j, f"topic {j}") for j in range(self.k)]
        src = self._phrases_df if self._phrases_df is not None else self._phrase_list
        return topic_catalogue(
            src,
            self.responsibilities,
            labels=label_seq,
            dirty=sorted(self.dirty),
            phrase_col=self.phrase_col,
            seed=self.seed,
            parent_labels=self.parent_of,
            proposed=self.proposed_topic_ids(),
        )

    def diagnostics(self) -> dict[str, Any]:
        return subject_grain_diagnostics(self.fit)

    def _push_undo(self) -> None:
        self._undo_stack.append(
            {
                "fit": _snapshot_fit(self.fit),
                "labels": dict(self.labels),
                "descriptions": dict(self.descriptions),
                "dirty": set(self.dirty),
                "action_history": list(self.action_history),
                "locked": None if self.locked is None else dict(self.locked),
                "parent_of": dict(self.parent_of),
                "pending_proposal": (
                    None
                    if self.pending_proposal is None
                    else deepcopy(self.pending_proposal)
                ),
            }
        )

    def _maybe_name_after(self) -> None:
        if self.name_after_action and self.dirty and self.label_work is not None:
            self.name_dirty()

    def merge(
        self,
        topic_ids: Sequence[int],
        *,
        refit: bool = True,
        name_merged: bool | None = None,
    ) -> dict[str, Any]:
        """Propose a merge: geometry updates; leaf stays *proposed* until accept.

        Snapshots the source catalogue labels / local PPCA fits so
        :meth:`fit_view` can draw the originals inside the merged ``U_q``.
        """
        ids = sorted({int(i) for i in topic_ids})
        if len(ids) < 2:
            raise ValueError("merge needs at least two topic ids")
        if self.pending_proposal is not None:
            raise ValueError(
                "Accept or reject the pending proposal before another merge/split"
            )
        cfs = list(self.fit.get("component_fits") or [])
        sources = []
        for i in ids:
            src: dict[str, Any] = {
                "topic_id": i,
                "label": self.labels.get(i, f"topic {i}"),
                "description": self.descriptions.get(i, ""),
            }
            if 0 <= i < len(cfs) and cfs[i] is not None:
                src["component_fit"] = deepcopy(cfs[i])
            sources.append(src)
        source_labels = [str(s["label"]) for s in sources]
        self._push_undo()
        out = propose_merge(
            self.X, self.fit, ids, refit=refit, seed=self.seed
        )
        old_to_new: dict[int, int] = out["old_to_new"]
        new_labels: dict[int, str] = {}
        new_desc: dict[int, str] = {}
        for old, new in old_to_new.items():
            if old in self.labels:
                new_labels[new] = self.labels[old]
            if old in self.descriptions:
                new_desc[new] = self.descriptions[old]
        merged_id = int(out["dirty"][0])
        new_labels[merged_id] = " + ".join(source_labels) + " → (unnamed)"
        new_parent_of = {
            old_to_new[old]: pl
            for old, pl in self.parent_of.items()
            if old in old_to_new
        }
        R_old = self.responsibilities
        merged_mass = R_old[:, ids].sum(axis=1)
        self.fit = out["fit"]
        self.labels = new_labels
        self.descriptions = new_desc
        self.parent_of = new_parent_of
        remapped_dirty = {old_to_new[d] for d in self.dirty if d in old_to_new}
        remapped_dirty.update(out["dirty"])
        self.dirty = remapped_dirty
        self.action_history.append(out["history_entry"])
        self.locked = None
        new_cfs = list(self.fit.get("component_fits") or [])
        merged_cf = (
            deepcopy(new_cfs[merged_id])
            if 0 <= merged_id < len(new_cfs)
            else None
        )
        self.pending_proposal = {
            "kind": "merge",
            "sources": sources,
            "source_ids": ids,
            "source_labels": source_labels,
            "merged_id": merged_id,
            "merged_mass": np.asarray(merged_mass, dtype=float).copy(),
            "merged_component_fit": merged_cf,
            "named": False,
            "accepted": False,
        }
        do_name = (
            bool(name_merged)
            if name_merged is not None
            else (self.label_work is not None)
        )
        if do_name and self.label_work is not None:
            saved = set(self.dirty)
            self.dirty = {merged_id}
            try:
                self.name_dirty()
            finally:
                self.dirty = (saved - {merged_id}) | self.dirty
            if self.pending_proposal is not None:
                self.pending_proposal["named"] = merged_id not in self.dirty
        elif self.name_after_action:
            self._maybe_name_after()
            if self.pending_proposal is not None:
                self.pending_proposal["named"] = merged_id not in self.dirty
        return out

    def merge_preview_payload(
        self, topic_ids: Sequence[int], *, refit: bool = True
    ) -> dict[str, Any] | None:
        """Dry-run merge geometry for a live U_q preview (does not mutate state)."""
        ids = sorted({int(i) for i in topic_ids})
        if len(ids) < 2:
            return None
        cfs = list(self.fit.get("component_fits") or [])
        sources = []
        source_labels = []
        for i in ids:
            lab = self.labels.get(i, f"topic {i}")
            source_labels.append(str(lab))
            entry: dict[str, Any] = {"topic_id": i, "label": lab}
            if 0 <= i < len(cfs) and cfs[i] is not None:
                entry["component_fit"] = cfs[i]
            sources.append(entry)
        if any(s.get("component_fit") is None for s in sources):
            return None
        out = propose_merge(
            self.X, self.fit, ids, refit=refit, seed=self.seed
        )
        merged_id = int(out["dirty"][0])
        new_cfs = list(out["fit"].get("component_fits") or [])
        if merged_id >= len(new_cfs):
            return None
        R = self.responsibilities
        return {
            "merged_mass": R[:, ids].sum(axis=1),
            "merged_component_fit": new_cfs[merged_id],
            "source_component_fits": [s["component_fit"] for s in sources],
            "source_labels": source_labels,
            "merged_label": " + ".join(source_labels),
            "merged_id": merged_id,
        }

    def name_catalogue(
        self,
        label_work: LabelWork | None = None,
        *,
        force: bool = False,
    ) -> list[int]:
        """LLM-name topics that are placeholders / dirty (or *all* if ``force``).

        Call once before Assess splits so ``parent_label`` lineage is the real
        catalogue name, not ``topic 0``. Pass ``force=True`` after changing the
        prompt so existing human labels are re-generated.
        """
        for j in self.topic_ids():
            if force or is_placeholder_label(self.labels.get(j), j):
                self.dirty.add(j)
        return self.name_dirty(label_work=label_work)

    def _ensure_named(self, topic_id: int, label_work: LabelWork | None = None) -> str:
        """Return a non-placeholder label for ``topic_id``, naming via LLM if needed."""
        i = int(topic_id)
        name = self.labels.get(i, f"topic {i}")
        if not is_placeholder_label(name, i):
            return name
        work = label_work or self.label_work
        if work is None:
            return name
        saved = set(self.dirty)
        self.dirty = {i}
        try:
            self.name_dirty(label_work=work)
        finally:
            self.dirty = (saved - {i}) | self.dirty
        return self.labels.get(i, name)

    def split(
        self,
        topic_id: int,
        *,
        n_children: int = 2,
        mass_threshold: float = 0.05,
        name_children: bool | None = None,
    ) -> dict[str, Any]:
        """Propose a split: geometry updates; children stay *proposed* until accept.

        If the parent still has a placeholder name and ``label_work`` is set,
        the parent is named first so lineage records the LLM catalogue label.

        By default, when ``label_work`` is set, both children are LLM-named
        immediately (``name_children=True``). Pass ``name_children=False`` to
        leave them as ``«parent» → (unnamed)`` until :meth:`name_proposal`.
        """
        i = int(topic_id)
        # Capture lineage from a real catalogue name when possible
        parent_label = self._ensure_named(i)
        self._push_undo()
        out = propose_split(
            self.X,
            self.fit,
            i,
            n_children=n_children,
            seed=self.seed,
            mass_threshold=mass_threshold,
        )
        n_ch = int(n_children)
        new_labels: dict[int, str] = {}
        new_desc: dict[int, str] = {}
        for old, name in self.labels.items():
            if old < i:
                new_labels[old] = name
            elif old > i:
                new_labels[old + n_ch - 1] = name
        for old, desc in self.descriptions.items():
            if old < i:
                new_desc[old] = desc
            elif old > i:
                new_desc[old + n_ch - 1] = desc
        new_parent_of: dict[int, str] = {}
        for old, pl in self.parent_of.items():
            if old < i:
                new_parent_of[old] = pl
            elif old > i:
                new_parent_of[old + n_ch - 1] = pl
        children = [int(c) for c in out["dirty"]]
        for c in children:
            new_labels[c] = f"«{parent_label}» → (unnamed)"
            new_parent_of[c] = parent_label
        remapped_dirty: set[int] = set()
        for d in self.dirty:
            if d < i:
                remapped_dirty.add(d)
            elif d > i:
                remapped_dirty.add(d + n_ch - 1)
            # d == i dropped
        remapped_dirty.update(children)
        self.fit = out["fit"]
        self.labels = new_labels
        self.descriptions = new_desc
        self.parent_of = new_parent_of
        self.dirty = remapped_dirty
        self.action_history.append(out["history_entry"])
        self.locked = None
        self.pending_proposal = {
            "kind": "split",
            "parent_id": i,
            "parent_label": parent_label,
            "parent_component_fit": out.get("parent_component_fit"),
            "parent_mass": np.asarray(out["parent_mass"], dtype=float).copy(),
            "children": children,
            "local_fit": out.get("local_fit"),
            "named": False,
            "accepted": False,
        }
        do_name = (
            bool(name_children)
            if name_children is not None
            else (self.label_work is not None)
        )
        if do_name and self.label_work is not None:
            self.name_proposal()
        elif self.name_after_action:
            self._maybe_name_after()
            if self.pending_proposal is not None:
                self.pending_proposal["named"] = not bool(self.dirty & set(children))
        return out

    def accept_proposal(self) -> bool:
        """Mark the pending split as accepted (keeps geometry + names)."""
        if self.pending_proposal is None:
            return False
        self.pending_proposal["accepted"] = True
        self.pending_proposal = None
        return True

    def name_proposal(self, label_work: LabelWork | None = None) -> list[int]:
        """LLM-name only the children of the pending split proposal."""
        if self.pending_proposal is None:
            return []
        children = set(self.proposed_topic_ids())
        if not children:
            return []
        saved = set(self.dirty)
        self.dirty = set(children)
        try:
            named = self.name_dirty(label_work=label_work)
        finally:
            # Preserve unrelated dirties; keep any child still dirty
            self.dirty = (saved - children) | self.dirty
        if named and self.pending_proposal is not None:
            self.pending_proposal["named"] = True
        return named

    def undo(self) -> bool:
        """Pop the last structural action. Returns False if stack empty."""
        if not self._undo_stack:
            return False
        snap = self._undo_stack.pop()
        self.fit = snap["fit"]
        self.labels = snap["labels"]
        self.descriptions = snap["descriptions"]
        self.dirty = snap["dirty"]
        self.action_history = snap["action_history"]
        self.locked = snap["locked"]
        self.parent_of = snap.get("parent_of") or {}
        self.pending_proposal = snap.get("pending_proposal")
        return True

    def name_dirty(self, label_work: LabelWork | None = None) -> list[int]:
        """Label dirty topics only via ``label_work`` (make_label_work-compatible).

        Returns the topic ids that were named. Does not call the LLM for
        clean topics. Per-topic failures fall back to an exemplar-based title
        and are recorded on ``self.last_naming_errors`` (never leave ``→ ?``).
        """
        from .cluster import coerce_topic_label

        work = label_work or self.label_work
        if work is None:
            raise ValueError(
                "name_dirty requires label_work= (e.g. make_label_work(...)) "
                "or a shell constructed with label_work="
            )
        if not self.dirty:
            self.last_naming_errors = []
            return []
        units = example_phrases_for_soft_topics(
            self._phrase_list,
            self.responsibilities,
            n_top=12,
            n_sample=0,
            min_responsibility=None,  # auto: 1/k
            seed=self.seed,
        )
        named: list[int] = []
        errors: list[str] = []
        for u in units:
            c = int(u["cluster"])
            if c not in self.dirty:
                continue
            examples = list(u.get("examples") or [])
            if not examples:
                self.labels[c] = f"topic {c} (empty)"
                named.append(c)
                continue
            try:
                result = work(u)
                label = coerce_topic_label(
                    result.get("label"), examples=examples, cluster_id=c
                )
                self.labels[c] = label
                self.descriptions[c] = str(result.get("description", "") or "")[:400]
                named.append(c)
            except Exception as exc:  # noqa: BLE001 — surface to analyst, keep going
                fallback = coerce_topic_label(None, examples=examples, cluster_id=c)
                self.labels[c] = fallback
                self.descriptions[c] = f"(naming error: {exc})"
                errors.append(f"topic {c}: {exc}")
                named.append(c)
        for c in named:
            self.dirty.discard(c)
        self.last_naming_errors = errors
        return named

    def lock(
        self,
        *,
        path: str | Path | None = None,
        k_multiverse: str | Sequence[int] | None = None,
    ) -> dict[str, Any]:
        """Persist subject-grain lock via Layer A ``lock_subject_grain``."""
        if self.pending_proposal is not None:
            raise ValueError(
                "Accept or reject (undo) the pending split proposal before locking"
            )
        policy = self.k_multiverse if k_multiverse is None else k_multiverse
        artefact = lock_subject_grain(
            primary_k=self.k,
            responsibilities=self.responsibilities,
            means=self.means,
            history=self.action_history,
            k_multiverse=policy,
            sigma2=float(self.fit.get("sigma2", 0.0)) or None,
            diagnostics=self.diagnostics(),
            extra={
                "labels": {str(i): self.labels.get(i, "") for i in range(self.k)},
                "parent_of": {str(i): v for i, v in self.parent_of.items()},
                "dirty_remaining": sorted(self.dirty),
            },
        )
        self.locked = artefact
        if path is not None:
            dump_json(artefact, Path(path))
        return artefact

    def fit_view(
        self,
        *,
        focus: int | None = None,
        path: str | Path | None = None,
        show: bool = False,
    ):
        """Re-draw the local U_q plane for ``focus`` (never calls the LLM).

        While a split is pending, draws the *proposed* children (means + local
        covariance) in the **parent** ``U_q`` basis. Otherwise draws the usual
        single-topic local plane for ``focus``.
        """
        from .viz import proposed_merge_view, proposed_split_view, topic_fit_view

        if focus is None:
            focus = 0 if self.k else 0
        focus = int(focus)
        sigma2 = (
            float(self.fit.get("sigma2"))
            if self.fit.get("sigma2") is not None
            else None
        )
        prop = self.pending_proposal
        if (
            prop is not None
            and prop.get("kind") == "merge"
            and prop.get("merged_component_fit") is not None
            and prop.get("merged_mass") is not None
            and (
                focus == int(prop.get("merged_id", -1))
                or focus in (prop.get("source_ids") or ())
            )
        ):
            src_cfs = [
                s["component_fit"]
                for s in prop.get("sources") or []
                if s.get("component_fit") is not None
            ]
            src_labs = list(prop.get("source_labels") or [])
            merged_lab = self.labels.get(
                int(prop["merged_id"]), " + ".join(src_labs)
            )
            return proposed_merge_view(
                self.X,
                merged_mass=prop["merged_mass"],
                merged_component_fit=prop["merged_component_fit"],
                source_component_fits=src_cfs,
                source_labels=src_labs,
                merged_label=str(merged_lab),
                sigma2=float(sigma2 or 0.0),
                path=path,
                show=show,
            )
        if (
            prop is not None
            and prop.get("kind") == "split"
            and prop.get("parent_component_fit") is not None
            and prop.get("local_fit") is not None
            and (
                focus in prop.get("children", [])
                or focus == int(prop.get("parent_id", -1))
            )
        ):
            local = prop["local_fit"]
            children = [int(c) for c in prop["children"]]
            child_labels = [
                self.labels.get(c, f"child {j}") for j, c in enumerate(children)
            ]
            parent_name = str(prop.get("parent_label") or "")
            return proposed_split_view(
                self.X,
                parent_mass=prop["parent_mass"],
                parent_component_fit=prop["parent_component_fit"],
                child_component_fits=list(local.get("component_fits") or []),
                child_labels=child_labels,
                parent_label=parent_name,
                sigma2=float(sigma2 or 0.0),
                path=path,
                show=show,
            )
        # Live merge-candidate preview (selection only; geometry not yet applied)
        preview_ids = getattr(self, "_merge_preview_ids", None)
        if preview_ids and len(preview_ids) >= 2 and prop is None:
            payload = self.merge_preview_payload(preview_ids)
            if payload is not None:
                return proposed_merge_view(
                    self.X,
                    merged_mass=payload["merged_mass"],
                    merged_component_fit=payload["merged_component_fit"],
                    source_component_fits=payload["source_component_fits"],
                    source_labels=payload["source_labels"],
                    merged_label=payload["merged_label"],
                    sigma2=float(sigma2 or 0.0),
                    path=path,
                    show=show,
                )
        label = self.labels.get(focus, f"topic {focus}")
        parent = self.parent_of.get(focus)
        title = f"«{label}» — local U_q (k={self.k}"
        if parent:
            title += f"; from «{parent}»"
        title += f"; dirty={sorted(self.dirty) or '—'})"
        return topic_fit_view(
            self.X,
            self.responsibilities,
            self.means,
            focus=focus,
            component_fits=self.fit.get("component_fits"),
            sigma2=sigma2,
            path=path,
            show=show,
            title=title,
        )

    # -------------------------------------------------------------- widgets
    def widgets(self):
        """Build the ipywidgets UI. Raises ImportError if unavailable."""
        try:
            import ipywidgets as W
            from IPython.display import clear_output, display
        except ImportError as e:
            raise ImportError(
                "ipywidgets is required for SubjectGrainShell.widgets(); "
                "install multilogue[notebook] or use Layer A scripted cells."
            ) from e

        def _opt_label(j: int) -> str:
            name = self.labels.get(j, "")
            parent = self.parent_of.get(j)
            if parent:
                return f"{j}: {name}  ← «{parent}»"
            return f"{j}: {name}"

        merge_sel = W.SelectMultiple(
            options=[(_opt_label(j), j) for j in self.topic_ids()],
            description="Merge",
            rows=min(8, max(3, self.k)),
        )
        split_dd = W.Dropdown(
            options=[(_opt_label(j), j) for j in self.topic_ids()],
            description="Split",
        )
        btn_merge = W.Button(description="Propose merge", button_style="primary")
        btn_split = W.Button(description="Propose split")
        btn_undo = W.Button(description="Undo / reject")
        btn_name_prop = W.Button(
            description="Name proposed (LLM)", button_style="info"
        )
        btn_accept = W.Button(description="Accept proposal", button_style="success")
        self._merge_preview_ids: list[int] = []
        btn_name = W.Button(description="Name dirty topics")
        btn_name_all = W.Button(description="Name catalogue (LLM)", button_style="info")
        btn_lock = W.Button(description="Lock", button_style="success")
        btn_apply_label = W.Button(
            description="Apply & re-name all", button_style="warning"
        )
        prompt_ta = W.Textarea(
            value=self.label_prompt,
            description="Label prompt",
            layout=W.Layout(width="100%", height="110px"),
            style={"description_width": "90px"},
        )
        model_dd = W.Dropdown(
            options=list(self.label_model_choices),
            value=self.label_model
            if self.label_model in self.label_model_choices
            else self.label_model_choices[0],
            description="Label model",
            style={"description_width": "90px"},
        )
        status = W.HTML()
        proposal_box = W.HTML()
        fig_out = W.Output()
        cat_out = W.Output()

        def _current_focus() -> int:
            ids = self.topic_ids()
            if not ids:
                return 0
            try:
                v = int(split_dd.value)
            except (TypeError, ValueError):
                return ids[0]
            return v if v in ids else ids[0]

        def _sync_selectors(*, prefer: int | None = None) -> None:
            """Refresh dropdown labels after merge/split; keep the selected topic."""
            ids = self.topic_ids()
            opts = [(_opt_label(j), j) for j in ids]
            keep = prefer if prefer in ids else _current_focus()
            if keep not in ids:
                keep = ids[0] if ids else 0
            split_dd.unobserve(_on_focus_change, names="value")
            try:
                merge_sel.options = opts
                split_dd.options = opts
                if ids:
                    split_dd.value = keep
            finally:
                split_dd.observe(_on_focus_change, names="value")

        def _proposal_html() -> str:
            prop = self.pending_proposal
            placeholders = [
                j for j in self.topic_ids()
                if is_placeholder_label(self.labels.get(j), j)
            ]
            hint = ""
            if placeholders and prop is None:
                hint = (
                    f"<p style='color:#a00;margin:0 0 6px 0'>"
                    f"Catalogue still has placeholder labels {placeholders}. "
                    f"Click <b>Name catalogue (LLM)</b> before splitting — "
                    f"otherwise parent_label stays «topic N».</p>"
                )
            preview = list(getattr(self, "_merge_preview_ids", None) or [])
            if prop is None:
                btn_name_prop.disabled = True
                btn_accept.disabled = True
                if len(preview) >= 2:
                    names = [
                        f"«{self.labels.get(j, f'topic {j}')}»" for j in preview
                    ]
                    return (
                        hint
                        + f"<b>Merge preview</b> (not yet proposed): "
                        f"{' + '.join(names)}. "
                        "Inspect the merged U_q below (originals listed), then "
                        "<b>Propose merge</b> → Accept (or change the selection)."
                    )
                return (
                    hint
                    + "<i>No pending proposal.</i> "
                    "Select ≥2 topics to preview a merge, or Propose split."
                )
            if prop.get("kind") == "merge":
                src = list(prop.get("source_labels") or [])
                mid = int(prop.get("merged_id", -1))
                named_flag = (
                    "yes" if prop.get("named") else "no — click Name proposed"
                )
                lines = [
                    hint,
                    f"<b>Pending merge</b> {' + '.join(f'«{s}»' for s in src)} "
                    f"→ topic {mid} «{self.labels.get(mid, '')}» "
                    f"(LLM named: {named_flag})",
                    "<ul style='margin:4px 0 0 1.2em;padding:0'>",
                ]
                for s in prop.get("sources") or []:
                    lines.append(
                        f"<li>original {s.get('topic_id')}: "
                        f"<b>{s.get('label', '')}</b></li>"
                    )
                lines.append(
                    f"<li>merged {mid}: <b>{self.labels.get(mid, '')}</b></li>"
                )
                lines.append("</ul>")
                btn_name_prop.disabled = False
                btn_accept.disabled = False
                return "".join(lines)
            parent = prop.get("parent_label", "")
            kids = prop.get("children") or []
            named_flag = (
                "yes"
                if prop.get("named")
                else "no — click Name proposed"
            )
            lines = [
                hint,
                f"<b>Pending split</b> of «{parent}» → children {list(kids)} "
                f"(LLM named: {named_flag})",
                "<ul style='margin:4px 0 0 1.2em;padding:0'>",
            ]
            for c in kids:
                c = int(c)
                lines.append(
                    f"<li>topic {c}: <b>{self.labels.get(c, '')}</b> "
                    f"<span style='color:#666'>(parent: «{parent}»)</span></li>"
                )
            lines.append("</ul>")
            btn_name_prop.disabled = False
            btn_accept.disabled = False
            return "".join(lines)

        def _redraw_fit(focus: int | None = None) -> None:
            """Update status + local / proposed U_q panel (no option rebuild)."""
            if focus is None:
                focus = _current_focus()
            focus = int(focus)
            prop = self.pending_proposal
            if prop is None:
                pend = (
                    f"merge preview {list(self._merge_preview_ids)}"
                    if len(getattr(self, "_merge_preview_ids", []) or []) >= 2
                    else "none"
                )
            else:
                pend = f"pending {prop.get('kind', '?')}"
            status.value = (
                f"<b>k={self.k}</b> · dirty={sorted(self.dirty) or '—'} · "
                f"undo={len(self._undo_stack)} · "
                f"locked={'yes' if self.locked else 'no'} · "
                f"proposal={pend} · view=topic {focus}"
            )
            proposal_box.value = _proposal_html()
            with fig_out:
                clear_output(wait=True)
                try:
                    import matplotlib.pyplot as plt

                    plt.close("all")
                except Exception:  # noqa: BLE001
                    pass
                self.fit_view(focus=focus, show=True)

        def _refresh_catalogue() -> None:
            with cat_out:
                clear_output(wait=True)
                display(self.catalogue())

        def _refresh_outputs(*, prefer_focus: int | None = None) -> None:
            """After structural edits: sync selectors, redraw plane, refresh catalogue."""
            _sync_selectors(prefer=prefer_focus)
            _redraw_fit(_current_focus())
            _refresh_catalogue()

        def _on_focus_change(change) -> None:
            if change.get("name") != "value":
                return
            if change.get("new") == change.get("old"):
                return
            try:
                focus = int(change["new"])
            except (TypeError, ValueError, KeyError):
                focus = _current_focus()
            _redraw_fit(focus)

        def _on_merge_sel_change(change) -> None:
            if change.get("name") != "value":
                return
            ids = [int(i) for i in (change.get("new") or ())]
            self._merge_preview_ids = ids
            if self.pending_proposal is not None:
                return
            # Live preview in merged U_q as soon as ≥2 candidates are selected
            if len(ids) >= 2:
                _redraw_fit(ids[0])
            else:
                _redraw_fit(_current_focus())

        def _on_merge(_):
            ids = list(merge_sel.value)
            if len(ids) < 2:
                status.value = (
                    "<span style='color:#a00'>Select ≥2 topics to merge.</span>"
                )
                return
            if self.pending_proposal is not None:
                status.value = (
                    "<span style='color:#a00'>Accept or reject the pending "
                    "proposal first.</span>"
                )
                return
            try:
                self.merge(ids)
            except Exception as exc:  # noqa: BLE001
                status.value = f"<span style='color:#a00'>Merge failed: {exc}</span>"
                return
            self._merge_preview_ids = []
            mid = int(self.pending_proposal["merged_id"]) if self.pending_proposal else 0
            status.value = _naming_status(
                f"Proposed merge of {ids} → topic {mid}",
                [mid] if self.pending_proposal else [],
            )
            _refresh_outputs(prefer_focus=mid)

        def _on_undo(_):
            if not self.undo():
                status.value = "<span style='color:#a00'>Nothing to undo.</span>"
                return
            self._merge_preview_ids = []
            _refresh_outputs()

        def _naming_status(prefix: str, named: list[int]) -> str:
            err = getattr(self, "last_naming_errors", None) or []
            labels = {c: self.labels.get(c, "") for c in named}
            msg = f"{prefix}: {named or 'none'} → {labels}"
            if err:
                msg += (
                    "<br><span style='color:#a00'>Naming issues (used exemplar "
                    f"fallback): {'; '.join(err)}</span>"
                )
            return msg

        def _sync_label_config(*, require: bool = True) -> bool:
            """Push textarea / model into label_work before LLM naming."""
            prompt = str(prompt_ta.value or "")
            model = str(model_dd.value or "")
            if self.label_work is None and self.label_client is None:
                if require:
                    status.value = (
                        "<span style='color:#a00'>No label_work on shell — "
                        "pass label_work= or label_client= at construction.</span>"
                    )
                    return False
                self.label_prompt = prompt
                self.label_model = model
                return True
            try:
                self.rebuild_label_work(prompt=prompt, model=model)
            except Exception as exc:  # noqa: BLE001
                status.value = (
                    f"<span style='color:#a00'>Label config: {exc}</span>"
                )
                return False
            return True

        def _on_apply_label(_):
            if not _sync_label_config(require=True):
                return
            prompt_l = (self.label_prompt or "").lower()
            conflict = (
                "english" in prompt_l
                and "language of the phrases" in prompt_l
            )
            before = {j: self.labels.get(j, "") for j in self.topic_ids()}
            try:
                named = self.name_catalogue(force=True)
            except Exception as exc:  # noqa: BLE001
                status.value = (
                    f"<span style='color:#a00'>Apply & re-name failed: {exc}</span>"
                )
                return
            after = {j: self.labels.get(j, "") for j in self.topic_ids()}
            changed = [j for j in named if before.get(j) != after.get(j)]
            lines = [
                _naming_status(
                    f"Re-named catalogue with {self.label_config_summary()}",
                    named,
                ),
                f"<br>Labels changed: {len(changed)}/{len(named)} "
                f"(threshold auto 1/k={1.0 / max(self.k, 1):.3f}).",
            ]
            if conflict:
                lines.append(
                    "<br><span style='color:#a00'>Prompt conflict: you ask for "
                    "English <i>and</i> «language of the phrases» — the model "
                    "often keeps the phrase language. Drop the language-of-"
                    "phrases clause (or re-run the cell for the English "
                    "default).</span>"
                )
            if changed:
                preview = "; ".join(
                    f"{j}: «{before[j]}» → «{after[j]}»" for j in changed[:6]
                )
                lines.append(f"<br>{preview}")
            else:
                lines.append(
                    "<br><span style='color:#a00'>No label strings changed — "
                    "check model / prompt.</span>"
                )
            if self.label_client_kind() == "fake":
                lines.append(
                    "<br><span style='color:#a00'><b>FakeClient is active</b> — "
                    "titles are taken from exemplar phrase words and ignore "
                    "English / translation instructions. Check "
                    "<code>OPENAI_API_KEY</code> in <code>.env</code> and that "
                    "<code>MULTILOGUE_FORCE_FAKE</code> is unset, then re-run "
                    "the client cell.</span>"
                )
            status.value = "".join(lines)
            if self.pending_proposal is not None:
                self.pending_proposal["named"] = True
            _refresh_outputs(prefer_focus=_current_focus())

        def _on_name_proposal(_):
            if self.pending_proposal is None:
                status.value = "<span style='color:#a00'>No pending proposal to name.</span>"
                return
            if not _sync_label_config(require=True):
                return
            try:
                if self.pending_proposal.get("kind") == "merge":
                    mid = int(self.pending_proposal["merged_id"])
                    saved = set(self.dirty)
                    self.dirty = {mid}
                    try:
                        named = self.name_dirty()
                    finally:
                        self.dirty = (saved - {mid}) | self.dirty
                    if self.pending_proposal is not None:
                        self.pending_proposal["named"] = mid not in self.dirty
                else:
                    named = self.name_proposal()
            except Exception as exc:  # noqa: BLE001
                status.value = f"<span style='color:#a00'>Name proposal failed: {exc}</span>"
                return
            status.value = _naming_status(
                f"Named proposal ({self.label_config_summary()})",
                named,
            )
            _refresh_outputs(prefer_focus=_current_focus())

        def _on_accept(_):
            if not self.accept_proposal():
                status.value = "<span style='color:#a00'>No pending proposal.</span>"
                return
            self._merge_preview_ids = []
            status.value = "Proposal accepted."
            _refresh_outputs(prefer_focus=_current_focus())

        def _on_name(_):
            if not _sync_label_config(require=True):
                return
            try:
                named = self.name_dirty()
            except Exception as exc:  # noqa: BLE001
                status.value = f"<span style='color:#a00'>Name dirty failed: {exc}</span>"
                return
            status.value = _naming_status(
                f"Named topics ({self.label_config_summary()})", named
            )
            _refresh_outputs(prefer_focus=_current_focus())

        def _on_name_catalogue(_):
            if not _sync_label_config(require=True):
                return
            try:
                named = self.name_catalogue(force=True)
            except Exception as exc:  # noqa: BLE001
                status.value = (
                    f"<span style='color:#a00'>Name catalogue failed: {exc}</span>"
                )
                return
            status.value = _naming_status(
                f"Named catalogue ({self.label_config_summary()})", named
            )
            _refresh_outputs(prefer_focus=_current_focus())

        def _on_lock(_):
            if self.pending_proposal is not None:
                status.value = (
                    "<span style='color:#a00'>Accept or reject the pending "
                    "proposal before locking.</span>"
                )
                return
            self.lock()
            _refresh_outputs(prefer_focus=_current_focus())

        def _on_split_with_sync(_):
            # Always push textarea / model into label_work before auto-name
            if self.label_client is not None or self.label_work is not None:
                if not _sync_label_config(require=True):
                    return
            parent = int(split_dd.value)
            try:
                self.split(parent)
            except Exception as exc:  # noqa: BLE001
                status.value = f"<span style='color:#a00'>Split failed: {exc}</span>"
                return
            kids = self.proposed_topic_ids()
            status.value = _naming_status(
                f"Proposed split of topic {parent} "
                f"({self.label_config_summary()}); child labels",
                kids,
            )
            _refresh_outputs(prefer_focus=parent if not kids else kids[0])

        btn_merge.on_click(_on_merge)
        btn_split.on_click(_on_split_with_sync)
        btn_undo.on_click(_on_undo)
        btn_name_prop.on_click(_on_name_proposal)
        btn_accept.on_click(_on_accept)
        btn_name.on_click(_on_name)
        btn_name_all.on_click(_on_name_catalogue)
        btn_apply_label.on_click(_on_apply_label)
        btn_lock.on_click(_on_lock)
        split_dd.observe(_on_focus_change, names="value")
        merge_sel.observe(_on_merge_sel_change, names="value")

        controls = W.HBox([merge_sel, split_dd])
        label_cfg = W.VBox(
            [
                W.HTML(
                    "<b>Labelling</b> — edit the prompt (must keep "
                    "<code>&lt;&lt;PHRASES&gt;&gt;</code>) and pick a model. "
                    "<b>Apply &amp; re-name all</b> re-labels the whole catalogue; "
                    "Propose split / Name also pick up the current text."
                ),
                prompt_ta,
                W.HBox([model_dd, btn_apply_label]),
            ]
        )
        buttons = W.HBox(
            [
                btn_name_all,
                btn_merge,
                btn_split,
                btn_name_prop,
                btn_accept,
                btn_undo,
                btn_name,
                btn_lock,
            ]
        )
        ui = W.VBox(
            [status, proposal_box, label_cfg, controls, buttons, fig_out, cat_out]
        )
        _refresh_outputs()
        return ui

    def display(self):
        """Display the widget shell in a notebook (requires ipywidgets)."""
        from IPython.display import display

        display(self.widgets())
