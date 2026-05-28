"""Generate semantic-enhanced context strings."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

from app.config import settings


class MockLLM:
    """Deterministic local LLM stand-in for pipeline verification."""

    def complete(self, prompt: str) -> str:
        return prompt[:400]


class OpenAICompatibleLLM:
    """Minimal OpenAI-compatible chat client for QA generation."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        max_rpm: int | None = None,
    ) -> None:
        self.api_key = api_key or settings.llm_api_key
        self.base_url = (base_url or settings.llm_base_url).rstrip("/")
        self.model = model or settings.llm_model
        self.max_rpm = max(1, max_rpm or settings.llm_max_rpm)
        self._last_call = 0.0
        if not self.api_key:
            raise ValueError("LLM_API_KEY is required for non-mock LLM provider.")
        if not self.base_url:
            raise ValueError("LLM_BASE_URL is required for non-mock LLM provider.")

    def complete(self, prompt: str) -> str:
        self._throttle()
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是严谨的中文 RAG 数据加工助手，只输出合法 JSON。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            self._url("chat/completions"),
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
            raise RuntimeError(f"LLM request failed: HTTP {exc.code} {detail}") from exc
        return str(data["choices"][0]["message"]["content"])

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _throttle(self) -> None:
        min_interval = 60.0 / self.max_rpm
        wait = min_interval - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.time()


class ContextGenerator:
    def __init__(self, llm: MockLLM | None = None) -> None:
        self.llm = llm or MockLLM()

    def generate(self, chunk_text: str) -> str:
        text = self._compact(chunk_text)
        if not text:
            return ""
        sentences = re.split(r"(?<=[。！？!?；;])\s*|(?<=\.)\s+", text)
        selected = [s.strip() for s in sentences if len(s.strip()) >= 8][:6]
        context = " ".join(selected) or text[:400]
        if len(context) < 150 and len(text) > len(context):
            context = f"{context} {text[: 400 - len(context)]}".strip()
        return context[:400].strip()

    @staticmethod
    def _compact(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
