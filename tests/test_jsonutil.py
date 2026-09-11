from generation.jsonutil import extract_json


def test_extract_plain_json():
    assert extract_json('{"a": 1}')["a"] == 1


def test_extract_fenced_json():
    text = """```json
{"purpose": "ok"}
```"""
    assert extract_json(text)["purpose"] == "ok"
