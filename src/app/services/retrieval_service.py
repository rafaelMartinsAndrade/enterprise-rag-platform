import math
import re

from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.answer_provider import RetrievedChunk
from app.models.document_chunk import DocumentChunk
from app.models.document_version import DocumentVersion
from app.models.knowledge_document import KnowledgeDocument
from app.schemas.common import RetrievalMode


class RetrievalService:
    token_pattern = re.compile(r"[a-z0-9]+", flags=re.IGNORECASE)

    def __init__(self, session: Session) -> None:
        self.session = session

    def search(
        self,
        *,
        organization_id: int,
        question: str,
        query_embedding: list[float],
        retrieval_mode: RetrievalMode,
        document_ids: list[int],
        top_k: int,
    ) -> list[RetrievedChunk]:
        candidate_count = max(top_k, settings.rerank_candidate_count)
        if self._supports_pgvector():
            rows = self._search_postgres(
                organization_id=organization_id,
                query_embedding=query_embedding,
                document_ids=document_ids,
                candidate_count=candidate_count,
            )
        else:
            rows = self._search_python(
                organization_id=organization_id,
                query_embedding=query_embedding,
                document_ids=document_ids,
            )[:candidate_count]

        question_terms = set(self.token_pattern.findall(question.lower()))
        reranked: list[RetrievedChunk] = []
        for chunk, document, version, vector_score in rows:
            keyword_score = self._keyword_overlap(question_terms, chunk.search_text)
            combined_score = vector_score if retrieval_mode is RetrievalMode.vector else (
                (vector_score * 0.7) + (keyword_score * 0.3)
            )
            if chunk.section_title and question_terms.intersection(
                self.token_pattern.findall(chunk.section_title.lower())
            ):
                combined_score = min(1.0, combined_score + 0.05)
            reranked.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    document_title=document.title,
                    version_number=version.version_number,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    content=chunk.content,
                    excerpt=chunk.content[:280],
                    score=round(max(0.0, min(1.0, combined_score)), 4),
                )
            )
        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked[:top_k]

    def _base_query(self, organization_id: int, document_ids: list[int]):
        query = (
            self.session.query(DocumentChunk, KnowledgeDocument, DocumentVersion)
            .join(KnowledgeDocument, DocumentChunk.document_id == KnowledgeDocument.id)
            .join(DocumentVersion, DocumentChunk.document_version_id == DocumentVersion.id)
            .filter(
                DocumentChunk.organization_id == organization_id,
                DocumentVersion.is_active.is_(True),
            )
        )
        if document_ids:
            query = query.filter(DocumentChunk.document_id.in_(document_ids))
        return query

    def _search_python(self, *, organization_id: int, query_embedding: list[float], document_ids: list[int]):
        rows = self._base_query(organization_id, document_ids).all()
        scored_rows = []
        for chunk, document, version in rows:
            score = self._cosine_similarity(query_embedding, chunk.embedding)
            scored_rows.append((chunk, document, version, round(score, 4)))
        scored_rows.sort(key=lambda item: item[3], reverse=True)
        return scored_rows

    def _search_postgres(
        self,
        *,
        organization_id: int,
        query_embedding: list[float],
        document_ids: list[int],
        candidate_count: int,
    ):
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        rows = (
            self._base_query(organization_id, document_ids)
            .add_columns(distance.label("distance"))
            .order_by(distance.asc())
            .limit(candidate_count)
            .all()
        )
        return [
            (chunk, document, version, round(max(0.0, 1 - float(distance_value)), 4))
            for chunk, document, version, distance_value in rows
        ]

    def _keyword_overlap(self, question_terms: set[str], search_text: str) -> float:
        if not question_terms:
            return 0.0
        chunk_terms = set(self.token_pattern.findall(search_text.lower()))
        return len(question_terms.intersection(chunk_terms)) / len(question_terms)

    def _supports_pgvector(self) -> bool:
        bind = self.session.get_bind()
        return bind is not None and bind.dialect.name == "postgresql"

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(a * a for a in left)) or 1.0
        right_norm = math.sqrt(sum(b * b for b in right)) or 1.0
        return numerator / (left_norm * right_norm)
