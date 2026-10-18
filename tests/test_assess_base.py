"""Assess text diagnostics (CIP-0008)."""
from __future__ import annotations

import pandas as pd

from multilogue.assess_base import (
    assess_text_report,
    character_inventory,
    flag_sentence_length,
    flag_unit_length,
    flag_unusual_characters,
    flag_word_length,
    infer_lang,
    sentence_length_table,
    split_sentences,
    unit_length_summary,
    unit_size_table,
    unusual_codepoints,
    word_length_table,
)


def _units():
    return [
        {
            "unit_id": "u1",
            "doc_id": "d1",
            "text": (
                "The cycle path near the station is too narrow for cargo bikes. "
                "Drivers often park on the pavement."
            ),
        },
        {
            "unit_id": "u2",
            "doc_id": "d2",
            "text": (
                "Der Radweg an der Rheinbrücke ist zu schmal für Lastenräder. "
                "Autos parken oft auf dem Bürgersteig."
            ),
        },
        {
            "unit_id": "u3",
            "doc_id": "d3",
            "text": "ok",
        },
        {
            "unit_id": "u4",
            "doc_id": "d4",
            "text": "Parking\ufffd\x00 issues with OCR\ufffd debris " + ("x" * 30),
        },
    ]


def test_unit_length_summary_and_flags():
    sizes = unit_size_table(_units())
    summary = unit_length_summary(sizes)
    assert len(summary) == 1
    assert summary.iloc[0]["n_units"] == 4
    flags = flag_unit_length(_units())
    assert "u3" in set(flags["unit_id"].astype(str))


def test_sentence_split_and_flags():
    sents = split_sentences("One. Two! Three?")
    assert len(sents) == 3
    tab = sentence_length_table(_units()[:1])
    assert len(tab) >= 2
    # Plant an absurdly long sentence
    long = [{"unit_id": "L", "doc_id": "d", "text": " ".join(["word"] * 100) + "."}]
    flagged = flag_sentence_length(sentence_length_table(long))
    assert len(flagged) >= 1
    assert flagged.iloc[0]["flag"] == "too_long"


def test_lang_and_word_lengths():
    assert infer_lang("Hello world parking") == "en"
    assert infer_lang("Der Bürgersteig ist zu schmal für Lastenräder.") == "de"
    words = word_length_table(_units()[:2], lang="auto")
    assert set(words["lang"]) <= {"de", "en"}
    assert words["n_chars"].min() >= 1
    fused = word_length_table(
        [{"unit_id": "f", "doc_id": "d", "text": "a " + ("supercalifragilistic" * 3)}]
    )
    flagged = flag_word_length(fused)
    assert (flagged["flag"] == "too_long").any()


def test_character_inventory_and_flags():
    inv = character_inventory(_units())
    assert set(inv["char_class"]) == {"letter", "digit", "punct", "space", "other"}
    assert abs(inv["share"].sum() - 1.0) < 1e-9
    unusual = unusual_codepoints(_units())
    assert len(unusual) >= 1
    flags = flag_unusual_characters(_units(), other_share=0.01)
    assert "u4" in set(flags["unit_id"].astype(str))


def test_assess_text_report_keys():
    report = assess_text_report(_units(), lang="auto")
    for key in (
        "sizes",
        "size_summary",
        "unit_length_flags",
        "sentences",
        "sentence_flags",
        "words",
        "word_flags",
        "char_classes",
        "unusual_codepoints",
        "char_flags",
        "empty",
    ):
        assert key in report
        assert isinstance(report[key], pd.DataFrame)
