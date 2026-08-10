# Backend

FastAPI backend for AI Support Agent RAG.

## Stack

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic Settings
- PostgreSQL + pgvector
- Redis/RQ
- Local or S3-compatible private file storage

## Project Structure

```
backend/
├── __main__.py           # Entry point for running the app as a module
├── requirements.txt      # Python dependencies
├── alembic/             # Database migrations
├── app/
│   ├── main.py          # FastAPI app factory
│   ├── core/            # Core configuration and utilities
│   │   └── config.py    # Settings (environment variables)
│   ├── api/             # API routers
│   │   ├── router.py    # Main API router
│   │   └── v1/          # API v1 endpoints
│   │       ├── router.py
│   │       └── routes/
│   │           └── health.py  # Health check endpoint
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic schemas for request/response validation
│   ├── services/        # Business logic services
│   └── db/              # Database utilities
│       ├── base.py      # Base model
│       └── session.py   # Database session management
```

## Local Setup

1. From `backend/`, create a virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
```

3. Create the backend environment file from the tracked root template:
```powershell
Copy-Item ..\.env.example .env
# Then set OPENAI_API_KEY in backend/.env.
```

4. Run the backend from the repository root with one of these methods:

**Option A:  Using the module entry point**
```powershell
python backend/__main__.py
```

**Option B: Using uvicorn from backend directory**
```powershell
cd backend
python -m uvicorn app.main:app --reload
```

**Option C: Using Docker Compose**
```powershell
docker compose up -d
```

The server will start on `http://localhost:8000`

## Health Check

```http
GET /health
```

Expected response:

```json
{
  "status": "ok",
  "service": "AI Support Agent RAG",
  "environment": "local"
}
```

## Migrations

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Start the local pgvector database from the repository root before migrating:

```powershell
docker compose up -d db
```

The first migration creates the multi-tenant application tables, enables PostgreSQL `vector`, and creates an HNSW cosine-similarity index for document chunk embeddings.

## API and Configuration

Required local backend settings:

```env
FRONTEND_ORIGIN=http://localhost:3000
JWT_SECRET_KEY=change-me-in-development
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
STORAGE_BACKEND=local
UPLOAD_DIR=storage/uploads
S3_ENDPOINT_URL=
S3_REGION=us-east-1
S3_BUCKET=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
S3_PREFIX=uploads
MAX_UPLOAD_SIZE_MB=10
AUTO_INGEST_ON_UPLOAD=false
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
OPENAI_API_KEY=
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
INDEX_BATCH_SIZE=50
CHAT_PROVIDER=openai
CHAT_MODEL=gpt-4o-mini
CHAT_TEMPERATURE=0.2
RAG_TOP_K=5
RAG_MAX_CONTEXT_CHARS=12000
```

Available endpoints:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/organizations`
- `GET /api/v1/organizations`
- `GET /api/v1/organizations/{organization_id}`
- `POST /api/v1/organizations/{organization_id}/knowledge-bases`
- `GET /api/v1/organizations/{organization_id}/knowledge-bases`
- `GET /api/v1/organizations/{organization_id}/knowledge-bases/{knowledge_base_id}`
- `POST /api/v1/organizations/{organization_id}/knowledge-bases/{knowledge_base_id}/documents/upload`
- `GET /api/v1/organizations/{organization_id}/documents`
- `GET /api/v1/organizations/{organization_id}/documents/{document_id}`
- `GET /api/v1/organizations/{organization_id}/documents/{document_id}/file`
- `POST /api/v1/organizations/{organization_id}/documents/{document_id}/prepare`
- `POST /api/v1/organizations/{organization_id}/documents/{document_id}/ingest`
- `POST /api/v1/organizations/{organization_id}/documents/{document_id}/index`
- `POST /api/v1/organizations/{organization_id}/knowledge-bases/{knowledge_base_id}/search`
- `POST /api/v1/organizations/{organization_id}/conversations`
- `GET /api/v1/organizations/{organization_id}/conversations`
- `GET /api/v1/organizations/{organization_id}/conversations/{conversation_id}`
- `POST /api/v1/organizations/{organization_id}/conversations/{conversation_id}/messages`

Register:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d '{"email":"user@example.com","password":"strongpassword","full_name":"User Name"}'
```

Login:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/auth/login `
  -H "Content-Type: application/json" `
  -d '{"email":"user@example.com","password":"strongpassword"}'
