#!/usr/bin/env python3
"""Write pedagogical notebooks under notebooks/.

Edit this file, then regenerate:

    python scripts/build_notebooks.py
    pytest tests/test_notebooks_smoke.py -q

Style (talk-notebook pattern):
  - Title, abstract, then methodological prose with equations
  - Separate cells for library imports, computation, and figures
  - Interpretive markdown after each visualisation
  - Public CIMT corpus by default; Colab bootstrap in setup
  - Offline Address uses phrases_from_units (no synthetic Civic units)
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf

GITHUB_REPO = "mlatcl/multilogue"
GITHUB_BRANCH = "main"
AUTHOR = "[Neil D. Lawrence](http://inverseprobability.com)"
DATE = "2026-10-18"

# Colab / path bootstrap only — no scientific imports here.
SETUP = r'''#@title Setup (run first)
# Infrastructure only: install or locate multilogue, prepare figure directory.
# Scientific imports live in later cells.

import sys, subprocess, pathlib

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "matplotlib", "pandas", "numpy", "scikit-learn", "pyyaml", "pot",
        "git+https://github.com/mlatcl/multilogue.git",
    ])
else:
    try:
        import multilogue  # noqa: F401
    except ImportError:
        _here = pathlib.Path.cwd().resolve()
        for _cand in (_here, _here.parent, *_here.parents):
            if (_cand / "pyproject.toml").is_file() and (_cand / "multilogue").is_dir():
                if str(_cand) not in sys.path:
                    sys.path.insert(0, str(_cand))
                break

from multilogue.notebook import setup

FIG = setup(figures_dir="outputs/notebook_figures")
print("Figures →", FIG)
'''

ENSURE_POT = r'''# Optional transport dependency (soft lenses + document EMD).
import importlib.util, subprocess, sys
if importlib.util.find_spec("ot") is None:
    subprocess.check_call([sys.executable, "-m", "pip", "-q", "install", "pot"])
print("POT available")
'''

# Prefer OpenAI from repo-root .env (cwd may be notebooks/). Fake only if forced.
RESOLVE_CLIENT = r'''
from multilogue.clients import (
    resolve_study_client, TOPIC_LABEL_PROMPT, TOPIC_LABEL_SYSTEM,
)
from multilogue.config import load_dotenv

root = FIG.parent
env_path = load_dotenv()
client, models, client_kind = resolve_study_client(
    log_path=root / "logs" / "llm.jsonl",
)
print(
    f"LLM client: {client_kind} · embed={models['embed']} · label={models['label']}"
    + (f" · .env={env_path}" if env_path else " · .env=(not found)")
)
'''


def colab_badge(name: str) -> str:
    url = (
        f"https://colab.research.google.com/github/{GITHUB_REPO}/blob/"
        f"{GITHUB_BRANCH}/notebooks/{name}"
    )
    return (
        f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})"
    )


def title_block(name: str, title: str, abstract: str) -> str:
    return (
        f"{colab_badge(name)}\n\n"
        f"# {title}\n\n"
        f"### {AUTHOR}, University of Cambridge\n\n"
        f"### {DATE}\n\n"
        f"**Abstract**: {abstract.strip()}\n"
    )


def md(src: str) -> tuple[str, str]:
    return ("md", src.strip() + "\n")


def code(src: str) -> tuple[str, str]:
    return ("code", src.strip() + "\n")



# Shared Access: CIMT Bonn cycling dialogue vs survey (no synthetic civic units).
LOAD_CIMT_PAIR = r"""
import os
os.environ.setdefault("MULTILOGUE_ACCESS_YES", "1")
from multilogue.experiment import load_cimt_format_pair
from multilogue.extract import phrases_from_units

units, cimt_meta = load_cimt_format_pair(max_units_per=40)
if units is None:
    raise RuntimeError(
        "CIMT Access failed: "
        + str(cimt_meta.get("error", "unknown"))
        + ". Need network once to populate MULTILOGUE_DATAPATH / ~/.cache/multilogue."
    )
print(cimt_meta)
phrases = phrases_from_units(units, extra_fields=["group", "format"])
print(f"{len(units)} units → {len(phrases)} phrases (unit-as-phrase; LLM extract optional)")
"""

NOTEBOOKS: dict[str, list[tuple[str, str]]] = {}

# ---------------------------------------------------------------------------
# 00 Access
# ---------------------------------------------------------------------------
NOTEBOOKS["00_access.ipynb"] = [
    md(
        title_block(
            "00_access.ipynb",
            "Access — units of civic text",
            """
Multilogue organises public-dialogue analysis around Access → Assess → Address.
Access is getting dialogue into computational form: loaders, units of text, and
provenance. This notebook teaches the *unit* contract and shows how named public
sources switch without changing the rest of the Address stack.
""",
        )
    ),
    md(
        """
# Introduction

Public dialogue studies share a methodological spine even when corpora and
headline questions differ. Multilogue is that spine as a library. Consumers bring
Access loaders; the package expects a small, corpus-agnostic object — the
**unit** — so extraction, clustering, and weighting never learn the file format.

Access is deliberately thin. It does not clean for a research question, propose
topics, or call a language model. Those belong later. The only job here is to
make text electronically usable under a clear contract, with citation and licence
metadata intact.
"""
    ),
    md(
        """
## The unit

A unit is one analysable span. Required fields are an identifier, a document id,
and text. Optional fields carry context for quote checks and free-form metadata
(group labels, format tags, gold codes). Downstream stages should treat
everything beyond the three required fields as opaque until Address asks for it.

Why this shape? A consultation CSV, a Polis export, and a CIMT TSV must feed
the same Address path. The reusable method lives *above* the file format.
"""
    ),
    code(
        """
from IPython.display import display
from multilogue.access import list_sources, load
from multilogue.protocols import Unit
"""
    ),
    code(
        """
print("Registered sources:", list_sources())
bundle = load("cimt", process="Cycling-Dialogue-Bonn", max_units=20)
units = bundle["units"]
print(f"{len(units)} units; license={bundle['license']!r}")
display(units[0])
"""
    ),
    md(
        """
The first unit above is a dictionary conforming to the contract. Pedagogy uses
**public** open corpora (CIMT by default). Downloads land in a gitignored cache
(`MULTILOGUE_DATAPATH` or `~/.cache/multilogue`), never in the repository.
"""
    ),
    md(
        """
## Switching sources

Following the old `pods.datasets.<name>()` pattern, each public corpus is a named
loader. `load(name, **kwargs)` returns units plus citation and licence metadata.
"""
    ),
    code(
        """
import pandas as pd

# Default public corpus: CIMT Bonn cycling dialogue. Polis is another CC BY option.
bundle = load("cimt", process="Cycling-Dialogue-Bonn", max_units=80)
# bundle = load("polis", conversation="vtaiwan.uberx", max_units=80)

units = bundle["units"]
print(bundle["citation"][:220], "…")
print("cache path:", bundle["path"])
df = pd.DataFrame(units)
display(df[["unit_id", "doc_id", "text"]].head())
print("docs:", df.doc_id.nunique(), "units:", len(df))
"""
    ),
    md(
        """
## Corpus shape (still Access)

Even before Assess, we can ask whether the switch left a usable shape — how many
documents per group, how long the texts are — without posing a research question.
"""
    ),
    code(
        """
from multilogue.assess_base import unit_size_table, docs_per_group
from multilogue import viz
"""
    ),
    code(
        """
sizes = unit_size_table(units)
docs = docs_per_group(units, "group") if any("group" in u for u in units) else None
display(sizes.describe())
if docs is not None:
    display(docs)
    viz.docs_per_group_bars(docs, path=FIG / "00_docs_per_group.png")
viz.unit_size_hist(sizes, group_col="group", units=units, path=FIG / "00_unit_sizes.png")
"""
    ),
    md(
        """
# Outlook

Access ends when units exist with provenance. The next notebook, Assess, asks
what you can say about those units *without* knowing the research question —
sizes, emptiness, crude vocabulary — so that quality work remains reusable when
the question changes.
"""
    ),
]

# ---------------------------------------------------------------------------
# 01 Assess
# ---------------------------------------------------------------------------
NOTEBOOKS["01_assess.ipynb"] = [
    md(
        title_block(
            "01_assess.ipynb",
            "Assess — without the research question",
            """
Assess is work that remains valid if the downstream research question changes:
unit and sentence lengths, word-length distributions, character-class sanity,
emptiness, crude vocabulary, coverage across documents. Anything that needs a
concern/benefit taxonomy, a framing lens, or a headline metric belongs in
Address. This notebook teaches that boundary on **CIMT German** dialogue/survey
units when the network is available, with synthetic English only as an offline
fallback (CIP-0008).
""",
        )
    ),
    md(
        """
# Introduction

The Fynesse rule of thumb is sharp: *Assess is only work you can do without the
question in mind.* If changing “concerns about cycling infrastructure” into
“benefits of remote work” would invalidate a diagnostic, that diagnostic is
already Address.

Why the split? Reusable quality work should not be locked inside a
question-specific notebook. Assess helpers return tables; plots here are
diagnostics, not findings. Prefer a real public corpus (CIMT Bonn cycling,
German) so length and character histograms reflect actual dialogue text; keep
synthetic units only when the download is unavailable.
"""
    ),
    md(
        """
## What counts as Assess

| In Assess | Not Assess (→ Address) |
|-----------|-------------------------|
| Unit / sentence / word lengths | Concern / benefit extraction |
| Character-class inventory + unusual codepoints | Framing lenses |
| Empty flags, token frequencies | Headline metric $\\ell$ |
| Coverage / missingness | Soft PPCA mixture weights |

The boundary is methodological, not computational. Counting tokens is cheap;
calling an LLM is expensive — but cost alone does not decide the phase.
"""
    ),
    code(
        """
import os
from IPython.display import display
from multilogue.access import load
from multilogue.experiment import load_cimt_format_pair
from multilogue.assess_base import (
    assess_text_report, docs_per_group, token_frequency,
)
from multilogue import viz
"""
    ),
    code(
        """
