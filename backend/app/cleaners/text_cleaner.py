"""Text normalization and light de-noising."""

from __future__ import annotations

import re


class TextCleaner:
    def __init__(self, min_line_length: int = 3) -> None:
        self.min_line_length = min_line_length

    def clean(self, text: str) -> str:
        text = self._normalize_chars(text)
        text = self._normalize_spaces(text)
        lines = [line.strip() for line in text.splitlines()]
        lines = self._remove_noise_lines(lines)
        lines = self._dedupe_lines(lines)
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

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

    def _remove_noise_lines(self, lines: list[str]) -> list[str]:
        cleaned: list[str] = []
        for line in lines:
            if not line:
                cleaned.append("")
                continue
            compact = re.sub(r"\s+", "", line)
            if len(compact) < self.min_line_length:
                continue
            if re.fullmatch(r"[-_=]{3,}", compact):
                continue
            if re.fullmatch(r"(page|p\.)?\d{1,4}", compact, flags=re.IGNORECASE):
                continue
            if re.fullmatch(r"第?\d{1,4}页", compact):
                continue
            cleaned.append(line)
        return cleaned

    @staticmethod
    def _dedupe_lines(lines: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for line in lines:
            key = re.sub(r"\s+", "", line).lower()
            if line and key in seen:
                continue
            if line:
                seen.add(key)
            if not line and result and not result[-1]:
                continue
            result.append(line)
        return result

