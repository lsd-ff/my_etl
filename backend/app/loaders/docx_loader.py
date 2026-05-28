"""DOCX loader using python-docx."""

from __future__ import annotations

from pathlib import Path

from app.loaders.base_loader import BaseLoader
from app.schemas.qa_record import LoadedSegment


class DocxLoader(BaseLoader):
    supported_extensions = {".docx"}

    def load(self, file_path: str | Path) -> list[LoadedSegment]:
        path = Path(file_path)
        try:
            from docx import Document
        except ImportError as exc:
            raise ImportError("DOCX support requires python-docx. Install requirements.txt.") from exc

        document = Document(str(path))
        lines: list[str] = []
        section = ""
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue
            style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
            if "heading" in style_name or "标题" in style_name:
                section = text
            lines.append(text)

        return [
            LoadedSegment(
                text="\n".join(lines),
                source=str(path),
                file_type="docx",
                page=0,
                section=section,
            )
        ]

