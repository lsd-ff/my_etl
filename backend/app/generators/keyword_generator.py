"""Keyword extraction for mock mode."""

from __future__ import annotations

import re
from collections import Counter


class KeywordGenerator:
    STOPWORDS = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "一个",
        "一种",
        "以及",
        "可以",
        "通过",
        "进行",
        "用于",
        "使用",
        "包括",
    }

    def generate(self, text: str, min_keywords: int = 5, max_keywords: int = 12) -> str:
        tokens = self._tokens(text)
        counter = Counter(tokens)
        keywords = [word for word, _ in counter.most_common(max_keywords) if word not in self.STOPWORDS]
        if len(keywords) < min_keywords:
            for fallback in ["文档", "知识库", "语义检索", "RAG", "Embedding", "上下文"]:
                if fallback not in keywords:
                    keywords.append(fallback)
                if len(keywords) >= min_keywords:
                    break
        return ",".join(keywords[:max_keywords])

    @staticmethod
    def _tokens(text: str) -> list[str]:
        english = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text)
        chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
        return english + chinese_terms

