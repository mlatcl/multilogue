"""Access loaders: switchable sources, parsers on fixtures (no network)."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from multilogue.access import datasets, download, list_sources, load, load_units, set_datapath

FIXTURES = Path(__file__).parent / "fixtures" / "access"


@pytest.fixture()
def cache(tmp_path, monkeypatch):
    set_datapath(tmp_path / "cache")
    monkeypatch.setattr(download, "override_manual_authorize", True)
    return tmp_path / "cache"


def test_list_sources_includes_expected():
    names = list_sources()
    for n in ("synthetic", "polis", "gdn_cc", "cdcp", "cimt", "decidim"):
        assert n in names


def test_load_synthetic_switch(cache):
    a = load("synthetic", n_docs_per_group=1, units_per_doc=2)
    b = load_units("synthetic", n_docs_per_group=1, units_per_doc=2)
    assert a["source"] == "synthetic"
    assert a["license"]
    assert len(a["units"]) == 4  # 2 groups × 1 doc × 2 units
    assert b == a["units"]
    assert all(u.get("text") for u in a["units"])


def test_unknown_source_raises():
    with pytest.raises(KeyError, match="Unknown source"):
        load("not_a_source")


def test_polis_parser_from_fixture(cache, monkeypatch):
    rel = "vtaiwan.uberx/comments.csv"
    dest = download.source_dir("polis") / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text((FIXTURES / "polis_comments.csv").read_text(encoding="utf-8"), encoding="utf-8")

    def no_download(*_a, **_k):
        raise AssertionError("should not download")

    monkeypatch.setattr(download, "download_url", no_download)
    bundle = datasets.polis(conversation="vtaiwan.uberx")
    assert len(bundle["units"]) == 2  # moderated row skipped
    assert bundle["units"][0]["doc_id"] == "vtaiwan.uberx"
    assert "taxi" in bundle["units"][0]["text"] or "ride" in bundle["units"][0]["text"]


def test_gdn_cc_parser_from_fixture(cache, monkeypatch):
    fname = "GDNCC_data_valid.jsonl"
    dest = download.source_dir("gdn_cc") / fname
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text((FIXTURES / "gdn_sample.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(download, "download_url", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    bundle = datasets.gdn_cc(split="valid")
    assert len(bundle["units"]) == 3
    assert bundle["units"][0]["unit_id"] == "1-1"
    assert "services" in bundle["units"][0]["text"] or "publics" in bundle["units"][0]["text"]


def test_cimt_parser_from_fixture(cache, monkeypatch):
    rel = "Cycling-Dialogue-Bonn/dataset_CDB.tsv"
    dest = download.source_dir("cimt") / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text((FIXTURES / "cimt_sample.tsv").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(download, "download_url", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    bundle = datasets.cimt(process="Cycling-Dialogue-Bonn")
    assert len(bundle["units"]) == 3
    assert bundle["units"][0]["meta"]["code"] == "mpos"


def test_decidim_parser_from_fixture(cache, monkeypatch):
    dest = download.source_dir("decidim") / "proposals.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text((FIXTURES / "decidim_proposals.csv").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(download, "download_url", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    bundle = datasets.decidim(resource="proposals")
    assert len(bundle["units"]) == 2
    assert "bike" in bundle["units"][0]["text"].lower()


def test_cdcp_from_local_zip(cache, monkeypatch):
    root = download.source_dir("cdcp")
    root.mkdir(parents=True, exist_ok=True)
    zpath = root / "cdcp_acl17.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("cdcp/train/00001.txt", "Debt collectors call at inappropriate times.")
        zf.writestr("cdcp/train/00002.txt", "I need clearer dispute procedures.")
        zf.writestr("cdcp/test/00003.txt", "test only")
    monkeypatch.setattr(download, "download_url", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    bundle = datasets.cdcp(subset="train")
    assert len(bundle["units"]) == 2
    assert bundle["units"][0]["doc_id"] == "cdcp/train"


def test_ensure_files_downloads_when_missing(cache, monkeypatch):
    called = {}

    def fake_download(url, dest, messages=True):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_text("comment-id,comment-body,moderated\n1,hello,0\n", encoding="utf-8")
        called["url"] = url
        return Path(dest)

    monkeypatch.setattr(download, "download_url", fake_download)
    monkeypatch.setattr(download, "override_manual_authorize", True)
    root = download.ensure_files(
        "polis",
        {"vtaiwan.uberx/comments.csv": "https://example.test/comments.csv"},
    )
    assert called["url"].endswith("comments.csv")
    assert (root / "vtaiwan.uberx" / "comments.csv").is_file()


def test_authorize_denied(cache, monkeypatch):
    monkeypatch.setattr(download, "override_manual_authorize", False)
    monkeypatch.setattr(download, "prompt_stdin", lambda _p: False)
    with pytest.raises(PermissionError):
        download.ensure_files(
            "polis",
            {"x/comments.csv": "https://example.test/x.csv"},
            force=True,
        )


def test_switch_between_sources(cache):
    """Same call shape for different sources (synthetic vs fixture-backed)."""
    syn = load("synthetic", n_docs_per_group=1, units_per_doc=1)
    # plant polis fixture then load
    rel = "scoop-hivemind.ubi/comments.csv"
    dest = download.source_dir("polis") / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text((FIXTURES / "polis_comments.csv").read_text(encoding="utf-8"), encoding="utf-8")
    pol = load("polis", conversation="scoop-hivemind.ubi")
    assert syn["source"] != pol["source"]
    assert isinstance(syn["units"], list) and isinstance(pol["units"], list)
