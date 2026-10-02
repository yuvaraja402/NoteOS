# EKS later

This folder is intentionally small. The app is prepared for ECS now, but these
scripts keep the first EKS move obvious later.

EKS and Argo CD are not deployed or enabled. The CI Argo CD example stays
commented, including on `main`. See [deployment controls](../DEPLOYMENT.md).

## Build the API image for both CPU families

```bash
bash infra/eks-later/build-api-multiarch.sh noteos-api:preview /tmp/noteos-api.oci.tar
```

Run from the repository root with a multi-platform Buildx builder. This creates
a local OCI archive; registry publication is disabled. A future release may
replace the script's output option with the commented `--push` guidance, but
only after release approval and ECR authentication. The helper never deploys.

## What to add when EKS is real

- Helm chart or Kustomize overlays for `web`, `api`, and ingress.
- A pod IAM role scoped to the two runtime SSM parameters, their KMS key, and
  the regional DynamoDB notes table.
- API pod networking to the private ElastiCache endpoint. Keep the flush worker
  running in API pods; Redis leases coordinate workers across replicas.
- Set `REDIS_AUTH_TOKEN_SSM_PARAM` and `SESSION_SIGNING_KEY_SSM_PARAM`.
  The API reads SSM through boto3 using the pod role; no plaintext Kubernetes secret is required.
- A separate Argo CD role scoped to its own SSM token, provisioned before enabling CD.
