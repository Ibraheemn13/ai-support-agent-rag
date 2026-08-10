# Architecture

## Overview

SupportMind is a multi-tenant retrieval-augmented support application. A
Next.js frontend calls a FastAPI API; PostgreSQL stores relational data,
full-text indexes, pgvector embeddings, and usage records; an RQ worker prepares
documents; private object storage holds originals.

The browser never talks directly to the database or object store. FastAPI is
the public data boundary for authentication, authorization, tenant scoping,
uploads, retrieval, and chat.

## High-Level Components

| Component | Technology | Responsibility |
| --- | --- | --- |
| Frontend | Next.js App Router | Onboarding, workspaces, knowledge, documents, conversations, cited answers |
| Backend API | FastAPI | JWT auth, HTTP contracts, membership and role checks, orchestration |
| Data access | SQLAlchemy 2.0 + Alembic | Repository queries, tenant transactions, reviewable migrations |
| Database | PostgreSQL + pgvector | Durable records, full-text search, vectors, RLS, usage metering |
| File storage | Local adapter or private S3-compatible storage | Original uploaded documents |
| Queue | Redis-compatible Render Key Value + RQ | Durable preparation jobs, retries, rate-limit counters |
| Worker | RQ worker | Extraction, chunking, embeddings, status transitions |
| AI providers | OpenAI behind provider protocols | Query/document embeddings and grounded answer generation |
| Observability | Structured logs and optional error reporting | Request/job correlation, redaction, failures, timing |

LangGraph and Celery are deliberately absent. The current workflow has one
linear preparation job and one grounded-answer path; RQ plus explicit Python
services exposes the behavior without adding orchestration machinery the
product does not yet need.

## Tenant Isolation

Every tenant-owned table carries `organization_id` directly. FastAPI resolves
the current user, checks organization membership and role, and scopes every
repository call. PostgreSQL RLS provides a second line of defense by reading
`app.current_organization_id`, which SQLAlchemy sets at the start of every
transaction.

Runtime traffic uses a non-owning, non-superuser database role so RLS actually
applies. Migrations use the owner role. On Supabase, Data API table privileges
are revoked because this application does not use PostgREST as a parallel data
path.

## Document Preparation Flow

1. An owner or admin uploads a supported document.
2. FastAPI validates its tenant, MIME type, extension, and size.
3. The configured storage provider saves the private original and a `pending`
   document row records its locator.
4. **Prepare for chat** changes the row to `processing` and enqueues one RQ job.
5. The worker claims the document conditionally so concurrent workers cannot
   both prepare it.
6. Storage materializes the object locally for PDF, DOCX, or text extraction.
7. The worker writes tenant-scoped chunks and marks the document `processed`.
8. It embeds chunks without vectors, writes them in batches, and marks the
   document `indexed`.
9. Retryable provider failures use bounded backoff. Permanent input errors mark
   the document `failed` with a concise reason.

Extraction replaces prior chunks and indexing skips vectors already present,
so at-least-once delivery converges without duplicating chunks or paying twice
for completed embeddings.

## Chat Answer Flow

1. A member sends a question inside one organization and knowledge space.
2. The API stores the user message and checks the daily token budget.
3. The embedding provider embeds the question.
4. PostgreSQL performs tenant-scoped vector and full-text retrieval.
5. Reciprocal rank fusion combines those rankings.
6. The chat provider receives only the selected context and an instruction to
   answer from it.
7. The API stores the assistant message, separate citation rows, and provider
   token usage.
8. The frontend renders the answer and its inspectable original sources.

## Logical Boundaries

### API Layer

- Owns request and response contracts.
- Resolves authenticated users and organization context.
- Enforces role checks before calling services.
- Maps domain failures to stable HTTP responses.

### Service and Repository Layers

- Services own business rules and transaction boundaries.
- Repositories own SQLAlchemy queries and explicit tenant filters.
- Provider protocols isolate storage, embeddings, and chat SDKs.

### Worker Layer

- Owns slow, retryable preparation work.
- Opens its own database sessions and organization scope.
- Uses conditional claims, timeouts, retries, and stale-work recovery.

### Data Layer

- PostgreSQL is the durable source of truth.
- pgvector and full-text search stay transactionally aligned with chunks.
- Object storage owns original bytes, never authorization.
- Redis is transient coordination, not durable product state.

## Deployment Shape

Local development uses Docker Compose for PostgreSQL/pgvector and Redis, local
file storage, a FastAPI process, an RQ worker, and the Next.js development
server.

The free public demo uses Supabase for PostgreSQL and private S3-compatible
Storage, Render Key Value for Redis/RQ, one Render web service containing the
API and worker, and a second Render web service for Next.js. The combined
backend process exists only because free Render background workers are not
available.

A production deployment should split API and worker services, use a persistent
queue, run Alembic as a release step, schedule stale-work recovery, enable
backups and monitoring, and use separate staging and production projects.

## Deliberately Deferred

- Secure cookie sessions, refresh-token rotation, email verification, and
  password reset
- Streaming answers
- OCR for scanned PDFs
- Queue priorities and per-tenant worker fairness
- Re-ranking and answer-quality evaluation
- Agent tool use or LangGraph, when a product workflow genuinely requires it
