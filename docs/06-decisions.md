# Architecture Decisions

## ADR-001: Shared Database, Shared Schema, Organization ID

Status: Accepted

The MVP uses one PostgreSQL database and one shared schema. Tenant-owned tables carry `organization_id` directly. This keeps local operations simple, supports efficient tenant filters, and prepares the system for PostgreSQL Row Level Security. The tradeoff is that tenant scoping must be enforced consistently in application queries until RLS is added.

## ADR-002: PostgreSQL and pgvector for MVP Retrieval

Status: Accepted

Embeddings live beside chunk metadata in PostgreSQL through pgvector rather than in a separate vector database. This reduces infrastructure, preserves transactional relationships, and is sufficient for the expected MVP scale. A dedicated vector system remains an option if scale or retrieval requirements outgrow PostgreSQL.

## ADR-003: SQLAlchemy and Alembic for Schema Control

Status: Accepted

SQLAlchemy 2.0 declarative models define the application schema, and Alembic records the database history. This gives the backend typed relationships, reviewable migrations, repeatable local setup, and a controlled path to production schema changes.

## ADR-004: Citations Stored Separately from Messages

Status: Accepted

`message_citations` is a separate table rather than JSON embedded in a message. Each citation can point to the source document and exact chunk, preserving traceability, supporting audits and feedback analysis, and allowing retrieval metadata to evolve independently of chat content.

## ADR-005: Separate Upload from Ingestion

Status: Accepted

Upload stores the original file and a pending database record. Ingestion independently extracts and chunks that stored file. This keeps HTTP uploads responsive, gives failures a retry path, and creates a clear boundary for a future worker service.

## ADR-006: FastAPI BackgroundTasks for MVP Ingestion

Status: Accepted

The MVP schedules ingestion with FastAPI `BackgroundTasks`, and each task opens its own database session. This avoids introducing queue infrastructure before ingestion behavior is proven. The tradeoff is that tasks are not durable across process restarts, so RQ, Celery, or a dedicated worker is expected as the workload grows.

## ADR-007: Simple Custom Chunking Before Framework Splitters

Status: Accepted

The first splitter is a small character-based implementation with overlap and readable-boundary detection. Keeping it local makes chunk boundaries and metadata easy to inspect and demonstrates the underlying mechanics before evaluating LangChain or another framework splitter.

## ADR-008: Nullable Embeddings Until Indexing

Status: Accepted

Text extraction creates chunks with null embeddings and marks the document processed. Embedding generation is a separate indexing phase that will move documents to indexed. This separates deterministic file processing from model-dependent external calls and allows either phase to be retried independently.

## ADR-009: Provider Abstraction for Embeddings

Status: Accepted

Indexing and search depend on a small provider interface rather than an SDK-specific client. OpenAI is selected through a factory, while Gemini, Cohere, Voyage, or local sentence-transformer adapters can later implement the same contract. This contains provider-specific configuration and API behavior.

## ADR-010: OpenAI text-embedding-3-small for MVP

Status: Accepted

The MVP uses OpenAI `text-embedding-3-small`. It is practical, fast, widely supported, and fits the project's current PostgreSQL vector schema. Provider batching reduces request overhead while explicit dimension validation prevents incompatible vectors from reaching the database.

## ADR-011: Store Embeddings in PostgreSQL pgvector

Status: Accepted

Chunk vectors remain beside tenant IDs, document relationships, metadata, and content in PostgreSQL. pgvector supplies cosine-distance ordering and the existing HNSW index without introducing a separate vector database for the MVP.

## ADR-012: Use 1536-dimensional OpenAI Embeddings for MVP

Status: Accepted

Context:

The `document_chunks` table stores vector embeddings for semantic search. The vector column needs a fixed dimensionality.

Decision:

Use OpenAI `text-embedding-3-small` with 1,536-dimensional embeddings for the MVP.

Reasoning:

It is practical, fast, widely supported, and fits the current pgvector schema. The embedding provider is hidden behind an abstraction so other providers can be added later.

Consequences:

Changing to a model with a different embedding size, such as a 384-dimensional local Sentence Transformer, will require a schema migration and re-indexing all chunks.

## ADR-013: Add Search Before RAG Chat

Status: Accepted

A direct semantic-search endpoint ships before chat answer generation. It exposes chunk ranking, distance, metadata, and tenant filters directly, making retrieval relevance and isolation easier to test before prompts, citations, and model-generated answers add more variables.

## ADR-014: Add RAG Chat After Semantic Search

Status: Accepted

RAG chat is added only after tenant-scoped semantic search is working and tested. The chat flow reuses the proven embedding and retrieval path, then adds bounded context, grounded generation, persistence, and citations. This sequencing isolates retrieval quality from generation quality and makes failures easier to diagnose.

## ADR-015: Provider Abstraction for Chat Models

Status: Accepted

RAG services depend on a small `generate_answer(system_prompt, user_prompt)` protocol. OpenAI SDK details stay inside the OpenAI adapter, while selection happens in a factory. Gemini, Anthropic, or a local model can be added later without coupling routes, retrieval, prompting, or persistence to a vendor SDK.

