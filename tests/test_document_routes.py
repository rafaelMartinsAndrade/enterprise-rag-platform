def test_upload_processes_and_lists_document(client, acme_headers) -> None:
    response = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "ERP Closing Rules", "tags": "erp,closing"},
        files={
            "file": (
                "closing_rules.txt",
                b"Month End Closing\nInvoices above 5000 require finance approval.\nClose payments every Friday.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"

    detail = client.get(f"/api/v1/documents/{body['document_id']}", headers=acme_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "processed"
    assert detail.json()["versions"][0]["processing_status"] == "processed"


def test_update_and_delete_document(client, acme_headers) -> None:
    created = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "Support Playbook", "tags": "support"},
        files={"file": ("support.txt", b"Support SLA\nCritical tickets answered in 30 minutes.", "text/plain")},
    ).json()

    updated = client.put(
        f"/api/v1/documents/{created['document_id']}",
        headers=acme_headers,
        data={"title": "Support Playbook v2"},
        files={"file": ("support_v2.txt", b"Support SLA\nCritical tickets answered in 15 minutes.", "text/plain")},
    )
    assert updated.status_code == 202

    detail = client.get(f"/api/v1/documents/{created['document_id']}", headers=acme_headers)
    assert detail.status_code == 200
    assert len(detail.json()["versions"]) == 2
    assert detail.json()["versions"][0]["version_number"] == 2

    deleted = client.delete(f"/api/v1/documents/{created['document_id']}", headers=acme_headers)
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"
