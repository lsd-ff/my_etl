"""Search test API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings
from app.vectorstores.chroma_store import ChromaStore


router = APIRouter(prefix="/api", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)


@router.post("/search")
def search(request: SearchRequest) -> list[dict[str, Any]]:
    store = ChromaStore(persist_path=settings.chroma_path)
    return store.search(request.query, top_k=request.top_k)

