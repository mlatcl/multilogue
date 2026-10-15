from multilogue.extract import make_extract_work, parse_items, phrase_table


def test_parse_items_skips_sentinel():
    text = "NO_CONCERN\nsome phrase || a quote here"
    assert parse_items("NO_CONCERN", "NO_CONCERN") == []
    items = parse_items(text, "NO_CONCERN")
    assert items == [("some phrase", "a quote here")]


def test_make_extract_work_quote_gate():
    class C:
        def complete(self, *a, **k):
            return "privacy risk || people worry about privacy\nbogus claim || not in source"

    work = make_extract_work(
        C(),
        kind="concern",
        system="s",
        user_for_unit=lambda u: u["text"],
        model="m",
        sentinel="NO_CONCERN",
        quote_threshold=0.8,
    )
    out = work({"text": "people worry about privacy a lot", "extract_text": "people worry about privacy a lot"})
    assert out["stats"]["kept"] == 2
    verified = [i for i in out["items"] if i["verified"]]
    assert len(verified) == 1
    assert verified[0]["phrase"] == "privacy risk"


def test_phrase_table():
    extraction = {
        "concern": {
            "u1": {"items": [{"phrase": "a", "quote": "q", "quote_support": 1.0, "verified": True}]}
        }
    }
    units = {"u1": {"doc_id": "d1", "format": "x"}}
    df = phrase_table(extraction, units, extra_unit_fields=["format"])
    assert list(df.phrase_id) == ["concern|u1|1"]
    assert df.iloc[0].format == "x"
