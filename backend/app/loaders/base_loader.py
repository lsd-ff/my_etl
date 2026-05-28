"""Common loader interfaces and loader selection."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.qa_record import LoadedSegment


class BaseLoader(ABC):
    supported_extensions: set[str] = set()

    @abstractmethod
    def load(self, file_path: str | Path) -> list[LoadedSegment]:
        """Load a file into text segments."""


def get_loader(file_path: str | Path) -> BaseLoader:
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        from app.loaders.pdf_loader import PDFLoader

        return PDFLoader()
    if suffix == ".docx":
        from app.loaders.docx_loader import DocxLoader

        return DocxLoader()
    if suffix == ".txt":
        from app.loaders.txt_loader import TxtLoader

        return TxtLoader()
    if suffix in {".md", ".markdown"}:
        from app.loaders.markdown_loader import MarkdownLoader

        return MarkdownLoader()
    raise ValueError(f"Unsupported file type: {suffix}")

