from __future__ import annotations

from pathlib import Path

from app.chunkers.recursive_chunker import RecursiveChunker
from app.generators.qa_generator import QAGenerator
from app.schemas.qa_record import Chunk, QARecord
from app.services.batch_service import BatchService
from app.services.document_service import DocumentService
from app.services.pipeline_service import PipelineService


class FakeStore:
    def __init__(self) -> None:
        self.records: list[QARecord] = []

    def add_or_upsert_qas(self, records: list[QARecord]) -> None:
        self.records.extend(records)


class FailingOnceGenerator(QAGenerator):
    def __init__(self) -> None:
        super().__init__()
        self.failed = False

    def generate_json_for_chunk(self, chunk: Chunk):  # type: ignore[override]
        if not self.failed:
            self.failed = True
            raise RuntimeError("planned failure")
        return [
            {
                "question": "What is retry?",
                "answer": "Retry processes failed chunks again.",
                "context": "Retry is used to recover failed chunk processing.",
                "keywords": "retry,chunk,qa",
            }
        ]


def create_document(service: DocumentService) -> str:
    content = (
        "Vector databases store high-dimensional vectors. "
        "RAG pipelines parse documents, split text into chunks, generate QA records, "
        "and import embeddings into Chroma."
    ).encode("utf-8")
    return service.create_or_update_document("demo.txt", content)["doc_id"]


def test_document_service_upload_creates_state_and_files(tmp_path: Path) -> None:
    service = DocumentService(tmp_path / "data")

    state = service.create_or_update_document("demo.txt", b"hello world")

    assert state["status"] == "uploaded"
    assert Path(state["file_path"]).exists()
    assert service.state_path(state["doc_id"]).exists()
    assert service.chunks_path(state["doc_id"]).exists()
    assert service.qa_records_path(state["doc_id"]).exists()


def test_pipeline_service_chunk_generate_import(tmp_path: Path) -> None:
    service = DocumentService(tmp_path / "data")
    doc_id = create_document(service)
    store = FakeStore()
    pipeline = PipelineService(
        document_service=service,
        chunker=RecursiveChunker(chunk_size=120, chunk_overlap=20),
        store=store,
    )

    chunk_result = pipeline.chunk_document(doc_id)
    qa_result = pipeline.generate_qa(doc_id)
    import_result = pipeline.import_chroma(doc_id)
    state = service.load_state(doc_id)

    assert chunk_result["status"] == "chunked"
    assert chunk_result["chunks"] >= 1
    assert qa_result["status"] == "qa_done"
    assert state["qa_records"] >= 1
    assert import_result["status"] == "imported"
    assert len(store.records) == state["qa_records"]
    assert service.paginate_jsonl(service.chunks_path(doc_id), page=1, page_size=20)["total"] >= 1
    assert service.paginate_jsonl(service.qa_records_path(doc_id), page=1, page_size=20)["total"] >= 1


def test_failed_chunks_can_be_retried(tmp_path: Path) -> None:
    service = DocumentService(tmp_path / "data")
    doc_id = create_document(service)
    pipeline = PipelineService(
        document_service=service,
        chunker=RecursiveChunker(chunk_size=120, chunk_overlap=20),
        qa_generator=FailingOnceGenerator(),
        store=FakeStore(),
    )

    pipeline.chunk_document(doc_id)
    first = pipeline.generate_qa(doc_id)
    retry = pipeline.retry_failed(doc_id)

    assert first["status"] == "qa_failed"
    assert first["failed_chunks"] == 1
    assert retry["retried"] == 1
    assert retry["failed_chunks"] == 0
    assert service.load_state(doc_id)["status"] == "qa_done"


def test_batch_service_runs_steps_for_document(tmp_path: Path) -> None:
    service = DocumentService(tmp_path / "data")
    doc_id = create_document(service)
    store = FakeStore()
    pipeline = PipelineService(
        document_service=service,
        chunker=RecursiveChunker(chunk_size=120, chunk_overlap=20),
        store=store,
    )
    batch = BatchService(pipeline)

    result = batch.process([doc_id], ["chunk", "generate_qa", "import_chroma"])

    assert result["status"] == "finished"
    assert result["results"][0]["status"] == "success"
    assert service.load_state(doc_id)["status"] == "imported"

