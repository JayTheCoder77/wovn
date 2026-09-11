from __future__ import annotations


def test_user_cannot_read_another_users_job(client, user_a, user_b, login_as):
    created = client.post("/jobs", json={"repo_url": "https://github.com/pallets/flask"})
    assert created.status_code == 200
    job_id = created.json()["id"]

    login_as(user_b)
    response = client.get(f"/jobs/{job_id}")
    assert response.status_code == 404


def test_user_cannot_confirm_or_read_doc_for_another_users_job(client, user_a, user_b, login_as):
    created = client.post("/jobs", json={"repo_url": "https://github.com/pallets/flask"})
    job = created.json()
    job_id = job["id"]

    from api.jobs import store
    from api.jobs.paths import doc_path, skeleton_path

    store.update_job(job_id, status="awaiting_confirmation")
    skeleton_path(job_id).write_text("{}", encoding="utf-8")
    doc_path(job_id).write_text("{}", encoding="utf-8")

    login_as(user_b)
    confirm = client.post(f"/jobs/{job_id}/confirm", json={"model": None})
    assert confirm.status_code == 404
    doc = client.get(f"/jobs/{job_id}/doc")
    assert doc.status_code == 404


def test_user_cannot_update_another_users_settings(client, user_a, user_b, login_as):
    client.put("/settings", json={"groq_api_key": "gsk_user_a"})
    login_as(user_b)
    response = client.get("/settings")
    assert response.status_code == 200
    assert response.json()["has_groq_key"] is False
