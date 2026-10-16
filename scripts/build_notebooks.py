#!/usr/bin/env python3
"""Write pedagogical notebooks under notebooks/.

Edit this file, then regenerate:

    python scripts/build_notebooks.py
    pytest tests/test_notebooks_smoke.py -q

Style (talk-notebook pattern):
  - Title, abstract, then methodological prose with equations
  - Separate cells for library imports, computation, and figures
  - Interpretive markdown after each visualisation
  - Offline FakeClient path always runs; Colab bootstrap in setup
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf

GITHUB_REPO = "mlatcl/multilogue"
GITHUB_BRANCH = "main"
AUTHOR = "[Neil D. Lawrence](http://inverseprobability.com)"
DATE = "2026-10-16"

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

Why this shape? A consultation CSV, a Polis export, and a synthetic generator
must feed the same Address path. The reusable method lives *above* the file
format.
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
bundle = load("synthetic", n_docs_per_group=2, units_per_doc=2)
units = bundle["units"]
print(f"{len(units)} units; license={bundle['license']!r}")
display(units[0])
"""
    ),
    md(
        """
The first unit above is a dictionary conforming to the contract. Synthetic loaders
exist so pedagogy and CI never need a network or an API key. Real open corpora
use the same call shape.
"""
    ),
    md(
        """
## Switching sources

Following the old `pods.datasets.<name>()` pattern, each public corpus is a named
loader. `load(name, **kwargs)` returns units plus citation and licence metadata.
Downloads land in a gitignored cache (`MULTILOGUE_DATAPATH` or
`~/.cache/multilogue`), never in the repository.
"""
    ),
    code(
        """
import pandas as pd

# Default: generated units (no download). Uncomment Polis for a real CC BY corpus.
bundle = load("synthetic", n_docs_per_group=3, units_per_doc=3)
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
sizes, emptiness, crude vocabulary, coverage across documents. Anything that
needs a concern/benefit taxonomy, a framing lens, or a headline metric belongs
in Address. This notebook teaches that boundary and runs the Assess helpers on
synthetic units.
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
diagnostics, not findings.
"""
    ),
    md(
        """
## What counts as Assess

| In Assess | Not Assess (→ Address) |
|-----------|-------------------------|
| Unit lengths, empty flags | Concern / benefit extraction |
| Documents per group | Framing lenses |
| Token frequencies | Headline metric $\\ell$ |
| Coverage / missingness | Soft PPCA mixture weights |

The boundary is methodological, not computational. Counting tokens is cheap;
calling an LLM is expensive — but cost alone does not decide the phase.
"""
    ),
    code(
        """
from IPython.display import display
from multilogue.access import load
from multilogue.assess_base import (
    unit_size_table, docs_per_group, empty_unit_flags, token_frequency,
)
from multilogue import viz
"""
    ),
    code(
        """
units = load("synthetic", n_docs_per_group=4, units_per_doc=3)["units"]
sizes = unit_size_table(units)
empty = empty_unit_flags(units, min_words=4)
print(f"units={len(units)}; below min_words={len(empty)}")
display(docs_per_group(units, "group"))
display(token_frequency([u["text"] for u in units], top_n=15))
"""
    ),
    md(
        """
## Diagnostics

Unit-size histograms catch OCR debris and truncated chunks before any model
call. Document counts by group show whether later *document-weighted*
comparisons will rest on a thin sample.
"""
    ),
    code(
        """
viz.unit_size_hist(sizes, group_col="group", units=units, path=FIG / "01_unit_sizes.png")
viz.docs_per_group_bars(docs_per_group(units, "group"), path=FIG / "01_docs.png")
"""
    ),
    md(
        """
The figures are not answers to a research question. They characterise the corpus
so that Address — extraction, clustering, weighting — starts from a known base.
If the empty-unit count is large, fix Access or the min-words gate before paying
for LLM calls.
"""
    ),
    md(
        """
# Outlook

Address begins when we ask the model for structured points. Notebook 02 shows
narrow extraction passes, checkpoints, and quote support — the first place the
research question enters through prompts and kinds.
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
notebook teaches those ideas with FakeClient so pedagogy never needs an API key.
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
model so the same work is not repeated.
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
from collections import defaultdict
from IPython.display import display
from multilogue.access import load
from multilogue.dummy import FakeClient
from multilogue.extract import make_extract_work, phrase_table, yield_report
from multilogue.llm import StageRunner
from multilogue.text import quote_support
from multilogue import viz
"""
    ),
    code(
        """
units = load("synthetic", n_docs_per_group=3, units_per_doc=3)["units"]
units_by_id = {u["unit_id"]: u for u in units}
client = FakeClient()
runner = StageRunner(
    FIG.parent / "ckpt_extract", FIG.parent / "logs_extract",
    max_workers=2, sleep=lambda _: None,
)

extraction = {}
for kind in ("concern", "benefit"):
    work = make_extract_work(
        client, kind=kind, system="extract",
        user_for_unit=lambda u, k=kind: u["text"],
        model="fake-small", sentinel=f"NO_{kind.upper()}", quote_threshold=0.8,
    )
    extraction[kind] = runner.run(
        f"extract_{kind}", units, lambda u: u["unit_id"], work,
        f"extract|{kind}|fake-small|v1", quiet=True,
    )

phrases = phrase_table(
    extraction, units_by_id, kinds=["concern", "benefit"],
    extra_unit_fields=["group"],
)
display(phrases.head())
"""
    ),
    code(
        """
by_group = defaultdict(list)
for u in units:
    by_group[u["group"]].append(u["unit_id"])
yd = yield_report(extraction, dict(by_group))
display(yd)
viz.yield_bars(yd, path=FIG / "02_yield.png")
"""
    ),
    md(
        """
Yield bars show how many units produced at least one phrase of each kind, by
group. FakeClient returns bank phrases that appear in the synthetic units, so
quote checks can fire without a paid model. With a real client the same
checkpoint layout applies.
"""
    ),
    code(
        """
demo_text = units[0]["text"]
span = " ".join(demo_text.split()[:8])
print("support(exact span):", round(quote_support(span, demo_text), 3))
print("support(noise):", round(quote_support("completely unrelated words", demo_text), 3))
if "verified" in phrases.columns:
    display(phrases.groupby(["group", "kind"]).verified.mean().rename("pct_verified"))
"""
    ),
    md(
        """
# Outlook

Phrases alone are not a comparison. Notebook 03 places them in a shared
embedding space, freezes $k$-means assignments when the phrase set is unchanged,
and proposes blind labels and framing lenses.
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
            "Shared topic space — embed, freeze, label, lens",
            """
Once phrases exist, we place them in one embedding space and partition with
$k$-means. Two design choices matter more than the brand of embedder: frozen
assignments when the phrase set is unchanged, and blind labels and lenses
proposed without seeing group labels. This notebook teaches those choices and
shows a PCA view as a diagnostic — not as the generative story for the phrases.
""",
        )
    ),
    md(
        """
# Introduction

Hard clustering gives every phrase a single topic label. Multilogue embeds
phrases, runs $k$-means, and optionally freezes the assignment vector so later
notebooks do not silently reshuffle topics when $k$-means initialisation differs
across machines.

Labels name clusters; lenses group clusters into coarser framings (economic,
social, …). Both are proposed from example phrases alone — *format-blind* or
*group-blind* — so the taxonomy is not fitted to the comparison we later want
to make.
"""
    ),
    md(
        """
## Frozen assignments

$k$-means is sensitive to initialisation and is not bit-stable across machines.
When the phrase set (and fingerprint) is unchanged we reuse saved assignments.
That is a reproducibility device: the scientific claim is “these phrases under
this embedding and $k$”, not “whatever $k$-means happened to return today”.
"""
    ),
    md(
        """
## PCA as a viewing device

The scatter below projects embeddings onto the first two principal components.
Classical PCA finds linear directions of high variance; it is a *view*, not the
generative model for the phrases. Soft lens memberships under probabilistic PCA
and $\\sigma^2$ chosen by earth mover's distance live in notebook 08.
"""
    ),
    code(
        """
from IPython.display import display
import numpy as np
from multilogue.access import load
from multilogue.dummy import FakeClient
from multilogue.extract import make_extract_work, phrase_table
from multilogue.llm import StageRunner
from multilogue.cluster import (
    Embedder, frozen_or_new_assignments, example_phrases_for_clusters,
    make_label_work, make_lens_work, resolve_lenses,
)
from multilogue import viz
"""
    ),
    code(
        """
units = load("synthetic", n_docs_per_group=3, units_per_doc=3)["units"]
units_by_id = {u["unit_id"]: u for u in units}
client = FakeClient()
root = FIG.parent
runner = StageRunner(root / "ckpt_cl", root / "logs_cl", max_workers=2, sleep=lambda _: None)
extraction = {}
for kind in ("concern", "benefit"):
    work = make_extract_work(
        client, kind=kind, system="e",
        user_for_unit=lambda u, k=kind: u["text"], model="fake-small",
        sentinel=f"NO_{kind.upper()}",
    )
    extraction[kind] = runner.run(
        f"ex_{kind}", units, lambda u: u["unit_id"], work, f"ex|{kind}", quiet=True,
    )
phrases = phrase_table(
    extraction, units_by_id, kinds=["concern", "benefit"], extra_unit_fields=["group"],
)
k = 4
embedder = Embedder(root / "emb", client, model="fake-emb")
E = np.asarray(embedder(phrases.phrase.tolist()), float)
labels, centroids, frozen = frozen_or_new_assignments(
    phrases, E, k, 0, root / "clusters",
)
phrases = phrases.copy()
phrases["cluster"] = labels
phrases["centroid_sim"] = (E * centroids[labels]).sum(1)
print("frozen_assignments:", frozen)
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
Cluster sizes show whether $k$ produced empty or tiny topics. The PCA scatter
colours phrases by hard cluster. Hopeless overlap suggests revisiting $k$ or the
phrase set before interpreting shares.
"""
    ),
    md(
        """
## Blind labels and lenses

Labels name clusters; lenses group them. Researchers may edit the lens mapping
afterwards — the point of the first pass is a blind proposal.
"""
    ),
    code(
        """
cluster_units = example_phrases_for_clusters(phrases, k, 0)
lab = runner.run(
    "labels", cluster_units, lambda cu: cu["key"],
    make_label_work(
        client, system="label",
        prompt_template="Label these:\\n<<PHRASES>>", model="fake-small",
    ),
    "labels|v1", quiet=True,
)
names = {
    cu["cluster"]: lab.get(cu["key"], {}).get("label", f"cluster {cu['cluster']}")
    for cu in cluster_units
}
print(names)
cl_desc = "\\n".join(
    f"{c}: {names[c]} — ({int((phrases.cluster == c).sum())})" for c in range(k)
)
lens_runs = runner.run(
    "lenses", [1, 2], lambda r: str(r),
    make_lens_work(
        client, system="lens", prompt_template="Group:\\n<<CLUSTERS>>",
        cluster_description=cl_desc, model="fake-small", k=k,
    ),
    f"lenses|{cl_desc[:60]}", quiet=True,
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

Hard lens labels are useful but brittle. Notebook 04 turns cluster or lens
assignments into *document-weighted* shares so long documents do not drown short
ones. Notebook 08 softens lenses with a mixture of probabilistic PCAs.
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
from multilogue.access import load
from multilogue.dummy import FakeClient
from multilogue.extract import make_extract_work, phrase_table
from multilogue.llm import StageRunner
from multilogue.cluster import (
    Embedder, frozen_or_new_assignments, make_lens_work, resolve_lenses,
    make_label_work, example_phrases_for_clusters,
)
from multilogue.weight import doc_profile, group_compare
from multilogue import viz
"""
    ),
    code(
        """
units = load("synthetic", n_docs_per_group=4, units_per_doc=3)["units"]
units_by_id = {u["unit_id"]: u for u in units}
client = FakeClient()
root = FIG.parent
runner = StageRunner(root / "ckpt_w", root / "logs_w", max_workers=2, sleep=lambda _: None)
extraction = {}
for kind in ("concern", "benefit"):
    work = make_extract_work(
        client, kind=kind, system="e",
        user_for_unit=lambda u, k=kind: u["text"], model="fake-small",
        sentinel=f"NO_{kind.upper()}",
    )
    extraction[kind] = runner.run(
        f"ex_{kind}", units, lambda u: u["unit_id"], work, f"ex|{kind}", quiet=True,
    )
phrases = phrase_table(
    extraction, units_by_id, kinds=["concern", "benefit"], extra_unit_fields=["group"],
)
k = 4
E = np.asarray(Embedder(root / "emb", client, "fake-emb")(phrases.phrase.tolist()), float)
labels, centroids, _ = frozen_or_new_assignments(phrases, E, k, 0, root / "cl")
phrases = phrases.copy()
phrases["cluster"] = labels
phrases["centroid_sim"] = (E * centroids[labels]).sum(1)
cluster_units = example_phrases_for_clusters(phrases, k, 0)
lab = runner.run(
    "lab", cluster_units, lambda cu: cu["key"],
    make_label_work(
        client, system="l", prompt_template="Label:\\n<<PHRASES>>", model="fake-small",
    ),
    "lab", quiet=True,
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
        cluster_description=cl_desc, model="fake-small", k=k,
    ),
    "lens", quiet=True,
)
mapping, _ = resolve_lenses(k, lens_runs)
phrases["lens"] = phrases["cluster"].map(mapping)

prof = doc_profile(phrases, "lens", sorted(phrases.lens.unique()))
display(prof.head())
rng = np.random.default_rng(0)
cmp = group_compare(
    phrases, "group", "lens", None, rng, reps=400,
    groups=sorted(phrases.group.unique()),
)
display(cmp)
"""
    ),
    code(
        """
g0, g1 = sorted(phrases.group.unique())[:2]
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
notebook teaches those tools on synthetic labels and phrases.
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
from multilogue.access import load
from multilogue.validate import stratified_sample
from multilogue.weight import kappa, rank_agreement
from multilogue.report import evidence_pack, write_manifest
from multilogue.dummy import FakeClient
from multilogue.extract import make_extract_work, phrase_table
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
    code(
        """
units = load("synthetic", n_docs_per_group=2, units_per_doc=3)["units"]
units_by_id = {u["unit_id"]: u for u in units}
client = FakeClient()
root = FIG.parent
runner = StageRunner(root / "ckpt_v", root / "logs_v", max_workers=2, sleep=lambda _: None)
extraction = {}
for kind in ("concern", "benefit"):
    work = make_extract_work(
        client, kind=kind, system="e",
        user_for_unit=lambda u, k=kind: u["text"], model="fake-small",
        sentinel=f"NO_{kind.upper()}",
    )
    extraction[kind] = runner.run(
        f"ex_{kind}", units, lambda u: u["unit_id"], work, f"ex|{kind}", quiet=True,
    )
phrases = phrase_table(
    extraction, units_by_id, kinds=["concern", "benefit"], extra_unit_fields=["group"],
)
k = 3
E = np.asarray(Embedder(root / "emb", client, "fake-emb")(phrases.phrase.tolist()), float)
labels, centroids, _ = frozen_or_new_assignments(phrases, E, k, 0, root / "cl")
phrases = phrases.copy()
phrases["cluster"] = labels
phrases["centroid_sim"] = (E * centroids[labels]).sum(1)
cluster_units = example_phrases_for_clusters(phrases, k, 0)
lab = runner.run(
    "lab", cluster_units, lambda cu: cu["key"],
    make_label_work(
        client, system="l", prompt_template="Label:\\n<<PHRASES>>", model="fake-small",
    ),
    "lab", quiet=True,
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
        cluster_description=cl_desc, model="fake-small", k=k,
    ),
    "lens", quiet=True,
)
phrases["lens"] = phrases["cluster"].map(resolve_lenses(k, lens_runs)[0])

sheet = stratified_sample(phrases, by="group", n_per_stratum=2, random_state=0)
display(sheet[["unit_id", "group", "phrase", "lens"]])
html = evidence_pack(
    phrases, root / "evidence_pack.html", group_col="group",
    title="Synthetic evidence pack", seed=0,
)
write_manifest(root / "manifest.json", {"n_phrases": len(phrases), "synthetic": True})
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

Notebook 07 assembles notebooks 00–06 into one offline smoke experiment.
Notebook 08 develops the soft geometry under Multilogue's lens model.
"""
    ),
]

