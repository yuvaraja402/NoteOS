# NotesOS

A notes workspace with a glassy React/Next.js interface, FastAPI service, and
Postgres storage. The AWS setup is a single-region, three-tier deployment in
`ca-central-1`, targeting ECS Fargate first.

## Layout

```text
frontend/              Next.js app, package lock, Dockerfile
backend/               FastAPI, migrations, tests, Dockerfile
infra/
  terraform/           Regional ECS, RDS, ALB, Route 53, SSM
    ci-bootstrap/      Separate GitHub OIDC role and CI KMS key
  scripts/             SSM secret loader and its tests
  eks-later/           Future EKS build script and migration notes
.github/workflows/     Validation, Trivy, Snyk, multi-arch builds
docker-compose.yml     Local frontend + API + Postgres
```

## Run locally

Requires Docker Compose:

```bash
cp .env.example .env
docker compose up --build
```

Set a local password in `.env` and use the same URL-encoded password in
`NOTEOS_DATABASE_URL`. Open http://localhost:3050. Local service ports are
bound to loopback; the API uses port `8000` and Postgres uses `5432`.

For direct development, use [frontend setup](frontend/README.md) and
[backend setup](backend/README.md).

## AWS and CI

[Infrastructure setup](infra/README.md) documents the network, configuration,
SSM parameters, GitHub OIDC bootstrap, and deployment prerequisites.
[Multi-region plan](infra/MULTI_REGION.md) covers expansion into North America,
Europe, and Asia.

Application and CI secret values come from SSM SecureString. GitHub repository
variables hold only non-secret role ARNs, regions, and parameter paths.
Local `.env` files are ignored and excluded from container build contexts.

CI runs frontend checks, backend secret tests and migrations, Terraform
validation, Trivy, Snyk, and Buildx for `linux/amd64` and `linux/arm64`.
Snyk runs on trusted `main` pushes and requires the documented AWS bootstrap.
Pull requests run checks without AWS credentials. Argo CD remains commented
out for the later EKS migration. CI does not publish images or deploy.

The current app is a shared notes demo. User authentication and tenant isolation
are required before serving separate SaaS customers.
