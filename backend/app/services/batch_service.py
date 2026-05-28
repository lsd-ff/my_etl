"""Batch processing service."""

from __future__ import annotations

from typing import Any

from app.services.pipeline_service import PipelineService


class BatchService:
    def __init__(self, pipeline_service: PipelineService | None = None) -> None:
        self.pipeline = pipeline_service or PipelineService()

    def process(self, doc_ids: list[str], steps: list[str]) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        for doc_id in doc_ids:
            doc_result: dict[str, Any] = {"doc_id": doc_id, "steps": [], "status": "success"}
            for step in steps:
                try:
                    if step == "chunk":
                        result = self.pipeline.chunk_document(doc_id)
                    elif step == "generate_qa":
                        result = self.pipeline.generate_qa(doc_id)
                    elif step == "import_chroma":
                        result = self.pipeline.import_chroma(doc_id)
                    else:
                        raise ValueError(f"Unsupported batch step: {step}")
                    doc_result["steps"].append({"step": step, "status": "success", "result": result})
                except Exception as exc:
                    doc_result["status"] = "failed"
                    doc_result["steps"].append({"step": step, "status": "failed", "error": str(exc)})
                    break
            results.append(doc_result)
        return {"status": "finished", "results": results}

