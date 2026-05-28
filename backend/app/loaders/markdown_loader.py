"""Markdown loader with lightweight section inference."""

from __future__ import annotations

from pathlib import Path

from app.loaders.base_loader import BaseLoader
from app.schemas.qa_record import LoadedSegment


class MarkdownLoader(BaseLoader):
    supported_extensions = {".md", ".markdown"}

    def load(self, file_path: str | Path) -> list[LoadedSegment]:
        path = Path(file_path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        section = ""
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                section = stripped.lstrip("#").strip()
                break
        return [
            LoadedSegment(
                text=text,
                source=str(path),
                file_type="markdown",
                page=0,
                section=section,
            )
        ]

