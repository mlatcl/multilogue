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


class SubjectGrainShell:
    """Assess controller: merge / split / undo / name-dirty / lock.

    Geometry updates never call the LLM. Labelling runs only via
    :meth:`name_dirty` (or when ``name_after_action=True``).
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
        name_after_action: bool = False,
        k_multiverse: str | Sequence[int] | None = "hold",
    ) -> None:
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
        self.label_work = label_work
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
        # Ensure every leaf has a display name
        for j in range(k):
            self.labels.setdefault(j, f"topic {j}")

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
            }
        )

    def _maybe_name_after(self) -> None:
        if self.name_after_action and self.dirty and self.label_work is not None:
            self.name_dirty()

    def merge(self, topic_ids: Sequence[int], *, refit: bool = True) -> dict[str, Any]:
        ids = sorted({int(i) for i in topic_ids})
        if len(ids) < 2:
            raise ValueError("merge needs at least two topic ids")
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
        new_labels[merged_id] = "unnamed / stale"
        self.fit = out["fit"]
        self.labels = new_labels
        self.descriptions = new_desc
        # Remap prior dirty ids that survived
        remapped_dirty = {old_to_new[d] for d in self.dirty if d in old_to_new}
        remapped_dirty.update(out["dirty"])
        self.dirty = remapped_dirty
        self.action_history.append(out["history_entry"])
        self.locked = None
        self._maybe_name_after()
        return out

    def split(
        self,
        topic_id: int,
        *,
        n_children: int = 2,
        mass_threshold: float = 0.05,
    ) -> dict[str, Any]:
        i = int(topic_id)
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
        for c in out["dirty"]:
            new_labels[int(c)] = "unnamed / stale"
        remapped_dirty: set[int] = set()
        for d in self.dirty:
            if d < i:
                remapped_dirty.add(d)
            elif d > i:
                remapped_dirty.add(d + n_ch - 1)
            # d == i dropped
        remapped_dirty.update(int(c) for c in out["dirty"])
        self.fit = out["fit"]
        self.labels = new_labels
        self.descriptions = new_desc
        self.dirty = remapped_dirty
        self.action_history.append(out["history_entry"])
        self.locked = None
        self._maybe_name_after()
        return out

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
        return True

    def name_dirty(self, label_work: LabelWork | None = None) -> list[int]:
        """Label dirty topics only via ``label_work`` (make_label_work-compatible).

        Returns the topic ids that were named. Does not call the LLM for
        clean topics.
        """
        work = label_work or self.label_work
        if work is None:
            raise ValueError(
                "name_dirty requires label_work= (e.g. make_label_work(...)) "
                "or a shell constructed with label_work="
            )
        if not self.dirty:
            return []
        units = example_phrases_for_soft_topics(
            self._phrase_list,
            self.responsibilities,
            n_top=12,
            n_sample=0,
            seed=self.seed,
        )
        named: list[int] = []
        for u in units:
            c = int(u["cluster"])
            if c not in self.dirty:
                continue
            if not u.get("examples"):
                self.labels[c] = f"topic {c} (empty)"
                named.append(c)
                continue
            result = work(u)
            self.labels[c] = str(result.get("label", f"topic {c}"))[:80]
            self.descriptions[c] = str(result.get("description", ""))
            named.append(c)
        for c in named:
            self.dirty.discard(c)
        return named

    def lock(
        self,
        *,
        path: str | Path | None = None,
        k_multiverse: str | Sequence[int] | None = None,
    ) -> dict[str, Any]:
        """Persist subject-grain lock via Layer A ``lock_subject_grain``."""
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
                "dirty_remaining": sorted(self.dirty),
            },
        )
        self.locked = artefact
        if path is not None:
            dump_json(artefact, Path(path))
        return artefact

    def fit_view(self, *, path: str | Path | None = None, show: bool = False):
        """Re-draw geometry (never calls the LLM)."""
        from .viz import topic_fit_view

        return topic_fit_view(
            self.X,
            self.responsibilities,
            self.means,
            path=path,
            show=show,
            title=f"Topic fit (k={self.k}, dirty={sorted(self.dirty)})",
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

        merge_sel = W.SelectMultiple(
            options=[(f"{j}: {self.labels.get(j, '')}", j) for j in self.topic_ids()],
            description="Merge",
            rows=min(8, max(3, self.k)),
        )
        split_dd = W.Dropdown(
            options=[(f"{j}: {self.labels.get(j, '')}", j) for j in self.topic_ids()],
            description="Split",
        )
        btn_merge = W.Button(description="Merge", button_style="primary")
        btn_split = W.Button(description="Split")
        btn_undo = W.Button(description="Undo")
        btn_name = W.Button(description="Name dirty topics", button_style="info")
        btn_lock = W.Button(description="Lock", button_style="success")
        status = W.HTML()
        fig_out = W.Output()
        cat_out = W.Output()

        def _sync_selectors() -> None:
            opts = [(f"{j}: {self.labels.get(j, '')}", j) for j in self.topic_ids()]
            merge_sel.options = opts
            split_dd.options = opts

        def _refresh_outputs() -> None:
            status.value = (
                f"<b>k={self.k}</b> · dirty={sorted(self.dirty) or '—'} · "
                f"undo={len(self._undo_stack)} · "
                f"locked={'yes' if self.locked else 'no'}"
            )
            _sync_selectors()
            with fig_out:
                clear_output(wait=True)
                self.fit_view(show=True)
            with cat_out:
                clear_output(wait=True)
                cat = self.catalogue()
                display(cat)

        def _on_merge(_):
            ids = list(merge_sel.value)
            if len(ids) < 2:
                status.value = "<span style='color:#a00'>Select ≥2 topics to merge.</span>"
                return
            self.merge(ids)
            _refresh_outputs()

        def _on_split(_):
            self.split(int(split_dd.value))
            _refresh_outputs()

        def _on_undo(_):
            if not self.undo():
                status.value = "<span style='color:#a00'>Nothing to undo.</span>"
                return
            _refresh_outputs()

        def _on_name(_):
            if self.label_work is None:
                status.value = (
                    "<span style='color:#a00'>No label_work on shell — "
                    "pass label_work= at construction.</span>"
                )
                return
            named = self.name_dirty()
            status.value = f"Named topics: {named or 'none dirty'}"
            _refresh_outputs()

        def _on_lock(_):
            self.lock()
            _refresh_outputs()

        btn_merge.on_click(_on_merge)
        btn_split.on_click(_on_split)
        btn_undo.on_click(_on_undo)
        btn_name.on_click(_on_name)
        btn_lock.on_click(_on_lock)

        controls = W.HBox([merge_sel, split_dd])
        buttons = W.HBox([btn_merge, btn_split, btn_undo, btn_name, btn_lock])
        ui = W.VBox([status, controls, buttons, fig_out, cat_out])
        _refresh_outputs()
        return ui

    def display(self):
        """Display the widget shell in a notebook (requires ipywidgets)."""
        from IPython.display import display

        display(self.widgets())
