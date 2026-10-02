# Multi-region plan

NotesOS starts as a single-region SaaS deployment in `ca-central-1`. That keeps
the first release understandable while still leaving a clean path to a broader
North America, Europe, and Asia footprint.

## Target regions

- North America east/current: `ca-central-1`
- North America west: `us-west-2`
- Europe west: `eu-west-1`
- Europe central/east: `eu-central-1`
- Asia south/west: `ap-south-1`
- Asia southeast/east: `ap-southeast-1`

## Expansion model

- Keep one regional Terraform stack per AWS region.
- Keep ECR either replicated cross-region or built per region from GitHub Actions.
- Put Route 53 latency routing, Route 53 geolocation routing, or AWS Global
  Accelerator in front of regional ALBs.
- Use one Route 53 routing policy per hostname. For example, use
  `notes.example.com` for latency-based routing and `geo.notes.example.com` for
  geolocation experiments.
- Use one ALB per region with path-based routing: `/api/*` to the private API
  service and all other paths to the public frontend service.
- Use Aurora Global Database when the product needs multi-region recovery or
  lower-latency reads.
- Keep SSM parameters region-local so each ECS task reads secrets from its own region.

## EKS and Argo CD

ECS is the initial runtime target. Argo CD is intentionally present only as a
commented CD phase in CI until the EKS track is active.
