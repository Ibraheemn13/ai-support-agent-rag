# Frontend v1

## Goal

Frontend v1 turns the working multi-tenant RAG API into a complete, usable product flow. An authenticated user can enter an organization workspace, create and manage knowledge bases, upload and process documents, and ask grounded questions whose answers include source citations.

This milestone is intentionally focused. It provides a professional dashboard for the capabilities already supported by the backend; it does not add billing, invitations, analytics, advanced settings, streaming, or agent orchestration.

## Technology Stack

- Next.js with the App Router
- React and TypeScript
- Tailwind CSS for layout and visual tokens
- Reusable shadcn/ui-style primitives for buttons, inputs, cards, dialogs, menus, badges, skeletons, alerts, and forms
- TanStack Query for API-backed server state and mutations
- React Hook Form with Zod validation
- Axios through a shared API client
- Lucide icons where an icon improves navigation or comprehension
- Sonner for action feedback

## UI and UX Principles

The interface follows a restrained SaaS design system:

- Neutral surfaces, strong contrast, and a single restrained accent color
- Clear type hierarchy, predictable spacing, consistent borders, and modest corner radii
- Subtle or no shadows instead of decorative depth effects
- No ornamental gradients, glass effects, emoji decoration, or heavy animation
- Reusable interaction patterns for forms, actions, status, errors, and empty data
- Visible loading, disabled, success, empty, and failure states
- Plain-language action labels and backend errors
- Semantic color only where status needs it, such as `indexed` or `failed`
- Content widths that remain readable while allowing the chat workspace to use more horizontal space

The UI renders data returned by the API. It does not use fake production records or simulated chat messages.

## Routing Structure

Public routes:

| Route | Purpose |
| --- | --- |
| `/login` | Authenticate an existing user |
| `/register` | Create a user account |

Protected routes use the dashboard application shell:

| Route | Purpose |
| --- | --- |
| `/dashboard` | Workspace overview, counts, and quick actions |
| `/dashboard/knowledge-bases` | List and create knowledge bases |
| `/dashboard/knowledge-bases/[knowledgeBaseId]` | View one knowledge base, upload documents, and run ingest/index actions |
| `/dashboard/documents` | View organization documents and their processing state |
| `/dashboard/chat` | Choose a knowledge base, start or select a conversation, and chat |
| `/dashboard/conversations/[conversationId]` | Load saved messages, review citations, and continue a conversation |

The protected layout provides the desktop sidebar, responsive mobile navigation, organization selector, and account/logout controls. Settings appears only as a disabled future destination.

## Page Structure

### Authentication

Login and registration use compact, validated forms in a centered desktop card and a comfortable full-width mobile layout. Successful authentication stores the access token and sends the user to the dashboard. Invalid credentials and validation errors remain visible and readable.

### Overview

The overview shows counts for knowledge bases, documents, indexed documents, and conversations. Quick actions lead to knowledge-base creation, document upload, and chat. When the organization has no content, the page explains the first useful step instead of presenting empty metric chrome.

### Knowledge Bases

The list page loads the current organization's knowledge bases and supports creation through a validated dialog. Cards show each knowledge base's name, description, creation date when supplied by the API, and a direct link to its detail page.

The detail page shows the selected knowledge base and its documents. It also explains the document lifecycle:

```text
upload -> ingest -> index -> chat
```

Available actions depend on document status and are disabled while a mutation is running.

### Documents

The organization document view includes document title, knowledge base, upload date, status, and relevant actions. It uses a table at larger breakpoints and stacked document cards on small screens so controls do not cause horizontal overflow.

Status presentation covers:

- `pending`
- `processing`
- `processed`
- `indexed`
- `failed`

### Chat and Conversation Detail

The chat page requires an organization and knowledge base. A user can create a conversation or select an existing one, submit a question, and see the persisted user and assistant messages.

User and assistant messages have distinct but restrained presentation. Assistant messages render a collapsible citation section beneath the answer. Its responsive citation cards contain the source document title, retrieved quote, and relevance score when returned by the backend.

The conversation detail route reloads saved messages and their citations from the API, then allows the user to continue within the same conversation. A no-context answer is shown as a neutral grounded outcome, not as an application failure.

## API Client Structure

Frontend API access is kept outside page components:

