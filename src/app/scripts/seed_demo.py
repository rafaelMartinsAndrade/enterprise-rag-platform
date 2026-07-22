import hashlib
import shutil
from pathlib import Path

from app import models  # noqa: F401
from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.models.base import Base
from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.services.processing_service import ProcessingService
from app.services.storage_service import StorageService


ROOT = Path(__file__).resolve().parents[3]
DEMO_ROOT = ROOT / "demo_data" / "documents"
DEMO_USERS = {
    "acme-erp": {
        "organization_name": "ACME ERP",
        "user_email": "ana@acme.demo",
        "user_name": "Ana Martins",
        "role": "knowledge-manager",
    },
    "northwind-finance": {
        "organization_name": "Northwind Finance",
        "user_email": "bruno@northwind.demo",
        "user_name": "Bruno Andrade",
        "role": "finance-ops",
    },
}


def main() -> None:
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(engine)

    storage_service = StorageService()
    with SessionLocal() as session:
        organization_repo = OrganizationRepository(session)
        user_repo = UserRepository(session)
        knowledge_repo = KnowledgeRepository(session)
        processor = ProcessingService(session)

        for organization_slug, files in _iter_demo_documents().items():
            seed = DEMO_USERS[organization_slug]
            organization = organization_repo.get_by_slug(organization_slug)
            if organization is None:
                organization = organization_repo.create(
                    name=seed["organization_name"],
                    slug=organization_slug,
                )
            user = user_repo.get_by_org_and_email(
                organization_id=organization.id,
                email=seed["user_email"],
            )
            if user is None:
                user = user_repo.create(
                    organization_id=organization.id,
                    email=seed["user_email"],
                    full_name=seed["user_name"],
                    role=seed["role"],
                )

            for file_path in files:
                existing = _find_document_by_title(
                    knowledge_repo=knowledge_repo,
                    organization_id=organization.id,
                    title=file_path.stem.replace("_", " ").title(),
                )
                if existing is not None:
                    continue

                document = knowledge_repo.create_document(
                    organization_id=organization.id,
                    created_by_user_id=user.id,
                    title=file_path.stem.replace("_", " ").title(),
                    source_type="upload",
                    tags=[organization_slug, file_path.suffix.replace(".", "")],
                )
                version_number = 1
                target_dir = (
                    storage_service.root
                    / organization_slug
                    / f"document_{document.id}"
                    / f"v{version_number}"
                )
                target_dir.mkdir(parents=True, exist_ok=True)
                target_path = target_dir / file_path.name
                shutil.copy2(file_path, target_path)
                checksum = hashlib.sha256(target_path.read_bytes()).hexdigest()
                version = knowledge_repo.create_version(
                    organization_id=organization.id,
                    document_id=document.id,
                    created_by_user_id=user.id,
                    version_number=version_number,
                    filename=file_path.name,
                    content_type=_guess_content_type(file_path),
                    storage_path=str(target_path),
                    checksum=checksum,
                )
                processor.process_version(version.id)
                print(f"seeded {organization_slug}: {document.title}")


def _iter_demo_documents() -> dict[str, list[Path]]:
    return {
        directory.name: sorted(path for path in directory.iterdir() if path.is_file())
        for directory in sorted(DEMO_ROOT.iterdir())
        if directory.is_dir()
    }


def _find_document_by_title(*, knowledge_repo: KnowledgeRepository, organization_id: int, title: str):
    for document in knowledge_repo.list_documents(organization_id):
        if document.title == title:
            return document
    return None


def _guess_content_type(path: Path) -> str:
    return {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".json": "application/json",
    }.get(path.suffix.lower(), "text/plain")


if __name__ == "__main__":
    main()
