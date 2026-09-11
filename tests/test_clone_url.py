import base64
import subprocess

import pytest

from ingest.clone import CloneError, clone_repo, parse_github_url


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


def test_clone_with_token_uses_extra_header(tmp_path, monkeypatch):
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("ingest.clone._dir_size_bytes", lambda path: 1)
    dest = tmp_path / "repo"
    parsed = clone_repo("https://github.com/pallets/flask", dest, access_token="gho_secret")
    assert parsed.https_url == "https://github.com/pallets/flask.git"
    header = next(part for part in captured["cmd"] if str(part).startswith("http.extraHeader=Authorization:"))
    assert header.startswith("http.extraHeader=Authorization: Basic ")
    decoded = base64.b64decode(header.split(" ", 2)[2]).decode("ascii")
    assert decoded == "x-access-token:gho_secret"
    clone_url = next(part for part in captured["cmd"] if str(part).startswith("https://"))
    assert clone_url == parsed.https_url
    assert "gho_secret" not in clone_url


def test_public_clone_has_no_authorization_header(tmp_path, monkeypatch):
    captured: dict = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("ingest.clone._dir_size_bytes", lambda path: 1)
    clone_repo("https://github.com/pallets/flask", tmp_path / "repo")
    assert not any("Authorization" in str(part) for part in captured["cmd"])