## ADR-016: Simple RAG Service Before LangGraph

Status: Accepted

The first RAG workflow is an explicit synchronous service rather than a LangGraph graph. The flow is currently linear, has no tools or branching, and benefits from easy transaction boundaries and straightforward tests. LangGraph remains appropriate when orchestration adds routing, tool calls, retries, memory workflows, or human handoffs.

## ADR-017: Return Citation Metadata with the Answer

Status: Accepted

The chat response returns document ID, document title, chunk ID, quote, score, and chunk metadata alongside the answer. Clients can show sources immediately without parsing model-generated markdown or making an additional request. Citation identity is built by the application from retrieved rows, not invented by the model.

## ADR-018: Next.js App Router for the Frontend

Status: Accepted

Frontend v1 uses Next.js with the App Router and TypeScript. Nested layouts provide a natural boundary between public authentication pages and the protected dashboard shell, while file-based routes map directly to product areas and conversation detail views. This keeps routing and page composition explicit without introducing a separate routing framework.

## ADR-019: Tailwind CSS and shadcn/ui-Style Components

Status: Accepted

The frontend uses Tailwind CSS for design tokens and responsive layout, with reusable shadcn/ui-style primitives composed into project-specific components. This supports a restrained custom interface without committing the project to an opaque theme or a large component suite. Accessibility states, spacing, borders, and status colors remain consistent while product components stay editable in the repository.

## ADR-020: TanStack Query for Server State

Status: Accepted

Current-user, organization, knowledge-base, document, conversation, and message data come from the FastAPI backend and are managed as server state through TanStack Query. Query keys make tenant scope explicit, and targeted invalidation keeps reads fresh after writes. Local component state remains appropriate for transient UI such as open dialogs or draft input.

## ADR-021: localStorage JWT for MVP

Status: Accepted for MVP

Frontend v1 stores the API access token in browser `localStorage` and attaches it through the shared Axios client. This matches the existing bearer-token backend and keeps local setup straightforward. The tradeoff is exposure to token theft if an XSS vulnerability exists. A production authentication milestone should move session credentials to `Secure`, `HttpOnly` cookies with appropriate same-site and CSRF controls.

## ADR-022: Build the Frontend After the RAG API

Status: Accepted

The product UI is added after authentication, organization isolation, document ingestion and indexing, semantic search, and RAG chat with citations are working through the API. As a result, Frontend v1 can exercise the real upload-to-answer lifecycle rather than designing against guessed contracts or placeholder messages. The backend remains the authorization and tenant-isolation boundary.

## ADR-023: Product Language in the UI, Backend Language in the API

Status: Accepted

The API keeps its domain vocabulary (organizations, knowledge bases, ingestion, indexing, citations) while the interface speaks only in product terms. A single module, `frontend/src/lib/terminology.ts`, owns the translation: status labels, tones, timeline position, and the decision about whether to keep polling all derive from one table. Components ask that module rather than mapping strings themselves, so the rule is enforced by construction instead of by reviewer memory, and a future rename is one edit. Raw identifiers never reach the interface; where a name is needed, the client resolves it from a list it already holds.

## ADR-024: Workspace and Knowledge Space as Product Terms

Status: Accepted

"Organization" is accurate but reads as billing and administration, and "knowledge base" describes the retrieval mechanism rather than the user's goal. The UI says workspace and knowledge space. The API is unchanged, so this is a presentation decision with no migration cost, and the mapping lives in the terminology module rather than being spelled out per component.

## ADR-025: One Prepare for Chat Action Instead of Ingest and Index

Status: Accepted

Extraction and indexing are two API operations with independent failure modes, which is right for the backend and wrong for the interface: it made the user sequence two calls and guess when the first had finished. `POST /documents/{id}/prepare` runs both server-side in one background task and stops if extraction produces nothing, so clients call one endpoint and poll one status. Ingest and index remain available for operating on a single phase. Doing this server-side rather than orchestrating in the browser keeps the sequencing correct when a client disconnects mid-flow.

## ADR-026: Guided Onboarding Before the Dashboard

Status: Accepted

A new account has no workspace, no knowledge space, and no documents, so the dashboard would open on four empty panels and no clear first move. Users without a workspace or knowledge space are routed to a four-step flow that creates each in turn and finishes with a real question against a real document. The gate is evaluated on entry only: completing a step mid-flow satisfies the condition that sent the user there, and re-checking would eject them before the end.

## ADR-027: Marketing Landing Page at the Root Route

Status: Accepted

The root route previously redirected straight to the dashboard, so an unauthenticated visitor met a login form with no explanation of the product. `/` is now a landing page covering the problem, the three-step flow, features, and use cases. For a portfolio project this is also the page a reviewer sees first, and it carries the positioning that the dashboard cannot.

## ADR-028: Responsive Dashboard with a Drawer Sidebar

Status: Accepted

