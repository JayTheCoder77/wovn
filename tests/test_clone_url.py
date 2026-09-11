from ingest.clone import CloneError, parse_github_url
import pytest


def test_parse_github_https():
    parsed = parse_github_url("https://github.com/pallets/flask")
    assert parsed.owner == "pallets"
    assert parsed.name == "flask"
    assert parsed.https_url.endswith("flask.git")


def test_parse_github_git_suffix():
    parsed = parse_github_url("https://github.com/pallets/flask.git/")
    assert parsed.name == "flask"


def test_reject_non_github():
    with pytest.raises(CloneError):
        parse_github_url("https://gitlab.com/foo/bar")


def test_reject_nested_path():
    with pytest.raises(CloneError):
        parse_github_url("https://github.com/pallets/flask/tree/main")