# ---------------------------------------------------------------------------
# 07 End-to-end
# ---------------------------------------------------------------------------
NOTEBOOKS["07_end_to_end.ipynb"] = [
    md(
        title_block(
            "07_end_to_end.ipynb",
            "End-to-end synthetic experiment",
            """
The pieces in notebooks 00–06 assemble into one callable,
`run_validation_experiment`, also exposed as `multilogue-validate`. It uses only
synthetic units and FakeClient — safe for CI and Colab without keys — and writes
tables, a multiverse decomposition, and an evidence pack. Use this notebook as a
smoke test after installing multilogue, then return to earlier notebooks when you
want to change one aspect at a time.
""",
        )
    ),
    md(
        """
# Introduction

A full Address path is a sequence of explicit stages: extract, cluster, weight,
multiverse, validate. The experiment helper wires them with defaults so that
“does the install work?” is one cell, not ten. It is not a substitute for the
methodological walkthroughs — it is the integration test you can also read.
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
    code(
        """
out = Path("outputs/notebook_e2e")
summary = run_validation_experiment(
    out, n_docs_per_group=3, units_per_doc=3, k=4, quiet=True,
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
- Swap `load("synthetic")` for a public corpus in Access when you want real civic
  text; replace FakeClient with an OpenAI or LiteLLM client for real extraction
  (checkpoints still apply).
"""
    ),
]

# ---------------------------------------------------------------------------
# 08 Soft / EMD  (absorbs talk pedagogical core)
# ---------------------------------------------------------------------------
NOTEBOOKS["08_soft_distance.ipynb"] = [
    md(
        title_block(
            "08_soft_distance.ipynb",
            "Soft lenses and earth mover's distance",
            """
Hard $k$-means plus a single lens map assigns each cluster to one framing. Soft
Address replaces one-hot lens assignment with a mixture of probabilistic PCAs:
each lens is a Gaussian in embedding space, all sharing isotropic noise
$\\sigma^2$. Earth mover's distance appears twice — once when choosing
$\\sigma^2$ across independent lens runs, and once when comparing documents as
distributions over clusters. This notebook teaches both geometries and runs the
multilogue APIs offline.
""",
        )
    ),
    md(
        """
# Introduction

Framing lenses — LLM labels such as economic, social, or environmental — are
useful for interpretation but brittle if treated as hard membership.
Responsibilities give every cluster a distribution over lenses rather than a
single label. Separately, documents can be compared by transport distance on
their cluster-share profiles without using lens names at all. Same Kantorovich
programme; different histograms and ground costs.
"""
    ),
    code(ENSURE_POT),
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
import pandas as pd
from multilogue import soft as ms
from multilogue import viz
"""
    ),
    code(
        """
rng = np.random.default_rng(0)
k, dim, n_lenses, n_runs = 24, 12, 6, 3
centroids = rng.normal(size=(k, dim))
centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)
mappings = []
for _ in range(n_runs):
    perm = rng.permutation(k)
    mappings.append({
        f"L{j}": {"cluster_ids": perm[j::n_lenses].tolist()} for j in range(n_lenses)
    })

sweep = ms.sigma2_sweep_select(centroids, mappings)
curve = pd.DataFrame(sweep["curve"])
print(f"Selected σ²: {sweep['sigma2_best']:.4g} ({sweep['selection']})")
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
from multilogue import distance as dd
"""
    ),
    code(
        """
prof_a = np.array([0.4, 0.4, 0.05, 0.05, 0.05, 0.05])
prof_b = np.array([0.05, 0.05, 0.05, 0.05, 0.4, 0.4])
docs = {f"a{i}": prof_a for i in range(8)}
docs.update({f"b{i}": prof_b for i in range(8)})
rows = []
for doc, profile in docs.items():
    for c in rng.choice(6, size=120, p=profile):
        rows.append({"doc_id": doc, "cluster": int(c)})
phrases = pd.DataFrame(rows)
group = {d: ("A" if d.startswith("a") else "B") for d in docs}
C6 = centroids[:6]
res = dd.run_document_distance_analysis(
    phrases, C6, group, min_phrases=50, n_perm=199, seed=0,
)
pm = res["permanova"]
print(f"Docs kept: {len(res['docs'])}; dropped: {res['dropped_docs']}")
print(f"PERMANOVA R²={pm['R2']:.3f}, p={pm['p_value']:.4f}")
display(res["pairwise"][["comparison", "R2", "p_value", "dispersion_p"]])
"""
    ),
    code(
        """
coords = res["mds"]["coords"]
fig, ax = plt.subplots(figsize=(5, 4))
for g, marker in (("A", "o"), ("B", "s")):
    m = res["groups"] == g
    ax.scatter(coords[m, 0], coords[m, 1], label=g, marker=marker)
ax.set_xlabel("MDS 1")
ax.set_ylabel("MDS 2")
ax.set_title("Document EMD → classical MDS")
ax.legend()
fig.tight_layout()
fig.savefig(FIG / "08_doc_mds.png", dpi=120)
plt.show()
"""
    ),
    md(
        """
Two planted groups with different cluster profiles separate under EMD → MDS.
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
on a public format pair, then Address that prefers a cached CIMT LLM run
(resuming via StageRunner when an API key is present), with a FakeClient
formats demo as the offline fallback — soft contrasts, document EMD, and a
multiverse over analytic decisions.
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
"""
    ),
    code(ENSURE_POT),
    md(
        """
## Access — public format pair

CIMT Bonn cycling *dialogue* vs *survey* stand in for workshop vs survey when
the network is available. Assess without the analysis question: coverage by
format and unit sizes. If CIMT cannot be fetched, we fall back to a short
synthetic Access table so the notebook still runs.
"""
    ),
    code(
        """
import os
from IPython.display import display
import pandas as pd
from multilogue.experiment import load_cimt_format_pair, format_tagged_units
from multilogue.assess_base import docs_per_group, unit_size_table
"""
    ),
    code(
        """
os.environ.setdefault("MULTILOGUE_ACCESS_YES", "1")
cimt_units, cimt_meta = load_cimt_format_pair(max_units_per=60)
if cimt_units is None:
    print("CIMT unavailable:", cimt_meta.get("error", "unknown"))
    access_units = format_tagged_units(n_docs_per_group=3, units_per_doc=2)
    access_label = "synthetic format stand-in (Access fallback)"
else:
    access_units = cimt_units
    access_label = "CIMT Cycling-Dialogue-Bonn vs Survey-Bonn"
    display(cimt_meta)

print(access_label, "—", len(access_units), "units")
display(docs_per_group(access_units, "format"))
display(unit_size_table(access_units).describe())
"""
    ),
    md(
        """
## Address — cache first, then FakeClient fallback

StageRunner checkpoints under `outputs/formats_cimt_llm/` mean a prior CIMT LLM
run can be reused without paying again. The next cell therefore:

1. loads `.env` if present;
2. if `OPENAI_API_KEY` is set and CIMT units exist — *resume or recache* the live
   demo (completed fingerprints are skipped);
3. else if a complete cached run is already on disk — use those tables;
4. else run the offline FakeClient formats demo so Colab / CI still work.

German CIMT text does not match the English FakeClient phrase bank, so the
synthetic fallback keeps the same `format` group mechanics without an API.
"""
    ),
    code(
        """
import json
import os
from pathlib import Path
from IPython.display import display, Markdown
from multilogue.config import load_dotenv
from multilogue.experiment import run_formats_complexity_demo
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

if key and cimt_units is not None:
    from multilogue.openai_client import OpenAIClient
    units_live = [
        u for u in cimt_units
        if (u.get("meta") or {}).get("code") != "non-arg"
    ]
    print(
        f"Live / resume CIMT Address → {LLM_OUT} "
        f"({len(units_live)} units; checkpoints reused when fingerprints match)"
    )
    summary = run_formats_complexity_demo(
        LLM_OUT,
        units=units_live,
        client=OpenAIClient(log_path=LLM_OUT / "logs" / "openai.jsonl"),
        kinds=("concern", "benefit"),
        extract_model="gpt-4.1-mini",
        embed_model="text-embedding-3-small",
        label_model="gpt-4.1-mini",
        k=6, lens_runs=3, quiet=True, max_workers=4,
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
else:
    out = Path("outputs/notebook_formats_complexity")
    print(
        "No CIMT cache and no API key — FakeClient formats demo →", out
    )
    summary = run_formats_complexity_demo(
        out, n_docs_per_group=4, units_per_doc=3, k=5, lens_runs=3, quiet=True,
    )
    tables = out / "tables"
    address_source = "fakeclient"

display(summary)
print("Address source:", address_source)
print("Tables:", tables.resolve())
print("Checkpoints:", LLM_OUT / "checkpoints" if address_source != "fakeclient" else tables.parent / "checkpoints")
"""
    ),
    code(
        """
for name in [
    "yield.csv",
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
if isinstance(summary, dict):
    print("Soft:", summary.get("soft"))
    print("Distance:", summary.get("distance"))
"""
    ),
    md(
        """
## Reading the run

Findings summarise clusters, top concerns by format, and which analytic
decisions move $\\ell$. This cell only reads tables — no LLM calls.
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
    else "Dialogue vs survey — findings (FakeClient)"
)
md_text = findings_markdown(
    ph, compare=cmp, multiverse=multi, variance_shares=shares, title=title,
)
write_findings(
    ph, tables / "findings.md", compare=cmp,
    multiverse=multi, variance_shares=shares, title=title,
)
display(Markdown(md_text))
"""
    ),
    md(
        """
# Outlook

Multilogue owns the shared stages above. A formats-style consumer package still
keeps: PDF/docx Access, study prompts and experience coding, researcher-edited
lens YAML, and the precise definition of headline $\\ell$. See the formats
cookbook and the soft / EMD concepts page in the documentation.
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
