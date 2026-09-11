from __future__ import annotations


def test_settings_are_independent_per_user(client, user_a, user_b, login_as):
    saved = client.put("/settings", json={"groq_api_key": "gsk_only_for_ada", "max_tokens": 5000})
    assert saved.status_code == 200
    assert saved.json()["has_groq_key"] is True
    assert saved.json()["max_tokens"] == 5000

    login_as(user_b)
    other = client.get("/settings")
    assert other.status_code == 200
    assert other.json()["has_groq_key"] is False
    assert other.json()["max_tokens"] != 5000