os.environ.setdefault("MULTILOGUE_ACCESS_YES", "1")
cimt_units, cimt_meta = load_cimt_format_pair(max_units_per=60)
if cimt_units is not None:
    units = list(cimt_units)
    for u in units:
        u.setdefault("group", u.get("format"))
    assess_lang = "de"
    corpus_label = "CIMT Cycling-Dialogue-Bonn vs Survey-Bonn (de)"
    display(cimt_meta)
else:
    print("CIMT unavailable:", (cimt_meta or {}).get("error", "unknown"))
    units = load("synthetic", n_docs_per_group=4, units_per_doc=3)["units"]
    # Plant one OCR-ish / undersized unit so flags are visible offline.
    units = list(units) + [{
        "unit_id": "junk", "doc_id": "junk_doc", "group": "group_a",
        "text": "ok\\ufffd\\x00 " + ("fusedtoken" * 4),
    }]
    assess_lang = "en"
    corpus_label = "synthetic English (Access fallback)"

report = assess_text_report(units, lang=assess_lang)
group_key = "format" if any(u.get("format") for u in units) else "group"
print(
    f"{corpus_label} — units={len(units)}; lang={assess_lang}; "
    f"empty={len(report['empty'])}; "
    f"unit_flags={len(report['unit_length_flags'])}; "
    f"char_flags={len(report['char_flags'])}"
)
display(docs_per_group(units, group_key))
display(report["size_summary"])
display(token_frequency([u["text"] for u in units], top_n=15))
"""
    ),
    md(
        """
## Diagnostics — lengths

Ask whether *units* (often paragraphs from Access) are a sensible length, whether
they contain sentences of a sensible length, and whether letter-token lengths
look like German (CIMT) or English (fallback) words rather than OCR fused
strings. Defaults are dialogue-ish bands (see `assess_base` constants); retune
for your corpus, but keep the bands question-agnostic.
"""
    ),
    code(
        """
viz.unit_size_hist(
    report["sizes"], group_col=group_key, units=units, path=FIG / "01_unit_sizes.png",
)
viz.sentence_length_hist(report["sentences"], path=FIG / "01_sentence_lengths.png")
viz.word_length_hist(report["words"], path=FIG / "01_word_lengths.png")
viz.docs_per_group_bars(docs_per_group(units, group_key), path=FIG / "01_docs.png")
display(report["unit_length_flags"].head())
display(report["sentence_flags"].head())
display(report["word_flags"].head())
"""
    ),
    md(
        """
## Diagnostics — characters

Character-class shares catch replacement characters (`U+FFFD`), controls, and
other non-text debris that word counts miss. Flag units whose share of
``other`` exceeds a small threshold; inspect the unusual-codepoint table before
paying for extraction.
"""
    ),
    code(
        """
viz.char_class_bars(report["char_classes"], path=FIG / "01_char_classes.png")
display(report["char_classes"])
display(report["unusual_codepoints"].head(10))
display(report["char_flags"])
"""
    ),
    md(
        """
The figures are not answers to a research question. They characterise the corpus
so that Address — extraction, clustering, weighting — starts from a known base.

**Stop before Address if**: many units are empty / too short; sentence or word
lengths are wildly extreme; ``other`` character share is high. Fix Access (or
the min-words gate) first.
"""
    ),
    md(
        """
# Outlook

Address begins when we ask the model for structured points. Notebook 02 shows
narrow extraction passes, checkpoints, quote support, and how phrases are
embedded — the first place the research question enters through prompts and kinds.
"""
    ),
]

# ---------------------------------------------------------------------------
# 02 Extract
# ---------------------------------------------------------------------------
NOTEBOOKS["02_extract.ipynb"] = [
    md(
        title_block(
            "02_extract.ipynb",
            "Extract — kinds, checkpoints, quote support",
            """
Address begins when we ask a model for structured points. Multilogue keeps
extraction generic: a kind name, a prompt template, a sentinel for “nothing
here”, and an optional quote-support gate so each phrase is grounded in the
speaker's words. Checkpoints make reruns resume without paying twice. This
notebook teaches those ideas on the public CIMT corpus; offline pedagogy uses
`phrases_from_units` so we never invent civic text.
""",
        )
    ),
    md(
        """
# Introduction

Extraction is the first Address stage. The library does not hard-code
“concern” or “benefit”: those are *kinds* supplied by the consumer. What
multilogue owns is the machinery — parse items from a model response, verify
quotes against unit text, and persist results under a fingerprint of prompt +
model so the same work is not repeated. When a live model is unavailable,
`phrases_from_units` builds a phrase table from Access units (one phrase per
unit; kind from gold `meta.code` when present).
"""
    ),
    md(
        """
## Checkpoints

Model stages run through `StageRunner`: append-only JSONL keyed by item, with a
fingerprint of prompt + model. Reruns resume; fingerprint changes supersede;
replay needs no API. That is engineering for reproducible dialogue analysis, not
a modelling claim.
"""
    ),
    md(
        """
## Quote support

A phrase without a recoverable quote is easy for a model to invent. The score
`quote_support` asks how well the quoted span sits in the unit text. Write $q$
for the quote and $s$ for the source unit. Support is high when a normalised
form of $q$ appears (approximately) in $s$. Thresholds are a design choice —
high enough to catch fabrications, low enough to tolerate light paraphrase.
"""
    ),
    code(
        """
from IPython.display import display
from multilogue.text import quote_support
from multilogue import viz
"""
    ),
    code(LOAD_CIMT_PAIR),
    code(
        """
display(phrases.head())
yd = (
    phrases.groupby(["format", "kind"], dropna=False)
    .size()
    .rename("kept")
    .reset_index()
)
display(yd)
viz.yield_bars(yd.rename(columns={"format": "group"}), path=FIG / "02_yield.png")
"""
    ),
    md(
        """
Yield counts show how many unit-as-phrases of each kind appear by format.
With a live client the same columns come from `phrase_table` after
`StageRunner` extract; the Access corpus stays public either way.
"""
    ),
    code(
        """
demo_text = units[0]["text"]
span = " ".join(demo_text.split()[:8])
print("support(exact span):", round(quote_support(span, demo_text), 3))
print("support(noise):", round(quote_support("completely unrelated words", demo_text), 3))
if "verified" in phrases.columns:
    display(phrases.groupby(["format", "kind"]).verified.mean().rename("pct_verified"))
"""
    ),
    md(
        """
# Outlook

Phrases alone are not a comparison. Notebook 03 places them in a shared
embedding space with soft MPPCA topics (harden only for labels / lenses).
"""
    ),
]

# ---------------------------------------------------------------------------
# 03 Cluster
# ---------------------------------------------------------------------------
NOTEBOOKS["03_cluster.ipynb"] = [
    md(
        title_block(
            "03_cluster.ipynb",
            "Shared topic space — soft MPPCA, harden views, lenses",
            """
Once phrases exist, we place them in one embedding space. Soft-throughout
Address (CIP-0017) fits a **mixture of probabilistic PCAs**: $k$-means only
initialises component means; soft responsibilities $r_{ik}$ are the primary
topic state. Hard labels and exemplars are a *late view* for LLM labelling and
lens prompts. This notebook teaches that split and shows a PCA view as a
diagnostic — not as the generative story for the phrases.
""",
        )
    ),
    md(
        """
# Introduction

Hard $k$-means gives every phrase a single topic label. Soft-throughout instead
keeps a distribution over topics. Multilogue's [`mppca_fit`](https://mlatcl.github.io/multilogue/api/mppca/)
uses $k$-means only to seed means, then EM under a **fixed** topic noise
$\\sigma^2_{\\mathrm{topic}}$ (independent of the lens-level $\\sigma^2$ in
notebook 08).

Labels name topics; lenses group topics into coarser framings. Both LLM steps
consume a **harden view** (MAP labels / top-mass exemplars) — *format-blind* —
so the taxonomy is not fitted to the comparison we later want to make.
"""
    ),
    md(
        """
## Soft topics (MPPCA)

Topic $\\sigma^2$ is fixed for the run (default `DEFAULT_TOPIC_SIGMA2`). Soft
responsibilities are checkpointed as the geometry; MAP labels are derived when
a discrete interface is required.
"""
    ),
    md(
        """
## PCA as a viewing device

The scatter below projects embeddings onto the first two principal components.
Classical PCA is a *view*, not the generative model. Soft lens memberships and
document EMD on soft histograms live in notebook 08.
"""
    ),
    code(
        """
from IPython.display import display
import numpy as np
from multilogue.llm import StageRunner
from multilogue.cluster import (
    Embedder, make_label_work, make_lens_work, resolve_lenses,
)
from multilogue.mppca import (
    DEFAULT_TOPIC_SIGMA2,
    mppca_fit,
    responsibilities_to_labels,
    example_phrases_for_soft_topics,
)
from multilogue import viz
"""
    ),
    code(LOAD_CIMT_PAIR),
    code(RESOLVE_CLIENT),
    code(
        """
# client_kind comes from resolve_study_client (openai, or fake only if forced).
_runner_kw = {"max_workers": 2}
if client_kind == "fake":
    _runner_kw["sleep"] = lambda _: None
