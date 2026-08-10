# Deploying SupportMind with Supabase and Render

This guide deploys the portfolio demo with services that can all start on free
instance types:

- Supabase Postgres with pgvector
- A private Supabase Storage bucket through its S3-compatible API
- Render Key Value for the RQ queue and rate limiter
- One Render web service running FastAPI and one RQ worker
- One Render web service running Next.js

This is a demo topology. Render's free plan does not offer free background
workers, so the API and worker deliberately share one web service. A paid
deployment should split them.

## 1. Push the Repository

Render deploys from GitHub, so commit the deployment changes and push them:

```powershell
git add .
git commit -m "Add Supabase and Render deployment"
git push origin main
```

If you deploy another branch, select that branch when creating the Render
Blueprint.

## 2. Create the Supabase Project

1. Create a project at `supabase.com/dashboard`.
2. Pick a region reasonably close to Render's `Oregon` region.
3. Save the project reference and database password in a password manager.
4. Open **Connect** and select the **Session pooler** connection string.

Render is IPv4-based, so use the Supavisor session pooler on port `5432`, not
the direct database hostname. Add SQLAlchemy's driver and require TLS:

```text
postgresql+psycopg://postgres.PROJECT_REF:DB_PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres?sslmode=require
```

This owner connection becomes `MIGRATION_DATABASE_URL`. Copy the exact host and
project reference shown by Supabase instead of typing them from the template.
Percent-encode special characters in URL passwords.

## 3. Choose the Application Database Password

Generate a different, URL-safe secret for the non-owning application role. A
32-character letters-and-digits value avoids URL-encoding mistakes. Call it
`APP_DB_PASSWORD`.

The migrations create the `supportmind_app` login role and grant only the
database privileges the backend needs. Build its pooled URL from the same
Supabase connection details:

```text
postgresql+psycopg://supportmind_app.PROJECT_REF:APP_DB_PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres?sslmode=require
```

This becomes `DATABASE_URL`. Do not use the owner URL for normal application
traffic: the owner can bypass row-level-security policies.

The application role does not exist yet. That is expected. `start-render.sh`
runs Alembic with the owner URL before starting the API or worker.

## 4. Create Private Object Storage

1. In Supabase, open **Storage** and create a bucket named
   `supportmind-documents`.
2. Leave **Public bucket** disabled.
3. Open the project's Storage S3 settings and generate an S3 access-key pair.
4. Record the endpoint, region, access key ID, and secret immediately.

The endpoint has this shape:

```text
https://PROJECT_REF.storage.supabase.co/storage/v1/s3
```

These S3 keys bypass Storage RLS and can access every bucket, so they belong
only in the Render backend environment. Never put them in a `NEXT_PUBLIC_*`
variable or commit them to Git.

## 5. Create the Render Blueprint

1. Sign in to Render and choose **New > Blueprint**.
2. Connect the GitHub repository.
3. Render detects the root `render.yaml`.
4. Give the Blueprint a name and apply it.

The Blueprint creates:

- `supportmind-redis`: free Render Key Value
- `supportmind-api`: free Python web service
- `supportmind-web`: free Node web service

Render prompts for every value marked `sync: false`. Enter:

| Service | Variable | Value |
| --- | --- | --- |
| API | `FRONTEND_ORIGIN` | `https://supportmind-web.onrender.com` initially |
| API | `MIGRATION_DATABASE_URL` | Supabase owner session-pooler URL |
| API | `DATABASE_URL` | `supportmind_app` session-pooler URL |
| API | `APP_DB_PASSWORD` | Exact application-role password chosen above |
| API | `S3_ENDPOINT_URL` | Endpoint copied from Supabase Storage S3 settings |
| API | `S3_REGION` | Region copied from Supabase Storage S3 settings |
| API | `S3_BUCKET` | `supportmind-documents` |
| API | `S3_ACCESS_KEY_ID` | Generated Supabase S3 access key |
| API | `S3_SECRET_ACCESS_KEY` | Generated Supabase S3 secret |
| API | `OPENAI_API_KEY` | Your server-side OpenAI API key |
| Web | `NEXT_PUBLIC_API_BASE_URL` | `https://supportmind-api.onrender.com` initially |

The two suggested URLs are correct when Render accepts those exact service
names. If Render adds a suffix or you rename a service, use the actual URLs in
the next step.

## 6. Correct the Cross-Service URLs

After Render has created both web services, copy their actual public URLs.

1. In `supportmind-api`, set `FRONTEND_ORIGIN` to the exact frontend origin,
   with no trailing slash.
2. In `supportmind-web`, set `NEXT_PUBLIC_API_BASE_URL` to the exact API origin,
   with no trailing slash.
3. Redeploy both services.

