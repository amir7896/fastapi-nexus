def test_health_returns_ok(client, api_prefix):
    response = client.get(f"{api_prefix}/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
