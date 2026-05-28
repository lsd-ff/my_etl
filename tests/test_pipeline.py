from __future__ import annotations

import json
from pathlib import Path

from app.chunkers.recursive_chunker import RecursiveChunker
from app.cleaners.text_cleaner import TextCleaner
from app.embeddings.embedding_service import EmbeddingService
from app.loaders.markdown_loader import MarkdownLoader
from app.loaders.txt_loader import TxtLoader
from app.pipeline.ingestion_pipeline import IngestionPipeline
from app.schemas.qa_record import QARecord


class FakeStore:
    def __init__(self) -> None:
        self.records: dict[str, QARecord] = {}
        self.file_hashes: set[tuple[str, str]] = set()
        self.chunk_hashes: set[tuple[str, str]] = set()
        self.batch_calls = 0

    def add_or_upsert_qa(self, record: QARecord) -> None:
        self.add_or_upsert_qas([record])

    def add_or_upsert_qas(self, records: list[QARecord]) -> None:
        self.batch_calls += 1
        for record in records:
            self.records[record.qa_id] = record
            self.file_hashes.add((record.source, record.file_hash))
            self.chunk_hashes.add((record.source, record.chunk_hash))

    def has_file_hash(self, source: str, file_hash: str) -> bool:
        return (source, file_hash) in self.file_hashes

    def has_chunk_hash(self, source: str, chunk_hash: str) -> bool:
        return (source, chunk_hash) in self.chunk_hashes


def test_txt_and_markdown_loaders_return_page_zero(tmp_path: Path) -> None:
    txt = tmp_path / "sample.txt"
    txt.write_text("hello\nworld", encoding="utf-8")
    md = tmp_path / "sample.md"
    md.write_text("# Heading\nBody", encoding="utf-8")

    txt_segment = TxtLoader().load(txt)[0]
    md_segment = MarkdownLoader().load(md)[0]

    assert txt_segment.page == 0
    assert txt_segment.file_type == "txt"
    assert md_segment.page == 0
    assert md_segment.section == "Heading"


def test_cleaner_removes_duplicate_and_noise_lines() -> None:
    text = "Title\n\n\nPage 1\nRepeated line\nRepeated line\nA\nBody  text"

    cleaned = TextCleaner().clean(text)

    assert "Page 1" not in cleaned
    assert cleaned.count("Repeated line") == 1
    assert "Body text" in cleaned
    assert "\n\n\n" not in cleaned


def test_chunker_generates_stable_chunk_fields() -> None:
    content = "# Heading\n" + "This paragraph exists to test stable chunk splitting. " * 80
    chunker = RecursiveChunker(chunk_size=120, chunk_overlap=20)
    chunks = chunker.chunk_segments(
        "doc001",
        [
            type(
                "Segment",
                (),
                {
                    "text": content,
                    "page": 0,
                    "section": "Heading",
                },
            )()
        ],
    )

    assert chunks
    assert chunks[0].chunk_id == "doc001_chunk1"
    assert chunks[0].chunk_index == 1
    assert len(chunks[0].chunk_hash) == 64


def test_qa_record_uses_question_as_document_and_rich_embedding_text() -> None:
    record = QARecord(
        doc_id="doc001",
        chunk_id="doc001_chunk3",
        chunk_index=3,
        qa_index=1,
        question="What is a vector database?",
        answer="A vector database stores and retrieves high-dimensional vectors.",
        context="Detailed semantic context.",
        keywords="vector database,RAG,Embedding",
        source="demo.pdf",
        file_type="pdf",
        page=12,
        section="Chapter 3",
        file_hash="filehash",
        chunk_hash="chunkhash",
    )

    assert record.qa_id == "doc001_chunk3_qa1"
    assert record.document == "What is a vector database?"
    assert "问题：" in record.embedding_text
    assert "详细上下文：" in record.embedding_text
    assert "关键词：" in record.embedding_text
    assert record.metadata["context"] == "Detailed semantic context."
    assert isinstance(record.metadata["keywords"], str)


def test_pipeline_writes_jsonl_state_then_batches_to_chroma(tmp_path: Path) -> None:
    source = tmp_path / "rag.txt"
    source.write_text(
        "Vector databases store and retrieve high-dimensional vectors. "
        "RAG systems combine parsing, chunking, embeddings, and semantic search. "
        "This content can be converted into QA records for a vector database.",
        encoding="utf-8",
    )
    store = FakeStore()
    processing_path = tmp_path / "state"
    pipeline = IngestionPipeline(
        chunker=RecursiveChunker(chunk_size=160, chunk_overlap=20),
        store=store,  # type: ignore[arg-type]
        processing_path=str(processing_path),
    )

    first = pipeline.ingest(str(source))
    second = pipeline.ingest(str(source))
    doc_dir = processing_path / first.doc_id
    state = json.loads((doc_dir / "process_state.json").read_text(encoding="utf-8"))

    assert first.status == "success"
    assert first.chunks >= 1
    assert first.qa_records >= 1
    assert (doc_dir / "chunks.jsonl").exists()
    assert (doc_dir / "qa_records.jsonl").exists()
    assert state["embedded"] is True
    assert state["chroma_written"] is True
    assert store.batch_calls == 1
    assert second.status == "skipped"
    assert second.qa_records == 0


def test_ai_payload_validation_rejects_non_json_shape() -> None:
    valid = IngestionPipeline._validate_ai_payloads(
        [
            {
                "question": "Q?",
                "answer": "A",
                "context": "C",
                "keywords": "k1,k2",
            },
            {
                "question": "Q?",
                "answer": "A",
                "context": "C",
                "keywords": ["k1", "k2"],
            },
        ]
    )

    assert valid == [{"question": "Q?", "answer": "A", "context": "C", "keywords": "k1,k2"}]


def test_mock_embedding_is_deterministic() -> None:
    service = EmbeddingService(provider="mock")

    first = service.embed("question: what is RAG?")
    second = service.embed("question: what is RAG?")

    assert first == second
    assert len(first) > 0


def test_qa_metadata_contains_chroma_simple_fields() -> None:
    record = QARecord(
        doc_id="doc001",
        chunk_id="doc001_chunk1",
        chunk_index=1,
        qa_index=1,
        question="What is RAG?",
        answer="RAG is retrieval augmented generation.",
        context="RAG passes retrieval results to a generation model.",
        keywords="RAG,retrieval augmented generation,Embedding",
        source="demo.md",
        file_type="markdown",
        page=0,
        section="Overview",
        file_hash="filehash",
        chunk_hash="chunkhash",
    )

    assert set(record.metadata) >= {
        "answer",
        "context",
        "keywords",
        "source",
        "file_type",
        "page",
        "section",
        "chunk_id",
        "doc_id",
        "chunk_index",
        "qa_index",
        "file_hash",
        "chunk_hash",
    }
    assert all(not isinstance(value, list) for value in record.metadata.values())

