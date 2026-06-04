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
        segments: list[LoadedSegment] = []
        heading_path: list[str] = []
        section = ""
        current_lines: list[str] = []
        current_start = 0
        offset = 0

        def flush() -> None:
            nonlocal current_lines, current_start
            segment_text = "\n".join(current_lines).strip()
            if not segment_text:
                current_lines = []
                current_start = offset
                return
            segments.append(
                LoadedSegment(
                    text=segment_text,
                    source=str(path),
                    file_type="markdown",
                    page=0,
                    section=section,
                    heading_path=tuple(heading_path),
                    block_type="markdown",
                    start_offset=current_start,
                    end_offset=current_start + len(segment_text),
                )
            )
            current_lines = []
            current_start = offset

        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if stripped.startswith("#"):
                flush()
                level = len(stripped) - len(stripped.lstrip("#"))
                section = stripped.lstrip("#").strip()
                heading_path[:] = heading_path[: max(0, level - 1)]
                heading_path.append(section)
            if not current_lines:
                current_start = offset
            current_lines.append(line)
            offset += len(raw_line) + 1

        flush()
        if not segments and text.strip():
            segments.append(
                LoadedSegment(
                    text=text,
                    source=str(path),
                    file_type="markdown",
                    page=0,
                    section=section,
                    heading_path=tuple(heading_path),
                    block_type="markdown",
                    start_offset=0,
                    end_offset=len(text),
                )
            )
        return segments
