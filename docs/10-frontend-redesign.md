# Frontend Redesign

This document covers the second frontend, which replaced Frontend v1. It explains what was wrong with the first version, what the product looks like now, and which parts are deliberately unfinished.

Decisions are recorded as ADR-023 through ADR-032 in [06-decisions.md](06-decisions.md).

## Why the redesign happened

Frontend v1 was a working, competent CRUD interface over the API. That was the problem: it was an interface over the API rather than over the product.

The flow read as: log in, create an organization, create a knowledge base, upload a document, click Ingest, wait, click Index, wait, open chat, create a conversation, ask a question. Nine steps, of which four exist only because the backend is built that way. The interface used the backend's vocabulary directly — `organization_id`, ingest, index, knowledge base, citations — so understanding it required understanding retrieval-augmented generation first.

Three specific failures:

1. **Backend concepts were the user's problem.** Ingestion and indexing are two operations because they have independent failure modes and different dependencies. That is a good backend design and a bad interface. The user's goal is "make this document answerable", which is one intention.
2. **There was no first-run experience.** A new account landed on a dashboard with four zeroed counters and no obvious first move.
3. **There was no product identity.** The root route redirected to the dashboard, so an unauthenticated visitor met a login form with no explanation of what they were logging into.

The redesign keeps the backend's design and changes what the user is asked to understand.

## Terminology mapping

The API is unchanged. The interface translates.

| Backend concept | Product term |
| --- | --- |
| Organization | Workspace |
| Knowledge Base | Knowledge Space |
| Document Upload | Add Knowledge |
| Ingestion | Processing |
| Indexing | Preparing for chat |
| Indexed document | Ready |
| RAG Chat | Ask AI |
| Citations | Sources |
| Conversation | Chat thread |

Document status labels:

| Backend status | UI label | Meaning shown to the user |
| --- | --- | --- |
| `pending` | Uploaded | Stored and waiting to be prepared |
| `processing` | Processing | Reading the file and splitting it into passages |
| `processed` | Extracted | Text extracted, preparing it for chat |
| `indexed` | Ready | The assistant can answer from this document |
| `failed` | Failed | Something went wrong; can be retried |

This table is not a convention that reviewers enforce. It lives in `frontend/src/lib/terminology.ts` as a single descriptor table, and components derive labels, badge tones, timeline position, and polling decisions from it. `StatusBadge` does not know what `indexed` means; it asks. A rename is one edit.

Raw identifiers never appear in normal UI. Where a name is needed — a document's knowledge space, a chat thread's knowledge space — the client resolves it from a list it already holds in cache rather than displaying a UUID.

## User flow

```
Landing page → Sign up / Log in → Onboarding → Dashboard → Add knowledge → Ask AI
```

A returning user with a workspace and a knowledge space skips onboarding and goes straight to the dashboard.

## Landing page

`/` is a marketing page rather than a redirect. Sections in order: header, hero with the product preview, the problem, how it works, features, use cases, call to action, footer.

The header is auth-aware — signed-in visitors see "Go to dashboard" instead of sign-in and sign-up. The product preview in the hero is a static illustration of an answer with its sources, labelled "Example" so it cannot be mistaken for live state.

## Onboarding

Four steps, each wired to real endpoints, at `/onboarding`:

1. **Create your workspace** — `POST /api/v1/organizations`
2. **Create your first knowledge space** — asks what the assistant will help with (customer support, product documentation, internal team knowledge, policies and FAQs) and seeds a name and description from the answer. `POST /api/v1/organizations/{id}/knowledge-bases`
3. **Add your first document** — upload, then preparation starts automatically with a visible status timeline
4. **Ask your first question** — sample prompts, a real question against the real document, and the answer with its sources

Users without a workspace or knowledge space are routed here from the dashboard. The check runs **on entry only**: creating a knowledge space at step 2 satisfies the condition that sent the user here, and re-evaluating it would eject them before steps 3 and 4. There is a "Skip setup" escape hatch once a workspace exists.

## Dashboard

- **Setup checklist** while incomplete, replaced by "Your assistant is ready" when done. Only the next incomplete step gets a button — four competing calls to action is a menu, not guidance.
- **Stats**: knowledge spaces, documents, ready for chat, chat threads
- **Recent documents** with status badges and relative timestamps
- **Recent chats** with the last message preview and the knowledge space name
- **Quick actions**: add document, ask AI, create knowledge space. "Ask AI" is disabled with an explanation until at least one document is ready.

## The "Prepare for chat" flow

This is the redesign's central interaction. The user sees one action. Behind it:

1. `POST /api/v1/organizations/{id}/documents/{id}/prepare` returns `202`
2. The backend extracts text and creates chunks
3. If extraction produced chunks, it embeds and indexes them
4. The client polls the document until it reports `indexed` or `failed`

The chaining is server-side (ADR-025). Orchestrating it in the browser would mean the sequence breaks if the tab closes between the two calls.

Progress is a four-step timeline, not a spinner. A failure renders as an interruption at the step that was reached, with the backend's error message and a retry that forces re-preparation — `failed` is not a stage users pass through on the way to anywhere, so it is not a fifth step.

