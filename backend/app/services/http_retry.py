"""Small retry helpers for OpenAI-compatible HTTP calls."""

from __future__ import annotations

import json
import time
import urllib.error
from collections.abc import Callable
from typing import Any

from app.config import settings


RETRYABLE_HTTP_CODES = {408, 409, 425, 429, 500, 502, 503, 504}


def urlopen_json_with_retries(call: Callable[[], Any], label: str) -> dict[str, Any]:
    max_attempts = max(1, settings.api_max_retries + 1)
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with call() as response:
                data = json.loads(response.read().decode("utf-8"))
            if not isinstance(data, dict):
                raise RuntimeError(f"{label} response must be a JSON object.")
            return data
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            last_error = RuntimeError(f"{label} request failed: HTTP {exc.code} {detail}")
            if exc.code not in RETRYABLE_HTTP_CODES or attempt >= max_attempts:
                raise last_error from exc
            time.sleep(_retry_delay(attempt, exc.headers.get("Retry-After")))
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = RuntimeError(f"{label} request failed: {exc}")
            if attempt >= max_attempts:
                raise last_error from exc
            time.sleep(_retry_delay(attempt))
    raise last_error or RuntimeError(f"{label} request failed.")


def _retry_delay(attempt: int, retry_after: str | None = None) -> float:
    if retry_after:
        try:
            return min(60.0, max(0.0, float(retry_after)))
        except ValueError:
            pass
    return min(60.0, settings.api_retry_base_seconds * (2 ** (attempt - 1)))
