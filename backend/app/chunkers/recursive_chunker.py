"""Recursive-ish chunker that favors headings, paragraphs, and sentences."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.config import settings
from app.schemas.qa_record import Chunk, LoadedSegment


@dataclass(frozen=True)
class TextUnit:
    text: str
    section: str
    block_type: str
    heading_path: tuple[str, ...]
    start_offset: int
    end_offset: int


class RecursiveChunker:
    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None) -> None:
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.chunk_overlap

    def chunk_segments(self, doc_id: str, segments: list[LoadedSegment]) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 1
        for segment in segments:
            for item in self._split_text(segment):
                content = item["content"]
                chunk_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                chunk_id = f"{doc_id}_chunk{chunk_index}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        chunk_index=chunk_index,
                        content=content,
                        page=segment.page,
                        section=item["section"],
                        chunk_hash=chunk_hash,
                        heading_path=tuple(item["heading_path"]),
                        block_types=tuple(item["block_types"]),
                        token_count=int(item["token_count"]),
                        quality_score=float(item["quality_score"]),
                        warnings=tuple(item["warnings"]),
                        source_start=int(item["source_start"]),
                        source_end=int(item["source_end"]),
                    )
                )
                chunk_index += 1
        return chunks

    def _split_text(self, segment: LoadedSegment | str, default_section: str = "") -> list[dict[str, object]]:
        if isinstance(segment, str):
            segment = LoadedSegment(text=segment, source="", file_type="", section=default_section)
        elif not hasattr(segment, "start_offset"):
            segment = LoadedSegment(
                text=str(getattr(segment, "text", "")),
                source=str(getattr(segment, "source", "")),
                file_type=str(getattr(segment, "file_type", "")),
                page=int(getattr(segment, "page", 0) or 0),
                section=str(getattr(segment, "section", "") or ""),
            )
        units = self._to_units(segment)
        chunks: list[dict[str, object]] = []
        current_units: list[TextUnit] = []
        current_section = segment.section
        for unit in units:
            detected_section = self._section_from_unit(unit)
            section = detected_section or current_section
            if detected_section:
                current_section = detected_section
                unit = TextUnit(
                    text=unit.text,
                    section=section,
                    block_type="heading",
                    heading_path=self._heading_path_for_unit(unit.heading_path, detected_section),
                    start_offset=unit.start_offset,
                    end_offset=unit.end_offset,
                )

            if self._token_len(unit.text) > self.chunk_size:
                if current_units:
                    chunks.append(self._build_chunk(current_units, current_section))
                    current_units = []
                for piece in self._hard_split(unit):
                    chunks.append(self._build_chunk([piece], section))
                continue

            candidate_units = current_units + [unit]
            if self._token_len(self._join_units(candidate_units)) <= self.chunk_size:
                current_units = candidate_units
                current_section = section
            else:
                if current_units:
                    chunks.append(self._build_chunk(current_units, current_section))
                overlap = self._overlap_units(current_units)
                current_units = overlap + [unit]
                current_section = section

        if current_units:
            chunks.append(self._build_chunk(current_units, current_section))
        return chunks

    @staticmethod
    def _section_from_unit(unit: TextUnit | str) -> str:
        text = unit.text if isinstance(unit, TextUnit) else unit
        first_line = text.strip().splitlines()[0] if text.strip() else ""
        markdown_heading = re.match(r"^#{1,6}\s+(.+)$", first_line)
        if markdown_heading:
            return markdown_heading.group(1).strip()
        numbered_heading = re.match(r"^第[一二三四五六七八九十\d]+[章节部分][：:\s]*(.+)?$", first_line)
        if numbered_heading:
            return first_line.strip()
        return ""

    def _to_units(self, segment: LoadedSegment) -> list[TextUnit]:
        blocks = re.split(r"(\n\s*\n)", segment.text)
        units: list[TextUnit] = []
        cursor = segment.start_offset
        for block in blocks:
            cursor_end = cursor + len(block)
            block = block.strip()
            if not block:
                cursor = cursor_end
                continue
            block_type = self._block_type(block, segment.block_type)
            if self._token_len(block) <= self.chunk_size:
                units.append(
                    TextUnit(
                        text=block,
                        section=segment.section,
                        block_type=block_type,
                        heading_path=segment.heading_path,
                        start_offset=cursor,
                        end_offset=cursor_end,
                    )
                )
                cursor = cursor_end
                continue
            sentences = re.split(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+", block)
            sentence_offset = cursor
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence:
                    start = max(cursor, sentence_offset)
                    end = start + len(sentence)
                    units.append(
                        TextUnit(
                            text=sentence,
                            section=segment.section,
                            block_type=block_type,
                            heading_path=segment.heading_path,
                            start_offset=start,
                            end_offset=end,
                        )
                    )
                    sentence_offset = end + 1
            cursor = cursor_end
        return units

    def _hard_split(self, unit: TextUnit) -> list[TextUnit]:
        step = max(1, int(self.chunk_size * 0.75))
        text = unit.text
        pieces: list[TextUnit] = []
        start = 0
        while start < len(text):
            end = self._char_boundary_for_token_limit(text, start, self.chunk_size)
            piece = text[start:end].strip()
            if piece:
                pieces.append(
                    TextUnit(
                        text=piece,
                        section=unit.section,
                        block_type=unit.block_type,
                        heading_path=unit.heading_path,
                        start_offset=unit.start_offset + start,
                        end_offset=unit.start_offset + end,
                    )
                )
            start += max(1, self._char_boundary_for_token_limit(text, start, step) - start)
        return pieces

    def _overlap_units(self, units: list[TextUnit]) -> list[TextUnit]:
        if self.chunk_overlap <= 0:
            return []
        result: list[TextUnit] = []
        total = 0
        for unit in reversed(units):
            unit_tokens = self._token_len(unit.text)
            if total + unit_tokens > self.chunk_overlap and result:
                break
            result.insert(0, unit)
            total += unit_tokens
            if total >= self.chunk_overlap:
                break
        return result

    def _build_chunk(self, units: list[TextUnit], section: str) -> dict[str, object]:
        content = self._join_units(units)
        token_count = self._token_len(content)
        warnings = self._quality_warnings(content, token_count, units)
        quality_score = max(0.0, 1.0 - 0.18 * len(warnings))
        heading_path = self._most_specific_heading_path(units)
        block_types = sorted({unit.block_type for unit in units})
        return {
            "content": content,
            "section": section or (heading_path[-1] if heading_path else ""),
            "heading_path": heading_path,
            "block_types": block_types,
            "token_count": token_count,
            "quality_score": round(quality_score, 3),
            "warnings": warnings,
            "source_start": min(unit.start_offset for unit in units),
            "source_end": max(unit.end_offset for unit in units),
        }

    @staticmethod
    def _join_units(units: list[TextUnit]) -> str:
        return "\n".join(unit.text for unit in units if unit.text.strip()).strip()

    @staticmethod
    def _heading_path_for_unit(existing: tuple[str, ...], heading: str) -> tuple[str, ...]:
        if existing and existing[-1] == heading:
            return existing
        return (*existing, heading)

    @staticmethod
    def _most_specific_heading_path(units: list[TextUnit]) -> tuple[str, ...]:
        paths = [unit.heading_path for unit in units if unit.heading_path]
        if not paths:
            return ()
        return max(paths, key=len)

    @staticmethod
    def _block_type(text: str, default: str) -> str:
        stripped = text.strip()
        if re.match(r"^#{1,6}\s+", stripped) or re.match(r"^第[一二三四五六七八九十\d]+[章节部分]", stripped):
            return "heading"
        lines = [line for line in stripped.splitlines() if line.strip()]
        if lines and sum(1 for line in lines if "|" in line or "\t" in line) / len(lines) >= 0.5:
            return "table"
        if lines and sum(1 for line in lines if re.match(r"^([-*]|\d+[.)、])\s+", line.strip())) / len(lines) >= 0.5:
            return "list"
        return default or "text"

    def _quality_warnings(self, content: str, token_count: int, units: list[TextUnit]) -> tuple[str, ...]:
        warnings: list[str] = []
        if token_count < max(40, int(self.chunk_size * 0.08)):
            warnings.append("chunk_too_short")
        if token_count > self.chunk_size:
            warnings.append("chunk_too_long")
        if len({unit.section for unit in units if unit.section}) > 2:
            warnings.append("multiple_sections")
        if not re.search(r"[。！？!?；;.]|$", content):
            warnings.append("no_sentence_punctuation")
        if self._table_like_ratio(content) > 0.55:
            warnings.append("table_like_chunk")
        return tuple(dict.fromkeys(warnings))

    @staticmethod
    def _table_like_ratio(text: str) -> float:
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return 0.0
        table_lines = [line for line in lines if "|" in line or "\t" in line]
        return len(table_lines) / len(lines)

    @staticmethod
    def _token_len(text: str) -> int:
        chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
        words = len(re.findall(r"[A-Za-z0-9_]+", text))
        punctuation = len(re.findall(r"[^\w\s\u4e00-\u9fff]", text))
        return chinese + words + max(0, punctuation // 4)

    def _char_boundary_for_token_limit(self, text: str, start: int, token_limit: int) -> int:
        best = min(len(text), start + max(1, token_limit))
        for end in range(best, len(text) + 1):
            if self._token_len(text[start:end]) > token_limit:
                return max(start + 1, end - 1)
        return len(text)
