"""QA generation and viewing APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.document_service import DocumentService
from app.services.pipeline_service import PipelineService


router = APIRouter(prefix="/api/files", tags=["qa"])


@router.post("/{doc_id}/generate-qa")
def generate_qa(doc_id: str) -> dict[str, Any]:
    try:
        return PipelineService().start_generate_qa(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{doc_id}/qa-records")
def get_qa_records(
    doc_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    q: str | None = Query(default=None),
) -> dict[str, Any]:
    service = DocumentService()
    try:
        service.load_state(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return service.paginate_jsonl(service.qa_records_path(doc_id), page=page, page_size=page_size, q=q)


@router.get("/{doc_id}/failed-chunks")
def get_failed_chunks(
    doc_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    service = DocumentService()
    try:
        service.load_state(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return service.paginate_jsonl(service.failed_chunks_path(doc_id), page=page, page_size=page_size)


@router.get("/{doc_id}/review-queue")
def get_review_queue(
    doc_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    service = DocumentService()
    try:
        return service.review_queue(doc_id, page=page, page_size=page_size)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{doc_id}/retry-failed")
def retry_failed(doc_id: str) -> dict[str, Any]:
    try:
        return PipelineService().retry_failed(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
