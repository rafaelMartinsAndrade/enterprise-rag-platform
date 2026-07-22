from dataclasses import dataclass

from app.core.config import settings
from app.services.text_extraction_service import ExtractedDocument, ExtractedPage


@dataclass(slots=True)
class ChunkCandidate:
    chunk_index: int
    page_number: int | None
    section_title: str | None
    heading_path: str | None
    content: str
    search_text: str
    metadata: dict


class ChunkingService:
    def chunk_document(self, extracted: ExtractedDocument) -> tuple[list[ChunkCandidate], dict]:
        chunks: list[ChunkCandidate] = []
        index = 0
        for page in extracted.pages:
            for chunk_text in self._window_page(page):
                chunks.append(
                    ChunkCandidate(
                        chunk_index=index,
                        page_number=page.page_number,
                        section_title=page.section_title,
                        heading_path=page.section_title,
                        content=chunk_text,
                        search_text=chunk_text.lower(),
                        metadata={
                            "page_number": page.page_number,
                            "section_title": page.section_title,
                            "chunk_size_chars": len(chunk_text),
                            "strategy": "paragraph_window_v1",
                        },
                    )
                )
                index += 1
        strategy = {
            "name": "paragraph_window_v1",
            "chunk_size_chars": settings.chunk_size_chars,
            "chunk_overlap_chars": settings.chunk_overlap_chars,
            "page_count": len(extracted.pages),
        }
        return chunks, strategy

    def _window_page(self, page: ExtractedPage) -> list[str]:
        paragraphs = [item.strip() for item in page.text.split("\n\n") if item.strip()]
        if not paragraphs:
            paragraphs = [page.text.strip()]

        windows: list[str] = []
        current = ""
        overlap = settings.chunk_overlap_chars
        for paragraph in paragraphs:
            proposed = f"{current}\n\n{paragraph}".strip() if current else paragraph
            if len(proposed) <= settings.chunk_size_chars:
                current = proposed
                continue
            if current:
                windows.append(current)
                tail = current[-overlap:] if overlap else ""
                current = f"{tail}\n\n{paragraph}".strip()
            else:
                windows.extend(self._slice_long_text(paragraph))
                current = ""
        if current:
            windows.append(current)
        return windows

    def _slice_long_text(self, text: str) -> list[str]:
        slices: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + settings.chunk_size_chars)
            slices.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(0, end - settings.chunk_overlap_chars)
        return [item for item in slices if item]