`NEXT_PUBLIC_API_BASE_URL` is embedded during the Next.js build, so the
frontend must rebuild after that value changes. The API validates production
CORS configuration at startup and refuses the known development JWT secret.

## 7. Watch the First Backend Deploy

The API start script performs these operations in order:

1. `python -m alembic upgrade head`
2. Start `python worker.py`
3. Start Uvicorn on Render's assigned `PORT`

The migration creates the `vector` extension, all tables and indexes, the
non-owning application role, row-level-security policies, and the Supabase
Data API privilege restrictions. A healthy startup log should report row-level
security as `enforced`, not `bypassed`.

Open:

```text
https://YOUR-API.onrender.com/health
https://YOUR-API.onrender.com/docs
```

`/health` should report `status: ok` and `queue: available`. A degraded queue
means `REDIS_URL` was not wired to Render Key Value or that service is
temporarily unavailable.

## 8. Verify Supabase

Run these read-only statements in Supabase's SQL editor:

```sql
SELECT extname
FROM pg_extension
WHERE extname = 'vector';

SELECT version_num
FROM alembic_version;

SELECT rolname, rolsuper, rolbypassrls
FROM pg_roles
WHERE rolname = 'supportmind_app';

SELECT relname, relrowsecurity, relforcerowsecurity
FROM pg_class
WHERE relname IN (
  'knowledge_bases', 'documents', 'document_chunks', 'conversations',
  'messages', 'message_citations', 'message_feedback',
  'organization_usage_days'
)
ORDER BY relname;

SELECT
  has_table_privilege('anon', 'public.users', 'SELECT') AS anon_users,
  has_table_privilege('authenticated', 'public.documents', 'SELECT')
    AS authenticated_documents,
  has_table_privilege('service_role', 'public.messages', 'SELECT')
    AS service_messages;
```

Expected results:

- `vector` exists.
- Alembic is at `20260809_0008` or a later revision.
- `supportmind_app` is neither superuser nor `BYPASSRLS`.
- Both RLS columns are true for every listed tenant table.
- All three Data API privilege checks are false because FastAPI is the only
  public data boundary.

## 9. Test the Product

1. Open the Render frontend URL.
2. Register a new account.
3. Create a workspace and knowledge space.
4. Upload a small TXT, Markdown, PDF, or DOCX document.
5. Click **Prepare for chat** and wait for the status to become ready.
6. Ask a question answered by that document and open its source.
7. In Supabase Storage, confirm an object exists below
   `uploads/{organization_id}/{knowledge_base_id}/`.
8. In Supabase Table Editor, confirm the document is `indexed` and its chunks
   have embeddings.

## Free-Plan Limits

This setup can run without a monthly hosting charge, but it is not production
infrastructure:

- Render free web services sleep after 15 minutes without inbound traffic and
  can take roughly a minute to wake.
- Render's free filesystem is ephemeral. SupportMind therefore stores uploads
  in Supabase rather than on the web-service disk.
- The two Render web services share the workspace's monthly free instance-hour
  allowance.
- Free Render Key Value is memory-only. A restart can lose queued jobs and
  rate-limit counters; upload metadata and files remain safe in Supabase, but a
  pending document may need **Prepare for chat** clicked again.
- Supabase free projects have usage limits and may pause after inactivity.
- OpenAI API usage is separate and billable. Keep the daily token budget and
  rate limits enabled.

For a real production deployment, use a paid worker, persistent Key Value,
backups, scheduled `sweep.py`, monitoring, and separate staging/production
projects.

## Troubleshooting

**Database connection fails.** Use the Supabase session pooler on port `5432`,
copy its host exactly, and percent-encode password characters. Confirm that
`MIGRATION_DATABASE_URL` uses `postgres.PROJECT_REF` while `DATABASE_URL` uses
`supportmind_app.PROJECT_REF`.

**The backend fails before Uvicorn starts.** Read the migration error in the
Render logs. Free web services have no shell access, so fix the environment
value and redeploy; migrations are safe to run again.

**The browser reports CORS errors.** Set `FRONTEND_ORIGIN` to the exact Render
frontend origin, with no path or trailing slash, then redeploy the API.

**Uploads return 503.** Confirm the bucket is present and private, and recopy
all four S3 endpoint/region/credential values from Supabase.

**Documents remain uploaded or processing.** Confirm `/health` reports the
queue available and that the API logs contain the RQ worker startup line. A
free Key Value restart can discard queued work; submit preparation again after
the document is no longer claimed, or upgrade and schedule the stale sweep.

**The frontend still calls localhost or an old API.** Update
`NEXT_PUBLIC_API_BASE_URL` and trigger a new frontend deploy; this is a build
time variable.
