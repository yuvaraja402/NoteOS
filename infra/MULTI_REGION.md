# Multi-region plan

The default deployment is one region, `ca-central-1`. Regional expansion
requires reviewed modules and data-replication choices; the example is not a
live six-region deployment.

No region is provisioned by branch CI. ECS release actions are disabled and
the future Argo CD job remains commented. Follow the
[deployment checklist](DEPLOYMENT.md) before enabling any regional release.

## Target regions

- North America east/current: `ca-central-1`
- North America west: `us-west-2`
- Europe west: `eu-west-1`
- Europe central/east: `eu-central-1`
- Asia south/west: `ap-south-1`
- Asia southeast/east: `ap-southeast-1`

## Promotion path

Extract the regional Terraform stack into a module and instantiate it using
provider aliases. Each region gets one path-routing ALB, frontend/API services,
ElastiCache, gateway endpoint, regional SSM secrets, and logging.

Use DynamoDB Global Tables when cross-region note replication is needed.
Review the consistency mode and application conflict policy before enabling
writes in several regions. The current revision scheme and Redis queue are
regional; do not enable active-active writes without a revision/fencing design
that remains correct across regions. A single write region is the first step.

Device cookies need stable identity during failover. For one global workspace,
replicate the same signing-key material securely into regional SSM parameters;
separate keys intentionally produce different workspace identities. Redis
credentials and buffers stay regional. Cloud failover can restore DynamoDB
documents, but unflushed Redis changes are not a cross-region recovery guarantee.

Use Route 53 latency routing for region selection. Use a different hostname
for geolocation rules; the Terraform root supports both. Add a geolocation
default record when opening service beyond the targeted continent. Each region
must have an ACM certificate for its ALB hostnames.

ECR image replication and the same API/frontend releases keep regions aligned.
Set explicit data-residency and recovery targets before adding Europe or Asia.

## EKS later

ECS remains the initial runtime. Argo CD is commented in CI. When moving to EKS,
use pod IAM roles for DynamoDB and SSM and retain private Redis networking.
