# Backend

FastAPI service for note CRUD. Docker Compose uses Postgres; direct local
development can use SQLite. AWS uses RDS and SSM.

## Run locally

From this directory:

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
set -a
source .env
set +a
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

`NOTEOS_ENV=local` allows `NOTEOS_DATABASE_URL`, defaulting to SQLite.
Docker Compose supplies its own local Postgres URL and runs migrations.

```bash
python -m unittest discover -s tests
```

Build from the repository root:

```bash
docker build -t noteos-api ./backend
```

## Deployed configuration

| Variable | Purpose |
| --- | --- |
| `NOTEOS_ENV` | `staging` or `production` |
| `AWS_REGION` | SSM region; defaults to `ca-central-1` |
| `CORS_ORIGINS` | Comma-separated browser origins |
| `NOTEOS_DATABASE_URL_SSM_PARAM` | SSM SecureString path, e.g. `/noteos/production/database/url` |
| `RUN_MIGRATIONS` | Container startup migration switch; default `false` |

The API reads and decrypts the database URL through boto3 using its ECS task
role. Staging/production require SSM, reject raw `NOTEOS_DATABASE_URL`, reject
wildcard CORS, and reject non-Postgres SSM values. Unknown environment names
fail validation. The frontend has no access to these secrets.

Secrets are resolved at process startup. After changing an SSM database URL,
restart API tasks. Coordinate password rotation with RDS and migrations; SSM
does not automatically rotate RDS credentials.

## Endpoints and migrations

`GET /health`, `GET /notes`, `POST /notes`,
`PATCH /notes/{id}`, and `DELETE /notes/{id}`.
All routes also accept the `/api` prefix for ALB path routing.

Schema revisions live in `alembic/versions/`. Run `alembic upgrade head` as
a one-off release task before starting a new API version. Deployed ECS tasks
do not run migrations concurrently on startup. See [infrastructure setup](../infra/README.md).
