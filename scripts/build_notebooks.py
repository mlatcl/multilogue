#!/usr/bin/env python3
"""Write pedagogical notebooks under notebooks/. Edit here, then run:

    python scripts/build_notebooks.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf

GITHUB_REPO = "mlatcl/multilogue"
GITHUB_BRANCH = "main"

SETUP = r'''#@title Setup (run first)
# Free path: synthetic units + FakeClient (no API key).
# Optional: load("polis", ...) downloads public open data into a local cache.

import sys, subprocess, pathlib

IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q",
        "matplotlib", "pandas", "numpy", "scikit-learn", "pyyaml",
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

from IPython.display import display, HTML, Markdown
from multilogue.notebook import setup

FIG = setup(figures_dir="outputs/notebook_figures")
print("Figures →", FIG)
'''


def colab_badge(name: str) -> str:
    url = (
        f"https://colab.research.google.com/github/{GITHUB_REPO}/blob/"
        f"{GITHUB_BRANCH}/notebooks/{name}"
    )
    return (
        f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})\n"
    )


# Each notebook: list of ("md"|"code", source)
NOTEBOOKS: dict[str, list[tuple[str, str]]] = {
    "00_access.ipynb": [
        (
            "md",
            "# 00 · Access — getting civic text into units\n\n"
            "Multilogue organises analysis around three *aspects* of the Fynesse framework — "
            "**Access**, **Assess**, and **Address** — rather than rigid stages. "
            "Access is the work of making data electronically usable under a clear contract. "
            "This notebook shows how multilogue keeps that contract small, and how named "
            "public sources can be switched without changing the rest of the pipeline.\n\n"
            "**Why a unit contract?** Downstream methods (extraction, clustering, weighting) "
            "should not know whether a paragraph came from a consultation CSV, a Polis export, "
            "or a synthetic generator. The reusable method lives above the file format.",
        ),
        (
            "md",
            "## The Unit\n\n"
            "A unit is one analysable span: an id, a document id, and text. Optional fields "
            "carry context for quote checks and free-form metadata. Multilogue never parses "
            "study PDFs here; study packages (or the open-data loaders below) hand it units.",
        ),
        (
            "code",
            "from multilogue.access import list_sources, load\n"
            "from multilogue.protocols import Unit\n\n"
            "print(\"Registered sources:\", list_sources())\n"
            "bundle = load(\"synthetic\", n_docs_per_group=2, units_per_doc=2)\n"
            "units = bundle[\"units\"]\n"
            "print(f\"{len(units)} units; license={bundle['license']!r}\")\n"
            "display(units[0])",
        ),
        (
            "md",
            "## Switching sources (pods-style)\n\n"
            "Following the old `pods.datasets.<name>()` pattern, each public corpus is a "
            "named loader. The same call shape — `load(name, **kwargs)` — returns units plus "
            "citation and licence metadata. Downloads land in a gitignored cache "
            "(`MULTILOGUE_DATAPATH` or `~/.cache/multilogue`), never in the repository.\n\n"
            "The cell below uses **synthetic** data by default so the notebook runs offline. "
            "Uncomment the Polis line to pull a real open CC BY conversation (needs network).",
        ),
        (
            "code",
            "import pandas as pd\n\n"
            "# Default: generated units (no download)\n"
            "bundle = load(\"synthetic\", n_docs_per_group=3, units_per_doc=3)\n"
            "# Optional public open data (CC BY 4.0) — uncomment to try:\n"
            "# bundle = load(\"polis\", conversation=\"vtaiwan.uberx\", max_units=80)\n\n"
            "units = bundle[\"units\"]\n"
            "print(bundle[\"citation\"][:200], \"…\")\n"
            "print(\"path:\", bundle[\"path\"])\n"
            "df = pd.DataFrame(units)\n"
            "display(df[[\"unit_id\", \"doc_id\", \"text\"]].head())\n"
            "print(\"docs:\", df.doc_id.nunique(), \"units:\", len(df))",
        ),
        (
            "md",
            "## Diagnostic: units and documents by group\n\n"
            "Even at Access time we can check that the switch left us with a usable corpus "
            "shape — how many documents per group, how long the texts are — without asking "
            "a research question yet (that restraint is Assess).",
        ),
        (
            "code",
            "from multilogue.assess_base import unit_size_table, docs_per_group\n"
            "from multilogue import viz\n\n"
            "sizes = unit_size_table(units)\n"
            "docs = docs_per_group(units, \"group\") if any(\"group\" in u for u in units) else None\n"
            "display(sizes.describe())\n"
            "if docs is not None:\n"
            "    display(docs)\n"
            "    viz.docs_per_group_bars(docs, path=FIG / \"00_docs_per_group.png\")\n"
            "viz.unit_size_hist(sizes, group_col=\"group\", units=units, path=FIG / \"00_unit_sizes.png\")",
        ),
    ],
    "01_assess.ipynb": [
        (
            "md",
            "# 01 · Assess — work you can do *without* the question\n\n"
            "Assess is deliberately narrow. In the Fynesse framing, it covers only tasks that "
            "remain valid if the downstream research question changes: sizes, emptiness, "
            "crude vocabulary, coverage across documents. Anything that needs a concern/"
            "benefit taxonomy, a framing lens, or a headline metric belongs in **Address**.\n\n"
            "**Why this split?** Reusable quality work should not be locked inside a "
            "question-specific notebook. Assess helpers return tables; plots here are "
            "diagnostics, not findings.",
        ),
        (
            "code",
            "from multilogue.access import load\n"
            "from multilogue.assess_base import (\n"
            "    unit_size_table, docs_per_group, empty_unit_flags, token_frequency,\n"
            ")\n"
            "from multilogue import viz\n\n"
            "units = load(\"synthetic\", n_docs_per_group=4, units_per_doc=3)[\"units\"]\n"
            "sizes = unit_size_table(units)\n"
            "empty = empty_unit_flags(units, min_words=4)\n"
            "print(f\"units={len(units)}; below min_words={len(empty)}\")\n"
            "display(docs_per_group(units, \"group\"))\n"
            "display(token_frequency([u[\"text\"] for u in units], top_n=15))",
        ),
        (
            "md",
            "## Diagnostics\n\n"
            "Unit-size histograms catch OCR debris and truncated chunks before any model "
            "call. Document counts by group show whether later *document-weighted* "
            "comparisons will rest on a thin sample.",
        ),
        (
            "code",
            "viz.unit_size_hist(sizes, group_col=\"group\", units=units, path=FIG / \"01_unit_sizes.png\")\n"
            "viz.docs_per_group_bars(docs_per_group(units, \"group\"), path=FIG / \"01_docs.png\")",
        ),
    ],
    "02_extract.ipynb": [
        (
            "md",
            "# 02 · Extract — narrow passes, checkpoints, quote support\n\n"
            "Address begins when we ask the model for structured points. Multilogue keeps "
            "extraction *generic*: a kind name, a prompt template, a sentinel for \"nothing "
            "here\", and an optional **quote support** gate so each phrase must be grounded "
            "in the speaker's own words.\n\n"
            "**Why checkpoints?** Model stages run through `StageRunner`: append-only JSONL "
            "keyed by item, with a fingerprint of prompt + model. Reruns resume; fingerprint "
            "changes supersede; replay needs no API. That is engineering for reproducible "
            "dialogue analysis, not a modelling claim.\n\n"
            "**Why FakeClient here?** Pedagogy and CI should not require a paid key. The "
            "fake model returns bank phrases that appear in the synthetic units so quote "
            "checks can fire.",
        ),
        (
            "code",
            "from collections import defaultdict\n"
            "from multilogue.access import load\n"
            "from multilogue.dummy import FakeClient\n"
            "from multilogue.extract import make_extract_work, phrase_table, yield_report\n"
            "from multilogue.llm import StageRunner\n"
            "from multilogue import viz\n\n"
            "units = load(\"synthetic\", n_docs_per_group=3, units_per_doc=3)[\"units\"]\n"
            "units_by_id = {u[\"unit_id\"]: u for u in units}\n"
            "client = FakeClient()\n"
            "runner = StageRunner(FIG.parent / \"ckpt_extract\", FIG.parent / \"logs_extract\",\n"
            "                     max_workers=2, sleep=lambda _: None)\n\n"
            "extraction = {}\n"
            "for kind in (\"concern\", \"benefit\"):\n"
            "    work = make_extract_work(\n"
            "        client, kind=kind, system=\"extract\",\n"
            "        user_for_unit=lambda u, k=kind: u[\"text\"],\n"
            "        model=\"fake-small\", sentinel=f\"NO_{kind.upper()}\", quote_threshold=0.8,\n"
            "    )\n"
            "    extraction[kind] = runner.run(\n"
            "        f\"extract_{kind}\", units, lambda u: u[\"unit_id\"], work,\n"
            "        f\"extract|{kind}|fake-small|v1\", quiet=True,\n"
            "    )\n\n"
            "phrases = phrase_table(extraction, units_by_id, kinds=[\"concern\", \"benefit\"],\n"
            "                       extra_unit_fields=[\"group\"])\n"
            "display(phrases.head())\n"
            "by_group = defaultdict(list)\n"
            "for u in units:\n"
            "    by_group[u[\"group\"]].append(u[\"unit_id\"])\n"
            "yd = yield_report(extraction, dict(by_group))\n"
            "display(yd)\n"
            "viz.yield_bars(yd, path=FIG / \"02_yield.png\")",
        ),
        (
            "md",
            "## Quote support\n\n"
            "A phrase without a recoverable quote is easy for a model to invent. The "
            "`quote_support` score asks how well the quoted span sits in the unit text. "
            "Thresholds are a design choice — high enough to catch fabrications, low enough "
            "to tolerate light paraphrase in the quote field.",
        ),
        (
            "code",
            "from multilogue.text import quote_support\n\n"
            "demo_text = units[0][\"text\"]\n"
            "span = \" \".join(demo_text.split()[:8])\n"
            "print(\"support(exact span):\", round(quote_support(span, demo_text), 3))\n"
            "print(\"support(noise):\", round(quote_support(\"completely unrelated words\", demo_text), 3))\n"
            "if \"verified\" in phrases.columns:\n"
            "    display(phrases.groupby([\"group\", \"kind\"]).verified.mean().rename(\"pct_verified\"))",
        ),
    ],
    "03_cluster.ipynb": [
        (
            "md",
            "# 03 · Shared topic space — embed, freeze, label, lens\n\n"
            "Once phrases exist, we place them in one embedding space and partition with "
            "*k*-means. Two design choices matter more than the brand of embedder:\n\n"
            "1. **Frozen assignments.** *k*-means is sensitive to initialisation and is not "
            "bit-stable across machines. When the phrase set is unchanged we reuse saved "
            "assignments so later notebooks do not silently reshuffle topics.\n"
            "2. **Blind labels and lenses.** Cluster names and framing lenses are proposed "
            "without seeing group labels (e.g. technology or format), so the taxonomy is "
            "not fitted to the comparison we later want to make.\n\n"
            "### A note on the PCA diagnostic\n\n"
            "The scatter below projects embeddings onto the first two principal components. "
            "Classical PCA is an *algorithm* that finds linear directions of high variance; "
            "it is a viewing device here, not the generative story for the phrases. "
            "For soft lens memberships under probabilistic PCA and σ² chosen by Earth "
            "Mover's Distance across lens runs, see notebook **08**. Multilogue keeps the "
            "weaker, local assumption for hard clustering: nearby embeddings tend to share "
            "a topic. If the scatter shows hopeless overlap, revisit *k* or the phrase set "
            "before interpreting shares.",
        ),
        (
            "code",
            "from multilogue.access import load\n"
            "from multilogue.dummy import FakeClient\n"
            "from multilogue.extract import make_extract_work, phrase_table\n"
            "from multilogue.llm import StageRunner\n"
            "from multilogue.cluster import (\n"
            "    Embedder, frozen_or_new_assignments, example_phrases_for_clusters,\n"
            "    make_label_work, make_lens_work, resolve_lenses,\n"
            ")\n"
            "from multilogue import viz\n"
            "import numpy as np\n\n"
            "units = load(\"synthetic\", n_docs_per_group=3, units_per_doc=3)[\"units\"]\n"
            "units_by_id = {u[\"unit_id\"]: u for u in units}\n"
            "client = FakeClient()\n"
            "root = FIG.parent\n"
            "runner = StageRunner(root / \"ckpt_cl\", root / \"logs_cl\", max_workers=2, sleep=lambda _: None)\n"
            "extraction = {}\n"
            "for kind in (\"concern\", \"benefit\"):\n"
            "    work = make_extract_work(client, kind=kind, system=\"e\",\n"
            "        user_for_unit=lambda u, k=kind: u[\"text\"], model=\"fake-small\",\n"
            "        sentinel=f\"NO_{kind.upper()}\")\n"
            "    extraction[kind] = runner.run(f\"ex_{kind}\", units, lambda u: u[\"unit_id\"], work,\n"
            "                                  f\"ex|{kind}\", quiet=True)\n"
            "phrases = phrase_table(extraction, units_by_id, kinds=[\"concern\", \"benefit\"],\n"
            "                       extra_unit_fields=[\"group\"])\n"
            "k = 4\n"
            "embedder = Embedder(root / \"emb\", client, model=\"fake-emb\")\n"
            "E = np.asarray(embedder(phrases.phrase.tolist()), float)\n"
            "labels, centroids, frozen = frozen_or_new_assignments(\n"
            "    phrases, E, k, 0, root / \"clusters\")\n"
            "phrases = phrases.copy()\n"
            "phrases[\"cluster\"] = labels\n"
            "phrases[\"centroid_sim\"] = (E * centroids[labels]).sum(1)\n"
            "print(\"frozen_assignments:\", frozen)\n"
            "viz.cluster_size_bars(phrases, path=FIG / \"03_cluster_sizes.png\")\n"
            "viz.embedding_scatter(E, phrases[\"cluster\"], path=FIG / \"03_pca_clusters.png\")",
        ),
        (
            "md",
            "## Blind labels and lenses\n\n"
            "Labels name clusters; lenses group clusters into coarser framings. Both are "
            "proposed from example phrases alone. Researchers may edit the lens mapping "
            "afterwards — the point of the first pass is a *format-blind* proposal.",
        ),
        (
            "code",
            "cluster_units = example_phrases_for_clusters(phrases, k, 0)\n"
            "lab = runner.run(\n"
            "    \"labels\", cluster_units, lambda cu: cu[\"key\"],\n"
            "    make_label_work(client, system=\"label\",\n"
            "                    prompt_template=\"Label these:\\n<<PHRASES>>\",\n"
            "                    model=\"fake-small\"),\n"
            "    \"labels|v1\", quiet=True,\n"
            ")\n"
            "names = {cu[\"cluster\"]: lab.get(cu[\"key\"], {}).get(\"label\", f\"cluster {cu['cluster']}\")\n"
            "         for cu in cluster_units}\n"
            "print(names)\n"
            "cl_desc = \"\\n\".join(\n"
            "    f\"{c}: {names[c]} — ({int((phrases.cluster == c).sum())})\" for c in range(k))\n"
            "lens_runs = runner.run(\n"
            "    \"lenses\", [1, 2], lambda r: str(r),\n"
            "    make_lens_work(client, system=\"lens\", prompt_template=\"Group:\\n<<CLUSTERS>>\",\n"
            "                   cluster_description=cl_desc, model=\"fake-small\", k=k),\n"
            "    f\"lenses|{cl_desc[:60]}\", quiet=True,\n"
            ")\n"
            "mapping, edited = resolve_lenses(k, lens_runs)\n"
            "phrases[\"lens\"] = phrases[\"cluster\"].map(mapping)\n"
            "print(\"lens mapping:\", mapping, \"edited:\", edited)\n"
            "viz.embedding_scatter(E, phrases[\"lens\"],\n"
            "                      title=\"Embedding space coloured by lens (PCA view)\",\n"
            "                      path=FIG / \"03_pca_lenses.png\")",
        ),
    ],
    "04_weight.ipynb": [
        (
            "md",
            "# 04 · Document weighting — shares that do not drown in long texts\n\n"
            "If we pool every phrase equally, a single long document dominates the "
            "comparison. Multilogue therefore averages **within documents first**, then "
            "across documents. Uncertainty comes from a **cluster bootstrap** that "
            "resamples documents, not phrases.\n\n"
            "**Why document level?** Public dialogue corpora are uneven: one consultation "
            "response may be a paragraph, another a short essay. The scientific object is "
            "usually the document (or conversation), so the weight should be too.\n\n"
            "Binary document presence (\"did this document raise cluster *c* at all?\") is "
            "available for temporal or rarity views; this notebook focuses on share "
            "comparisons between groups. Distances between whole topic *profiles* "
            "(Earth Mover's Distance under a cosine ground cost, with MDS and PERMANOVA) "
            "are in notebook **08** — they consume the same document-level shares.",
        ),
        (
            "code",
            "from multilogue.access import load\n"
            "from multilogue.dummy import FakeClient\n"
            "from multilogue.extract import make_extract_work, phrase_table\n"
            "from multilogue.llm import StageRunner\n"
            "from multilogue.cluster import (\n"
            "    Embedder, frozen_or_new_assignments, make_lens_work, resolve_lenses,\n"
            "    make_label_work, example_phrases_for_clusters,\n"
            ")\n"
            "from multilogue.weight import doc_profile, group_compare\n"
            "from multilogue import viz\n"
            "import numpy as np\n\n"
            "units = load(\"synthetic\", n_docs_per_group=4, units_per_doc=3)[\"units\"]\n"
            "units_by_id = {u[\"unit_id\"]: u for u in units}\n"
            "client = FakeClient()\n"
            "root = FIG.parent\n"
            "runner = StageRunner(root / \"ckpt_w\", root / \"logs_w\", max_workers=2, sleep=lambda _: None)\n"
            "extraction = {}\n"
            "for kind in (\"concern\", \"benefit\"):\n"
            "    work = make_extract_work(client, kind=kind, system=\"e\",\n"
            "        user_for_unit=lambda u, k=kind: u[\"text\"], model=\"fake-small\",\n"
            "        sentinel=f\"NO_{kind.upper()}\")\n"
            "    extraction[kind] = runner.run(f\"ex_{kind}\", units, lambda u: u[\"unit_id\"], work,\n"
            "                                  f\"ex|{kind}\", quiet=True)\n"
            "phrases = phrase_table(extraction, units_by_id, kinds=[\"concern\", \"benefit\"],\n"
            "                       extra_unit_fields=[\"group\"])\n"
            "k = 4\n"
            "E = np.asarray(Embedder(root / \"emb\", client, \"fake-emb\")(phrases.phrase.tolist()), float)\n"
            "labels, centroids, _ = frozen_or_new_assignments(phrases, E, k, 0, root / \"cl\")\n"
            "phrases = phrases.copy()\n"
            "phrases[\"cluster\"] = labels\n"
            "phrases[\"centroid_sim\"] = (E * centroids[labels]).sum(1)\n"
            "cluster_units = example_phrases_for_clusters(phrases, k, 0)\n"
            "lab = runner.run(\"lab\", cluster_units, lambda cu: cu[\"key\"],\n"
            "    make_label_work(client, system=\"l\", prompt_template=\"Label:\\n<<PHRASES>>\", model=\"fake-small\"),\n"
            "    \"lab\", quiet=True)\n"
            "names = {cu[\"cluster\"]: lab.get(cu[\"key\"], {}).get(\"label\", f\"c{cu['cluster']}\") for cu in cluster_units}\n"
            "cl_desc = \"\\n\".join(f\"{c}: {names[c]}\" for c in range(k))\n"
            "lens_runs = runner.run(\"lens\", [1], lambda r: str(r),\n"
            "    make_lens_work(client, system=\"L\", prompt_template=\"Group:\\n<<CLUSTERS>>\",\n"
            "                   cluster_description=cl_desc, model=\"fake-small\", k=k),\n"
            "    \"lens\", quiet=True)\n"
            "mapping, _ = resolve_lenses(k, lens_runs)\n"
            "phrases[\"lens\"] = phrases[\"cluster\"].map(mapping)\n\n"
            "prof = doc_profile(phrases, \"lens\", sorted(phrases.lens.unique()))\n"
            "display(prof.head())\n"
            "rng = np.random.default_rng(0)\n"
            "cmp = group_compare(phrases, \"group\", \"lens\", None, rng, reps=400,\n"
            "                    groups=sorted(phrases.group.unique()))\n"
            "display(cmp)\n"
            "g0, g1 = sorted(phrases.group.unique())[:2]\n"
            "viz.group_compare_dumbbell(cmp, label_col=\"lens\", group_a=g0, group_b=g1,\n"
            "                           path=FIG / \"04_group_compare.png\",\n"
            "                           title=\"Document-weighted lens shares\")",
        ),
    ],
    "05_multiverse.ipynb": [
        (
            "md",
            "# 05 · Multiverse — many analytic choices, one variance story\n\n"
            "A single pipeline path hides researcher degrees of freedom. Following "
            "Bell, Kampman, Dodge & Lawrence (2022), multilogue enumerates a Cartesian "
            "product of analytic choices and asks a **consumer-supplied** callback for the "
            "headline metric ℓ under each configuration.\n\n"
            "**Why a callback?** The shared library must not hard-code paper-specific "
            "outcomes (format gaps, technology distinctiveness, …). Consumers define ℓ; "
            "multilogue reports how much of ℓ's variance across the multiverse is "
            "associated with each dimension (a first-cut one-way share — interactions "
            "mean shares need not sum to one).\n\n"
            "Here ℓ is deliberately synthetic so the notebook stays offline.",
        ),
        (
            "code",
            "from multilogue.multiverse import (\n"
            "    enumerate_configurations, run_multiverse, variance_decomposition,\n"
            ")\n"
            "from multilogue import viz\n"
            "import numpy as np\n\n"
            "dims = {\"k\": [4, 5, 6], \"threshold\": [0.4, 0.5, 0.6], \"seed\": [0, 1]}\n"
            "configs = enumerate_configurations(dims)\n"
            "print(len(configs), \"configurations\")\n\n"
            "def evaluate(cfg):\n"
            "    # Toy ℓ: depends strongly on threshold, weakly on k, barely on seed\n"
            "    ell = 0.5 + 0.4 * cfg[\"threshold\"] + 0.05 * cfg[\"k\"] + 0.01 * cfg[\"seed\"]\n"
            "    ell += np.random.default_rng(cfg[\"seed\"] + 10 * cfg[\"k\"]).normal(0, 0.01)\n"
            "    return {\"ell\": ell}\n\n"
            "results = run_multiverse(configs, evaluate)\n"
            "display(results.head())\n"
            "shares = variance_decomposition(results, \"ell\", list(dims))\n"
            "display(shares)\n"
            "viz.variance_share_bars(shares, path=FIG / \"05_variance_shares.png\")\n"
            "viz.multiverse_metric_strip(results, \"ell\", colour_by=\"threshold\",\n"
            "                            path=FIG / \"05_metric_strip.png\")",
        ),
    ],
    "06_validate.ipynb": [
        (
            "md",
            "# 06 · Validate and report — agreement, sheets, evidence pack\n\n"
            "Validation scaffolding is deliberately thin in the library: stratified sampling "
            "for blind hand-check sheets, Cohen's κ and rank agreement helpers, and an "
            "HTML evidence-pack shell. Coding schemes and playbooks stay with the study.\n\n"
            "**Why κ here?** When two codings of the same items exist (human–model or "
            "model–model), κ summarises chance-corrected agreement. It is a diagnostic, "
            "not a substitute for reading the sheet.",
        ),
        (
            "code",
            "from multilogue.access import load\n"
            "from multilogue.validate import stratified_sample\n"
            "from multilogue.weight import kappa, rank_agreement\n"
            "from multilogue.report import evidence_pack, write_manifest\n"
            "from multilogue.dummy import FakeClient\n"
            "from multilogue.extract import make_extract_work, phrase_table\n"
            "from multilogue.llm import StageRunner\n"
            "from multilogue.cluster import Embedder, frozen_or_new_assignments, example_phrases_for_clusters, make_label_work, make_lens_work, resolve_lenses\n"
            "import numpy as np\n"
            "import pandas as pd\n\n"
            "# κ demo on synthetic labels\n"
            "a = [\"A\", \"A\", \"B\", \"B\", \"A\", \"B\", \"A\", \"B\"]\n"
            "b = [\"A\", \"B\", \"B\", \"B\", \"A\", \"B\", \"A\", \"A\"]\n"
            "print(\"kappa:\", round(kappa(a, b), 3))\n\n"
            "main = pd.Series([10.0, 8.0, 6.0, 4.0], index=list(\"WXYZ\"))\n"
            "other = pd.Series([9.5, 7.0, 6.5, 3.0], index=list(\"WXYZ\"))\n"
            "print(\"rank_agreement:\", rank_agreement(main, other))\n\n"
            "units = load(\"synthetic\", n_docs_per_group=2, units_per_doc=3)[\"units\"]\n"
            "units_by_id = {u[\"unit_id\"]: u for u in units}\n"
            "client = FakeClient()\n"
            "root = FIG.parent\n"
            "runner = StageRunner(root / \"ckpt_v\", root / \"logs_v\", max_workers=2, sleep=lambda _: None)\n"
            "extraction = {}\n"
            "for kind in (\"concern\", \"benefit\"):\n"
            "    work = make_extract_work(client, kind=kind, system=\"e\",\n"
            "        user_for_unit=lambda u, k=kind: u[\"text\"], model=\"fake-small\",\n"
            "        sentinel=f\"NO_{kind.upper()}\")\n"
            "    extraction[kind] = runner.run(f\"ex_{kind}\", units, lambda u: u[\"unit_id\"], work,\n"
            "                                  f\"ex|{kind}\", quiet=True)\n"
            "phrases = phrase_table(extraction, units_by_id, kinds=[\"concern\", \"benefit\"],\n"
            "                       extra_unit_fields=[\"group\"])\n"
            "k = 3\n"
            "E = np.asarray(Embedder(root / \"emb\", client, \"fake-emb\")(phrases.phrase.tolist()), float)\n"
            "labels, centroids, _ = frozen_or_new_assignments(phrases, E, k, 0, root / \"cl\")\n"
            "phrases = phrases.copy()\n"
            "phrases[\"cluster\"] = labels\n"
            "phrases[\"centroid_sim\"] = (E * centroids[labels]).sum(1)\n"
            "cluster_units = example_phrases_for_clusters(phrases, k, 0)\n"
            "lab = runner.run(\"lab\", cluster_units, lambda cu: cu[\"key\"],\n"
            "    make_label_work(client, system=\"l\", prompt_template=\"Label:\\n<<PHRASES>>\", model=\"fake-small\"),\n"
            "    \"lab\", quiet=True)\n"
            "names = {cu[\"cluster\"]: lab.get(cu[\"key\"], {}).get(\"label\", f\"c{cu['cluster']}\") for cu in cluster_units}\n"
            "cl_desc = \"\\n\".join(f\"{c}: {names[c]}\" for c in range(k))\n"
            "lens_runs = runner.run(\"lens\", [1], lambda r: str(r),\n"
            "    make_lens_work(client, system=\"L\", prompt_template=\"Group:\\n<<CLUSTERS>>\",\n"
            "                   cluster_description=cl_desc, model=\"fake-small\", k=k),\n"
            "    \"lens\", quiet=True)\n"
            "phrases[\"lens\"] = phrases[\"cluster\"].map(resolve_lenses(k, lens_runs)[0])\n\n"
            "sheet = stratified_sample(phrases, by=\"group\", n_per_stratum=2, random_state=0)\n"
            "display(sheet[[\"unit_id\", \"group\", \"phrase\", \"lens\"]])\n"
            "html = evidence_pack(phrases, root / \"evidence_pack.html\", group_col=\"group\",\n"
            "                     title=\"Synthetic evidence pack\", seed=0)\n"
            "write_manifest(root / \"manifest.json\", {\"n_phrases\": len(phrases), \"synthetic\": True})\n"
            "print(\"Evidence pack:\", html)\n"
            "display(HTML(f'<a href=\"{html}\" target=\"_blank\">Open evidence pack</a>'))",
        ),
    ],
    "07_end_to_end.ipynb": [
        (
            "md",
            "# 07 · End-to-end synthetic experiment\n\n"
            "The pieces in notebooks 00–06 assemble into one callable, "
            "`run_validation_experiment`, also exposed as `multilogue-validate`. "
            "It uses only synthetic units and `FakeClient` — safe for CI and Colab "
            "without keys — and writes tables, a multiverse decomposition, and an "
            "evidence pack under a directory you choose (keep it gitignored).\n\n"
            "Use this notebook as a smoke test after installing multilogue, then return "
            "to the earlier notebooks when you want to change one aspect at a time.",
        ),
        (
            "code",
            "from pathlib import Path\n"
            "from multilogue.experiment import run_validation_experiment\n"
            "from multilogue import viz\n"
            "import pandas as pd\n\n"
            "out = Path(\"outputs/notebook_e2e\")\n"
            "summary = run_validation_experiment(out, n_docs_per_group=3, units_per_doc=3, k=4, quiet=True)\n"
            "display(summary)\n"
            "tables = out / \"tables\"\n"
            "for name in [\"yield.csv\", \"group_compare_lenses.csv\", \"variance_shares.csv\"]:\n"
            "    p = tables / name\n"
            "    if p.is_file():\n"
            "        print(\"—\", name)\n"
            "        display(pd.read_csv(p).head())\n"
            "shares = pd.read_csv(tables / \"variance_shares.csv\")\n"
            "viz.variance_share_bars(shares, path=FIG / \"07_variance_shares.png\")\n"
            "print(\"Evidence pack:\", out / \"evidence_pack.html\")",
        ),
        (
            "md",
            "## Where next?\n\n"
            "- Swap `load(\"synthetic\")` for `load(\"polis\", …)` or `load(\"gdn_cc\", …)` in Access "
            "when you want public civic text.\n"
            "- Replace `FakeClient` with an OpenAI or LiteLLM client for real extraction "
            "(checkpoints still apply).\n"
            "- Soft PPCA lenses and document EMD: notebook **08**.\n"
            "- Keep study-specific PDF parsers, prompts, and headline ℓ in your own package; "
            "depend on multilogue for the shared method.",
        ),
    ],
    "08_soft_distance.ipynb": [
        (
            "md",
            "# 08 · Soft PPCA lenses, σ² by EMD, and document distance\n\n"
            "Hard *k*-means and a single lens map (notebook 03) assign each cluster to one "
            "framing. A richer Address layer treats each lens as a **probabilistic PCA** "
            "Gaussian over its member centroids and gives every cluster soft mixture "
            "weights over lenses. The shared noise scale σ² is not guessed: we sweep it "
            "and pick the value that minimises mean **Earth Mover's Distance** between "
            "independent lens runs, subject to a meaningful-soft band on effective support "
            "(so we do not collapse to the near-uniform solution).\n\n"
            "Separately, documents can be compared by EMD on their **cluster share** "
            "profiles (cosine ground cost between centroids), with classical MDS and "
            "PERMANOVA / PERMDISP for group tests — without using lens names at all.\n\n"
            "Requires the optional dependency ``pot`` "
            "(`pip install 'multilogue[distance]'`).",
        ),
        (
            "code",
            "import subprocess, sys\n"
            "subprocess.check_call([sys.executable, \"-m\", \"pip\", \"install\", \"-q\", \"pot\"])\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "from multilogue import soft as ms\n"
            "from multilogue import distance as dd\n"
            "from multilogue import viz\n\n"
            "rng = np.random.default_rng(0)\n"
            "k, dim, n_lenses, n_runs = 24, 12, 6, 3\n"
            "centroids = rng.normal(size=(k, dim))\n"
            "centroids /= np.linalg.norm(centroids, axis=1, keepdims=True)\n"
            "mappings = []\n"
            "for _ in range(n_runs):\n"
            "    perm = rng.permutation(k)\n"
            "    mappings.append({f\"L{j}\": {\"cluster_ids\": perm[j::n_lenses].tolist()}\n"
            "                     for j in range(n_lenses)})\n\n"
            "sweep = ms.sigma2_sweep_select(centroids, mappings)\n"
            "curve = pd.DataFrame(sweep[\"curve\"])\n"
            "print(f\"Selected σ²: {sweep['sigma2_best']:.4g} ({sweep['selection']})\")\n"
            "print(f\"Mean EMD at σ²*: {sweep['emd_best']:.4f}\")\n"
            "print(f\"Mean eff. support: {sweep['eff_support_best']:.2f}\")\n"
            "display(curve[[\"sigma2\", \"mean_emd\", \"mean_eff_support\"]].head(8))\n\n"
            "W, names = ms.compute_mixture_weights(\n"
            "    centroids, mappings[0], sweep[\"sigma2_best\"])\n"
            "print(\"Mixture weights shape:\", W.shape, \"lenses:\", names)\n"
            "print(\"Row sums:\", np.round(W.sum(axis=1)[:5], 3))",
        ),
        (
            "md",
            "## Document EMD and PERMANOVA\n\n"
            "Plant two groups with different cluster profiles. Documents with too few "
            "phrases are dropped; the rest are placed by transport distance and tested "
            "for group location differences.",
        ),
        (
            "code",
            "prof_a = np.array([0.4, 0.4, 0.05, 0.05, 0.05, 0.05])\n"
            "prof_b = np.array([0.05, 0.05, 0.05, 0.05, 0.4, 0.4])\n"
            "docs = {f\"a{i}\": prof_a for i in range(8)}\n"
            "docs.update({f\"b{i}\": prof_b for i in range(8)})\n"
            "rows = []\n"
            "for doc, profile in docs.items():\n"
            "    for c in rng.choice(6, size=120, p=profile):\n"
            "        rows.append({\"doc_id\": doc, \"cluster\": int(c)})\n"
            "phrases = pd.DataFrame(rows)\n"
            "group = {d: (\"A\" if d.startswith(\"a\") else \"B\") for d in docs}\n"
            "C6 = centroids[:6]\n"
            "res = dd.run_document_distance_analysis(\n"
            "    phrases, C6, group, min_phrases=50, n_perm=199, seed=0)\n"
            "pm = res[\"permanova\"]\n"
            "print(f\"Docs kept: {len(res['docs'])}; dropped: {res['dropped_docs']}\")\n"
            "print(f\"PERMANOVA R²={pm['R2']:.3f}, p={pm['p_value']:.4f}\")\n"
            "display(res[\"pairwise\"][[\"comparison\", \"R2\", \"p_value\", \"dispersion_p\"]])\n\n"
            "import matplotlib.pyplot as plt\n"
            "coords = res[\"mds\"][\"coords\"]\n"
            "fig, ax = plt.subplots(figsize=(5, 4))\n"
            "for g, marker in ((\"A\", \"o\"), (\"B\", \"s\")):\n"
            "    m = res[\"groups\"] == g\n"
            "    ax.scatter(coords[m, 0], coords[m, 1], label=g, marker=marker)\n"
            "ax.set_xlabel(\"MDS 1\"); ax.set_ylabel(\"MDS 2\")\n"
            "ax.set_title(\"Document EMD → classical MDS\")\n"
            "ax.legend()\n"
            "fig.tight_layout()\n"
            "path = FIG / \"08_doc_mds.png\"\n"
            "fig.savefig(path, dpi=120)\n"
            "plt.close(fig)\n"
            "display(Markdown(f\"![MDS]({path})\"))",
        ),
    ],
}


def main() -> None:
    out = Path(__file__).resolve().parents[1] / "notebooks"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.ipynb"):
        old.unlink()
    for name, cells in NOTEBOOKS.items():
        nb = nbf.v4.new_notebook()
        title_md = cells[0][1] if cells and cells[0][0] == "md" else name
        first = title_md.split("\n", 1)[0]
        intro = colab_badge(name) + "\n" + (cells[0][1] if cells[0][0] == "md" else f"# {name}")
        body = cells[1:] if cells[0][0] == "md" else cells
        nb.cells = [nbf.v4.new_markdown_cell(intro), nbf.v4.new_code_cell(SETUP)]
        for kind, src in body:
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
        print("wrote", name, f"({first})")


if __name__ == "__main__":
    main()
