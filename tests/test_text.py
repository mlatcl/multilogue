from multilogue.text import get_list, parse_json, quote_support, sha


def test_quote_support_verbatim():
    assert quote_support("hello world", "say hello world please") == 1.0


def test_quote_support_empty():
    assert quote_support("", "anything") == 0.0


def test_sha_stable():
    assert sha("x") == sha("x")
    assert sha("x") != sha("y")


def test_parse_json_fenced():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_get_list():
    assert get_list({"items": [1, 2]}, "items") == [1, 2]
    assert get_list({"other": [3]}, "items") == [3]
