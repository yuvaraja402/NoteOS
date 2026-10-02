# Backend

FastAPI for anonymous, device-scoped notes. Redis buffers edits and a worker
persists workspace documents to DynamoDB. No ORM, SQL migrations, or local
database fallback is included.

CI is validation-only. Tests and container builds do not provision AWS
or deploy the API. See the [release checklist](../infra/DEPLOYMENT.md) before
connecting to production resources; the AWS-backed runtime below is opt-in.

## Tests

From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-test.txt
python -m unittest discover -s tests
```

Tests inject service doubles at the AWS boundary. They do not create cloud
resources or start local database servers.

## Run with AWS

The frontend preview works on its own. Start the API only after the AWS resources
and SSM parameters are available and you have private network access to the
Redis endpoint (VPN, a development host in the VPC, or an equivalent approved path).

```bash
pip install -r requirements.txt
cp .env.example .env
# Set the Redis host and table name. Use your existing AWS profile.
set -a
source .env
set +a
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

TLS verification is always enabled for Redis. ECS uses its task role; direct
development uses the AWS credential chain. Secret values are read from SSM,
never passed in plaintext environment variables.

| Variable | Purpose |
| --- | --- |
| `NOTEOS_ENV` | `local`, `staging`, or `production`; controls cookie/CORS rules |
| `AWS_REGION` | Region, default `ca-central-1` |
| `DYNAMODB_TABLE_NAME` | Notes document table |
| `REDIS_HOST`, `REDIS_PORT` | Private ElastiCache primary endpoint and port |
| `REDIS_AUTH_TOKEN_SSM_PARAM` | Redis AUTH SecureString path |
| `SESSION_SIGNING_KEY_SSM_PARAM` | Device-cookie HMAC SecureString path |
| `CORS_ORIGINS` | Explicit allowed browser origins |
| `FLUSH_IDLE_SECONDS` | Idle write delay, default `60` |
| `FLUSH_MAX_SECONDS` | Maximum buffer window, default `300` |
| `FLUSH_POLL_SECONDS` | Worker polling interval, default `5` |
| `CACHE_TTL_SECONDS` | Clean workspace cache retention, default `86400` |

The signing key must have at least 32 bytes of random material. Rotating it
invalidates existing anonymous identities; keep it stable until a migration
strategy exists. Restart API tasks after changing runtime SSM secrets.

## API

All endpoints also accept the `/api` prefix for ALB routing:

- `GET /workspace`: notes, anonymous workspace identifier, buffered/persisted revisions.
- `GET /notes`: device-scoped note list.
- `PUT /notes/{uuid}`: idempotent create or replacement, used by the browser outbox.
- `POST /notes`: server-generated note ID.
- `PATCH /notes/{uuid}`: partial update.
- `DELETE /notes/{uuid}`: idempotent deletion.
- `GET /health`: runtime Redis connection health.

Writes return `X-NoteOS-Revision`. The client keeps drafts until the workspace's
persisted revision reaches that value. All note access is scoped by a signed
cookie; clients cannot choose a workspace ID. See [storage design](../infra/STORAGE.md).

Build from the repository root: `docker build -t noteos-api ./backend`.
