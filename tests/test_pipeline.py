from __future__ import annotations

from pathlib import Path

from app.chunkers.recursive_chunker import RecursiveChunker
from app.cleaners.text_cleaner import TextCleaner
from app.embeddings.embedding_service import EmbeddingService
from app.loaders.markdown_loader import MarkdownLoader
from app.loaders.txt_loader import TxtLoader
from app.schemas.qa_record import QARecord
from app.services.pipeline_service import PipelineService


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


def test_cleaner_returns_auditable_report() -> None:
    result = TextCleaner().clean_with_report("Title\nPage 1\nRepeated\nRepeated\nBody")

    assert result.report["removed_line_count"] >= 2
    assert result.report["noise_line_count"] >= 1
    assert result.report["duplicate_line_count"] >= 1
    assert result.report["cleaned_chars"] == len(result.text)


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
    assert chunks[0].token_count > 0
    assert 0 <= chunks[0].quality_score <= 1
    assert isinstance(chunks[0].warnings, tuple)


def test_chunker_preserves_heading_path_and_block_type() -> None:
    chunker = RecursiveChunker(chunk_size=200, chunk_overlap=20)
    chunks = chunker.chunk_segments(
        "doc001",
        [
            type(
                "Segment",
                (),
                {
                    "text": "# Heading\nA useful paragraph with enough detail to become a valid chunk.",
                    "page": 0,
                    "section": "Heading",
                    "heading_path": ("Heading",),
                    "block_type": "markdown",
                    "start_offset": 0,
                    "end_offset": 72,
                },
            )()
        ],
    )

    assert chunks[0].heading_path == ("Heading",)
    assert "heading" in chunks[0].block_types or "markdown" in chunks[0].block_types



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


def test_ai_payload_validation_rejects_non_json_shape() -> None:
    valid = PipelineService._validate_ai_payloads(
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
    assert "quality_score" in record.metadata
    assert "validation_warnings" in record.metadata


def test_qa_jsonl_dict_keeps_metadata_fields_deduplicated() -> None:
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

    row = record.to_jsonl_dict()

    assert set(row) == {"id", "document", "embedding_text", "metadata"}
    assert row["metadata"]["answer"] == record.answer
    assert row["metadata"]["doc_id"] == record.doc_id
    assert QARecord.from_dict(row) == record
