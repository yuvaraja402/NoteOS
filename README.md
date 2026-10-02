# NotesOS

Notes without signup. Next.js handles the workspace, FastAPI handles the API,
and AWS Redis buffers edits before DynamoDB stores them. The Terraform stack
targets a single-region, three-tier setup in `ca-central-1`.

## Deployment status

Nothing deploys on push or merge. CI tests, scans, and builds; it does not publish
images, apply Terraform, or update ECS. Argo CD remains commented out. The
Dockerfiles and infrastructure definitions are ready for a reviewed release.

The stack has not been deployed and verified in AWS. The
[deployment checklist](infra/DEPLOYMENT.md) covers setup and launch checks.

## Layout

```text
frontend/              Next.js app, browser session outbox, Dockerfile
backend/               FastAPI, Redis/DynamoDB storage, tests, Dockerfile
infra/
  terraform/           ECS, ElastiCache, DynamoDB, ALB, Route 53
    ci-bootstrap/      GitHub OIDC role and CI KMS key
  scripts/             CI SSM secret loader and tests
  eks-later/           Future EKS notes and Buildx script
.github/workflows/     Validation, Trivy, Snyk, multi-arch builds
docker-compose.yml     Frontend preview; optional AWS-backed API
```

## Preview locally

Use Node.js 22. Fork this repository on GitHub, then clone your fork:

```bash
git clone https://github.com/YOUR-USERNAME/NoteOS.git
cd NoteOS
```

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:3050. Notes are saved in browser `sessionStorage` and
survive a refresh in the same tab. The preview works without AWS. Closing the
tab clears session-only drafts; the UI reports whether changes reached cloud
storage. There are no local database or cache services.

Alternatively, from the root:

```bash
docker compose up --build
```

The cloud API needs AWS resources, an AWS profile, and private network access
to Redis. See [backend setup](backend/README.md).

## Write path

1. Each edit is captured in the current browser session and its outbox.
2. After a short debounce, FastAPI accepts it into AWS Redis.
3. A worker checks the queue every five seconds and writes to DynamoDB after
   60 idle seconds or a five-minute maximum wait during continuous editing.
4. The browser retains a recovery copy until DynamoDB confirms that revision.

An HMAC-signed, HttpOnly cookie identifies the anonymous device workspace.
IP addresses contribute only to short-lived, hashed rate limits. Shared IPs
do not share notes. Clearing the cookie or using another browser creates a new
workspace; there is no cross-device recovery without an account.

[Storage design](infra/STORAGE.md) covers timing, limits, and failure behavior.
[Infrastructure setup](infra/README.md) covers AWS, SSM, and GitHub OIDC.
[Multi-region plan](infra/MULTI_REGION.md) describes the expansion path.

## Checks and contributions

Branch pushes and pull requests run lint, tests, Trivy, Terraform validation,
and `linux/amd64` / `linux/arm64` image builds. Forks need no AWS credentials
for these checks. Python tests use service doubles, not a local database.

Snyk is opt-in: configure the read-only GitHub OIDC role and SSM SecureString,
then set the repository variable `ENABLE_SNYK=true`. It runs only on trusted
`main` pushes and must be enabled before a production release. Application and
scanner secrets stay in AWS SSM; never add them to GitHub or `.env` files.

Use a feature branch for changes and open a pull request against `main`.
Keep state, credentials, real tfvars, and generated build files out of commits.
Setup details and test commands live in each folder's README.

## License

[MIT](LICENSE).
