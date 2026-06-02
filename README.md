# 大文档 QA 向量化处理平台

这是一个 QA-only 的 RAG 数据加工与 Web 管理系统。系统支持 PDF、DOCX、TXT、Markdown，按步骤完成上传、解析、清洗、分块、QA 生成、JSONL 落盘、批量 embedding、写入 Chroma 和搜索测试。

核心约束：
- Chroma 中每条数据都是一个 QA。
- 不存原始 chunk 向量。
- Chroma `document` 字段只保存 `question`。
- embedding 输入固定拼接 `question + context + keywords`。
- `metadata.context` 是详细语义增强描述，不叫 summary。
- metadata 只使用 string、number、boolean 等简单类型，`keywords` 是逗号分隔字符串。

## 数据流

```text
upload raw file
  -> parse file
  -> clean text
  -> chunk text
  -> data/chunks/{doc_id}_chunks.jsonl
  -> read chunks.jsonl
  -> skip processed chunks
  -> generate context + keywords + QA
  -> validate AI JSON
  -> append data/processed/{doc_id}_qa_records.jsonl
  -> write data/failed/{doc_id}_failed_chunks.jsonl on failure
  -> update data/states/{doc_id}_process_state.json
  -> batch embedding
  -> batch upsert Chroma
```

默认配置使用真实 OpenAI-compatible 服务生成 QA 和 embedding；测试环境仍可通过 mock provider 离线验证基础流程。

## 目录结构

后端现在位于：

```text
backend/
  app/
  .venv/
  requirements.txt
```

运行后会在后端工作目录下生成：

```text
backend/data/
  raw/
  chunks/
  processed/
  states/
  failed/
  logs/
  chroma/
```

前端位于：

```text
frontend/
```

## Chroma 单条数据结构

```python
collection.add(
    ids=["doc001_chunk3_qa1"],
    documents=["什么是向量数据库？"],
    embeddings=[[0.123, 0.456]],
    metadatas=[{
        "answer": "...",
        "context": "...",
        "keywords": "向量数据库,RAG,Embedding",
        "source": "xxx.pdf",
        "file_type": "pdf",
        "page": 12,
        "section": "第三章",
        "chunk_id": "doc001_chunk3",
        "doc_id": "doc001",
        "chunk_index": 3,
        "qa_index": 1,
        "file_hash": "...",
        "chunk_hash": "..."
    }],
)
```

embedding 输入固定为：

```text
问题：
{question}

详细上下文：
{context}

关键词：
{keywords}
```

落盘的 QA JSONL 单条记录只保留：

```json
{
  "id": "doc001_chunk3_qa1",
  "document": "什么是向量数据库？",
  "embedding_text": "问题：\n...\n\n详细上下文：\n...\n\n关键词：\n...",
  "metadata": {
    "answer": "...",
    "context": "...",
    "keywords": "向量数据库,RAG,Embedding",
    "source": "xxx.pdf",
    "file_type": "pdf",
    "page": 12,
    "section": "第三章",
    "chunk_id": "doc001_chunk3",
    "doc_id": "doc001",
    "chunk_index": 3,
    "qa_index": 1,
    "file_hash": "...",
    "chunk_hash": "..."
  }
}
```

## 后端安装与启动

先复制配置文件：

```powershell
cd C:\Users\w\Desktop\my_etl\backend
copy .env.example .env
```

后端的大模型配置、embedding 配置、Chroma 配置都放在 `backend\.env` 中。真实 provider 需要填写对应 API key。

```powershell
cd C:\Users\w\Desktop\my_etl\backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload
```

默认地址：

```text
http://127.0.0.1:8000
```

如果想把 `data/` 放到其他目录，可以在启动前设置：

```powershell
$env:DATA_DIR="D:\my_rag_data"
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --reload
```

## 前端启动

```powershell
cd C:\Users\w\Desktop\my_etl\frontend
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:5173
```

Vite 已配置 `/api` 代理到 `http://127.0.0.1:8000`。

## 主要 API

```text
POST /api/files/upload
GET  /api/files
DELETE /api/files/{doc_id}
POST /api/files/{doc_id}/chunk
GET  /api/files/{doc_id}/chunks?page=1&page_size=20
POST /api/files/{doc_id}/generate-qa
GET  /api/files/{doc_id}/qa-records?page=1&page_size=20&q=
POST /api/files/{doc_id}/import-chroma
POST /api/files/{doc_id}/compact-qa-records
GET  /api/files/-/chroma-info
GET  /api/files/{doc_id}/state
GET  /api/files/{doc_id}/failed-chunks
POST /api/files/{doc_id}/retry-failed
GET  /api/files/{doc_id}/logs
POST /api/batch/process
POST /api/search
```

## 配置项

配置文件位置：`backend\.env`

```dotenv
DATA_DIR=./data
CHROMA_MODE=persistent
CHROMA_PATH=./data/chroma
CHROMA_COLLECTION=qa_records
CHROMA_HOST=127.0.0.1
CHROMA_PORT=8001
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
MOCK_EMBEDDING_DIM=384
ID_PAD_WIDTH=0
LLM_PROVIDER=autodl
LLM_MODEL=qwen3.6-plus
LLM_API_KEY=
LLM_BASE_URL=https://www.autodl.art/api/v1
LLM_MAX_RPM=100
API_TIMEOUT_SECONDS=120
API_MAX_RETRIES=3
API_RETRY_BASE_SECONDS=1.0
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

真实模型调用会对超时、429 和 5xx 错误自动重试；QA 生成会过滤同文档重复问题，失败 chunk 会记录错误类型、错误信息和失败时间，后续“重试失败”只重新处理 failed JSONL 中的 chunk。

## 测试

```powershell
cd C:\Users\w\Desktop\my_etl
python -m pytest
python -m compileall backend\app tests
```

前端依赖安装后：

```powershell
cd C:\Users\w\Desktop\my_etl\frontend
npm run build
```

## 模型接入

Embedding 入口在 `backend/app/embeddings/embedding_service.py`，只需要保证 `embed(text) -> list[float]`，且输入仍然使用完整的 `问题/详细上下文/关键词` 拼接文本。

LLM 入口在 `backend/app/generators/context_generator.py` 和 `backend/app/generators/qa_generator.py`。当前通过 OpenAI-compatible 调用真实 provider，返回必须通过 QA JSON 校验：`question`、`answer`、`context`、`keywords` 都必须是非空字符串。
