# EKS later

This folder is intentionally small. The app is prepared for ECS now, but these
scripts keep the first EKS move obvious later.

## Build the API image for both CPU families

```bash
bash infra/eks-later/build-api-multiarch.sh <account>.dkr.ecr.ca-central-1.amazonaws.com/noteos-api:latest
```

## What to add when EKS is real

- Helm chart or Kustomize overlays for `web`, `api`, and ingress.
- A pod IAM role scoped to `/noteos/production/database/url` and its KMS key.
- Set `NOTEOS_DATABASE_URL_SSM_PARAM` to that parameter path. The existing API
  reads SSM through boto3 using the pod role; no plaintext Kubernetes secret is required.
- A separate Argo CD role scoped to its own SSM token, provisioned before enabling CD.