The application shell uses a fixed sidebar that becomes a dialog-based drawer below the `lg` breakpoint, with a top bar carrying the workspace switcher and account menu. Data-dense views change shape rather than scroll: the documents table becomes stacked cards below `xl`, because the fixed sidebar leaves roughly 736px of content column at 1024px and five columns would have to scroll sideways. Layout is verified by measuring every element against the viewport at 360, 768, 1024, and 1440 rather than by inspection.

## ADR-029: Stock Next.js Instead of the vinext Adapter

Status: Accepted

Frontend v1 built through `vinext` with a Cloudflare Workers adapter. The redesign moved to the standard Next.js CLI. The application already used App Router conventions, so no application code changed; only the toolchain and its dependencies were removed. The reasons are that a pre-1.0 build adapter is a fair thing for a reviewer to question, and the planned deployment target expects standard Next.js output.

## ADR-030: Role-Named Design Tokens

Status: Accepted

Colour is defined once as CSS custom properties named for their role (`surface`, `foreground-muted`, `border-strong`, `success-surface`) and exposed to Tailwind through `@theme`. Components reference roles rather than palette positions, which is what makes a theme change a single file. The primary is a near-black neutral rather than a saturated accent, so colour is reserved for status and a green or amber badge carries meaning instead of competing with decoration.

## ADR-031: Aggregate Counts in List Responses

Status: Accepted

Knowledge bases return `document_count` and `ready_document_count`; conversations return `message_count` and `last_message_preview`. Without these a client renders a list by fetching every child record just to count it. Both use a single grouped or correlated query, so a list costs one round trip regardless of length, and the preview is truncated server-side so the response does not carry whole message bodies.

## ADR-032: Upload No Longer Starts Ingestion Automatically

Status: Accepted

`AUTO_INGEST_ON_UPLOAD` now defaults to false. With it enabled, upload left the document mid-flight in `processing`, so a `prepare` call moments later conflicted with work already running, and the document stalled after extraction with nothing to index it. Preparation is an explicit action that owns the whole lifecycle, which removes the race and matches the single user-facing action described in ADR-025.

## ADR-033: Redis and RQ for Durable Preparation

Status: Accepted

Document preparation moves from FastAPI `BackgroundTasks` (ADR-006) to an RQ job on Redis. The problem with the previous approach was not throughput but survival: a `BackgroundTask` runs inside the API process, so any restart during preparation loses the work and leaves the document in `processing` with nothing left to finish it. RQ was chosen over Celery because the workload is a handful of small job types with no chains, groups, or routing, and RQ's model is small enough to read in an afternoon; Celery's feature set would be configuration to maintain rather than capability used. The single-phase `ingest` and `index` endpoints remain in-process: they are operational tools, not part of the user-facing path.

## ADR-034: Idempotency by Claim and by Effect

Status: Accepted

A preparation job must be safe to run more than once, because a queue that guarantees at-least-once delivery will eventually deliver twice. Safety comes from two independent properties. *Effect idempotency*: extraction deletes a document's chunks before writing new ones, and indexing only embeds chunks whose vector is null, so a repeated run converges on the same state without repeating the paid work. *Claim idempotency*: a job takes ownership through a single conditional UPDATE, which the database resolves, so two workers cannot both believe they are clear to proceed. Reading the status and then writing it would leave a window between the two statements where both workers see an unclaimed document. A claim is granted when the document is unowned, when the previous owner has gone quiet past the stale threshold, or when the caller already owns it, which is what lets a retry continue its own work.

## ADR-035: Retry Only What Retrying Could Fix

Status: Accepted

Failures are classified before a retry is scheduled. Bad input — a corrupt file, an unsupported type, a document that yields no text — fails identically every time, so retrying spends time and embedding credit to reach the same answer; these are recorded as failed immediately. Environment failures such as provider timeouts and 5xx responses are retried with increasing backoff, capped at a configured number of attempts, after which the document is marked failed with the attempt count in its message. Unrecognized exceptions are treated as retryable on the grounds that a needless retry is cheaper than a document stuck failed because of a transient error nobody anticipated. The queue owns *when* a retry happens; the job owns *whether* one is deserved.

## ADR-036: A Sweep for Work Nobody Owns

Status: Accepted

Retries only help when a job fails. A worker killed between claiming a document and finishing it fails nothing: the queue has no record to retry, and the API will not start another job because the status already reads `processing`. Nothing in the system notices, and the user watches a progress timeline that will never move. A periodic sweep finds documents that have been processing longer than any real preparation should take and either requeues them or fails them, depending on attempts already spent. It compares against the claim timestamp where one exists and the row's `updated_at` where one does not, because a job lost before any worker claimed it leaves no claim behind. The threshold is deliberately generous: failing a document that is merely slow is worse than recovering it a few minutes late.

## ADR-037: Rate Limits Keyed to the Risk, Not to the User

Status: Accepted

Auth and chat are both limited, on different keys, because they carry different risks. Auth endpoints are limited per client address: the threat is credential stuffing against accounts this server has never seen, so the caller's identity is the only thing available to key on. Chat is limited per organization: each message costs an embedding call plus a completion, the bill lands on whoever owns the API key, and a per-user limit would let one organization multiply its spend by adding members. Counting lives in Redis, already present from ADR-033, so every API process spends one budget rather than one each.

