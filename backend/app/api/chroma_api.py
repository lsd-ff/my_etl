"""Chroma import APIs."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.services.pipeline_service import PipelineService


router = APIRouter(prefix="/api/files", tags=["chroma"])


@router.post("/{doc_id}/import-chroma")
def import_chroma(doc_id: str) -> dict[str, Any]:
    try:
        return PipelineService().import_chroma(doc_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

