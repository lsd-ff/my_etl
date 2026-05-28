"""End-to-end file ingestion pipeline with JSONL checkpoints."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.chunkers.recursive_chunker import RecursiveChunker
from app.cleaners.text_cleaner import TextCleaner
from app.config import settings
from app.generators.qa_generator import QAGenerator
from app.loaders.base_loader import get_loader
from app.schemas.qa_record import Chunk, IngestResult, LoadedSegment, QARecord
from app.vectorstores.chroma_store import ChromaStore


class IngestionPipeline:
    def __init__(
        self,
        cleaner: TextCleaner | None = None,
        chunker: RecursiveChunker | None = None,
        qa_generator: QAGenerator | None = None,
        store: ChromaStore | None = None,
        processing_path: str | None = None,
    ) -> None:
        self.cleaner = cleaner or TextCleaner()
        self.chunker = chunker or RecursiveChunker()
        self.qa_generator = qa_generator or QAGenerator()
        self.store = store or ChromaStore()
        self.processing_path = Path(processing_path or settings.processing_path)

    def ingest(self, file_path: str) -> IngestResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        source = str(path)
        doc_id = self._doc_id(path)
        file_hash = self._file_hash(path)
        doc_dir = self.processing_path / doc_id
        chunks_path = doc_dir / "chunks.jsonl"
        qa_path = doc_dir / "qa_records.jsonl"
        state_path = doc_dir / "process_state.json"
        doc_dir.mkdir(parents=True, exist_ok=True)

        state = self._load_state(state_path)
        same_file = state.get("source") == source and state.get("file_hash") == file_hash
        if same_file and state.get("chroma_written"):
            return IngestResult(doc_id=doc_id, chunks=0, qa_records=0, status="skipped")
        if self.store.has_file_hash(source, file_hash) and not same_file:
            self._save_state(
                state_path,
                self._initial_state(doc_id, source, file_hash, chunks_path, qa_path)
                | {"chroma_written": True, "embedded": True},
            )
            return IngestResult(doc_id=doc_id, chunks=0, qa_records=0, status="skipped")

        if not same_file:
            state = self._initial_state(doc_id, source, file_hash, chunks_path, qa_path)
            self._write_jsonl(qa_path, [])

        # 1-5. Parse, clean, chunk, save chunks.jsonl, and persist chunk_hash.
        loader = get_loader(path)
        loaded_segments = loader.load(path)
        cleaned_segments = self._clean_segments(loaded_segments)
        chunks = self.chunker.chunk_segments(doc_id=doc_id, segments=cleaned_segments)
        self._write_jsonl(chunks_path, [chunk.to_dict() for chunk in chunks])
        state.update(
            {
                "doc_id": doc_id,
                "source": source,
                "file_hash": file_hash,
                "chunks_jsonl": str(chunks_path),
                "qa_records_jsonl": str(qa_path),
                "chunk_count": len(chunks),
            }
        )
        self._save_state(state_path, state)

        # 6-11. Read chunks.jsonl, skip processed chunks, validate AI JSON,
        # append qa_records.jsonl, and update process_state.json per chunk.
        processed_hashes = set(state.get("processed_chunk_hashes") or [])
        processed_ids = set(state.get("processed_chunk_ids") or [])
        file_type = self._file_type(path)
        for chunk in self._read_chunks(chunks_path):
            if chunk.chunk_hash in processed_hashes or self.store.has_chunk_hash(source, chunk.chunk_hash):
                processed_hashes.add(chunk.chunk_hash)
                processed_ids.add(chunk.chunk_id)
                continue

            ai_payloads = self.qa_generator.generate_json_for_chunk(chunk)
            valid_payloads = self._validate_ai_payloads(ai_payloads)
            records = [
                self._qa_record_from_payload(
                    payload=payload,
                    chunk=chunk,
                    qa_index=index,
                    source=source,
                    file_type=file_type,
                    file_hash=file_hash,
                )
                for index, payload in enumerate(valid_payloads, start=1)
            ]
            self._append_jsonl(qa_path, [record.to_jsonl_dict() for record in records])
            processed_hashes.add(chunk.chunk_hash)
            processed_ids.add(chunk.chunk_id)
            state.update(
                {
                    "processed_chunk_hashes": sorted(processed_hashes),
                    "processed_chunk_ids": sorted(processed_ids),
                    "qa_record_count": self._count_jsonl(qa_path),
                    "embedded": False,
                    "chroma_written": False,
                }
            )
            self._save_state(state_path, state)

        # 12-13. After all QA JSONL records exist, embed in batch and write Chroma.
        qa_records = self._read_qa_records(qa_path)
        self._write_records_to_chroma(qa_records)
        state.update(
            {
                "processed_chunk_hashes": sorted(processed_hashes),
                "processed_chunk_ids": sorted(processed_ids),
                "qa_record_count": len(qa_records),
                "embedded": True,
                "chroma_written": True,
            }
        )
        self._save_state(state_path, state)
        return IngestResult(doc_id=doc_id, chunks=len(chunks), qa_records=len(qa_records), status="success")

    def _clean_segments(self, segments: list[LoadedSegment]) -> list[LoadedSegment]:
        cleaned: list[LoadedSegment] = []
        for segment in segments:
            text = self.cleaner.clean(segment.text)
            if text:
                cleaned.append(
                    LoadedSegment(
                        text=text,
                        source=segment.source,
                        file_type=segment.file_type,
                        page=segment.page,
                        section=segment.section,
                    )
                )
        return cleaned

    def _qa_record_from_payload(
        self,
        payload: dict[str, str],
        chunk: Chunk,
        qa_index: int,
        source: str,
        file_type: str,
        file_hash: str,
    ) -> QARecord:
        return QARecord(
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_index,
            qa_index=qa_index,
            question=payload["question"],
            answer=payload["answer"],
            context=payload["context"],
            keywords=payload["keywords"],
            source=source,
            file_type=file_type,
            page=chunk.page,
            section=chunk.section,
            file_hash=file_hash,
            chunk_hash=chunk.chunk_hash,
            id_pad_width=settings.id_pad_width,
        )

    @staticmethod
    def _validate_ai_payloads(payloads: Any) -> list[dict[str, str]]:
        if not isinstance(payloads, list):
            return []
        valid: list[dict[str, str]] = []
        for payload in payloads:
            if not isinstance(payload, dict):
                continue
            item: dict[str, str] = {}
            for field in ("question", "answer", "context", "keywords"):
                value = payload.get(field)
                if not isinstance(value, str) or not value.strip():
                    break
                item[field] = value.strip()
            else:
                if "[" not in item["keywords"] and "]" not in item["keywords"]:
                    valid.append(item)
        return valid[:5]

    def _write_records_to_chroma(self, records: list[QARecord]) -> None:
        if hasattr(self.store, "add_or_upsert_qas"):
            self.store.add_or_upsert_qas(records)
            return
        for record in records:
            self.store.add_or_upsert_qa(record)

    @staticmethod
    def _initial_state(
        doc_id: str,
        source: str,
        file_hash: str,
        chunks_path: Path,
        qa_path: Path,
    ) -> dict[str, Any]:
        return {
            "doc_id": doc_id,
            "source": source,
            "file_hash": file_hash,
            "chunks_jsonl": str(chunks_path),
            "qa_records_jsonl": str(qa_path),
            "chunk_count": 0,
            "qa_record_count": 0,
            "processed_chunk_hashes": [],
            "processed_chunk_ids": [],
            "embedded": False,
            "chroma_written": False,
        }

    @staticmethod
    def _load_state(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _save_state(path: Path, state: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    rows.append(json.loads(line))
        return rows

    def _read_chunks(self, path: Path) -> list[Chunk]:
        return [Chunk.from_dict(row) for row in self._read_jsonl(path)]

    def _read_qa_records(self, path: Path) -> list[QARecord]:
        return [QARecord.from_dict(row, id_pad_width=settings.id_pad_width) for row in self._read_jsonl(path)]

    def _count_jsonl(self, path: Path) -> int:
        return len(self._read_jsonl(path))

    @staticmethod
    def _file_hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _doc_id(path: Path) -> str:
        stem = path.stem.encode("utf-8")
        digest = hashlib.sha1(str(path.resolve()).encode("utf-8") + stem).hexdigest()[:10]
        safe_stem = "".join(ch if ch.isalnum() else "_" for ch in path.stem).strip("_")[:20]
        return f"{safe_stem or 'doc'}_{digest}"

    @staticmethod
    def _file_type(path: Path) -> str:
        file_type = path.suffix.lower().lstrip(".") or "unknown"
        if file_type in {"md", "markdown"}:
            return "markdown"
        return file_type
