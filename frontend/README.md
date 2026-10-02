# Frontend

React/Next.js notes workspace on port `3050`.

CI is validation-only. Local builds do not publish or deploy; AWS
deployment remains disabled. See the [release checklist](../infra/DEPLOYMENT.md).

```bash
npm ci
npm run dev
```

Open http://localhost:3050. New sessions get three randomized starter notes.
Edits, colors, tags, and deletions work with no backend. Notes and the retry
outbox are stored in browser `sessionStorage`, not a local database. Refresh
preserves this tab's session; closing the tab clears session-only drafts.

When the cloud API is available, changes are sent after a 750ms debounce,
with a two-second maximum browser-side wait. The UI distinguishes:

- `Saved in this tab`: not yet acknowledged by the cloud API.
- `Buffered in cloud`: accepted by Redis, awaiting DynamoDB.
- `Saved to cloud`: DynamoDB has confirmed the revision.

The browser keeps unpersisted recovery copies and retries idempotently.
Other tabs on the same device share the signed cookie, while their editing
outboxes are separate. Concurrent edits to the same note use last-write-wins.

Copy `.env.example` to `.env.local` only to change `API_INTERNAL_URL`.
It is server-side configuration and must not contain credentials.
Local `/api/*` requests use the Next.js proxy, which forwards the signed cookie
and revision acknowledgement. AWS ALB routes `/api/*` directly to FastAPI.

```bash
npm run lint
npm run build
```

Build from the repository root: `docker build -t noteos-web ./frontend`.
No frontend AWS credentials, SSM permissions, or `NEXT_PUBLIC_*` secrets are used.