runner = StageRunner(root / "ckpt_cl", root / "logs_cl", **_runner_kw)
k = min(4, max(2, len(phrases) // 3))
embedder = Embedder(root / "emb", client, model=models["embed"])
E = np.asarray(embedder(phrases.phrase.tolist()), float)
fit = mppca_fit(E, k=k, sigma2=DEFAULT_TOPIC_SIGMA2, seed=0)
R = fit["responsibilities"]
means = fit["means"]
labels = responsibilities_to_labels(R)
phrases = phrases.copy()
phrases["cluster"] = labels  # harden view for bars / lens map only
# Cosine similarity to MAP topic mean (diagnostic)
valid = labels >= 0
phrases["centroid_sim"] = 0.0
phrases.loc[valid, "centroid_sim"] = (E[valid] * means[labels[valid]]).sum(1)
print(f"topic σ²={fit['sigma2']}; EM iters={fit['n_iter']}")
print(f"mean max responsibility: {R.max(axis=1).mean():.3f}")
(root / "clusters").mkdir(parents=True, exist_ok=True)
np.save(root / "clusters" / "responsibilities.npy", R)
np.save(root / "clusters" / "topic_means.npy", means)
"""
    ),
    code(
        """
viz.cluster_size_bars(phrases, path=FIG / "03_cluster_sizes.png")
viz.embedding_scatter(E, phrases["cluster"], path=FIG / "03_pca_clusters.png")
"""
    ),
    md(
        """
Cluster-size bars use the MAP harden view so empty topics are visible. Soft
geometry remains in $R$. Hopeless overlap in the PCA scatter suggests revisiting
$k$ or the phrase set before interpreting shares — that decision is **Assess**,
not a format-gap maximisation.
"""
    ),
    md(
        """
## Assess — interactive subject grain (Bishop–Tipping)

Choosing how many subjects belong in the catalogue is closer to “what is the
human grain of this corpus?” than to “which quote threshold?”. Following
Bishop & Tipping’s hierarchical visualisation (TPAMI 1998), Assess **starts at
one soft bag** ($k{=}1$) and grows grain by **split** (CIP-000A). The analyst
sees **both**:

1. **Geometry** — the **local** $U_q$ plane of the topic you are considering
   splitting (not a global PCA of the whole embedding cloud). Soft mass on
   that component sets point opacity; the panel updates when you change the
   split target.
2. **Semantics** — an LLM catalogue of the same bags (exemplars + names).

Neither view replaces the other. Merge / split / keep is human feedback — not
automatic maximisation of a study metric $\\ell$. Under *assess without the
question*, this loop is Assess; lenses, format gap, and multiverse under a
**locked** catalogue are Address.

**Noise policy:** topic $\\sigma^2$ is **fixed** for the Assess loop (CIP-0017
dual of Bishop–Tipping’s fixed $q{=}2$: we pin noise, $q$ falls out). Optional
profile mode remains on the widget for experiments; live merge preview never
re-profiles. EM budgets separate cheap preview from Propose/Accept.

**Catalogue first:** the shell names every topic once (LLM) so the table shows
real subject labels — not ``topic 0``. The widget has a **label prompt** text
box and a **model** dropdown (keep ``<<PHRASES>>``). **Apply & re-name all**
pushes the new prompt into the live labelling work and re-labels every topic.

Select ≥2 topics in **Merge** to preview the *merged* $U_q$ with the originals
listed (means + ellipses); **Propose merge** then Accept (or Undo). A split is
likewise a *proposal*: child means in the **parent** $U_q$. Accept when happy.
Click a point in the live panel to read the phrase / paragraph in the side
box (Plotly + ipywidgets; ``pip install multilogue[notebook]``). After a
split, the child with more soft mass is listed first and selected. A
dendrogram grows on each Propose split with branch length
``|KL̂(parent ‖ child-mix)|`` under the parent soft mass; any merge
abandons the tree.
"""
    ),
    code(
        """
import os
from multilogue.subject_grain import initial_assess_fit
from multilogue.subject_grain_shell import SubjectGrainShell, ipywidgets_available

# CIP-000A: Assess entry is one soft topic; split grows the catalogue.
# Fixed σ² (DEFAULT_TOPIC_SIGMA2): pin noise, let q truncate — not profile-on-Accept.
# Earlier multi-k fit above remains a soft-throughout teaching view.
grain_fit = initial_assess_fit(
    E, k=1, sigma2_mode="fixed", sigma2=DEFAULT_TOPIC_SIGMA2, seed=0
)
# label_client= lets the widget Textarea / model Dropdown rebuild label_work
shell = SubjectGrainShell(
    E, grain_fit, phrases, phrase_col="phrase", seed=0,
    label_client=client,
    label_system=TOPIC_LABEL_SYSTEM,
    label_prompt=TOPIC_LABEL_PROMPT,
    label_model=models["label"],
    name_initial=True,
    sigma2_mode="fixed",
)
print(
    f"Assess entry k={shell.k}, σ²={shell.fit['sigma2']:.4g} "
    f"(mode={shell.sigma2_mode})"
)
print("initial catalogue labels:", {j: shell.labels[j] for j in shell.topic_ids()})
# Widgets for live try-combinations; CI / smoke force the scripted path.
use_widgets = (
    ipywidgets_available()
    and os.environ.get("MULTILOGUE_SUBJECT_GRAIN_WIDGETS", "1") != "0"
)
if use_widgets:
    print(
        "Layer B: start at k=1 → Propose split / merge preview → Accept"
    )
    shell.display()
else:
    print("Layer A scripted path (no widgets / MULTILOGUE_SUBJECT_GRAIN_WIDGETS=0)")
    display(shell.catalogue())
    # Local U_q of the single bag (Bishop–Tipping channel)
    focus = 0
    shell.fit_view(focus=focus, path=FIG / "03_topic_fit_view.png", show=True)
    # Grow grain: propose split from k=1, then accept
    parent = 0
    parent_name = shell.labels.get(parent, f"topic {parent}")
    shell.split(parent)
    print(
        "proposed split of", repr(parent_name),
        "→ children", shell.proposed_topic_ids(),
        "parent_of", {c: shell.parent_of.get(c) for c in shell.proposed_topic_ids()},
        "pending=", shell.pending_proposal is not None,
    )
    shell.fit_view(
        focus=shell.proposed_topic_ids()[0],
        path=FIG / "03_proposed_split.png",
        show=True,
    )
    display(shell.catalogue())
    print("child labels after split:", {
        c: shell.labels[c] for c in shell.proposed_topic_ids()
    })
    shell.accept_proposal()
    print("accepted; k =", shell.k, "parent_of =", shell.parent_of)
    # Demo propose-merge (merged U_q + originals) then undo
    if shell.k >= 2:
        shell.merge([0, 1])
        mid = int(shell.pending_proposal["merged_id"])
        print(
            "after propose merge: k =", shell.k,
            "merged_id =", mid,
            "sources =", shell.pending_proposal.get("source_labels"),
        )
        shell.fit_view(
            focus=mid, path=FIG / "03_topic_fit_after_merge.png", show=True
        )
        display(shell.catalogue())
        shell.undo()
        print("after undo: k =", shell.k)
    lock = shell.lock(
        path=root / "clusters" / "subject_grain_lock.json",
        k_multiverse="hold",
    )
    print("locked subject grain:", lock["primary_k"], lock["k_multiverse"])
    display(lock)
"""
    ),
    md(
        """
Lock before Address spend: the artefact records `primary_k` and a hold /
$\\pm 1$ multiverse policy. Wide $k$ grids belong in an explicit one-factor
resolution sweep — not in the default factorial multiverse (see notebook 09).
"""
    ),
    md(
        """
## Blind labels and lenses (harden view)

Exemplars are ranked by soft mass on each topic; the LLM never sees raw
responsibility matrices. Researchers may edit the lens mapping afterwards — the
first pass stays blind. After a subject-grain lock, labels here name the
*locked* leaves.
"""
    ),
    code(
        """
# Re-bind fit / R from the shell if the scripted path ran; widgets leave `fit` as initial.
R = shell.responsibilities
fit = shell.fit
means = fit["means"]
k = shell.k
labels = responsibilities_to_labels(R)
phrases = phrases.copy()
phrases["cluster"] = labels
valid = labels >= 0
phrases["centroid_sim"] = 0.0
phrases.loc[valid, "centroid_sim"] = (E[valid] * means[labels[valid]]).sum(1)

cluster_units = example_phrases_for_soft_topics(
    phrases.phrase.tolist(), R, n_top=8, n_sample=2, seed=0,
)
# Drop empty components for labelling
cluster_units = [cu for cu in cluster_units if cu["examples"]]
from multilogue.clients import label_stage_fingerprint
lab = runner.run(
    "labels", cluster_units, lambda cu: cu["key"],
    make_label_work(
        client, system=TOPIC_LABEL_SYSTEM,
        prompt_template=TOPIC_LABEL_PROMPT, model=models["label"],
    ),
    label_stage_fingerprint(
        models["label"], system=TOPIC_LABEL_SYSTEM, prompt=TOPIC_LABEL_PROMPT,
    ),
    quiet=True,
)
names = {
    cu["cluster"]: lab.get(cu["key"], {}).get("label", f"cluster {cu['cluster']}")
    for cu in cluster_units
}
print(names)
cl_desc = "\\n".join(
    f"{c}: {names.get(c, f'topic {c}')} — (mass {R[:, c].sum():.1f})" for c in range(k)
)
lens_runs = runner.run(
    "lenses", [1, 2], lambda r: str(r),
    make_lens_work(
        client, system="lens", prompt_template="Group:\\n<<CLUSTERS>>",
        cluster_description=cl_desc, model=models["label"], k=k,
    ),
    f"lenses|{models['label']}", quiet=True,
)
mapping, edited = resolve_lenses(k, lens_runs)
phrases["lens"] = phrases["cluster"].map(mapping)
print("lens mapping:", mapping, "edited:", edited)
"""
    ),
    code(
        """
viz.embedding_scatter(
    E, phrases["lens"],
    title="Embedding space coloured by lens (PCA view)",
    path=FIG / "03_pca_lenses.png",
)
"""
    ),
    md(
        """
# Outlook

Soft responsibilities $R$ and topic means feed notebook 08 (soft histograms →
document EMD; soft lenses under a separate fixed $\\sigma^2_{\\mathrm{lens}}$).
Notebook 04 can still use MAP or lens columns for document-weighted shares; soft
composition is the CIP-0017 default for transport. Notebook 09 consumes a
**locked** subject grain under format-gap $\\ell$ (multiverse holds $k$).
"""
    ),
]

# ---------------------------------------------------------------------------
# 04 Weight
# ---------------------------------------------------------------------------
NOTEBOOKS["04_weight.ipynb"] = [
    md(
        title_block(
            "04_weight.ipynb",
            "Document weighting — shares that respect documents",
            """
If we pool every phrase equally, a single long document dominates the
comparison. Multilogue averages within documents first, then across documents.
Uncertainty comes from a cluster bootstrap that resamples documents, not
phrases. This notebook teaches why the scientific object is usually the
document, and shows a dumbbell plot of group contrasts on lens shares.
""",
        )
    ),
    md(
        """
# Introduction

Public dialogue corpora are uneven: one consultation response may be a
paragraph, another a short essay. The scientific object is usually the document
(or conversation), so the weight should be too.

Write $s_{d,\\ell}$ for the share of phrases in document $d$ that fall under lens
$\\ell$. The group estimate is the mean of $s_{d,\\ell}$ over documents in the
group — not the mean over phrases. A cluster bootstrap resamples documents to
give intervals.
"""
    ),
    code(
        """
from IPython.display import display
import numpy as np
from multilogue.llm import StageRunner
from multilogue.cluster import (
    Embedder, frozen_or_new_assignments, make_lens_work, resolve_lenses,
    make_label_work, example_phrases_for_clusters,
)
from multilogue.weight import doc_profile, group_compare
from multilogue import viz
"""
    ),
    code(LOAD_CIMT_PAIR),
    code(RESOLVE_CLIENT),
    code(
        """
_runner_kw = {"max_workers": 2}
if client_kind == "fake":
    _runner_kw["sleep"] = lambda _: None
runner = StageRunner(root / "ckpt_w", root / "logs_w", **_runner_kw)
k = min(4, max(2, len(phrases) // 3))
E = np.asarray(
    Embedder(root / "emb", client, models["embed"])(phrases.phrase.tolist()), float
)
labels, centroids, _ = frozen_or_new_assignments(phrases, E, k, 0, root / "cl")
phrases = phrases.copy()
phrases["cluster"] = labels
phrases["centroid_sim"] = (E * centroids[labels]).sum(1)
cluster_units = example_phrases_for_clusters(phrases, k, 0)
from multilogue.clients import label_stage_fingerprint
lab = runner.run(
    "lab", cluster_units, lambda cu: cu["key"],
    make_label_work(
        client, system=TOPIC_LABEL_SYSTEM,
        prompt_template=TOPIC_LABEL_PROMPT, model=models["label"],
    ),
    label_stage_fingerprint(
        models["label"], system=TOPIC_LABEL_SYSTEM, prompt=TOPIC_LABEL_PROMPT,
        extra="weight",
    ),
    quiet=True,
)
names = {
    cu["cluster"]: lab.get(cu["key"], {}).get("label", f"c{cu['cluster']}")
    for cu in cluster_units
}
cl_desc = "\\n".join(f"{c}: {names[c]}" for c in range(k))
lens_runs = runner.run(
    "lens", [1], lambda r: str(r),
    make_lens_work(
        client, system="L", prompt_template="Group:\\n<<CLUSTERS>>",
        cluster_description=cl_desc, model=models["label"], k=k,
    ),
    f"lens|{models['label']}|{TOPIC_LABEL_PROMPT}", quiet=True,
)
mapping, _ = resolve_lenses(k, lens_runs)
phrases["lens"] = phrases["cluster"].map(mapping)

prof = doc_profile(phrases, "lens", sorted(phrases.lens.unique()))
display(prof.head())
rng = np.random.default_rng(0)
cmp = group_compare(
    phrases, "format", "lens", None, rng, reps=400,
    groups=sorted(phrases.format.unique()),
)
display(cmp)
"""
    ),
    code(
        """
g0, g1 = sorted(phrases.format.unique())[:2]
viz.group_compare_dumbbell(
    cmp, label_col="lens", group_a=g0, group_b=g1,
    path=FIG / "04_group_compare.png",
    title="Document-weighted lens shares",
)
"""
    ),
    md(
        """
The dumbbell compares document-weighted lens shares between groups. Intervals
come from resampling documents. Distances between whole topic *profiles*
(earth mover's distance under a cosine ground cost) are in notebook 08 — they
consume the same document-level shares.
"""
    ),
    md(
        """
# Outlook

A single pipeline path hides researcher degrees of freedom. Notebook 05 enumerates
a multiverse of analytic choices and asks how a consumer-supplied metric $\\ell$
moves.
"""
    ),
]

# ---------------------------------------------------------------------------
# 05 Multiverse
# ---------------------------------------------------------------------------
NOTEBOOKS["05_multiverse.ipynb"] = [
    md(
        title_block(
            "05_multiverse.ipynb",
            "Multiverse — which decisions move $\\ell$?",
            """
A single pipeline path hides researcher degrees of freedom. Following
Bell, Kampman, Dodge & Lawrence (2022), multilogue enumerates a Cartesian
product of analytic choices and asks a consumer-supplied callback for the
headline metric $\\ell$ under each configuration. Variance shares say which
decisions move $\\ell$. This notebook teaches the pattern with a transparent toy
$\\ell$ so the figures stay offline.
""",
        )
    ),
    md(
        """
# Introduction

The shared library must not hard-code paper-specific outcomes (format gaps,
technology distinctiveness, …). Consumers define $\\ell$; multilogue reports how
much of $\\ell$'s variance across the multiverse is associated with each
dimension. Shares are a first-cut one-way decomposition — interactions mean they
need not sum to one.
"""
    ),
    md(
        """
## The callback contract

For each configuration $c$ in the Cartesian product of dimensions, the consumer
returns a dict containing at least the scalar $\\ell(c)$. Multilogue never
inspects *how* $\\ell$ was computed — only that it is comparable across the grid.
"""
    ),
    code(
        """
from IPython.display import display
import numpy as np
from multilogue.multiverse import (
    enumerate_configurations, run_multiverse, variance_decomposition,
)
from multilogue import viz
"""
    ),
    code(
        """
dims = {"k": [4, 5, 6], "threshold": [0.4, 0.5, 0.6], "seed": [0, 1]}
configs = enumerate_configurations(dims)
print(len(configs), "configurations")

def evaluate(cfg):
    # Toy ℓ: depends strongly on threshold, weakly on k, barely on seed.
    ell = 0.5 + 0.4 * cfg["threshold"] + 0.05 * cfg["k"] + 0.01 * cfg["seed"]
    ell += np.random.default_rng(cfg["seed"] + 10 * cfg["k"]).normal(0, 0.01)
    return {"ell": ell}

results = run_multiverse(configs, evaluate)
display(results.head())
shares = variance_decomposition(results, "ell", list(dims))
display(shares)
"""
    ),
    code(
        """
viz.variance_share_bars(shares, path=FIG / "05_variance_shares.png")
viz.multiverse_metric_strip(
    results, "ell", colour_by="threshold", path=FIG / "05_metric_strip.png",
)
"""
    ),
    md(
        """
In this toy, threshold dominates the variance shares — by construction. On real
studies the same plots ask an empirical question: which analytic decisions move
the headline? Notebook 09 wires a *format-gap* $\\ell$ through the full Address
stack and reports the same decomposition.
"""
    ),
    md(
        """
# Outlook

Validation scaffolding — agreement statistics, stratified check sheets, evidence
packs — lives in notebook 06. Soft geometry and document EMD live in notebook 08.
"""
    ),
]

# ---------------------------------------------------------------------------
# 06 Validate
# ---------------------------------------------------------------------------
NOTEBOOKS["06_validate.ipynb"] = [
    md(
        title_block(
            "06_validate.ipynb",
            "Validate and report — agreement, sheets, evidence",
            """
Validation scaffolding is deliberately thin in the library: stratified sampling
for blind hand-check sheets, Cohen's $\\kappa$ and rank agreement helpers, and an
HTML evidence-pack shell. Coding schemes and playbooks stay with the study. This
notebook teaches those tools on the public CIMT corpus.
""",
        )
    ),
    md(
        """
# Introduction

When two codings of the same items exist (human–model or model–model), Cohen's
$\\kappa$ summarises chance-corrected agreement. It is a diagnostic, not a
substitute for reading the sheet. Stratified samples give researchers a
manageable blind-check set; the evidence pack is a readable HTML shell over
phrase tables.
"""
    ),
    code(
        """
from IPython.display import display, HTML
import numpy as np
import pandas as pd
from multilogue.validate import stratified_sample
from multilogue.weight import kappa, rank_agreement
from multilogue.report import evidence_pack, write_manifest
from multilogue.llm import StageRunner
from multilogue.cluster import (
    Embedder, frozen_or_new_assignments, example_phrases_for_clusters,
    make_label_work, make_lens_work, resolve_lenses,
)
"""
    ),
    code(
        """
a = ["A", "A", "B", "B", "A", "B", "A", "B"]
b = ["A", "B", "B", "B", "A", "B", "A", "A"]
print("kappa:", round(kappa(a, b), 3))

main = pd.Series([10.0, 8.0, 6.0, 4.0], index=list("WXYZ"))
other = pd.Series([9.5, 7.0, 6.5, 3.0], index=list("WXYZ"))
print("rank_agreement:", rank_agreement(main, other))
"""
    ),
    code(LOAD_CIMT_PAIR),
    code(RESOLVE_CLIENT),
    code(
        """
_runner_kw = {"max_workers": 2}
if client_kind == "fake":
    _runner_kw["sleep"] = lambda _: None
runner = StageRunner(root / "ckpt_v", root / "logs_v", **_runner_kw)
k = min(3, max(2, len(phrases) // 3))
E = np.asarray(
    Embedder(root / "emb", client, models["embed"])(phrases.phrase.tolist()), float
)
labels, centroids, _ = frozen_or_new_assignments(phrases, E, k, 0, root / "cl")
phrases = phrases.copy()
phrases["cluster"] = labels
phrases["centroid_sim"] = (E * centroids[labels]).sum(1)
cluster_units = example_phrases_for_clusters(phrases, k, 0)
from multilogue.clients import label_stage_fingerprint
lab = runner.run(
    "lab", cluster_units, lambda cu: cu["key"],
    make_label_work(
        client, system=TOPIC_LABEL_SYSTEM,
        prompt_template=TOPIC_LABEL_PROMPT, model=models["label"],
    ),
    label_stage_fingerprint(
        models["label"], system=TOPIC_LABEL_SYSTEM, prompt=TOPIC_LABEL_PROMPT,
        extra="validate",
    ),
    quiet=True,
)
names = {
    cu["cluster"]: lab.get(cu["key"], {}).get("label", f"c{cu['cluster']}")
    for cu in cluster_units
}
cl_desc = "\\n".join(f"{c}: {names[c]}" for c in range(k))
lens_runs = runner.run(
    "lens", [1], lambda r: str(r),
    make_lens_work(
        client, system="L", prompt_template="Group:\\n<<CLUSTERS>>",
        cluster_description=cl_desc, model=models["label"], k=k,
    ),
    f"lens|{models['label']}|{TOPIC_LABEL_PROMPT}", quiet=True,
)
phrases["lens"] = phrases["cluster"].map(resolve_lenses(k, lens_runs)[0])

sheet = stratified_sample(phrases, by="format", n_per_stratum=2, random_state=0)
display(sheet[["unit_id", "format", "phrase", "lens"]])
html = evidence_pack(
    phrases, root / "evidence_pack.html", group_col="format",
    title="CIMT evidence pack", seed=0,
)
write_manifest(root / "manifest.json", {"n_phrases": len(phrases), "source": "cimt"})
print("Evidence pack:", html)
display(HTML(f'<a href="{html}" target="_blank">Open evidence pack</a>'))
"""
    ),
    md(
        """
The stratified sheet is what a researcher would code blind. The evidence pack is
a navigable HTML view of the same phrase table — useful for reading, not a
substitute for $\\kappa$ or for substantive judgment.
"""
    ),
    md(
        """
# Outlook

Notebook 07 assembles notebooks 00–06 into one offline smoke experiment on
public CIMT units. Notebook 08 develops the soft geometry under Multilogue's
lens model.
"""
    ),
]

NOTEBOOKS["07_end_to_end.ipynb"] = [
    md(
        title_block(
            "07_end_to_end.ipynb",
            "End-to-end experiment on public CIMT",
            """
The pieces in notebooks 00–06 assemble into one callable,
`run_validation_experiment`, also exposed as `multilogue-validate`. It runs on
the public CIMT format pair with `phrases_from_units`. Labels/embeds use OpenAI
from ``.env`` when ``OPENAI_API_KEY`` is set (else FakeClient offline). Writes
tables, a multiverse decomposition, and an evidence pack. Use this notebook as
a smoke test after installing multilogue, then return to earlier notebooks when
you want to change one aspect at a time.
""",
        )
    ),
    md(
        """
# Introduction

A full Address path is a sequence of explicit stages: extract (or unit-as-phrase),
cluster, weight, multiverse, validate. The experiment helper wires them with
defaults so that “does the install work?” is one cell, not ten. It is not a
substitute for the methodological walkthroughs — it is the integration test you
can also read.
"""
    ),
    code(
        """
from IPython.display import display
from pathlib import Path
import pandas as pd
from multilogue.experiment import run_validation_experiment
from multilogue import viz
"""
    ),
    code(LOAD_CIMT_PAIR),
    code(
        """
out = Path("outputs/notebook_e2e")
summary = run_validation_experiment(
    out, units=units, phrases=phrases, k=4, quiet=True,
)
display(summary)
tables = out / "tables"
for name in ["yield.csv", "group_compare_lenses.csv", "variance_shares.csv"]:
    p = tables / name
    if p.is_file():
        print("—", name)
        display(pd.read_csv(p).head())
"""
    ),
    code(
        """
shares = pd.read_csv(tables / "variance_shares.csv")
viz.variance_share_bars(shares, path=FIG / "07_variance_shares.png")
print("Evidence pack:", out / "evidence_pack.html")
"""
    ),
    md(
        """
# Outlook

- Soft PPCA lenses and document EMD: notebook **08**.
- Formats-style Address (format as group, format-gap $\\ell$): notebook **09**.
- Live extract/label/embed: set ``OPENAI_API_KEY`` in ``.env`` (checkpoints still
  apply). Force offline with ``MULTILOGUE_FORCE_FAKE=1``. Access stays public CIMT.
"""
    ),
]

NOTEBOOKS["08_soft_distance.ipynb"] = [
    md(
        title_block(
            "08_soft_distance.ipynb",
            "Soft topics, soft lenses, and earth mover's distance",
            """
Soft-throughout Address keeps phrase→topic responsibilities from a mixture of
PPCA (notebook 03), then softens framing lenses with a second mixture of PPCAs
over topic means. Earth mover's distance appears twice — once when choosing
lens $\\sigma^2$ across independent LLM runs, and once when comparing documents
as distributions over topics (preferably soft histograms). Two noise floors stay
independent and fixed per run. This notebook teaches both geometries offline.
""",
        )
    ),
    md(
        """
# Introduction

Framing lenses — LLM labels such as economic, social, or environmental — are
useful for interpretation but brittle if treated as hard membership.
Responsibilities give every *topic* a distribution over lenses rather than a
single label. Separately, documents can be compared by transport distance on
their **soft** topic-share profiles without using lens names at all. Same
Kantorovich programme; different histograms and ground costs.
"""
    ),
    md(
        """
## Two $\\sigma^2$ floors (CIP-0017)

| Floor | Role |
|-------|------|
| Topic $\\sigma^2_{\\mathrm{topic}}$ | Fixed in `mppca_fit` (notebook 03) |
| Lens $\\sigma^2_{\\mathrm{lens}}$ | Shared when scoring lens runs; $\\sigma^{2\\star}$ by EMD below, then fixed |

Do not re-fit a different $\\sigma^2$ per lens replicate or per document.
"""
    ),
    code(ENSURE_POT),
    md(
        """
# Soft topics → soft document histograms
"""
    ),
    code(
        """
import numpy as np
import pandas as pd
from IPython.display import display
import matplotlib.pyplot as plt
from multilogue.mppca import mppca_fit, DEFAULT_TOPIC_SIGMA2
from multilogue import distance as dd
from multilogue import viz
"""
    ),
    code(
        """
rng = np.random.default_rng(0)
# Planted soft geometry: three subspace topics, then soft document histograms
n_per, d, k = 40, 12, 3
X = []
doc_ids = []
for j in range(k):
    mean = np.zeros(d)
    mean[2 * j] = 2.5
    cov = np.eye(d) * 0.08
    cov[2 * j, 2 * j] = 0.6
    Xj = rng.multivariate_normal(mean, cov, size=n_per)
    X.append(Xj)
    # two docs per topic component
    doc_ids += [f"d{j}a"] * (n_per // 2) + [f"d{j}b"] * (n_per - n_per // 2)
X = np.vstack(X)
fit = mppca_fit(X, k=k, sigma2=DEFAULT_TOPIC_SIGMA2, seed=0)
R = fit["responsibilities"]
P_soft, docs_soft, mass = dd.document_soft_topic_distributions(
    doc_ids, R, min_mass=5.0,
)
print(f"soft docs kept: {docs_soft}; mass={mass.to_dict()}")
print("P_soft rows sum:", P_soft.sum(axis=1))
"""
    ),
    md(
        """
`document_soft_topic_distributions` sums phrase responsibilities per document
and normalises — the CIP-0017 default for document EMD. The hard-count helper
`document_cluster_distributions` remains a sensitivity view.
"""
    ),
    md(
        """
# Soft lenses
"""
    ),
    md(
        """
## Mixture responsibilities

Hard clustering gives every point a single label: point $i$ belongs to component
$c(i)$ and to no other. A *mixture* model treats the component index as a latent
variable and returns a full posterior. Write $\\pi_c = p(c)$ for the prior weight
of component $c$, and $p(\\mathbf{y}_i\\mid c)$ for that component's density.
Bayes' rule yields the *responsibility*
$$
r_{ic}
=
p(c\\mid\\mathbf{y}_i)
=
\\frac{
\\pi_c\\, p(\\mathbf{y}_i\\mid c)
}{
\\sum_{c'} \\pi_{c'}\\, p(\\mathbf{y}_i\\mid c')
}.
$$
The row $(r_{i1},\\ldots,r_{iC})$ is a discrete distribution over components for
point $i$. Hard assignment is the special case that replaces this row by a
one-hot vector at $\\arg\\max_c r_{ic}$.
"""
    ),
    code(
        """
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from IPython.display import display
"""
    ),
    code(
        """
rng = np.random.default_rng(0)
means = np.array([[-1.2, 0.0], [1.2, 0.3]])
sigma2_sharp, sigma2_soft = 0.35, 2.0
priors = np.array([0.5, 0.5])
probes = np.array([
    [-1.2, 0.0], [-0.4, 0.1], [0.0, 0.15], [0.4, 0.2], [1.2, 0.3],
])

def responsibilities(X, means, sigma2, priors):
    log_lik = np.stack([
        -0.5 * np.sum((X - m) ** 2, axis=1) / sigma2 for m in means
    ], axis=1)
    log_post = log_lik + np.log(priors)[None, :]
    log_post -= log_post.max(axis=1, keepdims=True)
    post = np.exp(log_post)
    return post / post.sum(axis=1, keepdims=True)

cloud = np.vstack([
    rng.normal(means[0], np.sqrt(sigma2_sharp), size=(40, 2)),
    rng.normal(means[1], np.sqrt(sigma2_sharp), size=(40, 2)),
])
colours = ["#4C72B0", "#DD8452"]
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
for ax, sigma2, title in [
    (axes[0], sigma2_sharp, rf"sharp ($\\sigma^2={sigma2_sharp:g}$)"),
    (axes[1], sigma2_soft, rf"soft ($\\sigma^2={sigma2_soft:g}$)"),
]:
    R = responsibilities(probes, means, sigma2, priors)
    ax.scatter(cloud[:, 0], cloud[:, 1], s=12, c="#bbbbbb", alpha=0.7, zorder=1)
    for c, m in enumerate(means):
        ax.plot(*m, "o", color=colours[c], markersize=10, zorder=3)
        ell = Ellipse(
            m, 2 * np.sqrt(sigma2), 2 * np.sqrt(sigma2),
            fill=False, ec=colours[c], lw=1.5, ls="--", zorder=2,
        )
        ax.add_patch(ell)
    bar_w, bar_h = 0.35, 0.9
    for x, r in zip(probes, R):
        y0 = x[1] + 0.55
        ax.add_patch(plt.Rectangle(
            (x[0] - bar_w / 2, y0), bar_w * r[0], bar_h,
            color=colours[0], zorder=4, clip_on=False,
        ))
        ax.add_patch(plt.Rectangle(
            (x[0] - bar_w / 2 + bar_w * r[0], y0), bar_w * r[1], bar_h,
            color=colours[1], zorder=4, clip_on=False,
        ))
        ax.plot(x[0], x[1], "k.", markersize=8, zorder=5)
    ax.set_xlim(-2.6, 2.6)
    ax.set_ylim(-2.0, 2.8)
    ax.set_aspect("equal")
    ax.set_title(title)
fig.tight_layout()
fig.savefig(FIG / "08_mixture_responsibilities.png", dpi=120, bbox_inches="tight")
plt.show()
"""
    ),
    md(
        """
The figure places five probe points between two isotropic Gaussian components.
Stacked bars above each probe show the responsibility vector
$(r_{i1}, r_{i2})$. When $\\sigma^2$ is small, probes near a mean are almost
one-hot — soft assignment collapses toward hard labels. When $\\sigma^2$ is
large, the same probes carry mass on both components. Only the component
densities — and therefore the posteriors — have become flatter.
"""
    ),
    md(
        """
## Choosing $\\sigma^2$ by cross-run EMD

Independent LLM lens runs disagree. Multilogue fits a PPCA Gaussian per lens
over member cluster centroids, recomputes mixture weights for each candidate
$\\sigma^2$, and measures mean earth mover's distance between runs (ground cost =
cosine distance between lens means). We pick $\\sigma^{2\\star}$ that minimises
that EMD among values whose mean *effective support* lies in a meaningful-soft
band — so we do not collapse to the near-uniform high-$\\sigma^2$ solution where
group contrasts vanish.
"""
    ),
    code(
        """
from multilogue import soft as ms
"""
    ),
    code(
        """
k_lens, dim, n_lenses, n_runs = 24, 12, 6, 3
centroids = rng.normal(size=(k_lens, dim))
centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
mappings = []
for _ in range(n_runs):
    perm = rng.permutation(k_lens)
    mappings.append({
        f"L{j}": {"cluster_ids": perm[j::n_lenses].tolist()} for j in range(n_lenses)
    })

sweep = ms.sigma2_sweep_select(centroids, mappings)
curve = pd.DataFrame(sweep["curve"])
print(f"Selected lens σ²*: {sweep['sigma2_best']:.4g} ({sweep['selection']})")
print(f"Mean EMD at σ²*: {sweep['emd_best']:.4f}")
print(f"Mean eff. support: {sweep['eff_support_best']:.2f}")
display(curve[["sigma2", "mean_emd", "mean_eff_support"]].head(8))

W, names = ms.compute_mixture_weights(centroids, mappings[0], sweep["sigma2_best"])
print("Mixture weights shape:", W.shape, "lenses:", names)
"""
    ),
    code(
        """
viz.sigma2_stability_curve(curve, path=FIG / "08_sigma2_curve.png")
viz.mixture_weight_heatmap(W, names, path=FIG / "08_mixture_weights.png")
"""
    ),
    md(
        """
The stability curve shows mean cross-run EMD against $\\sigma^2$; the selected
value is marked when the band is non-empty. The heatmap shows soft mixture
weights for one run at $\\sigma^{2\\star}$ — rows are clusters, columns are lenses.
"""
    ),
    md(
        """
# Comparing distributions
"""
    ),
    md(
        """
## Earth mover's distance

The classical metaphor is dirt and work. One histogram is a pile of earth; the
other is the target landscape. A plan specifies how much mass travels from each
source bin to each destination bin. The total work is mass times ground cost,
summed over shipments. The EMD is the work of the *cheapest* such plan.

If the ground cost is a metric on the bins — for example cosine distance between
cluster centroids — the EMD inherits that geometry: documents whose topic mass
sits on nearby centroids look close; documents that raise unrelated topics look
far.
"""
    ),
    md(
        """
## Discrete optimal transport

Write source and target histograms $a\\in\\mathbb{R}^{m}$, $b\\in\\mathbb{R}^{n}$
with $\\sum_i a_i=\\sum_j b_j=1$. A coupling $\\Pi\\ge 0$ has row sums $a$ and
column sums $b$. Given ground cost $C$,
$$
\\mathrm{EMD}(a,b;C)
=
\\min_{\\Pi:\\,\\Pi\\mathbf{1}=a,\\,\\Pi^{\\top}\\mathbf{1}=b}
\\langle\\Pi,C\\rangle.
$$
This is Kantorovich's formulation. POT's `ot.emd` / `ot.emd2` return the optimal
cost and a coupling.
"""
    ),
    code(
        """
# Soft-histogram document EMD (CIP-0017 path)
prof_a = np.array([0.55, 0.35, 0.10])
prof_b = np.array([0.10, 0.35, 0.55])
rows_R = []
rows_doc = []
for i in range(8):
    for _ in range(40):
        rows_R.append(prof_a)
        rows_doc.append(f"a{i}")
    for _ in range(40):
        rows_R.append(prof_b)
        rows_doc.append(f"b{i}")
R_docs = np.asarray(rows_R, float)
# Add a little noise then renormalise so rows stay soft
R_docs = np.clip(R_docs + rng.normal(0, 0.02, size=R_docs.shape), 1e-6, None)
R_docs /= R_docs.sum(axis=1, keepdims=True)
P, docs, mass = dd.document_soft_topic_distributions(rows_doc, R_docs, min_mass=20.0)
means3 = fit["means"]
M = dd.cosine_ground_cost(means3)
D = dd.emd_distance_matrix(P, M)
groups = np.array(["A" if d.startswith("a") else "B" for d in docs])
pm = dd.permanova(D, groups, n_perm=199, seed=0)
mds = dd.classical_mds(D, 2)
print(f"Soft docs: {len(docs)}; PERMANOVA R²={pm['R2']:.3f}, p={pm['p_value']:.4f}")
"""
    ),
    code(
        """
coords = mds["coords"]
fig, ax = plt.subplots(figsize=(5, 4))
for g, marker in (("A", "o"), ("B", "s")):
    m = groups == g
    ax.scatter(coords[m, 0], coords[m, 1], label=g, marker=marker)
ax.set_xlabel("MDS 1")
ax.set_ylabel("MDS 2")
ax.set_title("Soft-histogram document EMD → classical MDS")
ax.legend()
fig.tight_layout()
fig.savefig(FIG / "08_doc_mds.png", dpi=120)
plt.show()
"""
    ),
    md(
        """
Two planted groups with different soft topic profiles separate under EMD → MDS.
PERMANOVA tests whether group locations differ in the transport geometry —
answering whether groups differ in *what* they raise, without using lens names.
"""
    ),
    md(
        """
# Outlook

What remains in consumer packages is study-specific: corpora, prompts, and the
precise definition of headline $\\ell$. Soft mixture weights also feed
`soft_group_compare` for document-weighted soft contrasts. Notebook 09 puts
format as the group column and a format-gap $\\ell$ through the full stack.
"""
    ),
    md(
        """
## References

Tipping, M.E., Bishop, C.M., 1999. Probabilistic principal component analysis.
Journal of the Royal Statistical Society, B 61, 611–622.
"""
    ),
]

# ---------------------------------------------------------------------------
# 09 Formats complexity
# ---------------------------------------------------------------------------
# Drawn flowchart for 09 (matplotlib; Mermaid in the markdown cell is for GitHub).
FLOW_09 = r'''# Drawn copy of the analysis flow (renders in Colab / plain Jupyter; Mermaid above is for GitHub).
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

stages = [
    (0.50, 0.96, "1. Setup"),
    (0.50, 0.88, "2. Access — public format pair"),
    (0.50, 0.80, "3. Assess — text diagnostics"),
    (0.50, 0.72, "4. Gold ℓ — mpos vs premise by format"),
    (0.50, 0.64, "5. Assess — interactive subject grain"),
    (0.50, 0.56, "6. Address — soft-throughout pipeline"),
]
inners = [
    (0.50, 0.46, "6a. Extract phrases"),
    (0.50, 0.38, "6b. Embed"),
    (0.50, 0.30, "6c. Soft cluster — MPPCA + topic σ² profile"),
    (0.50, 0.22, "6d. Topic labels + framing lenses"),
    (0.50, 0.14, "6e. Soft compare, EMD, multiverse ℓ (k held)"),
]
tail = [
    (0.50, 0.06, "7. Reading the run"),
    (0.50, -0.02, "8. Outlook"),
]

fig, ax = plt.subplots(figsize=(9.5, 12.0))
ax.set_xlim(0, 1)
ax.set_ylim(-0.06, 1.02)
ax.axis("off")
ax.set_title("Formats complexity — analysis flow", fontsize=14, pad=12)

def _box(x, y, text, *, face, edge, width=0.72, height=0.055, fontsize=10, weight="normal"):
    box = FancyBboxPatch(
        (x - width / 2, y - height / 2),
        width, height,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor=face, edgecolor=edge, linewidth=1.4, transform=ax.transAxes,
        clip_on=False,
    )
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            fontweight=weight, transform=ax.transAxes, color="#1a202c")

def _arrow(y0, y1, gap=0.028):
    ax.annotate(
        "", xy=(0.50, y1 + gap), xytext=(0.50, y0 - gap),
        xycoords=ax.transAxes, textcoords=ax.transAxes,
        arrowprops=dict(arrowstyle="->", color="#2c5282", lw=1.3),
    )

frame = FancyBboxPatch(
    (0.08, 0.105), 0.84, 0.40,
    boxstyle="round,pad=0.01,rounding_size=0.02",
    facecolor="#f7fafc", edgecolor="#a0aec0", linewidth=1.0,
    linestyle="--", transform=ax.transAxes, clip_on=False,
)
ax.add_patch(frame)
ax.text(0.10, 0.490, "Address internals (one StageRunner run)",
        fontsize=9, color="#4a5568", transform=ax.transAxes, style="italic")

for x, y, t in stages:
    _box(x, y, t, face="#e8f1fa", edge="#2c5282", weight="bold")
for x, y, t in inners:
    _box(x, y, t, face="#edf2f7", edge="#718096", width=0.78, height=0.05, fontsize=9)
for x, y, t in tail:
    _box(x, y, t, face="#e8f1fa", edge="#2c5282", weight="bold")

chain = [s[1] for s in stages] + [i[1] for i in inners] + [t[1] for t in tail]
for a, b in zip(chain, chain[1:]):
    _arrow(a, b)

fig.tight_layout()
plt.show()
path = FIG / "09_analysis_flow.png"
fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
print("Saved", path)
'''

NOTEBOOKS["09_formats_complexity.ipynb"] = [
    md(
        title_block(
            "09_formats_complexity.ipynb",
            "Formats complexity — comparing modes of convening",
            """
Public-dialogue studies often ask whether *how* people are convened changes
*what* they raise — workshop versus survey, chatbot versus in-person. Multilogue
does not hard-code “format”; it supplies the Address machinery with a group
column and a consumer metric $\\ell$. This notebook teaches that pattern: Access
on a public format pair; a paper-aligned gold $\\ell$ (major position vs premise
by format); **Assess** that locks subject grain before spend; then Address that
prefers a cached CIMT LLM run at locked $k{=}10$ with German municipal cycling
lenses (resuming via StageRunner when an API key is present). Offline Address
uses `phrases_from_units` on the same CIMT units (FakeClient only when no key /
``MULTILOGUE_FORCE_FAKE``). Multiverse holds $k$ (or $\\pm 1$) by default — not a
wide resolution grid.
""",
        )
    ),
    md(
        """
# Introduction

An `ai-dialogue-formats`-style study keeps PDF parsers, prompts, and the precise
definition of $\\ell$ in the consumer package. Multilogue owns extract → cluster →
weight → soft lenses → document distance → multiverse. The group column here is
`format` $\\in\\{\\mathrm{dialogue},\\mathrm{survey}\\}$. The headline $\\ell$ is a
document-weighted format gap on the lens with largest absolute difference —
recomputed under each analytic configuration without new LLM calls.

The flowchart below is the map for this notebook. Section headings use the same
numbers and titles so you can jump from the diagram to the matching cell.
"""
    ),
    md(
        """
## Analysis flow

Eight numbered stages. **Assess** covers text diagnostics (CIP-0008) and locks
subject grain (Bishop–Tipping dual view) before **Address** spends on lenses /
$\\ell$. Address expands into the soft-throughout pipeline that `StageRunner`
resumes from disk (extract → embed → MPPCA topics → labels/lenses → soft compare
/ EMD → multiverse $\\ell$ with $k$ **held** or $\\pm 1$ only).

```mermaid
flowchart TD
  S["1. Setup"] --> A["2. Access — public format pair"]
  A --> T["3. Assess — text diagnostics"]
  T --> G["4. Gold ℓ — mpos vs premise by format"]
  G --> AG["5. Assess — interactive subject grain"]
  AG --> AD["6. Address — soft-throughout pipeline"]

  subgraph ADDR["Address internals (one StageRunner run)"]
    direction TB
    E1["6a. Extract phrases"] --> E2["6b. Embed"]
    E2 --> E3["6c. Soft cluster — MPPCA + topic σ² profile"]
    E3 --> E4["6d. Topic labels + framing lenses"]
    E4 --> E5["6e. Soft compare, document EMD, multiverse ℓ (k held)"]
  end

  AD --> ADDR
  ADDR --> R["7. Reading the run"]
  R --> O["8. Outlook"]

  classDef stage fill:#e8f1fa,stroke:#2c5282,stroke-width:1.5px,color:#1a202c
  classDef inner fill:#f7fafc,stroke:#718096,stroke-width:1px,color:#1a202c
  class S,A,T,G,AG,AD,R,O stage
  class E1,E2,E3,E4,E5 inner
```

| # | Section | What it does |
|---|---------|--------------|
| 1 | Setup | Install / locate multilogue (first code cell) |
| 2 | Access — public format pair | CIMT dialogue vs survey |
| 3 | Assess — text diagnostics | Lengths / characters (CIP-0008); stop if debris dominates |
| 4 | Gold $\\ell$ — mpos vs premise by format | Paper-aligned argument codes; no LLM |
| 5 | Assess — interactive subject grain | Bishop–Tipping dual view; lock $k$ before Address |
| 6 | Address — soft-throughout pipeline | Cache / live / phrases_from_units; StageRunner stages |
| 7 | Reading the run | Catalogue, top concerns, findings markdown |
| 8 | Outlook | What stays in a consumer formats package |
"""
    ),
    code(FLOW_09),
    code(ENSURE_POT),
    md(
        """
## 2. Access — public format pair

CIMT Bonn cycling *dialogue* vs *survey* stand in for workshop vs survey.
Network is required once to populate the cache (`MULTILOGUE_DATAPATH` or
`~/.cache/multilogue`).
"""
    ),
    code(
        """
import os
from IPython.display import display
import pandas as pd
from multilogue.experiment import load_cimt_format_pair
from multilogue.extract import phrases_from_units
from multilogue.assess_base import assess_text_report, docs_per_group
from multilogue import viz
"""
    ),
    code(
        """
os.environ.setdefault("MULTILOGUE_ACCESS_YES", "1")
cimt_units, cimt_meta = load_cimt_format_pair(max_units_per=60)
if cimt_units is None:
    raise RuntimeError(
        "CIMT Access failed: "
        + str(cimt_meta.get("error", "unknown"))
        + ". Need network once to populate MULTILOGUE_DATAPATH / ~/.cache/multilogue."
    )
access_units = cimt_units
access_label = "CIMT Cycling-Dialogue-Bonn vs Survey-Bonn"
access_lang = "de"
display(cimt_meta)

print(access_label, "—", len(access_units), "units")
display(docs_per_group(access_units, "format"))
offline_phrases = phrases_from_units(access_units, extra_fields=["group", "format"])
print(f"{len(offline_phrases)} offline phrases (unit-as-phrase)")
"""
    ),
    md(
        """
## 3. Assess — text diagnostics

Question-agnostic checks (same helpers as notebook 01): are paragraphs a
sensible length? Do sentences and letter-tokens look sane for German? Is the
character inventory mostly letters/punctuation?

**Do not proceed to Address if** empty/too-short units dominate, sentence or
word lengths are wildly extreme, or ``other`` character share is high — fix
Access first (CIP-0008).
"""
    ),
    code(
        """
report = assess_text_report(access_units, lang=access_lang)
print(
    f"empty={len(report['empty'])}; "
    f"unit_flags={len(report['unit_length_flags'])}; "
    f"sent_flags={len(report['sentence_flags'])}; "
    f"word_flags={len(report['word_flags'])}; "
    f"char_flags={len(report['char_flags'])}"
)
display(report["size_summary"])
viz.unit_size_hist(
    report["sizes"], group_col="format", units=access_units,
    path=FIG / "09_unit_sizes.png",
)
viz.sentence_length_hist(report["sentences"], path=FIG / "09_sentence_lengths.png")
viz.word_length_hist(report["words"], path=FIG / "09_word_lengths.png")
viz.char_class_bars(report["char_classes"], path=FIG / "09_char_classes.png")
display(report["char_classes"])
display(report["unusual_codepoints"].head(8))
display(report["unit_length_flags"].head())
display(report["char_flags"].head())
"""
    ),
    md(
        """
## 4. Gold $\\ell$ — mpos vs premise by format

Romberg & Conrad (2021) report that map *dialogue* contributions are longer and
**premise-rich**, while the Bonn *survey* is short and **major-position-heavy**.
That contrast uses the dataset's gold `meta.code` (`mpos` / `premise`), not LLM
topics. The next cell is the paper-aligned headline $\\ell$: document-weighted
shares of each code by format. It needs no API key.
"""
    ),
    code(
        """
import importlib
import multilogue.experiment as _ml_exp
importlib.reload(_ml_exp)  # pick up edits without a full kernel restart
gold_argument_format_compare = _ml_exp.gold_argument_format_compare

gold_cmp = gold_argument_format_compare(access_units, formats=("dialogue", "survey"))
if len(gold_cmp):
    display(gold_cmp)
    for r in gold_cmp.itertuples():
        print(
            f"{r.metric}: dialogue {r.dialogue_pct:.1f}% vs survey {r.survey_pct:.1f}% "
            f"(Δ {r.difference:+.1f} pp)"
        )
else:
    print("No gold argument codes on these units.")
"""
    ),
    md(
        """
The sign of $\\Delta$ (survey − dialogue) should be **positive for mpos** and
**negative for premise** if this slice reproduces the paper. Topic clustering
below is a separate question — first **Assess** the subject grain, then Address.
"""
    ),
    md(
        """
## 5. Assess — interactive subject grain

Subject count $k$ defines how many topics the analysis admits. Putting a wide
$k$ grid in the factorial multiverse swamps quote / kind / membership and
answers the wrong stability question. CIP-0009 treats grain as **Assess EDA
with a human in the loop** (Bishop–Tipping geometry + LLM catalogues); only
after a **lock** does Address proceed.

Notebook 03 teaches the dual-view shell on CIMT phrases. Here we record
the lock policy for this formats run and keep the offline path
scripted (no widgets required). **Lock grain before Address spend** — do not
re-fit $k$ to maximise format-gap $\\ell$.
"""
    ),
    code(
        """
import os
from pathlib import Path
from multilogue.subject_grain import lock_subject_grain

# Formats Address default: hold locked primary k (CIP-0009). Optional pm1
# via resolve_k_multiverse(10, "pm1") → [9, 10, 11]. Wide grids only via
# explicit k_grid= on run_formats_complexity_demo (one-factor sweep).
PRIMARY_K = 10
grain_lock = lock_subject_grain(
    primary_k=PRIMARY_K,
    k_multiverse="hold",
    extra={
        "note": "Assess lock before Address; dual-view merge/split lives in notebook 03",
        "lock_before_spend": True,
    },
)
lock_dir = Path("outputs/notebook_formats_complexity")
lock_dir.mkdir(parents=True, exist_ok=True)
from multilogue.config import dump_json
dump_json(grain_lock, lock_dir / "subject_grain_lock.json")
print("subject-grain lock →", lock_dir / "subject_grain_lock.json")
print("primary_k =", grain_lock["primary_k"], "k_multiverse =", grain_lock["k_multiverse"])
display(grain_lock)
"""
    ),
    md(
        """
## 6. Address — soft-throughout pipeline

StageRunner checkpoints under `outputs/formats_cimt_llm/` mean a prior CIMT LLM
run can be reused without paying again. Internally this is stages **5a–5e** on
the flowchart (extract → embed → MPPCA + topic $\\sigma^2$ profile → labels/lenses
→ soft compare / EMD / multiverse $\\ell$ with **$k$ held**). The next cell
therefore:

1. loads `.env` if present;
2. if `OPENAI_API_KEY` is set — *resume or recache* the live
   demo at the **locked** $k{=}10$ with **German labels** and a fixed municipal
   cycling lens vocabulary (paths, parking, surface, junctions/tram,
   access/Rhein, mixed traffic). Completed extract/embed fingerprints are
   reused; new prompts re-run cluster labels and lenses — do not sweep a wide
   $k$ grid here;
3. else if a complete cached run is already on disk — use those tables;
4. else run offline Address on the same CIMT units via `phrases_from_units`
   (OpenAI from ``.env`` when available; FakeClient offline — no synthetic civic text).
"""
    ),
    code(
        """
import json
import os
import importlib
from pathlib import Path
from IPython.display import display, Markdown
from multilogue.config import load_dotenv
import multilogue.experiment as _ml_exp
importlib.reload(_ml_exp)
run_formats_complexity_demo = _ml_exp.run_formats_complexity_demo
CYCLING_LABEL_PROMPT = _ml_exp.CYCLING_LABEL_PROMPT
CYCLING_LENS_PROMPT = _ml_exp.CYCLING_LENS_PROMPT
from multilogue import viz
from multilogue.report import (
    cluster_catalogue, findings_markdown, top_phrases_by_group, write_findings,
)
"""
    ),
    code(
        """
load_dotenv(Path.cwd() / ".env")
load_dotenv(Path.cwd().parent / ".env")
# Prefer repo-root outputs when the notebook cwd is notebooks/.
for _root in (Path.cwd(), Path.cwd().parent):
    _cand = _root / "outputs" / "formats_cimt_llm"
    if (_cand / "tables" / "phrases_clustered.csv").is_file() or (_cand / "checkpoints").is_dir():
        LLM_OUT = _cand
        break
else:
    LLM_OUT = Path("outputs/formats_cimt_llm")

CACHE_TABLES = LLM_OUT / "tables"
cache_ready = (CACHE_TABLES / "phrases_clustered.csv").is_file()
key = os.environ.get("OPENAI_API_KEY", "").strip()
summary = None
address_source = None

if key:
    from multilogue.openai_client import OpenAIClient
    units_live = [
        u for u in access_units
        if (u.get("meta") or {}).get("code") != "non-arg"
    ]
    print(
        f"Live / resume CIMT Address → {LLM_OUT} "
        f"(locked k={PRIMARY_K}, German cycling lenses; {len(units_live)} units)"
    )
    summary = run_formats_complexity_demo(
        LLM_OUT,
        units=units_live,
        client=OpenAIClient(log_path=LLM_OUT / "logs" / "openai.jsonl"),
        kinds=("concern", "benefit"),
        extract_model="gpt-4.1-mini",
        embed_model="text-embedding-3-small",
        label_model="gpt-4.1-mini",
        k=PRIMARY_K, lens_runs=3, quiet=True, max_workers=4,
        label_prompt_template=CYCLING_LABEL_PROMPT,
        lens_prompt_template=CYCLING_LENS_PROMPT,
        k_multiverse="hold",
        subject_grain_lock=grain_lock,
    )
    tables = CACHE_TABLES
    address_source = "cimt_llm"
elif cache_ready:
    print(f"Using cached CIMT Address tables → {CACHE_TABLES.resolve()}")
    tables = CACHE_TABLES
    address_source = "cimt_cache"
    man = LLM_OUT / "run_manifest.json"
    if man.is_file():
        summary = json.loads(man.read_text())
        display(summary)
        if summary.get("k", 0) < 10:
            print(
                "Note: cache used k =", summary.get("k"),
                "— re-run with OPENAI_API_KEY to refresh at k=10 + German lenses.",
            )
else:
    out = Path("outputs/notebook_formats_complexity")
    print(
        "No CIMT cache and no API key — offline phrases_from_units →", out
    )
    summary = run_formats_complexity_demo(
        out,
        units=access_units,
        phrases=offline_phrases,
        k=PRIMARY_K,
        lens_runs=3,
        quiet=True,
        k_multiverse="hold",
        subject_grain_lock=grain_lock,
    )
    tables = out / "tables"
    address_source = "cimt_offline"

display(summary)
print("Address source:", address_source)
print("Subject grain:", (summary or {}).get("subject_grain") if isinstance(summary, dict) else None)
print("Multiverse dims (no wide k by default):", (summary or {}).get("multiverse_dims") if isinstance(summary, dict) else None)
print("Tables:", tables.resolve())
print("Checkpoints:", LLM_OUT / "checkpoints" if address_source != "cimt_offline" else tables.parent / "checkpoints")
"""
    ),
    code(
        """
for name in [
    "yield.csv",
    "gold_argument_format_compare.csv",
    "group_compare_format_lenses.csv",
    "soft_group_compare_format.csv",
    "sigma2_rules.csv",
    "doc_distance_pairwise.csv",
    "variance_shares_format_gap.csv",
]:
    p = tables / name
    if p.is_file():
        print("—", name)
        display(pd.read_csv(p).head(12))

shares_path = tables / "variance_shares_format_gap.csv"
if shares_path.is_file():
    shares = pd.read_csv(shares_path)
    viz.variance_share_bars(shares, path=FIG / "09_format_gap_variance.png")
    # CIP-0009: factorial dims should not be dominated by a silent k grid
    if "dimension" in shares.columns and (shares["dimension"] == "k").any():
        print("Note: k appears in variance shares — pass k_grid= only for deliberate sweeps.")
if isinstance(summary, dict):
    print("Soft:", summary.get("soft"))
    print("Distance:", summary.get("distance"))
    print("Locked subject grain:", summary.get("subject_grain"))
"""
    ),
    md(
        """
## 7. Reading the run

Findings summarise gold argument structure (when present), clusters, top
concerns by format, and which analytic decisions move the topic-gap $\\ell$.
Multiverse variance shares here are over quote / kind / membership — **not** a
wide $k$ grid (stage **5e** holds locked grain). This cell only reads tables —
no LLM calls.
"""
    ),
    code(
        """
ph = pd.read_csv(tables / "phrases_clustered.csv")
cmp = (
    pd.read_csv(tables / "group_compare_format_lenses.csv")
    if (tables / "group_compare_format_lenses.csv").is_file() else None
)
multi = (
    pd.read_csv(tables / "multiverse_format_gap.csv")
    if (tables / "multiverse_format_gap.csv").is_file() else None
)
shares = (
    pd.read_csv(tables / "variance_shares_format_gap.csv")
    if (tables / "variance_shares_format_gap.csv").is_file() else None
)
gold_path = tables / "gold_argument_format_compare.csv"
gold_tab = pd.read_csv(gold_path) if gold_path.is_file() else (
    gold_cmp if len(gold_cmp) else None
)
display(Markdown("### Cluster catalogue"))
display(cluster_catalogue(ph))
display(Markdown("### Top concerns by format"))
for g, tab in top_phrases_by_group(ph, kind="concern", n=8).items():
    display(Markdown(f"**{g}**"))
    display(tab)
if shares is not None:
    display(Markdown("### Multiverse variance shares"))
    display(shares)
title = (
    "CIMT dialogue vs survey — findings"
    if address_source in {"cimt_llm", "cimt_cache"}
    else "CIMT dialogue vs survey — findings (offline phrases)"
)
md_text = findings_markdown(
    ph, compare=cmp, multiverse=multi, variance_shares=shares,
    gold_compare=gold_tab, title=title,
)
write_findings(
    ph, tables / "findings.md", compare=cmp,
    multiverse=multi, variance_shares=shares,
    gold_compare=gold_tab, title=title,
)
display(Markdown(md_text))
"""
    ),
    md(
        """
## 8. Outlook

Multilogue owns the shared stages above. A formats-style consumer package still
keeps: PDF/docx Access, study prompts and experience coding, researcher-edited
lens YAML, and the precise definition of headline $\\ell$. Subject grain is
locked in Assess (notebook 03 dual-view shell; this notebook's lock artefact)
before Address spend. See the formats cookbook and the soft / EMD concepts page
in the documentation.
"""
    ),
]


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "notebooks"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.ipynb"):
        old.unlink()
    for name, cells in NOTEBOOKS.items():
        first_kind, first_src = cells[0]
        if first_kind != "md":
            raise SystemExit(f"{name}: first cell must be title markdown")
        nb = nbf.v4.new_notebook()
        # Title/abstract, then infrastructure setup, then teaching body.
        nb.cells = [nbf.v4.new_markdown_cell(first_src), nbf.v4.new_code_cell(SETUP)]
        for kind, src in cells[1:]:
            if kind == "md":
                nb.cells.append(nbf.v4.new_markdown_cell(src))
            else:
                nb.cells.append(nbf.v4.new_code_cell(src))
        nb.metadata = {
            "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"},
            "colab": {"provenance": []},
        }
        nbf.write(nb, out / name)
        first_line = next(
            (ln for ln in first_src.splitlines() if ln.startswith("# ")), name
        )
        print("wrote", name, f"({first_line})")


if __name__ == "__main__":
    main()
