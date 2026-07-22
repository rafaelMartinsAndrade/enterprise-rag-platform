def test_celery_status_route(client, acme_headers) -> None:
    created = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "Ops Manual", "tags": "ops"},
        files={"file": ("ops.txt", b"Operations manual content for eager task run.", "text/plain")},
    ).json()

    response = client.get(f"/api/v1/jobs/celery/{created['task_id']}")
    assert response.status_code == 200
    assert response.json()["status"] in {"success", "pending"}
