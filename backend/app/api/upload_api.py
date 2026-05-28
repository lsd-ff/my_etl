"""Upload API."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.document_service import DocumentService


router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict[str, str]:
    try:
        content = await file.read()
        state = DocumentService().create_or_update_document(file.filename or "document", content)
        return {"doc_id": state["doc_id"], "filename": state["filename"], "status": state["status"]}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

