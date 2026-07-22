from types import SimpleNamespace

from app.schemas.common import RetrievalMode
from app.services.retrieval_service import RetrievalService


def test_retrieval_service_uses_python_path_for_sqlite(seeded_session, monkeypatch) -> None:
    service = RetrievalService(seeded_session)
    calls = {"python": 0, "postgres": 0}
    fake_row = (
        SimpleNamespace(
            id=1,
            section_title="Refund Policy",
            search_text="refunds above 1000 require director approval",
            content="Refunds above 1000 require director approval.",
            page_number=1,
        ),
        SimpleNamespace(id=1, title="Closing Policy"),
        SimpleNamespace(version_number=1),
        0.92,
    )

    def fake_python(**kwargs):
        calls["python"] += 1
        return [fake_row]

    def fake_postgres(**kwargs):
        calls["postgres"] += 1
        return [fake_row]

    monkeypatch.setattr(service, "_search_python", fake_python)
    monkeypatch.setattr(service, "_search_postgres", fake_postgres)

    result = service.search(
        organization_id=1,
        question="Who approves refunds above 1000?",
        query_embedding=[0.1, 0.2],
        retrieval_mode=RetrievalMode.hybrid,
        document_ids=[],
        top_k=3,
    )

    assert calls == {"python": 1, "postgres": 0}
    assert result[0].document_title == "Closing Policy"


def test_retrieval_service_uses_pgvector_path_for_postgres(seeded_session, monkeypatch) -> None:
    service = RetrievalService(seeded_session)
    calls = {"python": 0, "postgres": 0}
    fake_row = (
        SimpleNamespace(
            id=7,
            section_title="Invoice Policy",
            search_text="invoice prefix is nw inv",
            content="Northwind invoice prefix is NW-INV.",
            page_number=1,
        ),
        SimpleNamespace(id=3, title="Billing Handbook"),
        SimpleNamespace(version_number=1),
        0.88,
    )

    monkeypatch.setattr(seeded_session.bind.dialect, "name", "postgresql", raising=False)

    def fake_python(**kwargs):
        calls["python"] += 1
        return [fake_row]

    def fake_postgres(**kwargs):
        calls["postgres"] += 1
        return [fake_row]

    monkeypatch.setattr(service, "_search_python", fake_python)
    monkeypatch.setattr(service, "_search_postgres", fake_postgres)

    result = service.search(
        organization_id=2,
        question="What is invoice prefix?",
        query_embedding=[0.4, 0.5],
        retrieval_mode=RetrievalMode.vector,
        document_ids=[],
        top_k=2,
    )

    assert calls == {"python": 0, "postgres": 1}
    assert result[0].document_title == "Billing Handbook"