Two details worth knowing:

- **Polling continues in the background.** TanStack Query pauses `refetchInterval` when the tab loses focus. Preparation takes long enough that people switch away, and without `refetchIntervalInBackground` they return to a timeline frozen mid-progress.
- **`409` is not an error.** It means the document is already being prepared or already ready. Polling will show the real outcome, so the client stays quiet rather than showing a toast for something the user did not get wrong.

## Chat

Desktop is three columns: thread list, conversation, sources panel. Below `xl` the side panels collapse and sources move inline underneath each answer, where they are collapsible.

- Only knowledge spaces with at least one ready document are selectable. Offering the others would produce confident "I don't know" answers.
- A thread is created lazily on the first question, so an abandoned "new chat" never leaves an empty thread behind.
- Sources are labelled "Sources" and show the document title and the passage. The similarity score is available but off by default: a cosine similarity means little to a reader without context.
- If nothing is ready, the page says so and links to adding knowledge rather than presenting an input that cannot work.

## Responsive approach

Four breakpoints are treated as requirements: 360, 768, 1024, 1440.

- The sidebar becomes a drawer below `lg`
- The documents table becomes stacked cards below `xl`, not `lg`, because the fixed 240px sidebar leaves roughly 736px of content at 1024px and the table's 832px minimum would scroll sideways
- Chat side panels collapse below `xl`; the input stays in the viewport at every width
- Cards stack; the dashboard stat grid steps 1 → 2 → 2 → 4

Verification is by measurement, not inspection: each page is loaded at each width and every element's right edge is compared against the viewport. That is how the 1024px table issue was found — the page looked fine because the table scrolled inside its own container rather than overflowing the document.

## Visual identity

A later pass replaced the neutral palette with a designed one. Structure, routing, and component logic were untouched; what changed is how it looks. Decisions are in [ADR-046](06-decisions.md).

- **One accent, burnt terracotta** (`#b4471f` light, `#e8734a` dark), on primary actions, active navigation, section eyebrows, and the hero diagram. The status ramps were moved away from it — success olive, warning gold, danger crimson — because terracotta otherwise sits between amber and red and makes three meanings look like three shades of the brand.
- **Fraunces on headings only**: the hero, marketing section headings, and in-app page titles. Everything denser stays on the UI sans.
- **A hero diagram** of several documents converging into one cited answer, drawn from tokens so dark mode repaints it rather than needing a second asset.
- **A mark** of three bars resolving into a dot — the hero diagram at 32×32 — with the same geometry in `app/icon.svg` for the favicon.
- **Dark mode** via `next-themes`, class strategy, system default, persisted. The two palettes were designed together; dark is not an inversion.
- **`.on-ink`** is a token scope for the two bands that are dark in both themes. Children read the tokens they always read and get values that are correct against ink, instead of overriding classes at each call site.

Contrast is enforced rather than eyeballed: `npm run check:contrast` parses the tokens out of `globals.css` and asserts WCAG AA over both themes, failing the command if any pair drops below its floor.

## Component structure

```
frontend/src/
  components/
    layout/      app-shell, dashboard-shell, sidebar, top-bar, workspace-switcher
    marketing/   landing-header, hero, product-preview, feature-grid, use-cases, ...
    onboarding/  onboarding-flow, onboarding-stepper, step-*
    dashboard/   setup-checklist, stat-cards, recent-documents, recent-chat-threads, quick-actions
    knowledge/   knowledge-space-card, create-knowledge-space-dialog
    documents/   document-dropzone, document-status-timeline, document-table, document-mobile-card, document-actions
    chat/        chat-message, chat-input, source-card, thread-list, knowledge-space-select
    settings/    settings-section, workspace-settings-form
    common/      page-header, empty-state, error-state, loading-skeleton, status-badge
    ui/          shadcn-style primitives
  hooks/         use-auth (via context), use-workspace, use-documents, use-chat,
                 use-dashboard-data, use-document-preparation, use-onboarding-status, use-is-hydrated
  lib/
    api/         client, auth, organizations, knowledge-bases, documents, conversations
    auth/        token, auth-context, post-auth-route
    terminology.ts
  types/         api, auth, workspace, knowledge, document, conversation
```

Domain types live in `types/` and are named for product concepts (`Workspace`, `KnowledgeSpace`, `ChatThread`, `Source`). The API modules import them and re-export their previous names, so the rename was not a breaking change for callers.

## API integration

All network access goes through `lib/api/client.ts`. It reads `NEXT_PUBLIC_API_BASE_URL`, attaches the bearer token, normalizes FastAPI's error shapes into readable messages, and on `401` clears the token and redirects to login with a `returnTo` parameter. Components never call `fetch` directly.

Server state is TanStack Query. Cache keys are centralized in `lib/query-keys.ts`.

Endpoints added during the redesign:

- `POST /api/v1/organizations/{id}/documents/{id}/prepare` — extraction and indexing in one step (ADR-025)
- `PATCH /api/v1/organizations/{id}` — rename a workspace, owners and admins only

Response fields added:

- Knowledge bases: `document_count`, `ready_document_count`
- Conversations: `message_count`, `last_message_preview`

