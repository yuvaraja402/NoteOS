# Deployment controls

CI is for review and validation only; it never deploys to AWS.
These controls also apply after a merge to
`main`; a merge is not release approval.

## What runs now

| Entry point | Behavior |
| --- | --- |
| Branch push / pull request | Lint, tests, Trivy, Terraform validation, multi-architecture builds |
| Trusted `main` push | Same checks; Snyk runs only with `ENABLE_SNYK=true`, using a read-only OIDC role and SSM token |
| Docker build jobs | `push: false`; no ECR login or registry publication |
| Terraform jobs | Formatting, `init -backend=false`, and validation; no plan/apply against AWS |
| EKS Buildx helper | Local OCI archive only; publication disabled |
| CD | ECS automation absent; future Argo CD job commented out |

Feature branches and pull requests must never gain SSM access merely to run
checks. Before enabling Snyk on `main`, configure the CI bootstrap and its
SecureString as described in [infrastructure setup](README.md). That role has
no ECR write, ECS update, or Terraform provisioning permissions.
Snyk is disabled by default for fresh forks; Trivy stays enabled. Set
`ENABLE_SNYK=true` only after the OIDC role and SSM token are configured.

Terraform resources are deliberately not commented out. Keep the complete
single-region, three-tier stack in source; running `terraform apply` manually
would still provision resources. Example inputs are not real account settings.
CI's provider initialization downloads plugins, but creates no AWS resources.

## Before a production release

Production deployment is not yet verified in AWS. Passing local checks is not
a production certification. Complete these gates for `ca-central-1`:

- Review the branch through a pull request. Require passing checks and review on `main`.
- Configure and enable Snyk; a skipped scan is not a completed security check.
- Configure encrypted, access-controlled remote Terraform state and locking for both roots. State includes the Redis AUTH token.
- Use a separate, least-privilege deployment identity. Do not reuse the Snyk SSM reader.
- Create the runtime KMS key, two SSM SecureStrings, an issued ACM certificate, and the DNS zone where applicable. Never commit secret values.
- Bootstrap the ECR repositories before publishing the initial images. For a first installation only, review an ECR-only Terraform plan; the ECS stack requires images that already exist. Avoid routine targeted applies.
- Build and scan both images for `linux/amd64` and `linux/arm64`. Publish immutable release tags; set `web_image` and `api_image` to reviewed image digests.
- Fill the regional inputs with real account IDs, endpoints, certificate/KMS ARNs, HTTPS origins, and SSM paths. Leave the 60-second idle / 300-second maximum flush settings unless intentionally changed.
- Review a saved Terraform plan, its cost and IAM changes, and the single-region failure boundary before approving apply. Do not upload plans or state as unrestricted CI artifacts.
- Smoke-test HTTPS and ALB path routing, device isolation, CRUD, Redis TLS, and DynamoDB persistence after flush. Test retries and deletion persistence.
- Set queue-lag/capacity/error alarms, perform backup restoration and rollback drills, and decide retention and anonymous-device recovery policies before customer traffic.

Redis acceptance is not durable database confirmation. The buffered-write loss
window and browser recovery limitations are documented in [storage design](STORAGE.md).
The [multi-region plan](MULTI_REGION.md) is a future design, not an enabled failover system.

## Future release actions: disabled

The commands below are reminders, not an executable release workflow. Keep
them commented until a separate release is explicitly approved. Configure a
protected production environment, its allowed release branch and approvals
before adding CD. No automatic CD trigger is present today.

```bash
# Registry publication, after ECR bootstrap/authentication and image scans:
# docker buildx build --platform linux/amd64,linux/arm64 --push -t "$WEB_IMAGE" ./frontend
# docker buildx build --platform linux/amd64,linux/arm64 --push -t "$API_IMAGE" ./backend
# Provisioning, from infra/terraform with real inputs and a secured backend:
# terraform plan -out=release.tfplan
# terraform apply release.tfplan
# Future EKS only; not used by the ECS release:
# argocd app sync noteos --grpc-web
```

Use Terraform to manage ECS task-definition/image changes, not a competing
untracked service-update process. After release, verify service health and
database persistence before opening traffic. Roll back to known-good image
digests through another reviewed plan; do not destroy the data stores.

References: [GitHub workflow triggers](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
and [Docker Buildx builder outputs](https://docs.docker.com/build/builders/drivers/docker-container/).
