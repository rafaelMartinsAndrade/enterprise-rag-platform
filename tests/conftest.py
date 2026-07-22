from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core import db as core_db
from app.core.config import settings
from app.main import app
from app.models.base import Base
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.workers import tasks as worker_tasks
from app.workers.celery_app import celery_app


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture()
def seeded_session(engine, tmp_path: Path) -> Generator[Session, None, None]:
    settings.storage_root = str(tmp_path / "storage")
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    core_db.SessionLocal = session_factory
    worker_tasks.SessionLocal = session_factory
    celery_app.conf.update(
        task_always_eager=True,
        task_store_eager_result=True,
        broker_url="memory://",
        result_backend="cache+memory://",
    )
    with Session(engine) as session:
        organization_repo = OrganizationRepository(session)
        user_repo = UserRepository(session)
        acme = organization_repo.create(name="ACME ERP", slug="acme-erp")
        northwind = organization_repo.create(name="Northwind Finance", slug="northwind-finance")
        user_repo.create(
            organization_id=acme.id,
            email="ana@acme.test",
            full_name="Ana ACME",
            role="analyst",
        )
        user_repo.create(
            organization_id=northwind.id,
            email="bruno@northwind.test",
            full_name="Bruno Northwind",
            role="manager",
        )
        yield session


@pytest.fixture()
def client(engine, seeded_session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[core_db.get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def acme_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer change-me",
        "X-Organization-Slug": "acme-erp",
        "X-User-Email": "ana@acme.test",
    }


@pytest.fixture()
def northwind_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer change-me",
        "X-Organization-Slug": "northwind-finance",
        "X-User-Email": "bruno@northwind.test",
    }