```text
src/lib/api/
|-- client.ts
|-- auth.ts
|-- organizations.ts
|-- knowledge-bases.ts
|-- documents.ts
`-- conversations.ts
```

Responsibilities are split as follows:

- `client.ts` owns the Axios instance, base URL, bearer-token attachment, common error extraction, and unauthorized handling.
- `auth.ts` implements registration, login, and current-user requests.
- `organizations.ts` implements organization listing and creation.
- `knowledge-bases.ts` implements organization-scoped knowledge-base requests.
- `documents.ts` implements upload, list/detail, ingestion, and indexing requests.
- `conversations.ts` implements conversation creation/list/detail and RAG message requests.

The base URL comes from:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

TanStack Query owns API-backed state for the current user, organizations, knowledge bases, documents, conversations, and conversation details. Mutations invalidate only the affected query keys after successful writes.

All tenant-owned requests include the selected `organization_id`, and knowledge-base or conversation requests include their scoped resource IDs. The frontend's selection controls improve usability, but backend membership checks and tenant filters remain the security boundary.

## Authentication and Token Handling

For this MVP, the browser stores the backend JWT in `localStorage`. The shared Axios client attaches it as:

```http
Authorization: Bearer <access_token>
```

Logout removes the token and returns the user to login. When a protected request returns `401 Unauthorized`, the client clears the stale token and redirects to login where browser navigation is available. The protected layout also prevents unauthenticated dashboard use.

`localStorage` is a deliberate MVP tradeoff, not the recommended production design. A production deployment should prefer server-managed, `Secure`, `HttpOnly`, appropriately scoped cookies with CSRF protection. That reduces the ability of injected browser scripts to read session credentials.

## Responsive Design

The implementation is mobile-first and targets practical use at 360 px, 768 px, 1024 px, and 1440 px widths.

- The fixed 256 px desktop sidebar becomes a dialog-based navigation drawer below the `lg` breakpoint.
- Page grids collapse to one column before controls become cramped.
- Document tables become stacked cards on mobile.
- Forms use full-width controls at narrow widths.
- Long titles, filenames, message text, and citation quotes wrap instead of widening the viewport.
- Chat input controls remain usable at mobile width.
- Citation grids collapse to one column on mobile and remain beneath their assistant message.
- Main pages use bounded content containers; chat uses a wider container with readable message measures.

## Component Structure

```text
src/components/
|-- ui/          # Shared shadcn/ui-style primitives
|-- layout/      # AppShell, SidebarNav, TopBar
|-- common/      # PageHeader, EmptyState, ErrorState, status and loading UI
|-- chat/        # ChatMessage, CitationCard, ChatInput
|-- documents/   # Responsive document views, upload, and status actions
|-- kb/          # Knowledge-base cards and create form
`-- organizations/ # Organization creation
```

Reusable product components include:

- `AppShell`
- `SidebarNav`
- `TopBar`
- `PageHeader`
- `EmptyState`
- `ErrorState`
- `LoadingSkeleton`
- `StatusBadge`
- `CitationCard`
- `ChatMessage`
- `ChatInput`
- `DocumentList`
- `DocumentCard`
- `DocumentUploadForm`
- `DocumentStatusActions`
- `KnowledgeBaseCard`
- `KnowledgeBaseForm`

Pages compose these components and query hooks rather than duplicating API or presentation logic.

## Local Configuration

Create the frontend environment file:

```powershell
Copy-Item frontend/.env.example frontend/.env.local
```

The local default is:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

The backend development configuration uses:

```env
FRONTEND_ORIGIN=http://localhost:3000
```

FastAPI always enables narrowly scoped CORS middleware. The configured frontend
origin is the sole allowed origin; the API is not opened to `*`. Outside local
development, startup fails when `FRONTEND_ORIGIN` is empty so a broken deploy is
visible immediately. If the frontend URL changes, update it to the exact browser
origin and restart the API.

## Manual Test Flow

Start PostgreSQL, run migrations, start the FastAPI backend, then start the frontend. In the browser:

1. Open `http://localhost:3000/register`.
2. Register a new user and confirm the dashboard opens after authentication.
3. Create an organization if the account does not already have one.
4. Use the organization selector to make that workspace active.
5. Open **Knowledge Bases** and create a knowledge base.
6. Open the knowledge-base detail page.
7. Upload a small text document containing a policy with a clearly testable answer.
8. Confirm the document appears with its backend status.
9. Ingest the document and wait for `processed`.
10. Index the document and wait for `indexed`.
11. Open **Chat**, select the indexed knowledge base, and create a conversation.
12. Ask a question answered by the uploaded text.
13. Confirm the user message and grounded assistant answer appear.
14. Confirm at least one citation shows the correct document title and supporting quote.
15. Open the saved conversation route and confirm messages and citations reload.
16. Refresh the browser and confirm the authenticated application can restore its API state.
17. Log out and confirm protected dashboard routes return to login.
18. Repeat key views at 360 px and 768 px in browser responsive mode and confirm there is no horizontal overflow.

For a no-context case, ask a question that the indexed document cannot answer. The assistant should return the backend's safe insufficient-context response with no fabricated citation.

## Current Limitations

- JWT storage uses `localStorage`, not production-grade cookie sessions.
- No streaming chat response.
- No reranking controls or retrieval tuning UI.
- No conversation-memory summarization.
- No tool use or LangGraph orchestration.
- No billing, team invitations, analytics, advanced settings, or role-management UI.
- No human escalation or support-ticket workflow.
- No offline mode or optimistic message queue.
- No automated end-to-end browser suite yet.

## Future Improvements

- Move authentication to secure server-managed `HttpOnly` cookies.
- Stream assistant responses while preserving final persisted citations.
- Add stronger keyboard focus management and automated accessibility checks.
- Add Playwright end-to-end coverage for the complete upload-to-chat flow.
- Add document previews and richer supported-file feedback.
- Add reranking diagnostics and retrieval-quality controls.
- Add conversation-memory summarization.
- Add LangGraph when the RAG flow requires branching, tools, or human handoffs.
- Add human escalation and support-ticket creation.
- Move ingestion and indexing to a durable RQ or Celery worker.
- Add observability for frontend errors, API latency, retrieval, model calls, and trace correlation.
