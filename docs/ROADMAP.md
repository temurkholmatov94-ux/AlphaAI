# AlphaAI Roadmap

## Gate A — Foundation
- [x] Founder direction: public, performance-first, all three strategic priorities
- [x] Master architecture
- [x] Initial control-plane service skeleton
- [x] Local PostgreSQL and Redis development services
- [x] Threat model and public-beta safety gate
- [ ] CI workflow and dependency/security checks
- [ ] Run tests in CI and verify Docker build

## Gate B — Secure control plane
- [ ] Database migrations and typed persistence models
- [ ] Authentication and verified account flow
- [ ] Organization, project and role model
- [ ] API key issuance, hashing, scopes, rotation and revocation
- [ ] Audit events and admin operations
- [ ] Atomic quota/spend reservation and global kill switch

## Gate C — Model Universe
- [ ] Model registry schema and APIs
- [ ] Hub/provider discovery connectors
- [ ] Provenance and license review states
- [ ] Search, filtering, aliases and model capability metadata
- [ ] Connector health and last-verified timestamps

## Gate D — Inference and intelligence
- [ ] Provider adapter contract and contract tests
- [ ] Self-hosted inference adapter (vLLM)
- [ ] Official hosted provider adapters
- [ ] Policy-aware gateway and model routing
- [ ] Multi-model comparison and fallback
- [ ] Usage metering, budget enforcement and load tests

## Gate E — Controlled public beta
- [ ] Web dashboard and onboarding
- [ ] Terms, privacy and acceptable-use policies
- [ ] Abuse reporting, rate limits and moderation controls
- [ ] Admin kill switch and incident runbook
- [ ] Security review and load-test sign-off
- [ ] Public beta with bounded quotas

## Gate F — Training and model lifecycle
- [ ] Dataset intake, validation and provenance
- [ ] Job queue and isolated GPU workers
- [ ] LoRA/QLoRA fine-tuning
- [ ] Evaluation suites and regression gates
- [ ] Artifact registry, immutable versions and rollback

## Gate G — Distributed performance
- [ ] GPU inventory and scheduler
- [ ] Multi-GPU serving and workload isolation
- [ ] Queue-aware autoscaling
- [ ] Cost/performance dashboards
- [ ] Multi-region and organization billing when justified
