"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_dotenv()


@dataclass(frozen=True)
class Config:
    data_dir: str = os.getenv("DATA_DIR", "./data")
    chroma_path: str = os.getenv("CHROMA_PATH", os.path.join(os.getenv("DATA_DIR", "./data"), "chroma"))
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "qa_records")
    chroma_mode: str = os.getenv("CHROMA_MODE", "persistent")
    chroma_host: str = os.getenv("CHROMA_HOST", "127.0.0.1")
    chroma_port: int = int(os.getenv("CHROMA_PORT", "8001"))
    processing_path: str = os.getenv("PROCESSING_PATH", "./processing_state")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    embedding_dim: int = int(os.getenv("MOCK_EMBEDDING_DIM", "384"))
    id_pad_width: int = int(os.getenv("ID_PAD_WIDTH", "0"))
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_model: str = os.getenv("LLM_MODEL", "mock")
    llm_max_rpm: int = int(os.getenv("LLM_MAX_RPM", "60"))
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "mock")
    embedding_api_key: str = os.getenv("EMBEDDING_API_KEY", "")
    embedding_base_url: str = os.getenv("EMBEDDING_BASE_URL", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "mock")

    @property
    def raw_dir(self) -> Path:
        return Path(self.data_dir) / "raw"

    @property
    def chunks_dir(self) -> Path:
        return Path(self.data_dir) / "chunks"

    @property
    def processed_dir(self) -> Path:
        return Path(self.data_dir) / "processed"

    @property
    def states_dir(self) -> Path:
        return Path(self.data_dir) / "states"

    @property
    def failed_dir(self) -> Path:
        return Path(self.data_dir) / "failed"

    @property
    def logs_dir(self) -> Path:
        return Path(self.data_dir) / "logs"


settings = Config()
