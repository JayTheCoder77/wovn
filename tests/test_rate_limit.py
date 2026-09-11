from __future__ import annotations


def test_eleventh_job_create_is_rate_limited(client, user_a):
    repo = client.post("/repos", json={"url": "https://github.com/pallets/flask"}).json()
    for _ in range(10):
        response = client.post(f"/repos/{repo['id']}/jobs")
        assert response.status_code == 200
    limited = client.post(f"/repos/{repo['id']}/jobs")
    assert limited.status_code == 429
