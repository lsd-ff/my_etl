"""Document listing, state, logs, and batch APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.batch_service import BatchService
from app.services.document_service import DocumentService


router = APIRouter(prefix="/api", tags=["documents"])


class BatchProcessRequest(BaseModel):
    doc_ids: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)


@router.get("/files")
def list_files() -> list[dict[str, Any]]:
    return DocumentService().list_documents()


@router.delete("/files/{doc_id}")
def delete_file(doc_id: str) -> dict[str, Any]:
    try:
        return DocumentService().delete_document(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/files/{doc_id}/state")
def get_state(doc_id: str) -> dict[str, Any]:
    try:
        state = DocumentService().load_state(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "doc_id": state.get("doc_id", doc_id),
        "status": state.get("status", ""),
        "total_chunks": state.get("total_chunks", 0),
        "processed_chunks": state.get("processed_chunks", 0),
        "failed_chunks": state.get("failed_chunks", 0),
        "qa_records": state.get("qa_records", 0),
        "imported_to_chroma": state.get("imported_to_chroma", False),
        **state,
    }


@router.get("/files/{doc_id}/logs")
def get_logs(doc_id: str) -> dict[str, str]:
    service = DocumentService()
    try:
        service.load_state(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"doc_id": doc_id, "log": service.read_log(doc_id)}


@router.post("/batch/process")
def batch_process(request: BatchProcessRequest) -> dict[str, Any]:
    return BatchService().process(request.doc_ids, request.steps)
