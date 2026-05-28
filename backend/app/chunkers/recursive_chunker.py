"""Recursive-ish chunker that favors headings, paragraphs, and sentences."""

from __future__ import annotations

import hashlib
import re

from app.config import settings
from app.schemas.qa_record import Chunk, LoadedSegment


class RecursiveChunker:
    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None) -> None:
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    def chunk_segments(self, doc_id: str, segments: list[LoadedSegment]) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 1
        for segment in segments:
            for content, section in self._split_text(segment.text, segment.section):
                chunk_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                chunk_id = f"{doc_id}_chunk{chunk_index}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        chunk_index=chunk_index,
                        content=content,
                        page=segment.page,
                        section=section,
                        chunk_hash=chunk_hash,
                    )
                )
                chunk_index += 1
        return chunks

    def _split_text(self, text: str, default_section: str = "") -> list[tuple[str, str]]:
        units = self._to_units(text)
        chunks: list[tuple[str, str]] = []
        current = ""
        current_section = default_section
        for unit in units:
            detected_section = self._section_from_unit(unit)
            section = detected_section or current_section
            if detected_section:
                current_section = detected_section

            if len(unit) > self.chunk_size:
                if current.strip():
                    chunks.append((current.strip(), current_section))
                    current = ""
                for piece in self._hard_split(unit):
                    chunks.append((piece.strip(), section))
                continue

            candidate = f"{current}\n{unit}".strip() if current else unit
            if len(candidate) <= self.chunk_size:
                current = candidate
                current_section = section
            else:
                if current.strip():
                    chunks.append((current.strip(), current_section))
                overlap = self._overlap_tail(current)
                current = f"{overlap}\n{unit}".strip() if overlap else unit
                current_section = section

        if current.strip():
            chunks.append((current.strip(), current_section))
        return chunks

    @staticmethod
    def _section_from_unit(unit: str) -> str:
        first_line = unit.strip().splitlines()[0] if unit.strip() else ""
        markdown_heading = re.match(r"^#{1,6}\s+(.+)$", first_line)
        if markdown_heading:
            return markdown_heading.group(1).strip()
        numbered_heading = re.match(r"^第[一二三四五六七八九十\d]+[章节部分][：:\s]*(.+)?$", first_line)
        if numbered_heading:
            return first_line.strip()
        return ""

    def _to_units(self, text: str) -> list[str]:
        blocks = re.split(r"\n\s*\n", text)
        units: list[str] = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            if len(block) <= self.chunk_size:
                units.append(block)
                continue
            sentences = re.split(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+", block)
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    units.append(sentence)
        return units

    def _hard_split(self, text: str) -> list[str]:
        step = max(1, self.chunk_size - self.chunk_overlap)
        return [text[start : start + self.chunk_size] for start in range(0, len(text), step)]

    def _overlap_tail(self, text: str) -> str:
        if self.chunk_overlap <= 0:
            return ""
        tail = text[-self.chunk_overlap :]
        boundary = max(tail.rfind("。"), tail.rfind("\n"), tail.rfind("."))
        if boundary > 20:
            tail = tail[boundary + 1 :]
        return tail.strip()