The window is fixed rather than sliding. A fixed window lets a caller send up to twice the limit across a boundary, which is the known cost of one `INCR` and one `EXPIRE` per request instead of a stored request log to trim; at these limits the burst is not worth a sorted set per caller. The limiter fails open: if Redis is unreachable the request proceeds and the outage is logged, because a limiter that is down should not also be a login outage. That choice is what makes this a spend and abuse control rather than a security boundary — the boundaries are authentication and the policies in ADR-038.

The address key is only as good as the deployment. Behind a load balancer, `request.client.host` is the balancer, and trusting `X-Forwarded-For` without knowing the hop count would let a caller forge an identity and opt out of the limit entirely. Proxy header trust is configuration for the deployment phase, not a default to guess at here.

## ADR-038: Row-Level Security as the Second Line, With a Role That It Applies To

Status: Accepted

Every organization-scoped table carries a policy admitting only rows whose `organization_id` matches `app.current_organization_id`, a session variable set from the request's organization. The repositories already filter by organization; this exists for the query that forgets to, which then returns nothing instead of another tenant's rows. Unset scope resolves to NULL and matches nothing, so the failure mode is an empty result — a bug someone notices immediately — rather than a leak.

Two implementation facts turned out to matter more than the policies themselves. Postgres exempts superusers and a table's owner from row-level security, so an application connecting as `postgres` passes through every policy while the database reports them as enabled and forced; the first version of the test suite passed for exactly this reason. The migration therefore creates a non-owning login role for the application, migrations keep the owner through `MIGRATION_DATABASE_URL`, and a startup check logs loudly when the connected role bypasses the policies anyway. Separately, SQLAlchemy returns its connection to the pool on commit, so a setting applied once per session is gone by the next statement; the scope is applied on `after_begin`, for every transaction.

Identity and membership tables — `users`, `organizations`, `organization_members` — are deliberately excluded: they are what a request consults to work out which organization it is in, so they cannot be gated on that having already been decided. The stale-preparation sweep is inherently cross-tenant and was given no way around the policies; it walks the organizations and runs the same scoped query inside each, which costs a query per organization on a small table and keeps the invariant worth having.

The scope is taken from the client-supplied path or header, which is safe because it narrows rather than grants: whether this user may use that organization is still decided by `require_organization_member`. Because the test suite runs on SQLite, which has neither policies nor session variables, these tests run against a real Postgres in CI or fail — a skipped security test reads the same as a passing one in a job summary.

## ADR-039: localStorage and a Sixty-Minute Session, Stated Rather Than Fixed

Status: Accepted, with known cost

The access token stays in `localStorage` (ADR-021) and still expires after sixty minutes with no refresh token. Both are shortcuts, and this records what they cost and why they were kept.

`localStorage` is readable by any script running on the origin, so an XSS vulnerability becomes a stolen session. The alternative — a `Secure`, `HttpOnly`, `SameSite` cookie — moves the token out of JavaScript's reach entirely, which is the right end state, but it is not a one-line change: it means a login endpoint that sets a cookie, CSRF protection for every state-changing request now that the browser attaches credentials automatically, and CORS with credentials across the two origins this app runs on. What mitigates the current position is narrow but real: the frontend renders no user-supplied HTML, there is no third-party script on the authenticated pages, and the token's short life bounds how long a stolen one is useful.

The sixty-minute expiry with no refresh is the other half of that bound, and it is why the expiry has not been extended: a longer-lived token in `localStorage` would make the first tradeoff worse. The cost is a user being logged out mid-task with no warning. Refresh tokens would fix the interruption, but done properly they mean rotation, reuse detection, and a revocation store — real work whose payoff is convenience, not isolation, which is why rate limiting and tenant policies were built first. The honest summary is that this is a portfolio application's session design, chosen with the failure modes known rather than by not thinking about them.

## ADR-040: Deletion Cascades in the Database, Files Afterwards

Status: Accepted

Deleting a document, knowledge space or workspace issues a single Core `DELETE` and lets the `ON DELETE CASCADE` already declared on every `organization_id` and parent foreign key do the rest. The ORM was the wrong tool here and not marginally: `session.delete` loads each child collection in order to null its foreign key, those keys are `NOT NULL`, so it fails — and where it would succeed it would issue a query per collection to do what one statement already does correctly.

Three semantics are worth stating because each was a choice rather than a default. **A deleted document disappears from past answers' sources.** Its citations cascade with it, so a previous reply keeps its text but no longer lists it. Keeping the citation would mean quoting a passage from a document someone deliberately removed, which is the wrong side to err on when the reason for deleting was that the content was wrong or shouldn't have been there. **A deleted knowledge space keeps its chat threads.** The foreign key is `SET NULL`, so history survives with nothing left to search; deleting the conversations too would destroy a second thing the user did not ask about. **A deleted workspace keeps its members' accounts** — a person is not owned by a workspace, and someone in two of them must keep their account when one goes.

