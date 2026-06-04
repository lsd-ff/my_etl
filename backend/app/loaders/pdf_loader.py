"""PDF loader using pypdf."""

from __future__ import annotations

from pathlib import Path

from app.loaders.base_loader import BaseLoader
from app.schemas.qa_record import LoadedSegment


class PDFLoader(BaseLoader):
    supported_extensions = {".pdf"}

    def load(self, file_path: str | Path) -> list[LoadedSegment]:
        path = Path(file_path)
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ImportError("PDF support requires pypdf. Install requirements.txt.") from exc

        reader = PdfReader(str(path))
        segments: list[LoadedSegment] = []
        offset = 0
        for index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            stripped = text.strip()
            if stripped:
                start = offset
                end = start + len(stripped)
                segments.append(
                    LoadedSegment(
                        text=stripped,
                        source=str(path),
                        file_type="pdf",
                        page=index,
                        section="",
                        block_type="page",
                        start_offset=start,
                        end_offset=end,
                    )
                )
                offset = end + 1
        return segments
