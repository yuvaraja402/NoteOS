# Infrastructure

A single-region, three-tier NotesOS stack in `ca-central-1`, using ECS Fargate.
CI validates and builds; it does not deploy.

Branch pushes, pull requests, and merges to `main` never publish containers,
apply Terraform, or update ECS. Keep the Terraform resources active in source;
commenting them out would remove the infrastructure definition, not safely
disable deployment. Release actions remain disabled/commented instead.
See [deployment checklist](DEPLOYMENT.md) for the later production promotion.

## Network and data

One ALB accepts HTTPS on `443`, redirects HTTP to HTTPS, and routes
`/api/*` to FastAPI on `8000`; other paths go to Next.js on `3050`.
Supply an issued ACM certificate for the configured application domains.

- Public subnets: ALB and frontend ECS tasks. Frontend ingress permits only ALB traffic.
- Private app subnets: API tasks without public IPs, with NAT for AWS API access.
- Isolated data subnets: AWS ElastiCache for Redis, reachable only by API tasks over TLS.
- DynamoDB: a regional managed service, reached from private app subnets through a restricted gateway VPC endpoint.

DynamoDB cannot be placed inside a subnet. The gateway endpoint and IAM role
restrict access to the notes table. Redis has an encrypted primary/replica pair
across availability zones, automatic failover, seven-day snapshots, and
`noeviction`. DynamoDB uses on-demand capacity, encryption, point-in-time
recovery, and deletion protection.

Optional Route 53 latency and geolocation records point to the same ALB.
Use a different hostname for each policy and certificates covering both.
[Multi-region plan](MULTI_REGION.md) covers the expansion.

## Runtime SSM parameters

Create both SecureStrings before planning the regional stack, using the
customer-managed KMS key provided as `runtime_secrets_kms_key_arn`.

| Parameter | Content | Reader |
| --- | --- | --- |
| `/noteos/production/redis/auth-token` | A random 32-128 character Redis AUTH token | Terraform provisioning identity and API task role |
| `/noteos/production/session/signing-key` | At least 32 bytes of random signing material | API task role |
| `/noteos/ci/snyk-token` | Snyk token, encrypted with the CI bootstrap key | GitHub CI OIDC role |

Use supported Redis AUTH characters; an alphanumeric random token is simplest.
For staging, replace `production` in runtime paths with `staging`.
Never put values in tfvars, GitHub variables, container images, or frontend code.

Terraform needs the Redis token to configure the managed cache, so its value
appears in state. Keep state in an encrypted remote backend with locking and
restricted IAM. The signing-key value is not read by Terraform. The API role
can read only the two runtime parameters, decrypt them through SSM using the
specified KMS key and parameter encryption contexts, and access the one notes
table. The frontend receives no AWS task role or secrets.

The signing key establishes device identity. Rotating it without a migration
plan makes existing anonymous workspaces inaccessible. Redis AUTH rotation
also needs coordination with API task restarts.

## CI bootstrap

`terraform/ci-bootstrap/` is an independent root for GitHub OIDC and the CI
KMS key. An administrator reviews it manually:

```bash
cd infra/terraform/ci-bootstrap
cp terraform.tfvars.example terraform.tfvars
# Set OWNER/REPO and reuse the account's existing GitHub OIDC provider if present.
terraform init
terraform plan
```

After an approved bootstrap apply, create the Snyk token as an SSM SecureString
in the AWS console using the `ci_ssm_kms_key_arn` output.
The token never enters Terraform inputs or bootstrap state.

Set these non-secret GitHub repository variables:

| Variable | Value |
| --- | --- |
| `AWS_CI_ROLE_ARN` | Bootstrap `aws_ci_role_arn` output |
| `AWS_REGION` | `ca-central-1` |
| `SNYK_TOKEN_SSM_PARAMETER` | `/noteos/ci/snyk-token` |
| `ENABLE_SNYK` | `true`, after the role and SSM token are configured |

Only trusted pushes to the configured repository's `main` branch can assume
the CI role. All branch pushes run validation; feature branches and pull requests
run without AWS access. The CI role cannot deploy. Snyk is skipped until
`ENABLE_SNYK=true`, so a fresh fork needs no AWS account. Once enabled, missing
configuration or denied SSM access fails the job. Enable it before release.

`scripts/load_ci_secret.py` reads one SecureString with decryption, masks it,
and exports it only to that job's temporary environment. It rejects empty or
multiline values. Secrets are never job outputs or artifacts. GitHub's generated
platform token is used separately for the permitted SARIF upload.

Actions are pinned to commits and the Snyk CLI to a version. Review dependency
updates regularly. See [GitHub OIDC guidance](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
and [SSM encryption guidance](https://docs.aws.amazon.com/systems-manager/latest/userguide/secure-string-parameter-kms-encryption.html).

## Regional setup

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Set image URIs, HTTPS origin, ACM certificate, KMS key, SSM paths, and optional DNS.
terraform init
terraform plan
```

For a later approved release, publish reviewed web/API images to ECR before
applying the app stack. These operations are not run by CI or preview scripts.
No SQL migration step is required. Both services can scale independently.
Each API task runs the flush loop; Redis leases and revision checks coordinate
persistence across workers.

Each workspace is capped at 100 notes and 200 KiB of serialized content.
Plan Redis sizing, alarms, recovery targets, anonymous-session retention, and
account recovery before a customer launch. See [storage design](STORAGE.md)
for the write-delay and durability tradeoff.

`eks-later/` keeps the EKS migration separate. Argo CD stays commented in CI;
enable it only after provisioning its separate OIDC role and SSM token.