Files are removed after the commit, never before. The two stores cannot be deleted atomically, so the ordering is a choice about which inconsistency to prefer: a file with no row is invisible and costs disk, a row with no file is a document that opens to nothing. Cleanup problem beats data loss, and a failed unlink is logged rather than raised. Paths are resolved and checked for containment under the upload directory first, because `file_path` is a column and a column is data.

Deleting a document mid-preparation is refused with `409` rather than accepted. The embedding calls are already in flight and already billable; accepting the delete would imply they had been called back. The stale sweep from ADR-036 bounds the wait. Workspace deletion is the exception — the whole tenant is going, so there is no in-flight work worth preserving — and it is owner-only, gated in the UI behind typing the workspace name, because it is the one destructive action that takes other members' history with it.

## ADR-041: Keyset Cursors Instead of Offset Pagination

Status: Accepted

Documents and messages are paged with an opaque cursor encoding `(created_at, id)`, not with `LIMIT`/`OFFSET`.

Offset is the obvious choice and wrong for both. `OFFSET 200` asks the database to walk and discard two hundred rows before returning anything, so a page costs more the deeper it is. The correctness problem matters more: both lists are mutated while someone is reading them. Delete a document while a user is on page two and every later row shifts up one — they skip a row and never know. Upload one and they see the same row twice. A cursor names a position in the sort order rather than a count of rows, so the row after it is still the row after it.

The sort key is a pair, not a timestamp. Two documents uploaded in the same millisecond would make a timestamp-only cursor ambiguous, and an ambiguous cursor either repeats a row or skips one. The cursor is base64 rather than two plain query parameters so its shape stays an implementation detail; a malformed one is rejected with `422` rather than silently treated as page one, because a client that thinks it is paging and is actually restarting will loop forever. Pages are fetched as `limit + 1` rows so "is there more" costs nothing beyond the row that answers it.

What this gives up is jumping to page seven and knowing how many pages exist. Neither list needs either: documents are searched and filtered rather than paged through, and nobody navigates a chat thread by page number. Where a total genuinely is needed — the numbers on the filter chips — it comes from a separate grouped count that describes the current search but ignores the selected status, so every chip can say how many documents it would reveal.

Directions differ because reading directions differ. Documents page forwards from newest. A thread returns its most recent page and walks backwards, because opening a conversation should show its end.

Implementing this surfaced a real ordering bug. `created_at` came only from `server_default=func.now()`, which renders as the backend's own timestamp function: Postgres gives microseconds, SQLite's `CURRENT_TIMESTAMP` gives whole seconds and stores them as text. Whole seconds mean rows written in the same second tie, and text storage means a stored `...:32` compares against a bound `...:32.000000` as a shorter string rather than an equal instant — so the cursor matched every row and pages repeated forever. Timestamps are now set application-side as well, which makes stored and compared representations the same one.

## ADR-042: Measure Retrieval Before Changing It

Status: Accepted

Every retrieval change in this phase was gated on an evaluation harness written first. Without one, "better chunking" and "hybrid search" are opinions with plausible reasoning attached, and the reasoning is plausible for changes that turn out to help, do nothing, and actively hurt alike — as all three did here.

The harness indexes a fixed corpus of sixteen support documents, asks fifty-seven fixed questions, and records which documents came back. It drives the production chunker, the production embedding provider, and the production search method; an eval that measures its own copy of the pipeline measures nothing. It skips only HTTP and file upload, which do not vary between runs.

**Scoring is on documents, not chunks.** Chunk size is one of the things being tuned, so counting chunk hits would make a smaller chunk size look like better retrieval. **Grading is on sources, not answer text.** Judging generated prose needs a second model to do the judging, and its verdicts move with the chat model rather than with retrieval — the thing being measured. An optional pass does check that expected facts survive into the answer, deliberately as a crude substring test rather than a pretence at grading. **Questions are tagged by kind** — direct, paraphrase, inference, cross-document, literal, unanswerable — because a single average hides the case that matters: a change which helps lookups and hurts paraphrases leaves the headline number flat. **Unanswerable questions are scored separately**, since recall is undefined when no document is correct; returning 0 would penalise correct behaviour and returning 1 would reward retrieving anything.

Embeddings are cached by content hash, so a re-run costs nothing and only changed text is paid for. This is not a convenience: an eval that costs money on every run is an eval that stops being run. It is not part of `pytest` for the same reason `e2e.yml` is manual — it needs real Postgres and a paid key. Its scoring arithmetic *is* unit-tested there, because a metric that miscounts is worse than no metric: the numbers get believed.

The first version of the corpus scored a meaningless recall of 1.0000 — six documents, one chunk each, retrieving five of six. A harness that cannot fail cannot measure improvement, and noticing that is the reason the corpus was rebuilt before any retrieval work started.

## ADR-043: Structure-Aware Chunking, and Hybrid Retrieval to Pay for It

Status: Accepted

Chunking now splits on markdown headings rather than on a character count, and each chunk is prefixed with its heading path. Retrieval fuses vector search with Postgres full-text search by reciprocal rank.

