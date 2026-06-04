"""Plain text loader."""

from __future__ import annotations

from pathlib import Path

from app.loaders.base_loader import BaseLoader
from app.schemas.qa_record import LoadedSegment


class TxtLoader(BaseLoader):
    supported_extensions = {".txt"}

    def load(self, file_path: str | Path) -> list[LoadedSegment]:
        path = Path(file_path)
        text = self._read_text(path)
        return [
            LoadedSegment(
                text=text,
                source=str(path),
                file_type="txt",
                page=0,
                section="",
                block_type="text",
                start_offset=0,
                end_offset=len(text),
            )
        ]

    @staticmethod
    def _read_text(path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gb18030"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return path.read_text(encoding="utf-8", errors="ignore")
