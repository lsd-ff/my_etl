"""Chunk APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.document_service import DocumentService
from app.services.pipeline_service import PipelineService


router = APIRouter(prefix="/api/files", tags=["chunks"])


@router.post("/{doc_id}/chunk")
def chunk_file(doc_id: str) -> dict[str, Any]:
    try:
        return PipelineService().chunk_document(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{doc_id}/chunks")
def get_chunks(
    doc_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    service = DocumentService()
    try:
        service.load_state(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return service.paginate_jsonl(service.chunks_path(doc_id), page=page, page_size=page_size)

