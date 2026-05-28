"""FastAPI entrypoint."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.api import chroma_api, chunk_api, document_api, qa_api, search_api, upload_api
from app.pipeline.ingestion_pipeline import IngestionPipeline
from app.vectorstores.chroma_store import ChromaStore


app = FastAPI(title="Large Document QA Vectorization Platform", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_api.router)
app.include_router(document_api.router)
app.include_router(chunk_api.router)
app.include_router(qa_api.router)
app.include_router(chroma_api.router)
app.include_router(search_api.router)


class IngestRequest(BaseModel):
    file_path: str


class LegacySearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=50)


@app.post("/ingest")
def ingest(request: IngestRequest) -> dict[str, Any]:
    pipeline = IngestionPipeline()
    return pipeline.ingest(request.file_path).to_dict()


@app.post("/search")
def legacy_search(request: LegacySearchRequest) -> list[dict[str, Any]]:
    store = ChromaStore()
    return store.search(request.query, top_k=request.top_k)

