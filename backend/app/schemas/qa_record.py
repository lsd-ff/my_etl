"""Schemas for chunks, QA records, and API results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def format_index(value: int, pad_width: int = 0) -> str:
    if pad_width > 0:
        return str(value).zfill(pad_width)
    return str(value)


@dataclass(frozen=True)
class LoadedSegment:
    text: str
    source: str
    file_type: str
    page: int = 0
    section: str = ""


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    chunk_index: int
    content: str
    page: int
    section: str
    chunk_hash: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "page": self.page,
            "section": self.section,
            "chunk_hash": self.chunk_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chunk":
        return cls(
            chunk_id=str(data["chunk_id"]),
            doc_id=str(data["doc_id"]),
            chunk_index=int(data["chunk_index"]),
            content=str(data["content"]),
            page=int(data.get("page") or 0),
            section=str(data.get("section") or ""),
            chunk_hash=str(data["chunk_hash"]),
        )


@dataclass(frozen=True)
class QARecord:
    doc_id: str
    chunk_id: str
    chunk_index: int
    qa_index: int
    question: str
    answer: str
    context: str
    keywords: str
    source: str
    file_type: str
    page: int
    section: str
    file_hash: str
    chunk_hash: str
    id_pad_width: int = 0

    @property
    def qa_id(self) -> str:
        chunk_index = format_index(self.chunk_index, self.id_pad_width)
        qa_index = format_index(self.qa_index, self.id_pad_width)
        return f"{self.doc_id}_chunk{chunk_index}_qa{qa_index}"

    @property
    def document(self) -> str:
        return self.question

    @property
    def embedding_text(self) -> str:
        return (
            f"问题：\n{self.question}\n\n"
            f"详细上下文：\n{self.context}\n\n"
            f"关键词：\n{self.keywords}"
        )

    @property
    def metadata(self) -> dict[str, str | int | float | bool]:
        return {
            "answer": self.answer,
            "context": self.context,
            "keywords": self.keywords,
            "source": self.source,
            "file_type": self.file_type,
            "page": int(self.page or 0),
            "section": self.section or "",
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "chunk_index": int(self.chunk_index),
            "qa_index": int(self.qa_index),
            "file_hash": self.file_hash,
            "chunk_hash": self.chunk_hash,
        }

    def to_jsonl_dict(self) -> dict[str, Any]:
        return {
            "id": self.qa_id,
            "document": self.document,
            "embedding_text": self.embedding_text,
            "metadata": self.metadata,
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "qa_index": self.qa_index,
            "question": self.question,
            "answer": self.answer,
            "context": self.context,
            "keywords": self.keywords,
            "source": self.source,
            "file_type": self.file_type,
            "page": self.page,
            "section": self.section,
            "file_hash": self.file_hash,
            "chunk_hash": self.chunk_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], id_pad_width: int = 0) -> "QARecord":
        metadata = data.get("metadata") or {}
        return cls(
            doc_id=str(data.get("doc_id") or metadata.get("doc_id")),
            chunk_id=str(data.get("chunk_id") or metadata.get("chunk_id")),
            chunk_index=int(data.get("chunk_index") or metadata.get("chunk_index")),
            qa_index=int(data.get("qa_index") or metadata.get("qa_index")),
            question=str(data.get("question") or data.get("document")),
            answer=str(data.get("answer") or metadata.get("answer")),
            context=str(data.get("context") or metadata.get("context")),
            keywords=str(data.get("keywords") or metadata.get("keywords")),
            source=str(data.get("source") or metadata.get("source")),
            file_type=str(data.get("file_type") or metadata.get("file_type")),
            page=int(data.get("page") or metadata.get("page") or 0),
            section=str(data.get("section") or metadata.get("section") or ""),
            file_hash=str(data.get("file_hash") or metadata.get("file_hash")),
            chunk_hash=str(data.get("chunk_hash") or metadata.get("chunk_hash")),
            id_pad_width=id_pad_width,
        )


@dataclass(frozen=True)
class IngestResult:
    doc_id: str
    chunks: int
    qa_records: int
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "chunks": self.chunks,
            "qa_records": self.qa_records,
            "status": self.status,
        }

