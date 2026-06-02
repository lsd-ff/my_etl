"""Chroma import APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.services.pipeline_service import PipelineService
from app.vectorstores.chroma_store import ChromaStore


router = APIRouter(prefix="/api/files", tags=["chroma"])


@router.post("/{doc_id}/import-chroma")
def import_chroma(doc_id: str) -> dict[str, Any]:
    try:
        return PipelineService().import_chroma(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{doc_id}/compact-qa-records")
def compact_qa_records(doc_id: str) -> dict[str, Any]:
    try:
        return PipelineService().compact_qa_records(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/-/chroma-info")
def chroma_info() -> dict[str, Any]:
    return ChromaStore(persist_path=settings.chroma_path).info()
