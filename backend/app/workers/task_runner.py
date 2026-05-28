"""Synchronous task runner with a future async queue seam."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.services.document_service import DocumentService


class TaskRunner:
    def __init__(self, document_service: DocumentService | None = None) -> None:
        self.document_service = document_service or DocumentService()

    def run(self, doc_id: str, step: str, func: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        try:
            self.document_service.update_state(doc_id, current_step=step, error="")
            self.document_service.append_log(doc_id, f"Started {step}")
            result = func()
            self.document_service.append_log(doc_id, f"Finished {step}")
            return result
        except Exception as exc:
            self.document_service.update_state(doc_id, status="failed", current_step=step, error=str(exc))
            self.document_service.append_log(doc_id, f"Failed {step}: {exc}")
            raise