**Why split on structure.** A fixed window splits wherever the count runs out, mid-sentence and mid-topic. Worse, at a window larger than the document it produces one chunk holding everything, so a single embedding stands for every topic the document covers — sixteen corpus documents produced seventeen chunks. "When do you charge for a pre-order?" wants the pre-order paragraph, not a vector averaging the whole stock policy. The heading prefix costs a few tokens and buys context: "Charged at dispatch, not at the time of ordering" is ambiguous alone and unambiguous under "Stock and availability › Pre-orders". Sections too long for one chunk still fall back to the character window, and sections too short to answer anything are merged into a neighbour.

**Why fuse rather than normalise.** A cosine distance and a `ts_rank` are different units on different scales, and `ts_rank` is unbounded. Putting them on a common scale means inventing a conversion, and that conversion would be the thing quietly deciding results. Reciprocal rank fusion discards the scores and keeps only positions, so a chunk ranked second by both retrievers beats one ranked first by a single retriever and missing from the other — agreement between two methods being better evidence than a strong score from one. Each retriever is asked for more candidates than the final `top_k`, or fusion could only ever reorder what vector search already found.

**What the measurements actually said.** Structure-aware chunking raised precision from 0.219 to 0.343 and fixed an inference failure — *and broke two literal-token questions*, because a rare word now sits in a small chunk whose embedding is dominated by the rest of its section. Hybrid retrieval, measured on its own against the first question set, changed recall and precision not at all and cost MRR. It earns its place only alongside the chunking change, where it repairs precisely that regression. Neither change is right by itself, which is not what either was expected to show.

Final against baseline: recall@k 0.9528 → 0.9811, precision@k 0.2189 → 0.3283, hit rate 0.9623 → 0.9811, MRR 0.8899 → 0.8805. The MRR cost is accepted knowingly: more chunks compete for rank one, and everything retrieved reaches the model anyway, so recall is worth more than rank here.

The full-text column is `GENERATED ALWAYS AS ... STORED` so Postgres maintains it; a trigger or an application write is one more thing to forget on an update path. It uses the `english` configuration, which is a limitation to name rather than hide — a non-English corpus needs a different one. Citations are deduplicated to one entry per document, because several chunks of one source became a common result once sections were chunked separately and listing them read as several sources; the context the model answers from still receives every chunk.

## ADR-044: JSON Logs, One Line Per Request, With an Id That Ties Them Together

Status: Accepted

Logs are one JSON object per line, formatted at the root handler so that uvicorn and SQLAlchemy match the application's own output. Human-readable prose is better on a laptop and worse everywhere else: once logs are shipped somewhere, grepping prose is how a team ends up unable to answer "which organization saw errors last night". A pipeline containing two formats is a pipeline where one of them goes unparsed.

Every line carries a request id, taken from an inbound `X-Request-Id` when present so a trace started by a load balancer survives the hop, and returned on the response so a user can quote it from a failure. The id lives in a context variable rather than being threaded through function signatures — the same mechanism as the tenant scope in ADR-038, with the same acknowledged cost of being invisible at the call site. Background jobs establish their own context keyed on the job id, since a context variable does not cross into a worker process. The organization is attached by middleware and the user after the token is validated, because before that there is nothing trustworthy to say.

Uvicorn's access log is silenced rather than reformatted. The middleware already logs the same event with the method, path, status, duration and request id on it; leaving both enabled prints every request twice, once with less information.

Sensitive keys are redacted by name wherever they appear, including nested, regardless of what a caller passes. A credential in a log line is a credential in every system the logs reach, and log retention routinely outlives the credential.

Error reporting is wired and disabled: no DSN, no account, no dependency. The decision worth making now is what gets scrubbed before an event leaves the process, and that belongs with the code that knows which fields are sensitive — not with whoever later pastes in a DSN and discovers tokens in their error tracker.

## ADR-045: A Daily Token Budget, Metered From What The Provider Charged

Status: Accepted

Each organization has a daily token budget, checked before chat and recorded after every call that spends anything. This is the second half of ADR-037: a per-minute rate limit bounds a burst and says nothing about a day, and twenty messages a minute is nearly thirty thousand a day.

**Metered on tokens reported by the provider.** Not a local tokenizer, which would be an estimate — and an estimate of a bill is a second source of truth that drifts from the real one, which is the worst possible property for the number a spending limit is enforced against. Not on request count either: one question against a full context costs many times another. Cost in dollars is derived and labelled an estimate everywhere it appears, and the cap is deliberately *not* enforced on it, so that a stale price table cannot silently move the limit.

**Providers report into a context-scoped accumulator** rather than returning usage alongside their result. Returning it would change the signature of every provider, every fake in the test suite, and every caller, none of which has any other interest in billing. Recording outside a tracked scope is a no-op rather than an error, so a provider used from a script or the eval harness does not fail because nothing is counting.

**Stored in Postgres, and this is the sharpest contrast with the rate limiter.** That one lives in Redis and fails open, because a limiter outage should not become a login outage. This one counts money: a spending record that evaporates when a cache restarts is not a record, and it is the row an invoice dispute would be settled from. Writes are an upsert that adds in SQL rather than a read-modify-write, because two requests finishing together would both read the same starting figure and one would overwrite the other's addition — losing spend, the one direction an accounting error must not go. The table is stored at daily grain, not as a ledger of calls: the daily figure is what the cap is enforced against, and a row per call would put a write on the hottest path in the application to answer questions nobody is asking.

