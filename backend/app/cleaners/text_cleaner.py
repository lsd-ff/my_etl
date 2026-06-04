"""Text normalization and light de-noising."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CleaningResult:
    text: str
    report: dict[str, Any]


class TextCleaner:
    def __init__(self, min_line_length: int = 3) -> None:
        self.min_line_length = min_line_length

    def clean(self, text: str) -> str:
        return self.clean_with_report(text).text

    def clean_with_report(self, text: str) -> CleaningResult:
        original_text = text
        mojibake_markers = text.count("�")
        text = self._normalize_chars(text)
        text = self._normalize_spaces(text)
        original_lines = [line.strip() for line in text.splitlines()]
        lines, removed_noise = self._remove_noise_lines(original_lines)
        lines, removed_duplicates = self._dedupe_lines(lines)
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()
        report = self._build_report(
            original_text=original_text,
            cleaned_text=cleaned,
            original_lines=original_lines,
            removed_noise=removed_noise,
            removed_duplicates=removed_duplicates,
            mojibake_markers=mojibake_markers,
        )
        return CleaningResult(text=cleaned, report=report)

    @staticmethod
    def _normalize_chars(text: str) -> str:
        text = text.replace("\ufeff", "").replace("\u00a0", " ")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        text = re.sub(r"[�]{1,}", "", text)
        return text

    @staticmethod
    def _normalize_spaces(text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        return text

    def _remove_noise_lines(self, lines: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
        cleaned: list[str] = []
        removed: list[dict[str, Any]] = []
        for index, line in enumerate(lines, start=1):
            if not line:
                cleaned.append("")
                continue
            compact = re.sub(r"\s+", "", line)
            if len(compact) < self.min_line_length:
                removed.append({"line_number": index, "text": line, "reason": "too_short"})
                continue
            if re.fullmatch(r"[-_=]{3,}", compact):
                removed.append({"line_number": index, "text": line, "reason": "rule_line"})
                continue
            if re.fullmatch(r"(page|p\.)?\d{1,4}", compact, flags=re.IGNORECASE):
                removed.append({"line_number": index, "text": line, "reason": "page_number"})
                continue
            if re.fullmatch(r"第?\d{1,4}页", compact):
                removed.append({"line_number": index, "text": line, "reason": "page_number"})
                continue
            cleaned.append(line)
        return cleaned, removed

    @staticmethod
    def _dedupe_lines(lines: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
        result: list[str] = []
        removed: list[dict[str, Any]] = []
        recent: list[str] = []
        for index, line in enumerate(lines, start=1):
            key = re.sub(r"\s+", "", line).lower()
            if line and key in recent:
                removed.append({"line_number": index, "text": line, "reason": "near_duplicate"})
                continue
            if line:
                recent.append(key)
                recent = recent[-12:]
            if not line and result and not result[-1]:
                continue
            result.append(line)
        return result, removed

    @staticmethod
    def _build_report(
        original_text: str,
        cleaned_text: str,
        original_lines: list[str],
        removed_noise: list[dict[str, Any]],
        removed_duplicates: list[dict[str, Any]],
        mojibake_markers: int,
    ) -> dict[str, Any]:
        original_chars = len(original_text)
        cleaned_chars = len(cleaned_text)
        removed_lines = removed_noise + removed_duplicates
        removal_ratio = 0.0 if not original_chars else max(0.0, (original_chars - cleaned_chars) / original_chars)
        warnings: list[str] = []
        if removal_ratio > 0.35:
            warnings.append("high_cleaning_removal_ratio")
        if mojibake_markers:
            warnings.append("mojibake_markers_removed")
        if cleaned_chars < 80 and original_chars >= 200:
            warnings.append("cleaned_text_too_short")
        return {
            "original_chars": original_chars,
            "cleaned_chars": cleaned_chars,
            "original_lines": len(original_lines),
            "cleaned_lines": len([line for line in cleaned_text.splitlines() if line.strip()]),
            "removed_line_count": len(removed_lines),
            "noise_line_count": len(removed_noise),
            "duplicate_line_count": len(removed_duplicates),
            "removal_ratio": round(removal_ratio, 4),
            "mojibake_markers": mojibake_markers,
            "warnings": warnings,
            "removed_lines": removed_lines[:200],
        }
