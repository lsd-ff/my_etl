"""Embedding provider abstraction."""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.error
import urllib.request

from app.config import settings


class MockEmbedding:
    """Deterministic hashing embedding for local development and tests."""

    def __init__(self, dim: int | None = None) -> None:
        self.dim = dim or settings.embedding_dim

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = self._tokens(text)
        if not tokens:
            tokens = [text]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + (digest[5] / 255.0)
            vector[index] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    @staticmethod
    def _tokens(text: str) -> list[str]:
        return re.findall(r"[A-Za-z0-9_\-\u4e00-\u9fff]{2,}", text.lower())


class EmbeddingService:
    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider or settings.embedding_provider
        if self.provider == "mock":
            self.client = MockEmbedding()
        elif self.provider in {"openai", "dashscope", "openai_compatible"}:
            self.client = OpenAICompatibleEmbedding()
        else:
            raise NotImplementedError(f"Unsupported embedding provider: {self.provider}")

    def embed(self, text: str) -> list[float]:
        return self.client.embed(text)


class OpenAICompatibleEmbedding:
    """OpenAI-compatible embeddings client, including DashScope compatible mode."""

    def __init__(self) -> None:
        self.api_key = settings.embedding_api_key
        self.base_url = settings.embedding_base_url.rstrip("/")
        self.model = settings.embedding_model
        if not self.api_key:
            raise ValueError("EMBEDDING_API_KEY is required for non-mock embedding provider.")
        if not self.base_url:
            raise ValueError("EMBEDDING_BASE_URL is required for non-mock embedding provider.")

    def embed(self, text: str) -> list[float]:
        payload = {"model": self.model, "input": text}
        request = urllib.request.Request(
            f"{self.base_url}/embeddings",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Embedding request failed: HTTP {exc.code} {detail}") from exc
        return [float(value) for value in data["data"][0]["embedding"]]
