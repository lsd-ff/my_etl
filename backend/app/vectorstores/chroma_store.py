"""Chroma storage for QA records."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from typing import Any

from app.config import settings
from app.embeddings.embedding_service import EmbeddingService
from app.schemas.qa_record import QARecord


class ChromaStore:
    def __init__(
        self,
        persist_path: str | None = None,
        collection_name: str | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise ImportError("Chroma support requires chromadb. Install requirements.txt.") from exc

        self.persist_path = persist_path or settings.chroma_path
        self.base_collection_name = collection_name or settings.chroma_collection
        self.collection_name = self._collection_name_for_current_embedding(self.base_collection_name)
        self.embedding_service = embedding_service or EmbeddingService()
        if settings.chroma_mode == "http":
            self.client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        else:
            self.client = chromadb.PersistentClient(path=self.persist_path)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata=self._collection_metadata(),
        )

    @staticmethod
    def _collection_name_for_current_embedding(base_name: str) -> str:
        if settings.embedding_provider == "mock":
            namespace = f"mock_{settings.embedding_dim}"
        else:
            namespace = f"{settings.embedding_provider}_{settings.embedding_model}"
        return ChromaStore._normalize_collection_name(f"{base_name}_{namespace}")

    @staticmethod
    def _normalize_collection_name(raw_name: str) -> str:
        normalized = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_name).strip("._-")
        normalized = normalized or "collection"
        if len(normalized) <= 63:
            return normalized

        digest = hashlib.sha1(raw_name.encode("utf-8")).hexdigest()[:8]
        prefix_length = 63 - len(digest) - 1
        prefix = normalized[:prefix_length].rstrip("._-") or "collection"
        return f"{prefix}_{digest}"

    @staticmethod
    def _collection_metadata() -> dict[str, str | int]:
        metadata: dict[str, str | int] = {
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
        }
        if settings.embedding_provider == "mock":
            metadata["embedding_dim"] = settings.embedding_dim
        return metadata

    def add_or_upsert_qa(self, record: QARecord) -> None:
        self.add_or_upsert_qas([record])

    def add_or_upsert_qas(
        self,
        records: list[QARecord],
        progress_callback: Callable[[int, int, QARecord], None] | None = None,
    ) -> None:
        if not records:
            return
        ids: list[str] = []
        documents: list[str] = []
        embeddings: list[list[float]] = []
        metadatas: list[dict[str, Any]] = []
        total = len(records)
        for index, record in enumerate(records, start=1):
            if progress_callback:
                progress_callback(index, total, record)
            ids.append(record.qa_id)
            documents.append(record.document)
            embeddings.append(self.embedding_service.embed(record.embedding_text))
            metadatas.append(record.metadata)
        payload = {
            "ids": ids,
            "documents": documents,
            "embeddings": embeddings,
            "metadatas": metadatas,
        }
        if hasattr(self.collection, "upsert"):
            self.collection.upsert(**payload)
            return
        existing = self.collection.get(ids=ids)
        existing_ids = set(existing.get("ids") or [])
        new_indexes = [index for index, qa_id in enumerate(ids) if qa_id not in existing_ids]
        if not new_indexes:
            return
        self.collection.add(
            ids=[ids[index] for index in new_indexes],
            documents=[documents[index] for index in new_indexes],
            embeddings=[embeddings[index] for index in new_indexes],
            metadatas=[metadatas[index] for index in new_indexes],
        )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        embedding = self.embedding_service.embed(query)
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        rows: list[dict[str, Any]] = []
        for question, metadata, distance in zip(documents, metadatas, distances):
            score = 1.0 / (1.0 + float(distance))
            rows.append(
                {
                    "question": question,
                    "answer": metadata.get("answer", ""),
                    "context": metadata.get("context", ""),
                    "keywords": metadata.get("keywords", ""),
                    "source": metadata.get("source", ""),
                    "page": metadata.get("page", 0),
                    "section": metadata.get("section", ""),
                    "score": score,
                    "chunk_id": metadata.get("chunk_id", ""),
                    "doc_id": metadata.get("doc_id", ""),
                }
            )
        return rows

    def has_file_hash(self, source: str, file_hash: str) -> bool:
        result = self.collection.get(where={"$and": [{"source": source}, {"file_hash": file_hash}]}, limit=1)
        return bool(result.get("ids"))

    def has_chunk_hash(self, source: str, chunk_hash: str) -> bool:
        result = self.collection.get(where={"$and": [{"source": source}, {"chunk_hash": chunk_hash}]}, limit=1)
        return bool(result.get("ids"))

    def delete_doc(self, doc_id: str) -> None:
        self.collection.delete(where={"doc_id": doc_id})

    def info(self) -> dict[str, Any]:
        try:
            count = self.collection.count()
        except Exception:
            count = 0
        return {
            "collection": self.collection_name,
            "base_collection": self.base_collection_name,
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "persist_path": self.persist_path,
            "count": count,
        }
