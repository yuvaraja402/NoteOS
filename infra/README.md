# Infrastructure

The current stack is a single-region, three-tier NotesOS setup in
`ca-central-1`. Terraform is in `terraform/`; it deploys ECS Fargate.
Nothing is deployed by CI.

## Runtime layout

One public ALB routes `/api/*` to FastAPI on port `8000` and all other paths
to Next.js on port `3050`.

- Public subnets: ALB and frontend ECS tasks. Frontend ingress permits only the ALB security group.
- Private app subnets: API ECS tasks with no public IP; NAT provides outbound AWS access.
- Isolated data subnets: encrypted RDS Postgres, reachable only from API tasks.

Two availability zones are used. Web and API services scale independently.
Optional Route 53 latency and geolocation records alias the regional ALB.
Use a separate hostname for each policy. [Multi-region plan](MULTI_REGION.md)
covers the six-region expansion.

## Secrets and configuration

All cloud secret values belong in SSM SecureString. Use separate paths and IAM
roles for CI and runtime. GitHub repository variables are non-secret metadata;
no GitHub Actions secret entries or static AWS access keys are needed.

| Parameter | Created by | Read by |
| --- | --- | --- |
| `/noteos/ci/snyk-token` | Operator, using the bootstrap CI KMS key | GitHub CI OIDC role |
| `/noteos/production/database/password` | Operator, before the regional plan | Terraform provisioning identity |
| `/noteos/production/database/url` | Regional Terraform, encrypted with the runtime KMS key | API ECS task role |

For staging, use `/noteos/staging/database/password`. Terraform builds the
runtime URL at `/noteos/staging/database/url`. The password input is an SSM
parameter name, never a plaintext tfvars value. Passwords are URL-encoded and
the RDS connection requires TLS.

The API role can read only its database URL and decrypt only that parameter
through SSM. The CI role can read only the Snyk token and decrypt only that
parameter through SSM; it has no RDS, ECS, ECR, or runtime-secret permissions.

SSM values used by Terraform still appear in state. Keep state in an encrypted
remote backend with access controls and locking before applying. Do not commit
state, plans, local env files, or tfvars.

## CI bootstrap

`terraform/ci-bootstrap/` is an independent root so CI can be configured
before creating app infrastructure. An AWS administrator runs it manually:

```bash
cd infra/terraform/ci-bootstrap
cp terraform.tfvars.example terraform.tfvars
# Set github_repository to your OWNER/REPO; reuse an existing OIDC provider if present.
terraform init
terraform plan
```

Apply that reviewed plan when ready. Then create an SSM SecureString named
`/noteos/ci/snyk-token` in the AWS console using the Snyk token and the
`ci_ssm_kms_key_arn` output. Token values are not Terraform inputs and do not
enter CI bootstrap state.

Set these GitHub repository **variables** under Settings > Secrets and variables
> Actions > Variables:

| Variable | Value |
| --- | --- |
| `AWS_CI_ROLE_ARN` | Bootstrap `aws_ci_role_arn` output |
| `AWS_REGION` | `ca-central-1` |
| `SNYK_TOKEN_SSM_PARAMETER` | `/noteos/ci/snyk-token` |

GitHub authenticates to AWS using OIDC. Trust is restricted to the configured
repository's `main` branch and the `sts.amazonaws.com` audience. If you change
the branch, update both the workflow trigger and bootstrap trust policy.
See [GitHub's AWS OIDC guide](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws)
and [AWS's SSM encryption guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/secure-string-parameter-kms-encryption.html)
for the trust and KMS encryption-context rules used here.

Only trusted pushes can read SSM. Pull requests never assume an AWS role;
Trivy and the other checks still run. Snyk is mandatory on `main`: missing
configuration, denied SSM access, or an invalid token fails the job.

`scripts/load_ci_secret.py` fetches one SecureString with decryption, masks it
before exporting it to the current job's temporary environment file, and
rejects empty/multiline values. Values are never job outputs or artifacts.
Only the Snyk job receives the token. GitHub's generated platform token is
separate from app secrets and is used for the permitted SARIF upload.

CI actions are pinned to commits and the Snyk CLI to a version. Review updates
regularly. Trivy checks dependencies, secret leaks, and built images; Terraform
validation checks syntax and provider configuration, not a full security audit.

## Regional stack

Create the database password as an SSM SecureString first. The provisioning
identity needs `ssm:GetParameter` and `kms:Decrypt` for its encryption key,
in addition to the infrastructure permissions.

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# Set image URIs, origin, optional DNS, and the existing password parameter path.
terraform init
terraform plan
```

Before applying, publish web/API images to ECR and review the plan. Run Alembic
as a one-off ECS task with the API task role and private-subnet networking
before accepting traffic. CI currently validates and builds only.

The starter ALB uses HTTP. Add ACM/HTTPS before a public production launch.
The app also needs authentication and tenant isolation for multiple customers.
The current RDS instance and default service counts are starter sizing; choose
Multi-AZ, backups, scaling policies, and recovery targets before production use.

`eks-later/` keeps the future EKS track separate. Argo CD is commented in CI;
when enabling it, provision a separate OIDC role and SSM token rather than
expanding the Snyk role.
