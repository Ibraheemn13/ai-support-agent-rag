# Document Ingestion Pipeline

## Why Upload and Ingestion Are Separate

Upload durably stores a file and its metadata. Ingestion reads that file,
extracts text, splits it into retrieval-ready chunks, and records the result.
Keeping these steps separate makes uploads responsive and lets failed
extraction be retried without asking a user to upload again.

The low-level operational endpoint remains available to owners and admins:

```http
POST /api/v1/organizations/{organization_id}/documents/{document_id}/ingest
```

Completed documents require `force=true` to replace existing chunks. The
normal product flow uses `/prepare`, which chains ingestion and indexing in one
durable RQ job.

## Document Lifecycle

- `pending`: file and metadata are stored but preparation has not started.
- `processing`: extraction and/or embedding work is running.
- `processed`: text chunks exist, but embeddings have not been generated.
- `indexed`: embeddings exist and the document is ready for retrieval.
- `failed`: work failed; `error_message` contains a concise cause.

## Pipeline Steps

The pipeline opens its own database session, reloads the tenant-scoped
document, marks it as processing, and asks the configured storage provider to
materialize the object as a temporary local file. This gives `pypdf`,
`python-docx`, and the text loaders the ordinary file path they expect without
coupling them to local disk or an S3 SDK.

It extracts text, replaces stale chunks on a forced run, inserts
`document_chunks`, and marks the document processed. Any extraction or
persistence error rolls back chunk changes and records a failed status. The
temporary file is removed after extraction.

Each chunk stores:

- Tenant and document IDs
- A zero-based chunk index
- Text content
- An approximate token count based on character length
- JSON metadata with source, character offsets, heading context, and PDF page
  number where available
- A null embedding until indexing completes

## Supported Files

- UTF-8 plain text
- UTF-8 Markdown
- PDFs containing embedded text
- DOCX paragraphs

PDF extraction uses `pypdf` page by page. It does not perform OCR. A scanned or
image-only PDF is marked failed with a message explaining that OCR is not
supported yet.

## Chunking Strategy

The custom splitter uses document structure where available and falls back to
the configured character window. The default chunk size is 1,200 characters
with 200 characters of overlap. Character offsets describe each chunk within
its source section.

Overlap preserves context around boundaries, which helps retrieval when a
useful answer spans the end of one chunk and the start of the next. The
strategy stays small and inspectable instead of hiding the behavior behind a
framework splitter.

## Queue and Recovery

The user-facing preparation flow runs on RQ with Redis. The API enqueues a job
and returns `202`; a worker performs extraction and indexing with retry and
timeout policies. Unlike the original FastAPI `BackgroundTasks` implementation,
queued work survives an API process restart.

An RQ job can still be interrupted after claiming a document. `python sweep.py`
finds documents left in `processing` beyond
`PREPARATION_STALE_AFTER_SECONDS` and requeues or fails them according to the
attempt budget. Production should run this as a scheduled task.

On Render's free plan, the API and one worker share a web service because free
background-worker services are unavailable. This is suitable for a portfolio
demo, not a scaling model; paid deployment should split them into separate
services.

## Configuration

```env
AUTO_INGEST_ON_UPLOAD=false
CHUNK_SIZE=1200
CHUNK_OVERLAP=200
REDIS_URL=redis://localhost:6379/0
PREPARATION_MAX_ATTEMPTS=3
PREPARATION_RETRY_DELAYS=10,60,180
PREPARATION_STALE_AFTER_SECONDS=900
PREPARATION_JOB_TIMEOUT_SECONDS=600
```

`CHUNK_OVERLAP` must be smaller than `CHUNK_SIZE`. Automatic ingestion remains
off because `/prepare` owns the full extract-then-index lifecycle.

## Manual Verification

After preparing a document, inspect the row and its chunks:

```sql
SELECT id, title, status, error_message
FROM documents
ORDER BY created_at DESC;

SELECT document_id, chunk_index, token_count, chunk_metadata,
       embedding IS NOT NULL AS indexed, content
FROM document_chunks
WHERE document_id = '<document-uuid>'
ORDER BY chunk_index;
```

The row should move through `processing` to `indexed`. If only the ingestion
endpoint was called, it stops at `processed` and embeddings remain null.

## Future Upgrade Path

- A separate RQ worker service with independent scaling
- Scheduled stale-work recovery
- Queue priorities and per-tenant fairness
- Celery only if richer workflow primitives become necessary
- OCR for scanned PDFs
- Structured extraction for tables and complex layouts