Recording happens in a `finally`, so a question that retrieved nothing still pays for embedding itself, and a completion the provider billed for before failing is still counted — a meter that only counts happy paths under-reports exactly when things are going wrong. It never raises into the caller: the answer has already been delivered, and losing the meter must not undo it. The failure is logged loudly instead, because silently uncounted spend is how a cap stops working without anyone noticing.

The check is against committed usage, so a request that starts just under the limit may finish over it. That is the same overshoot a fixed rate-limit window has and is accepted for the same reason: the alternative is reserving tokens before knowing how many the call will use, which means estimating. Zero means "no budget configured" rather than "no tokens allowed", because the opposite reading turns an unset value into a total outage. The `429` says the budget is daily and when it resets — "try again shortly" is wrong advice for a limit that clears at midnight — and usage is readable by any member, since a limit people cannot see arrives as an unexplained error.

## ADR-046: One Accent, Chosen Against the Status Palette, With Dark Designed Beside It

Status: Accepted

The previous palette was deliberately neutral — a near-black primary, colour reserved for status. That was a defensible starting point and it produced an interface that read as competently assembled rather than designed. This replaces it with one committed accent, a display typeface for headings only, and a hero illustration that states the product before the headline is read.

**Burnt terracotta, `#b4471f`.** Chosen partly for what it is not: the saturated indigo-to-violet band is the default costume of every AI product, and wearing it means being read as one of them before a word is read. Terracotta is warm without being playful, which matters because the product is now positioned for a freelancer as much as for a support team — a colder, more institutional accent would quietly answer "who is this for?" the wrong way. The neutrals were rewarmed to match: the page is paper `#fbf8f4` rather than grey, and every zinc became a stone. Half the impression comes from that, not from the accent.

**The status ramps were moved to make room for it.** This is the real cost of the choice and the reason it needs recording. Terracotta sits between amber and red, so the stock warning and danger hues would have read as three shades of the brand colour rather than as three meanings. Success is olive rather than emerald, warning is gold rather than amber, and danger is crimson pushed toward red-violet, which is the one direction with hue distance to spare. The stronger rule is that the accent never renders as a status badge, so the two vocabularies never appear in the same row for comparison.

**Fraunces, on headings only.** Applied to the hero, marketing section headings, and in-app page titles — nowhere else. Card titles, table headers, form labels, and body copy stay on the UI sans. A display face carries character at 40px and costs legibility at 14px, and a dashboard is mostly 14px. `SOFT` and `WONK` are requested explicitly in the font loader, because a variable font is subsetted to the axes asked for and the `font-variation-settings` would otherwise be silently inert.

**The hero is a drawn diagram rather than a screenshot.** A tilted product shot was the alternative and was rejected on the brief's own test: a screenshot has to be read before it means anything. The diagram runs a single accent chain — marked document, line, node, highlighted sentence, source pill — so following the colour is following the claim. One real filename inside the pill is the only text; fully abstract, the drawing reads as generic dataflow. It is built from tokens, so dark mode repaints it instead of needing a second asset.

**Light and dark were designed as a pair, not derived.** An inversion would have produced `#b4471f` on a dark ground, which is muddy and fails contrast, so dark uses `#e8734a` and flips the accent's foreground to near-black — a light accent no longer carries white text. Surfaces step *up* in lightness as they come forward rather than down. Two bugs found in this pass are the argument against auto-inversion: the modal scrim was a tint of the foreground, so it inverted into a *white* veil brightening the page it was meant to push back, and Sonner paints its own surfaces and renders light toasts over a dark app unless told the theme.

**The ink bands are a token scope, not a set of overrides.** The closing call to action and the auth panel are dark in both themes, which is a hole in the model: a child reading `--primary` in light mode gets the dark terracotta and paints it onto near-black at 1.6:1. Rather than overriding classes at each call site, `.on-ink` re-declares the tokens its children read, so a `Button` inside it needs no special casing. They are ink rather than accent for a separate reason: a full-bleed terracotta band would be the largest area of colour on the page, which makes the accent scenery instead of a signal and leaves the primary button nothing to stand against.

**Contrast is checked by a script, not by eye.** `npm run check:contrast` parses the tokens out of `globals.css` — rather than keeping a second copy that would drift — and asserts WCAG AA across both themes: 4.5:1 for text, 3:1 for control boundaries. It found that form-control borders sat at 1.6:1, because `--border-strong` was doing two unrelated jobs, decorative rule and interactive boundary. Splitting the control border onto `--input` fixed it without darkening the hero diagram's neutral lines.

## ADR-047: Serving the Original Upload Back, and Refusing to Let Anything Cache It

Status: Accepted

Documents could be uploaded, prepared, searched, and cited, but never read. The only way to see any of a document's own text was to ask a question and recognise a passage in the answer. `GET /organizations/{id}/documents/{id}/file` streams the stored upload back so it can be opened in the browser.

