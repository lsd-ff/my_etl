"""File, JSONL, state, and log persistence helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings


ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".markdown"}


class DocumentService:
    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir or settings.data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.chunks_dir = self.data_dir / "chunks"
        self.processed_dir = self.data_dir / "processed"
        self.states_dir = self.data_dir / "states"
        self.failed_dir = self.data_dir / "failed"
        self.logs_dir = self.data_dir / "logs"
        self.reports_dir = self.data_dir / "reports"
        self.chroma_dir = self.data_dir / "chroma"
        self.ensure_directories()

    def ensure_directories(self) -> None:
        for path in (
            self.raw_dir,
            self.chunks_dir,
            self.processed_dir,
            self.states_dir,
            self.failed_dir,
            self.logs_dir,
            self.reports_dir,
            self.chroma_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def create_or_update_document(self, filename: str, content: bytes) -> dict[str, Any]:
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_SUFFIXES:
            raise ValueError(f"Unsupported file type: {suffix}")
        file_hash = hashlib.sha256(content).hexdigest()
        doc_id = self.generate_doc_id(filename, file_hash)
        stored_filename = f"{doc_id}{suffix}"
        raw_path = self.raw_dir / stored_filename
        raw_path.write_bytes(content)

        now = self.now()
        previous = self.load_state(doc_id, default={})
        state = {
            "doc_id": doc_id,
            "filename": filename,
            "stored_filename": stored_filename,
            "file_path": str(raw_path),
            "file_type": self.file_type(filename),
            "status": "uploaded",
            "file_hash": file_hash,
            "total_chunks": 0,
            "processed_chunks": 0,
            "failed_chunks": 0,
            "qa_records": 0,
            "imported_to_chroma": False,
            "created_at": previous.get("created_at") or now,
            "updated_at": now,
            "current_step": "upload",
            "current_chunk_id": "",
            "current_chunk_index": 0,
            "total_work_chunks": 0,
            "current_qa_id": "",
            "embedded_records": 0,
            "total_embedding_records": 0,
            "progress_message": "",
            "error": "",
            "processed_chunk_hashes": [],
            "processed_chunk_ids": [],
            "low_quality_chunks": 0,
            "low_quality_qa": 0,
            "review_items": 0,
        }
        self.write_jsonl(self.chunks_path(doc_id), [])
        self.write_jsonl(self.qa_records_path(doc_id), [])
        self.write_jsonl(self.failed_chunks_path(doc_id), [])
        self.save_state(doc_id, state)
        self.append_log(doc_id, f"Uploaded {filename} as {stored_filename}")
        return state

    @staticmethod
    def generate_doc_id(filename: str, file_hash: str) -> str:
        stem = Path(filename).stem
        safe_stem = re.sub(r"[^A-Za-z0-9_\-\u4e00-\u9fff]+", "_", stem).strip("_")[:32]
        return f"{safe_stem or 'doc'}_{file_hash[:10]}"

    @staticmethod
    def file_type(filename: str) -> str:
        suffix = Path(filename).suffix.lower().lstrip(".")
        if suffix in {"md", "markdown"}:
            return "markdown"
        return suffix or "unknown"

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def state_path(self, doc_id: str) -> Path:
        return self.states_dir / f"{doc_id}_process_state.json"

    def chunks_path(self, doc_id: str) -> Path:
        return self.chunks_dir / f"{doc_id}_chunks.jsonl"

    def qa_records_path(self, doc_id: str) -> Path:
        return self.processed_dir / f"{doc_id}_qa_records.jsonl"

    def failed_chunks_path(self, doc_id: str) -> Path:
        return self.failed_dir / f"{doc_id}_failed_chunks.jsonl"

    def log_path(self, doc_id: str) -> Path:
        return self.logs_dir / f"{doc_id}.log"

    def quality_report_path(self, doc_id: str) -> Path:
        return self.reports_dir / f"{doc_id}_quality_report.json"

    def load_state(self, doc_id: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        path = self.state_path(doc_id)
        if not path.exists():
            if default is not None:
                return default
            raise FileNotFoundError(f"Document state not found: {doc_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def save_state(self, doc_id: str, state: dict[str, Any]) -> dict[str, Any]:
        state["updated_at"] = self.now()
        self.state_path(doc_id).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return state

    def update_state(self, doc_id: str, **updates: Any) -> dict[str, Any]:
        state = self.load_state(doc_id)
        state.update(updates)
        return self.save_state(doc_id, state)

    def list_documents(self) -> list[dict[str, Any]]:
        documents = []
        for path in self.states_dir.glob("*_process_state.json"):
            state = json.loads(path.read_text(encoding="utf-8"))
            documents.append(
                {
                    "doc_id": state.get("doc_id", ""),
                    "filename": state.get("filename", ""),
                    "file_type": state.get("file_type", ""),
                    "status": state.get("status", ""),
                    "total_chunks": int(state.get("total_chunks") or 0),
                    "processed_chunks": int(state.get("processed_chunks") or 0),
                    "failed_chunks": int(state.get("failed_chunks") or 0),
                    "qa_count": int(state.get("qa_records") or 0),
                    "imported_to_chroma": bool(state.get("imported_to_chroma")),
                    "created_at": state.get("created_at", ""),
                    "updated_at": state.get("updated_at", ""),
                    "progress_message": state.get("progress_message", ""),
                    "current_step": state.get("current_step", ""),
                }
            )
        return sorted(documents, key=lambda item: item.get("created_at", ""), reverse=True)

    def read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def write_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")

    def append_jsonl(self, path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")

    def paginate_jsonl(
        self,
        path: Path,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
    ) -> dict[str, Any]:
        rows = self.read_jsonl(path)
        if q:
            needle = q.lower()
            rows = [row for row in rows if needle in json.dumps(row, ensure_ascii=False).lower()]
        total = len(rows)
        start = max(0, (page - 1) * page_size)
        end = start + page_size
        return {"total": total, "items": rows[start:end]}

    def append_log(self, doc_id: str, message: str) -> None:
        line = f"{self.now()} {message}\n"
        with self.log_path(doc_id).open("a", encoding="utf-8") as file:
            file.write(line)

    def read_log(self, doc_id: str) -> str:
        path = self.log_path(doc_id)
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def count_jsonl(self, path: Path) -> int:
        return len(self.read_jsonl(path))

    def delete_document(self, doc_id: str, delete_chroma: bool = True) -> dict[str, Any]:
        state = self.load_state(doc_id)
        paths = [
            Path(state.get("file_path", "")),
            self.chunks_path(doc_id),
            self.qa_records_path(doc_id),
            self.failed_chunks_path(doc_id),
            self.log_path(doc_id),
            self.quality_report_path(doc_id),
            self.state_path(doc_id),
        ]
        deleted_files = 0
        for path in paths:
            if path and path.exists() and path.is_file():
                path.unlink()
                deleted_files += 1

        chroma_deleted = False
        chroma_error = ""
        if delete_chroma:
            try:
                from app.vectorstores.chroma_store import ChromaStore

                ChromaStore(persist_path=str(self.chroma_dir)).delete_doc(doc_id)
                chroma_deleted = True
            except Exception as exc:
                chroma_error = str(exc)

        return {
            "doc_id": doc_id,
            "filename": state.get("filename", ""),
            "deleted_files": deleted_files,
            "chroma_deleted": chroma_deleted,
            "chroma_error": chroma_error,
            "status": "deleted",
        }

    def compact_qa_records(self, doc_id: str) -> dict[str, Any]:
        state = self.load_state(doc_id)
        path = self.qa_records_path(doc_id)
        rows = self.read_jsonl(path)
        compacted: list[dict[str, Any]] = []
        seen_questions: set[str] = set()
        for row in rows:
            metadata = row.get("metadata") or {}
            document = str(row.get("document") or row.get("question") or "").strip()
            if not document:
                continue
            key = re.sub(r"[\W_]+", "", document.lower())
            if key in seen_questions:
                continue
            seen_questions.add(key)
            embedding_text = str(row.get("embedding_text") or "").strip() or self.embedding_text(
                document,
                str(metadata.get("context") or row.get("context") or ""),
                str(metadata.get("keywords") or row.get("keywords") or ""),
            )
            compacted.append(
                {
                    "id": row.get("id", ""),
                    "document": document,
                    "embedding_text": embedding_text,
                    "metadata": metadata,
                }
            )
        self.write_jsonl(path, compacted)
        self.update_state(
            doc_id,
            qa_records=len(compacted),
            imported_to_chroma=False,
            current_step="compact_qa_records",
            progress_message=f"Compacted {len(compacted)} QA records",
        )
        self.append_log(doc_id, f"Compacted QA JSONL for {state.get('filename', doc_id)}: {len(compacted)} records")
        return {"doc_id": doc_id, "records": len(compacted), "status": "compacted"}

    def write_quality_report(self, doc_id: str, report: dict[str, Any]) -> None:
        self.quality_report_path(doc_id).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    def read_quality_report(self, doc_id: str) -> dict[str, Any]:
        path = self.quality_report_path(doc_id)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def review_queue(self, doc_id: str, page: int = 1, page_size: int = 100) -> dict[str, Any]:
        self.load_state(doc_id)
        items: list[dict[str, Any]] = []
        for chunk in self.read_jsonl(self.chunks_path(doc_id)):
            warnings = chunk.get("warnings") or []
            quality_score = float(chunk.get("quality_score") or 1.0)
            if warnings or quality_score < 0.75:
                items.append(
                    {
                        "type": "chunk",
                        "severity": "warning" if quality_score >= 0.5 else "high",
                        "id": chunk.get("chunk_id", ""),
                        "score": quality_score,
                        "reasons": warnings,
                        "page": chunk.get("page", 0),
                        "section": chunk.get("section", ""),
                        "content": chunk.get("content", ""),
                    }
                )
        for row in self.read_jsonl(self.qa_records_path(doc_id)):
            metadata = row.get("metadata") or {}
            warnings = [
                item.strip()
                for item in str(metadata.get("validation_warnings") or "").split(",")
                if item.strip()
            ]
            quality_score = float(metadata.get("quality_score") or 1.0)
            if warnings or quality_score < 0.75:
                items.append(
                    {
                        "type": "qa",
                        "severity": "warning" if quality_score >= 0.5 else "high",
                        "id": row.get("id", ""),
                        "score": quality_score,
                        "reasons": warnings,
                        "page": metadata.get("page", 0),
                        "section": metadata.get("section", ""),
                        "question": row.get("document", ""),
                        "answer": metadata.get("answer", ""),
                        "evidence": metadata.get("evidence", ""),
                    }
                )
        for row in self.read_jsonl(self.failed_chunks_path(doc_id)):
            items.append(
                {
                    "type": "failed_chunk",
                    "severity": "high",
                    "id": row.get("chunk_id", ""),
                    "score": 0,
                    "reasons": [row.get("failure_class") or row.get("error_type") or "failed"],
                    "page": row.get("page", 0),
                    "section": row.get("section", ""),
                    "content": row.get("content", ""),
                    "error": row.get("error", ""),
                }
            )
        total = len(items)
        start = max(0, (page - 1) * page_size)
        end = start + page_size
        return {
            "total": total,
            "items": items[start:end],
            "summary": {
                "chunks": sum(1 for item in items if item["type"] == "chunk"),
                "qa": sum(1 for item in items if item["type"] == "qa"),
                "failed_chunks": sum(1 for item in items if item["type"] == "failed_chunk"),
                "high": sum(1 for item in items if item["severity"] == "high"),
            },
        }

    @staticmethod
    def embedding_text(question: str, context: str, keywords: str) -> str:
        return f"问题：\n{question}\n\n详细上下文：\n{context}\n\n关键词：\n{keywords}"
