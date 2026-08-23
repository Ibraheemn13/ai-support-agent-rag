# SupportMind

**Upload your support documents, then ask them questions and get answers with the passages they came from.**

A multi-tenant RAG application: FastAPI and Postgres/pgvector behind a Next.js product surface that never asks the user to understand retrieval, embeddings, or indexing.

[![CI](https://github.com/ZakwanZahid/ai-support-agent-rag/actions/workflows/ci.yml/badge.svg)](https://github.com/ZakwanZahid/ai-support-agent-rag/actions/workflows/ci.yml)
![Backend tests](https://img.shields.io/badge/backend-230%20tests-brightgreen)
![Frontend tests](https://img.shields.io/badge/frontend-52%20tests-brightgreen)
![E2E](https://img.shields.io/badge/e2e-1%20flow%20(manual)-blue)

<!-- Placeholders until Phase 18 deploys. Do not link these until they resolve. -->
🔗 **Live demo** — _not deployed yet_ · 🎥 **Demo video** — _not recorded yet_

<!--
  Screenshot goes here once Phase 18 deploys and seeds the demo workspace, so
  it shows real data. Kept as a comment rather than an <img> tag so the README
  does not render a broken image in the meantime:
  ![SupportMind dashboard](docs/screenshots/dashboard.png)
-->

---

## The problem

Most teams already have the documentation that answers their support questions. It's in a PDF, a wiki page, and one person's head. Finding the answer means knowing which of those to open.

General-purpose AI tools make that worse rather than better: ask one about your refund window and it will confidently describe a policy your company never had. And an answer you can't check is an answer you still have to verify by hand.

There's a third problem, which is the one this project is really about. The obvious way to build a retrieval app leaks its own machinery into the interface — upload a file, click **Ingest**, wait, click **Index**, wait, then chat. Those are two operations because they have different failure modes, which is a good backend design and a terrible product. The user's intent is *"make this document answerable"* — one thing, not two.

## What I built

A support assistant that answers only from documents you gave it, and shows the passage behind every answer.

The engineering interest isn't the RAG pipeline — that part is well-trodden. It's the layer above it: taking a system whose natural vocabulary is *organizations, knowledge bases, ingestion, indexing, citations* and presenting it as *workspaces, knowledge spaces, "Prepare for chat", sources* — without the translation rotting the first time someone adds a component.

## Architecture

```mermaid
flowchart TB
    subgraph client["Browser"]
        UI["Next.js App Router<br/>React · TanStack Query"]
    end

    subgraph api["FastAPI"]
        Routes["Routes<br/>auth · workspaces · documents · chat"]
        Deps["Dependencies<br/>JWT decode · membership · role checks"]
        Services["Services<br/>documents · preparation · RAG"]
    end

    subgraph queue["Worker"]
        RQ{{"RQ queue<br/>(Redis)"}}
        Job["Preparation job<br/>claim → extract → index"]
        Sweep["Stale sweep<br/>recovers abandoned work"]
    end

    subgraph data["Storage"]
        PG[("PostgreSQL<br/>+ pgvector")]
        Objects[["Uploaded files<br/>(local disk / private S3)"]]
    end

    subgraph external["OpenAI"]
        Embed["text-embedding-3-small"]
        Chat["gpt-4o-mini"]
    end

    UI -->|"JSON + Bearer token"| Routes
    Routes --> Deps --> Services
    Services --> PG
    Services --> Objects
    Services -.->|"enqueue"| RQ
    RQ --> Job
    Job -->|"claim, then write chunks"| PG
    Job -->|"embed chunks"| Embed
    Sweep -.->|"requeue abandoned"| RQ
    Sweep --> PG
    Services -->|"answer from retrieved context"| Chat
    UI -.->|"polls document status"| Routes
```

Every tenant-owned row carries an `organization_id`, and membership is checked on every request before a service runs. Embeddings live in the same Postgres instance as the chunk metadata, through pgvector — one datastore, transactional with the rest of the data.

### How "Prepare for chat" works

The single user-facing action, and the piece I'd point a reviewer at first:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Browser
    participant API as FastAPI
    participant Q as RQ queue
    participant W as Worker
    participant DB as Postgres
    participant AI as OpenAI

    User->>UI: Upload a document
    UI->>API: POST /documents/upload
    API->>DB: store file, status = pending
    UI->>API: POST /documents/{id}/prepare
    API->>DB: status = processing
    API->>Q: enqueue job
    API-->>UI: 202 Accepted

    Q->>W: deliver job
    W->>DB: claim (conditional UPDATE)
    Note over W,DB: refuses if another worker holds it
    W->>DB: extract text, write chunks
    Note over W,DB: status = processed
    W->>AI: embed chunks without vectors
    AI-->>W: vectors
    W->>DB: store embeddings, status = indexed

    loop until settled
        UI->>API: GET /documents/{id}
        API-->>UI: Uploaded → Processing → Extracted → Ready
    end
```

Chaining happens server-side, deliberately. Orchestrating it from the browser means the sequence breaks if the tab closes between the two calls. If extraction yields no chunks, the job stops rather than indexing nothing, and the document reports `Failed` with the reason.

The job is safe to run twice, which matters because a queue that delivers at-least-once eventually delivers twice. Extraction replaces a document's chunks rather than appending, and indexing only embeds chunks whose vector is still null — so a repeat run converges on the same state without paying for the same embeddings again. A conditional UPDATE decides ownership, so two workers cannot both proceed. See ADR-034.

Answers are assembled the same way every time: embed the question, retrieve the nearest chunks scoped to one knowledge space, build a context block, and ask the model to answer only from it. The chunks that fed the answer are stored alongside the message, which is what the UI shows as **Sources**.

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | Next.js (App Router), TypeScript, Tailwind, shadcn/ui-style components |
| Data fetching | TanStack Query · Axios · React Hook Form · Zod |
| API | FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic |
| Database | PostgreSQL + pgvector |
| File storage | Local adapter in development, private S3-compatible storage in deployment |
| Models | OpenAI `text-embedding-3-small`, `gpt-4o-mini`, behind provider interfaces |
| Queue | Redis + RQ for durable document preparation |
| Retrieval | pgvector + Postgres full-text, fused by reciprocal rank |
| Observability | JSON logs with request correlation, per-organization token metering |
| Tests | pytest (230) · Vitest (52) · Playwright (1 end-to-end flow) |

## Key engineering decisions

**One module owns the product vocabulary.** [`terminology.ts`](frontend/src/lib/terminology.ts) holds a single descriptor table; components derive labels, badge tones, timeline position, and *whether to keep polling* from it. `StatusBadge` doesn't know what `indexed` means — it asks. Enforced by tests that assert no forbidden API term ever appears in user-facing copy, so the rule fails loudly rather than eroding.

**Two operations, one endpoint.** [`POST /documents/{id}/prepare`](backend/app/api/v1/preparation.py) chains extraction and indexing in one RQ job, with `409` guards for already-running and already-ready. See ADR-025.

**Aggregate counts, not N+1.** Knowledge bases return `document_count`/`ready_document_count`; conversations return `message_count`/`last_message_preview`. Grouped and correlated subqueries, so a list is one round trip regardless of length — instead of the client fetching every child row to count it. See ADR-031.

**Tenant scoping is a dependency, not a convention.** `require_organization_member` and `require_role` run before any service. A missing workspace and a workspace you don't belong to both return `404`, so membership isn't discoverable by probing.

**Spend is metered from what the provider charged.** Token counts come from OpenAI's own `usage` field, never a local tokenizer — an estimate of a bill is a second source of truth that drifts from the real one. A daily per-organization budget complements the per-minute rate limit: one bounds a burst, the other bounds a day. Stored in Postgres rather than Redis, which is the opposite call from the rate limiter and deliberately so — that one counts bursts and may fail open, this one counts money. See ADR-045.

**Retrieval changes are measured, not argued.** An [evaluation harness](backend/eval/) indexes a fixed corpus, asks a fixed question set, and scores which documents came back — questions tagged by kind, so a change that helps direct lookups and hurts paraphrases cannot hide behind an average. It corrected the plan twice: structure-aware chunking broke two literal-token questions, and hybrid retrieval measured alone did nothing at all. Together: recall@k 0.9528 → 0.9811, precision 0.2189 → 0.3283. See ADR-042 and ADR-043.

**Lists are paged with keyset cursors, not offsets.** `OFFSET` costs more the deeper the page, and both paged collections are mutated while someone reads them — delete a row on page one and every later row shifts up, so the reader silently skips one. A cursor names a position in the sort order instead of a count. See ADR-041.

**And tenant isolation doesn't depend on that alone.** Postgres row-level security scopes every tenant table to the requesting organization, so a query that forgets its filter returns nothing rather than someone else's rows. The application connects as a role that owns nothing — a superuser or table owner bypasses policies outright, which makes the feature silently decorative (ADR-038).

**Provider interfaces over SDK calls.** Embedding, chat, and file storage sit behind small protocols resolved by factories, so swapping a provider is an adapter rather than a search-and-replace.

## Known limitations

Stated rather than hidden. The full list with severities is in [docs/10-frontend-redesign.md](docs/10-frontend-redesign.md).

**Free demo deployment**
- Render free web services sleep when idle, so the first request can take roughly a minute
- The API and one worker share a single free web service; they cannot scale independently
- Free Render Key Value is memory-only, so a restart can lose queued jobs and rate-limit counters

**Security**
- Tokens in `localStorage` — an XSS bug becomes a session compromise. Kept knowingly; the reasoning and what mitigates it are in ADR-039
- Sessions expire hard at 60 minutes with no refresh, which bounds a stolen token's life at the cost of being logged out mid-task (ADR-039)

**Reliability**
- One queue with no priorities, so a bulk upload delays everyone else
- The stale sweep is uncoordinated; two running at once would both try to recover the same documents

**Scale and product**
- Document search is `ILIKE '%term%'`, which cannot use an index — real search needs full-text or trigram (ADR-041)
- The filter counts are a `GROUP BY` over every matching document on each request
- Deletion is immediate and total; there is no trash or undo (ADR-040)
- The eval corpus is 16 documents and 57 questions, written by the same person who wrote the corpus — enough to catch a regression, not enough to separate 0.97 from 0.98 (ADR-042)
- `ts_rank` cannot use the GIN index for ordering, so ranking is a scan over the matched rows
- RRF's constant and the vector/keyword weighting are untuned; with 57 questions, tuning them would fit the noise
- No re-ranking, and nothing evaluates the generated answer — only which sources were retrieved
- Answers don't stream

**Engineering**
- Every request logs at INFO, which is the largest thing the system produces at real traffic; sampling needs traffic figures that don't exist yet (ADR-044)
- Usage is stored at daily grain, so it can show a workspace spent a lot but not that it spent it in four minutes
- The cost cap is per workspace, so one member can exhaust it for everyone
- No metrics or tracing; request duration is in the logs and nothing aggregates it
- The end-to-end test runs on demand rather than on every push, so a regression only it would catch can reach `main`
- Unit coverage is 7% overall by design — see the testing note below

## Testing

The strategy is deliberate rather than uniform: unit-test the modules whose correctness everything else depends on, and cover the actual product flow end to end.

| Suite | Count | What it covers |
| --- | --- | --- |
| pytest | 230 | Auth, tenancy, local/S3 storage, upload, ingestion, indexing, search, RAG chat, preparation, aggregates, workspace settings, queue claims and sweep, rate limiting, row-level security, deletion, pagination, chunking, rank fusion, eval scoring, logging redaction, usage metering, cost caps |
| Vitest | 52 | `terminology.ts` (100%), `api/client.ts` (91%), `StatusBadge` (100%), `ConfirmDeleteDialog` |
| Playwright | 1 flow | Signup → onboarding → upload → prepare → ask → sourced answer |

Overall unit coverage is ~7% because components and hooks are not unit-tested. Inflating that number by testing presentational markup would cost real time and prove little; the flow those components participate in is covered by the end-to-end spec instead. The end-to-end test also asserts the negative case that matters most — that no API vocabulary or UUID ever reaches the screen.

```bash
cd backend && pytest              # 221 tests; 9 more with Postgres, below
cd frontend && npm test           # 52 unit tests
cd frontend && npm run test:e2e   # end-to-end (needs backend + OpenAI key)
```

The row-level security tests are the one exception to the no-database rule, because SQLite has no policies to evaluate — they would report tenant isolation as working without ever testing it. They skip unless pointed at a real Postgres:

```bash
RLS_TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/rls_test pytest
```

**Retrieval evaluation.** Separate from the test suite, because it needs a real database and makes paid API calls:

```bash
cd backend && python -m eval.run --label mine --compare eval/results/baseline.json
```

It indexes [a fixed corpus](backend/eval/corpus/) of 16 support documents, asks [57 fixed questions](backend/eval/questions.json), and reports recall@k, MRR, precision@k, and recall broken down by question kind. Stored runs live in `backend/eval/results/`, so any retrieval change can be compared against the baseline rather than argued about. Embeddings are cached by content hash — the first run costs a few cents, later ones nothing.

**In CI:** [`ci.yml`](.github/workflows/ci.yml) runs backend tests plus frontend lint, typecheck, unit tests, and build on every push and pull request — no secrets and no paid API calls. It does run a Postgres service, solely so the row-level security tests execute; `REQUIRE_RLS_TESTS` makes a skip there a failure, since a skipped security test and a passing one look identical in a job summary.

[`e2e.yml`](.github/workflows/e2e.yml) is manual (`workflow_dispatch`) because each run makes real embedding and chat calls. Running it on every push would turn a few cents into a standing bill and a bottleneck, and the usual result is that someone switches it off. Keeping it deliberate keeps it trustworthy. It needs an `OPENAI_API_KEY` repository secret.

## What I'd build next

In priority order: split the API and worker onto paid services with a persistent queue; move sessions to secure cookies with refresh-token rotation; add metrics and tracing; then evaluate answer quality and streaming rather than adding retrieval complexity by instinct.

Agent orchestration (tool-calling, LangGraph) was scoped out deliberately — the retrieval and evaluation work demonstrates the same system-design thinking with less surface area to maintain.

---

## Local setup

Requires Docker, Python 3.12+, Node 22.13+, and an OpenAI API key.

**1. Infrastructure**

Postgres (with pgvector) and Redis:

```bash
cd backend
docker compose up -d
```

Postgres listens on **5433**, not the default 5432, so it does not collide with
a local install. `DATABASE_URL` must match.

**2. Backend**

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env                           # then set OPENAI_API_KEY
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API docs at http://127.0.0.1:8000/docs.

Two database URLs, and they are not interchangeable. `MIGRATION_DATABASE_URL` is the owner, which `alembic` needs in order to create tables and to create the application role. `DATABASE_URL` is that application role, which owns nothing — Postgres exempts superusers and table owners from row-level security, so an app connecting as `postgres` would pass through every tenant policy. `.env.example` has both filled in for the local compose stack; the role itself is created by the migration. If the app starts up logging a warning about bypassing row-level security, `DATABASE_URL` is still pointing at the owner.

**3. Frontend**

```bash
cd frontend
npm install
cp .env.example .env.local                        # NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
npm run dev
```

Open http://localhost:3000.

Detailed configuration is in [backend/README.md](backend/README.md) and [frontend/README.md](frontend/README.md).

## Deployment

**Ubuntu VPS (recommended for the Contabo deployment).** The production Compose
stack runs Caddy, Next.js, FastAPI, a separate RQ worker, PostgreSQL/pgvector,
Redis, persistent uploads, automatic migrations, and backups on one server.
Follow the [Contabo Ubuntu VPS deployment guide](docs/12-contabo-vps-deployment.md)
from DNS setup through HTTPS and ongoing updates.

**Render demo.** The repository also includes a Render Blueprint for a free
portfolio deployment:

- Supabase Postgres and pgvector
- Private Supabase Storage through its S3-compatible endpoint
- Render Key Value for Redis/RQ
- A combined FastAPI + RQ worker service
- A Next.js web service

Follow [the Supabase and Render deployment guide](docs/11-supabase-render-deployment.md). It includes every environment variable, database-role and RLS checks, first-deploy verification, and the free-plan tradeoffs. The combined API/worker process is deliberately a demo topology because Render background-worker instances are not available on the free plan.

## Demo flow

1. Open `/` — the landing page explains the product before asking for an account.
2. Register. A new account is routed into onboarding, not an empty dashboard.
3. Create a workspace, then choose what the assistant will help with.
4. Upload a policy document. Preparation starts automatically; the timeline moves Uploaded → Processing → Extracted → Ready.
5. Ask the suggested question. The answer arrives with the passage it came from.
6. Finish setup and confirm the dashboard reads "Your assistant is ready".

Nothing in that flow requires knowing what ingestion, indexing, or embeddings are.

## Repository structure

```text
backend/           FastAPI application, SQLAlchemy models, Alembic migrations, tests
  app/api/         Versioned routes and dependencies
  app/services/    Business logic
  app/ingestion/   Text extraction and chunking
  app/embeddings/  Provider interface and indexing
  app/rag/         Context building, prompts, citation assembly
frontend/          Next.js App Router application
  app/             Routes
  src/components/  Layout, marketing, onboarding, dashboard, knowledge, documents, chat, settings
  src/lib/         API client, auth, terminology
  tests/           Vitest unit tests and the Playwright flow
docs/              Architecture, schema, decisions (50 ADRs), deployment guide
```

## Documentation

- [Architecture](docs/architecture.md) · [Database schema](docs/03-database-schema.md) · [API design](docs/api-design.md)
- [Auth and tenancy](docs/04-auth-tenancy.md) · [Upload](docs/05-document-upload.md) · [Ingestion](docs/07-document-ingestion.md) · [Indexing](docs/08-embedding-indexing.md) · [RAG chat](docs/09-rag-chat.md)
- [Frontend redesign](docs/10-frontend-redesign.md) — terminology mapping, flows, and the full limitations list
- [Supabase and Render deployment](docs/11-supabase-render-deployment.md) — free demo setup, verification, and troubleshooting
- [Contabo Ubuntu VPS deployment](docs/12-contabo-vps-deployment.md) — Docker, HTTPS, persistent data, backups, and operations
- [Architecture decisions](docs/06-decisions.md) — 50 ADRs
- [Learning notes](docs/learning-notes/) — per-phase write-ups

## Screenshots

Captured after deployment so they show real seeded data rather than test fixtures.

| View | Path |
| --- | --- |
| Landing page | `docs/screenshots/landing.png` |
| Onboarding | `docs/screenshots/onboarding.png` |
| Dashboard | `docs/screenshots/dashboard.png` |
| Preparing a document | `docs/screenshots/prepare-timeline.png` |
| Grounded answer with sources | `docs/screenshots/chat-sources.png` |
| Mobile chat | `docs/screenshots/mobile-chat.png` |
