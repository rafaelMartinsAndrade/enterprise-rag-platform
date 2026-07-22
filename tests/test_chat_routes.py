def test_chat_returns_grounded_answer_with_citations(client, acme_headers) -> None:
    created = client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "Finance Manual", "tags": "finance,policy"},
        files={
            "file": (
                "finance_manual.txt",
                b"Finance Manual\nRefunds above 1000 require director approval.\nRefund register closes at 18:00.",
                "text/plain",
            )
        },
    ).json()

    answer = client.post(
        "/api/v1/chat/ask",
        headers=acme_headers,
        json={
            "question": "Who approves refunds above 1000?",
            "document_ids": [created["document_id"]],
        },
    )

    assert answer.status_code == 200
    body = answer.json()
    assert body["has_sufficient_evidence"] is True
    assert len(body["assistant_message"]["citations"]) >= 1
    assert "approval" in body["assistant_message"]["content"].lower()


def test_chat_returns_no_evidence_when_question_is_out_of_scope(client, acme_headers) -> None:
    client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "Accounts Payable", "tags": "finance"},
        files={"file": ("ap.txt", b"Accounts payable closes every Monday at 17:00.", "text/plain")},
    )

    answer = client.post(
        "/api/v1/chat/ask",
        headers=acme_headers,
        json={"question": "What is our vacation policy for HR interns?"},
    )

    assert answer.status_code == 200
    assert answer.json()["has_sufficient_evidence"] is False
    assert answer.json()["assistant_message"]["no_evidence"] is True


def test_multi_tenant_isolation_blocks_cross_org_answers(client, acme_headers, northwind_headers) -> None:
    client.post(
        "/api/v1/documents/upload",
        headers=acme_headers,
        data={"title": "ACME Treasury", "tags": "treasury"},
        files={"file": ("treasury.txt", b"ACME treasury code is TR-778 and cash sweep runs daily.", "text/plain")},
    )
    client.post(
        "/api/v1/documents/upload",
        headers=northwind_headers,
        data={"title": "Northwind Billing", "tags": "billing"},
        files={"file": ("billing.txt", b"Northwind invoice prefix is NW-INV.", "text/plain")},
    )

    answer = client.post(
        "/api/v1/chat/ask",
        headers=northwind_headers,
        json={"question": "What is ACME treasury code?"},
    )

    assert answer.status_code == 200
    assert answer.json()["has_sufficient_evidence"] is False
