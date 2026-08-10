# Knowledge Bases and Document Uploads

## Knowledge Bases

A knowledge base is an organization-owned collection of related support
material, such as product documentation, policies, or internal procedures.
Names are unique within one organization. Members can list and view knowledge
bases, while only owners and admins can create them.

Every knowledge-base query includes `organization_id`. Looking up a knowledge
base by its ID alone is insufficient because every tenant boundary must remain
explicit.

## Upload Flow

Owners and admins upload a file using multipart form data. The API validates
the knowledge base against the organization, checks the declared MIME type and
matching extension, enforces the configured size limit, and streams the file
through the configured storage provider. It generates a UUID-based server name
and keeps the safe original basename in the database.

Supported types are:

- PDF: `application/pdf` and `.pdf`
- Plain text: `text/plain` and `.txt`
- Markdown: `text/markdown` and `.md` or `.markdown`
- Word: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  and `.docx`

The default maximum upload size is 10 MB. The request is staged in a temporary
file while its size is checked, so the API does not hold the whole document in
memory.

## Storage Providers

`STORAGE_BACKEND=local` is the development default. Files are stored at:

```text
storage/uploads/{organization_id}/{knowledge_base_id}/{generated_filename}
```

`STORAGE_BACKEND=s3` stores the same tenant-qualified locator in a private
S3-compatible bucket. The deployment guide uses Supabase Storage's S3 endpoint.
The database column remains named `file_path` for compatibility, but its value
is a provider locator: a path for local storage or an object key for S3.

Objects remain private. Authenticated members read originals through the API's
`GET /documents/{document_id}/file` endpoint, which performs the same membership
check for either provider and streams the bytes with `private, no-store` cache
headers. No public bucket or permanent public URL is required.

Required S3 settings are:

```env
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://PROJECT_REF.storage.supabase.co/storage/v1/s3
S3_REGION=YOUR_SUPABASE_STORAGE_REGION
S3_BUCKET=supportmind-documents
S3_ACCESS_KEY_ID=YOUR_S3_ACCESS_KEY
S3_SECRET_ACCESS_KEY=YOUR_S3_SECRET
S3_PREFIX=uploads
```

## Document Lifecycle

Uploading creates only the file and its document metadata row:

- `pending`: uploaded and waiting for preparation
- `processing`: text extraction and embedding work are running
- `processed`: text chunks exist and are waiting for embeddings
- `indexed`: chunks and embeddings are ready for retrieval
- `failed`: preparation stopped and `error_message` explains why

Upload is intentionally separate from preparation. The HTTP request finishes
after durable file and metadata storage. The user-facing prepare endpoint then
queues extraction and indexing as one RQ job.

## Authorization and Isolation

All document queries are scoped directly by `organization_id`. Members may list
and view metadata. Only owners and admins may upload or delete. A knowledge base
or document from another organization is never returned through a mismatched
organization path, and non-members receive the same `404` used for an unknown
organization.

## Future Improvements

- Direct, short-lived signed uploads for large files
- Malware and virus scanning
- File signature inspection instead of relying only on MIME type and extension
- Checksums, deduplication, versioning, and retention policies
- Storage lifecycle rules and backup/restore exercises