### Session handling

The token is in `localStorage` (ADR-021). Writes publish an event that `useSyncExternalStore` observes, so a sign-in or sign-out in one place updates everything, including in another tab.

One subtlety worth recording: the first client render reuses the server snapshot, where no token can exist. Without a hydration flag a signed-in user looks signed out for exactly one render — long enough for a route guard to redirect them to login on every reload. `useIsHydrated` makes the session report `loading` rather than `unauthenticated` until storage has actually been read.

## Known limitations

The whole list, frontend and backend, with the phase that closes each one. Later
phases update the Status column rather than leaving stale entries behind.

Severity: **B** blocks deployment · **S** security · **R** reliability ·
**C** scale · **Q** retrieval quality · **P** product · **E** engineering.

| # | Sev | Limitation | Closed by | Status |
| --- | --- | --- | --- | --- |
| 1 | B | CORS middleware only registers when `APP_ENV` is a local value, so a deployed frontend is blocked by the browser | 18 | Open |
| 2 | B | Uploads written to the container filesystem, which is ephemeral on most hosts. Now also user-visible: viewing a document's original file depends on it (ADR-047) | 18 | Open |
| 3 | B | JWT secret falls back to a known default instead of failing loudly | 18 | Open |
| 4 | S | Tokens in `localStorage`; an XSS bug becomes a session compromise (ADR-021) | 13 | Open |
| 5 | S | Sessions expire hard at 60 minutes with no refresh | 13 | Accepted tradeoff |
| 6 | S | No rate limiting: login is brute-forceable and chat spend is uncapped | 13 | Open |
| 7 | S | No email verification or password reset | — | Won't do for now |
| 8 | S | Tenant isolation enforced in application queries, not Postgres RLS (ADR-001) | 13 | Open |
| 9 | R | `BackgroundTasks` are not durable; a restart strands a document in `processing` | 12 | Closed |
| 10 | R | No retry or backoff when the embedding provider fails | 12 | Closed |
| 11 | R | Status is polled every 1.5s and gives up after 2 minutes, rather than pushed | — | Deferred |
| 12 | C | No pagination on documents, knowledge spaces, threads, or messages | 14 | Open |
| 13 | C | Document search and filtering happen client-side | 14 | Open |
| 14 | C | Nothing can be deleted: documents, knowledge spaces, or workspaces | 14 | Open |
| 15 | Q | Vector-only retrieval; no keyword or BM25 hybrid | 15 | Open |
| 16 | Q | No re-ranking of retrieved chunks | 15 | Open |
| 17 | Q | Naive character-window chunking splits mid-table and mid-list | 15 | Open |
| 18 | Q | No evaluation harness, so retrieval changes cannot be measured | 15 | Open |
| 19 | Q | Answers are not streamed; a slow model reads as a hang | — | Deferred |
| 20 | Q | Sources are not deduplicated across chunks of the same document | 15 | Open |
| 21 | P | No team management UI, although roles exist in the schema and API | — | Won't do for now |
| 22 | P | Account details are read-only; no name, email, or password changes | — | Won't do for now |
| 23 | P | No light/dark theme switching, although the tokens support it | Visual identity | Closed |
| 24 | P | No copy, regenerate, edit, or delete on chat messages | — | Won't do for now |
| 25 | E | Frontend had no automated tests | 11 | Closed |
| 26 | E | No CI, so tests run only when invoked locally | 11b | Closed |
| 27 | E | No structured logging, metrics, tracing, or error reporting | 17 | Open |
| 28 | E | No cost controls on OpenAI usage | 17 | Open |
| 29 | E | Accessibility not formally audited; ARIA, skip links, and focus states are in place but unverified by a screen reader or axe | — | Deferred |

Three entries are worth expanding, because the reasoning matters more than the
one-line summary.

**Item 5, the 60-minute session, is an accepted tradeoff rather than an
oversight.** Refresh tokens were considered and deliberately skipped: the cost
is a mid-task logout during a long session, the benefit is not building token
rotation and revocation for a project with no production users. ADR in Phase 13
will record it.

**Items 25 and 26 closed in Phases 11 and 11b.** The frontend now has 41 Vitest tests covering
the terminology module and API client, plus one Playwright flow covering signup
through to a sourced answer. Overall unit coverage is intentionally low; see
"Testing strategy" in the README. CI runs the cheap suites on every push; the
end-to-end flow is triggered manually because each run costs real API credit.

**Items 7, 21 to 24, and 29 are marked "won't do for now" rather than "open".**
They are real gaps, but they demonstrate no system-design thinking a reviewer
would probe, and the time is better spent on durability, isolation, and
retrieval quality.

## Future improvements

In rough order of value:

1. Stream chat answers token by token
2. Replace polling with server-sent events for document status
3. Move sessions to `HttpOnly` cookies and add refresh
4. Add Playwright coverage of the onboarding and ask-a-question flows
5. Paginate documents and move search server-side
6. Durable background workers so preparation survives a restart
7. Workspace members and invitations, which the data model already supports
8. The two settings sections currently marked "Coming later": API keys and model configuration