```

Use the returned access token in protected requests:

```powershell
curl.exe http://127.0.0.1:8000/api/v1/auth/me `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Create a knowledge base:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/knowledge-bases `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"name":"Product Docs","description":"Product support documents"}'
```

Upload a document:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/knowledge-bases/KNOWLEDGE_BASE_ID/documents/upload `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -F "title=Getting Started" `
  -F "file=@C:\path\to\getting-started.txt;type=text/plain"
```

Uploads create a `pending` document. The prepare job changes it to `processing`,
then `processed`, `indexed`, or `failed`. With `STORAGE_BACKEND=local`, files
live under `storage/uploads/{organization_id}/{knowledge_base_id}/`. With
`STORAGE_BACKEND=s3`, that tenant-qualified layout is an object key in the
configured private bucket.

Manually schedule ingestion:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/documents/DOCUMENT_ID/ingest" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Reprocess a completed document and replace its chunks:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/documents/DOCUMENT_ID/ingest?force=true" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Apply the status-constraint migration before testing ingestion:

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Set a valid `OPENAI_API_KEY` in `backend/.env`, then index a processed document:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/documents/DOCUMENT_ID/index" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Search the indexed knowledge base:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/knowledge-bases/KNOWLEDGE_BASE_ID/search" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"query":"What is the refund policy?","top_k":5}'
```

Create a conversation:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/conversations" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"title":"Refund policy question","knowledge_base_id":"KNOWLEDGE_BASE_ID"}'
```

Send a grounded RAG question:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/organizations/ORGANIZATION_ID/conversations/CONVERSATION_ID/messages" `
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" `
  -H "Content-Type: application/json" `
  -d '{"question":"What is the refund policy?","knowledge_base_id":"KNOWLEDGE_BASE_ID","top_k":5}'
```

The response contains the stored user and assistant message IDs, the grounded answer, and application-generated citation metadata:

```json
{
  "conversation_id": "...",
  "user_message_id": "...",
  "assistant_message_id": "...",
  "answer": "Customers can request a refund within 14 days of purchase.",
  "citations": [
    {
      "document_id": "...",
      "document_title": "sample-faq",
      "chunk_id": "...",
      "quote": "Customers can request a refund within 14 days of purchase.",
      "score": 0.89,
      "chunk_metadata": {}
    }
  ]
}
```

## Background jobs

Document preparation runs on an RQ queue backed by Redis, not in the API
process. Start all three pieces:

```bash
docker compose up -d          # Postgres and Redis
uvicorn app.main:app --reload --port 8000
python worker.py              # in a second terminal
```

Without a worker running, prepare requests are accepted and queued but nothing
processes them; documents stay at "Uploaded". `GET /health` reports
`queue: unavailable` when Redis cannot be reached.

### Recovering abandoned work

A worker killed mid-job leaves its document in `processing` with no job left to
finish it. Retries do not help — nothing failed, the work simply stopped
existing. Run the sweep periodically to recover those:

```bash
python sweep.py
```

It requeues documents that have been processing longer than
`PREPARATION_STALE_AFTER_SECONDS` (default 900), or fails them once they have
used their attempt budget. In production this belongs in a scheduled task.

### Retry policy

| Setting | Default | Meaning |
| --- | --- | --- |
| `PREPARATION_MAX_ATTEMPTS` | `3` | Total attempts before a document is failed |
| `PREPARATION_RETRY_DELAYS` | `10,60,180` | Backoff in seconds between attempts |
| `PREPARATION_STALE_AFTER_SECONDS` | `900` | How long before a claim is treated as abandoned |
| `PREPARATION_JOB_TIMEOUT_SECONDS` | `600` | Hard ceiling on a single job |

Not every failure is retried. Bad input — a corrupt file, an unsupported type,
a document that yields no text — fails the same way every time, so it is
recorded immediately rather than retried at the cost of time and embedding
credit. Provider timeouts and 5xx responses are retried with backoff. See
ADR-035.

### A note on Windows

RQ's default worker forks a child process per job and enforces timeouts with
`SIGALRM`; Windows has neither. `worker.py` detects this and runs `SimpleWorker`
with a thread-based timeout instead. Jobs then run inside the worker process, so
a job that hard-crashes the interpreter takes the worker with it. Deployment
targets Linux, where the forking worker is used.

## Deployment

The root `render.yaml` deploys this backend with its RQ worker in one free
Render web service and stores files in private Supabase Storage. See
[`docs/11-supabase-render-deployment.md`](../docs/11-supabase-render-deployment.md)
for the database URLs, S3 settings, migration flow, and verification steps.
