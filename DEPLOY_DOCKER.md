# Docker deployment

This project can be deployed with Docker Compose. The server builds images from the GitHub source code, so there is no need to upload locally built images unless you choose to use a container registry.

## Local test

Create `backend/.env` from the example file and set the container data paths:

```dotenv
DATA_DIR=/app/data
CHROMA_MODE=persistent
CHROMA_PATH=/app/data/chroma
```

Then start the stack:

```bash
docker compose up -d --build
```

Open:

```text
http://localhost
http://localhost/api/files
```

Stop the stack:

```bash
docker compose down
```

## Server deploy

Install Docker and the Compose plugin on the ECS server, then clone the repository:

```bash
cd /opt
git clone <your-github-repo-url> my_etl
cd /opt/my_etl
```

Create the production env file:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env`:

```dotenv
DATA_DIR=/app/data
CHROMA_MODE=persistent
CHROMA_PATH=/app/data/chroma
CHROMA_COLLECTION=qa_records

LLM_PROVIDER=autodl
LLM_MODEL=qwen3.6-plus
LLM_API_KEY=your-production-key
LLM_BASE_URL=https://www.autodl.art/api/v1

EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_API_KEY=your-production-key
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

Build and start:

```bash
docker compose up -d --build
```

Verify:

```bash
docker compose ps
docker compose logs -f backend
curl http://127.0.0.1/api/files
```

Open:

```text
http://8.160.173.125
```

## Update deploy

```bash
cd /opt/my_etl
git pull
docker compose up -d --build
```

## Docker Hub access

If pulling base images times out, configure a Docker registry mirror on the server or use an accessible image source before running `docker compose up -d --build`.

The base images used by this project are:

```text
python:3.12-slim
node:20-alpine
nginx:1.27-alpine
```

## Data persistence

Runtime files are stored on the host at:

```text
backend/data
```

That directory is mounted into the backend container as:

```text
/app/data
```

Do not commit `backend/.env` or `backend/data` to Git.
