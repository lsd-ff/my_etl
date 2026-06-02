"""FastAPI entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chroma_api, chunk_api, document_api, qa_api, search_api, upload_api


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
