from __future__ import annotations


def test_register_repo_and_create_job(client, user_a):
    created = client.post("/repos", json={"url": "https://github.com/pallets/flask"})
    assert created.status_code == 200
    repo = created.json()
    assert repo["full_name"] == "pallets/flask"
    assert repo["default_url"] == "https://github.com/pallets/flask"
    assert repo["provider"] == "github"

    job_response = client.post(f"/repos/{repo['id']}/jobs")
    assert job_response.status_code == 200
    job = job_response.json()
    assert job["repo_url"] == "https://github.com/pallets/flask"
    assert job["repo_id"] == repo["id"]
    assert job["user_id"] == user_a["id"]
    assert job["status"] == "queued"


def test_list_repos_only_own(client, user_a, user_b, login_as):
    client.post("/repos", json={"url": "https://github.com/pallets/flask"})
    login_as(user_b)
    client.post("/repos", json={"url": "https://github.com/encode/starlette"})
    mine = client.get("/repos")
    assert mine.status_code == 200
    names = {row["full_name"] for row in mine.json()}
    assert names == {"encode/starlette"}


def test_github_repo_picker_uses_stored_token(client, user_a, monkeypatch):
    import api.auth.github_api as github_api

    def fake_list_user_repos(access_token: str):
        assert access_token == "gho_aaa"
        return [
            {
                "full_name": "octo/private-app",
                "html_url": "https://github.com/octo/private-app",
                "visibility": "private",
                "default_branch": "main",
            }
        ]

    monkeypatch.setattr(github_api, "list_user_repos", fake_list_user_repos)
    response = client.get("/github/repos")
    assert response.status_code == 200
    assert response.json()[0]["full_name"] == "octo/private-app"