**The original file rather than the extracted passages.** The passages were the safer option and were rejected deliberately: they are what the assistant sees, not what the user uploaded, and someone checking "is my policy actually in here" wants their document, formatting and all. The cost is that this feature is built on the one piece of infrastructure known to be temporary — uploads live on the container filesystem, which limitation 2 records as ephemeral. Until that moves to object storage, a deployed instance loses every original on restart while its passages, which are in Postgres, survive. The endpoint is written to say so rather than to pretend otherwise.

**`410 Gone`, not `404`.** A missing row and a missing file need different answers. The document is still listed, still searchable, still cited in past answers — telling the reader it does not exist would send them looking for the wrong problem. `410` plus a message that names the passages as still working is the honest report, and after object storage lands it is also the signal that a restore is what is needed.

**Fetched through the API client, not linked to.** The session is a bearer token in `localStorage` (ADR-021), and neither `<a href>` nor `<iframe src>` can carry a header. The client requests a blob and the component turns it into an object URL, which also means the URL is revocable and never leaves the tab. A signed-URL scheme would avoid the round trip and is the right answer once files are in object storage; it is not worth building against a local directory.

**Served `inline`, with `nosniff`.** Inline is the point — the file should render, not download. But that means returning bytes a user supplied, from our own origin, under a media type recorded at upload from the client's own claim. Without `X-Content-Type-Options: nosniff` a `.txt` full of markup can be sniffed as HTML and executed as this origin. The path is also checked to be inside the upload root before it is opened: today the column is only ever written by `upload` from generated UUIDs, but a filesystem read assembled from a database string is the exact shape of a traversal, and the check costs one comparison.

**Nothing may cache it, and this was found by watching it happen.** `FileResponse` sends an ETag and a last-modified date and no cache directive, which leaves a browser free to store the bytes and reuse them heuristically — observed still serving a document whose file had been deleted. `private` keeps one tenant's document out of any shared cache and `no-store` keeps it off disk. The errors carry `no-store` too, which is the less obvious half: `404` and `410` are both cacheable by default under RFC 9110, and a pinned `410` would go on reporting a file as gone after a re-upload had brought it back under the same document id. That is not a corner case here; it is the normal recovery path.

Deployment amendment: ADR-048 replaces local-only storage with a provider
boundary. The API still proxies original files and preserves these membership,
content-sniffing, and cache rules for both local and object storage.

## ADR-048: Private Object Storage Behind a Provider Boundary

Status: Accepted

Uploads use a small storage protocol with local and S3-compatible adapters.
Local disk remains the zero-friction development default. Deployed files live
in a private Supabase Storage bucket because Render free web-service filesystems
are ephemeral and the API and RQ worker must see the same bytes after a restart.

The existing `documents.file_path` column stores a provider locator: a local
path or an S3 object key. Renaming the column would add a migration without
changing behavior, so the compatibility cost is accepted and documented. Keys
retain organization and knowledge-base prefixes, which makes cleanup and
incident inspection tenant-readable without treating key layout as an
authorization boundary.

Extractors receive a temporary local materialization from the provider rather
than an S3 client. PDF and DOCX libraries stay storage-agnostic, and temporary
files are deleted when extraction ends. Original-file responses continue to
pass through FastAPI instead of returning permanent public URLs, preserving the
existing JWT and membership checks. Short-lived signed URLs are a later scale
optimization, not the privacy model.

## ADR-049: Supabase as Managed Postgres, Not as a Second Backend

Status: Accepted

Supabase hosts the existing PostgreSQL schema and pgvector extension. FastAPI,
SQLAlchemy, Alembic, JWT authentication, authorization, and RLS session scope
remain authoritative; Supabase Auth and the generated Data API are not added as
parallel application paths. This avoids two identity systems and two places
where tenant rules could diverge.

Render connects through Supavisor session pooling on port `5432`, which is
reachable over IPv4 and preserves normal session semantics. Migrations use the
`postgres` owner connection while application traffic uses the non-owning
`supportmind_app` role from ADR-038. The public schema is otherwise visible to
Supabase's Data API, so Alembic explicitly revokes application-table privileges
from `anon`, `authenticated`, and `service_role`. S3 access keys are separate
server-side credentials and are never exposed to the browser.

## ADR-050: A Combined API and Worker Process Only for Render Free

Status: Accepted for the public demo; rejected as the production topology

Render does not offer free background-worker instances. To keep the public
portfolio demo deployable at zero hosting cost, one free Python web service
starts Uvicorn and one RQ worker as sibling processes. If either exits, the
wrapper stops the other so Render restarts a coherent pair. Alembic runs before
both because free services have no shell access and a fresh Supabase database
must be bootstrapped automatically.

This gives the service one shared CPU and memory budget, one scaling unit, and
no independent worker health control. Free Render Key Value is memory-only, so
a restart can discard queued jobs even though document rows and uploaded bytes
remain durable. Those are acceptable demo constraints and named in the deploy
guide. A paid deployment splits API and worker services, enables persistent
queue storage, runs migrations as a release step, and schedules the stale-work
sweep independently.
