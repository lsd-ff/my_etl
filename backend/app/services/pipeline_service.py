"""Step-by-step document processing service."""

from __future__ import annotations

from typing import Any

from app.chunkers.recursive_chunker import RecursiveChunker
from app.cleaners.text_cleaner import TextCleaner
from app.config import settings
from app.generators.qa_generator import QAGenerator
from app.loaders.base_loader import get_loader
from app.schemas.qa_record import Chunk, LoadedSegment, QARecord
from app.services.document_service import DocumentService
from app.vectorstores.chroma_store import ChromaStore
from app.workers.task_runner import TaskRunner


class PipelineService:
    def __init__(
        self,
        document_service: DocumentService | None = None,
        cleaner: TextCleaner | None = None,
        chunker: RecursiveChunker | None = None,
        qa_generator: QAGenerator | None = None,
        store: Any | None = None,
        runner: TaskRunner | None = None,
    ) -> None:
        self.documents = document_service or DocumentService()
        self.cleaner = cleaner or TextCleaner()
        self.chunker = chunker or RecursiveChunker()
        self.qa_generator = qa_generator or QAGenerator()
        self.store = store
        self.runner = runner or TaskRunner(self.documents)

    def chunk_document(self, doc_id: str) -> dict[str, Any]:
        def task() -> dict[str, Any]:
            state = self.documents.update_state(doc_id, status="chunking", current_step="chunk", error="")
            loader = get_loader(state["file_path"])
            loaded_segments = loader.load(state["file_path"])
            cleaned_segments = self._clean_segments(loaded_segments)
            chunks = self.chunker.chunk_segments(doc_id=doc_id, segments=cleaned_segments)
            self.documents.write_jsonl(self.documents.chunks_path(doc_id), [chunk.to_dict() for chunk in chunks])
            self.documents.write_jsonl(self.documents.qa_records_path(doc_id), [])
            self.documents.write_jsonl(self.documents.failed_chunks_path(doc_id), [])
            self.documents.update_state(
                doc_id,
                status="chunked",
                total_chunks=len(chunks),
                processed_chunks=0,
                failed_chunks=0,
                qa_records=0,
                imported_to_chroma=False,
                processed_chunk_hashes=[],
                processed_chunk_ids=[],
                current_step="chunk",
                error="",
            )
            return {"doc_id": doc_id, "chunks": len(chunks), "status": "chunked"}

        return self.runner.run(doc_id, "chunk", task)

    def generate_qa(self, doc_id: str, chunks: list[Chunk] | None = None) -> dict[str, Any]:
        def task() -> dict[str, Any]:
            state = self.documents.update_state(doc_id, status="qa_processing", current_step="generate_qa", error="")
            chunk_rows = chunks or [Chunk.from_dict(row) for row in self.documents.read_jsonl(self.documents.chunks_path(doc_id))]
            processed_hashes = set(state.get("processed_chunk_hashes") or [])
            processed_ids = set(state.get("processed_chunk_ids") or [])
            failed_rows: list[dict[str, Any]] = []

            for chunk in chunk_rows:
                if chunk.chunk_hash in processed_hashes:
                    continue
                try:
                    payloads = self._validate_ai_payloads(self.qa_generator.generate_json_for_chunk(chunk))
                    records = [
                        self._qa_record_from_payload(payload, chunk, index, state)
                        for index, payload in enumerate(payloads, start=1)
                    ]
                    self.documents.append_jsonl(
                        self.documents.qa_records_path(doc_id),
                        [record.to_jsonl_dict() for record in records],
                    )
                    processed_hashes.add(chunk.chunk_hash)
                    processed_ids.add(chunk.chunk_id)
                    self.documents.append_log(doc_id, f"Generated {len(records)} QA records for {chunk.chunk_id}")
                except Exception as exc:
                    failed_rows.append({**chunk.to_dict(), "error": str(exc), "failed_at": self.documents.now()})
                    self.documents.append_log(doc_id, f"Chunk failed {chunk.chunk_id}: {exc}")

                self.documents.update_state(
                    doc_id,
                    processed_chunks=len(processed_hashes),
                    failed_chunks=len(failed_rows),
                    qa_records=self.documents.count_jsonl(self.documents.qa_records_path(doc_id)),
                    processed_chunk_hashes=sorted(processed_hashes),
                    processed_chunk_ids=sorted(processed_ids),
                    imported_to_chroma=False,
                    status="qa_processing",
                )

            self.documents.write_jsonl(self.documents.failed_chunks_path(doc_id), failed_rows)
            final_status = "qa_failed" if failed_rows else "qa_done"
            final_state = self.documents.update_state(
                doc_id,
                status=final_status,
                processed_chunks=len(processed_hashes),
                failed_chunks=len(failed_rows),
                qa_records=self.documents.count_jsonl(self.documents.qa_records_path(doc_id)),
                current_step="generate_qa",
            )
            return {
                "doc_id": doc_id,
                "status": final_state["status"],
                "message": "QA generation finished",
                "qa_records": final_state["qa_records"],
                "failed_chunks": final_state["failed_chunks"],
            }

        return self.runner.run(doc_id, "generate_qa", task)

    def start_generate_qa(self, doc_id: str) -> dict[str, Any]:
        self.generate_qa(doc_id)
        return {"doc_id": doc_id, "status": "processing", "message": "QA generation started"}

    def import_chroma(self, doc_id: str) -> dict[str, Any]:
        def task() -> dict[str, Any]:
            self.documents.update_state(doc_id, status="embedding_processing", current_step="import_chroma", error="")
            qa_rows = self.documents.read_jsonl(self.documents.qa_records_path(doc_id))
            records = [QARecord.from_dict(row, id_pad_width=settings.id_pad_width) for row in qa_rows]
            store = self.store or ChromaStore(persist_path=str(self.documents.chroma_dir))
            store.add_or_upsert_qas(records)
            self.documents.update_state(
                doc_id,
                status="imported",
                imported_to_chroma=True,
                qa_records=len(records),
                current_step="import_chroma",
                error="",
            )
            return {"doc_id": doc_id, "imported": len(records), "status": "imported"}

        return self.runner.run(doc_id, "import_chroma", task)

    def retry_failed(self, doc_id: str) -> dict[str, Any]:
        failed_rows = self.documents.read_jsonl(self.documents.failed_chunks_path(doc_id))
        chunks = [Chunk.from_dict(row) for row in failed_rows]
        self.documents.write_jsonl(self.documents.failed_chunks_path(doc_id), [])
        result = self.generate_qa(doc_id, chunks=chunks)
        return {
            "doc_id": doc_id,
            "status": result["status"],
            "retried": len(chunks),
            "failed_chunks": result["failed_chunks"],
        }

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

    @staticmethod
    def _qa_record_from_payload(payload: dict[str, str], chunk: Chunk, qa_index: int, state: dict[str, Any]) -> QARecord:
        return QARecord(
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_index,
            qa_index=qa_index,
            question=payload["question"],
            answer=payload["answer"],
            context=payload["context"],
            keywords=payload["keywords"],
            source=state["filename"],
            file_type=state["file_type"],
            page=chunk.page,
            section=chunk.section,
            file_hash=state["file_hash"],
            chunk_hash=chunk.chunk_hash,
            id_pad_width=settings.id_pad_width,
        )

