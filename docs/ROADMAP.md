# AlphaAI Roadmap

## Gate A — Foundation
- [x] Founder direction: public, performance-first, all three strategic priorities
- [x] Master architecture and threat model
- [x] FastAPI control-plane service skeleton
- [x] Local PostgreSQL and Redis development services
- [x] SQLAlchemy model registry schema and Alembic migrations
- [x] Read-only registry list/detail endpoints and filtering
- [x] CI migration, automated test and Docker build steps

## Gate B — Secure control plane
- [x] User registration and Argon2id password hashing
- [x] Single-use, expiring email-verification token records
- [x] Short-lived signed access tokens and verified-user guard
- [x] Initial user workspace and owner membership
- [x] Scoped API key creation, one-time display, hashed storage and revocation
- [x] Audit events for core identity and key lifecycle events
- [ ] Transactional email delivery and verification resend flow
- [ ] Login/registration/API-key rate limits and abuse protection
- [ ] Password recovery and MFA
- [ ] Organization invitations, membership management and role administration
- [ ] Organization/project isolation on every resource
- [ ] API key rotation, last-used UI and service accounts
- [ ] Usage ledger, atomic quota/spend reservation and global kill switch
- [ ] Production session revocation and security review

## Gate C — Model Universe
- [x] Initial model registry and public read-only API
- [x] Hugging Face Hub discovery adapter and bounded CLI ingestion
- [x] Discovery metadata and upstream revision/provenance fields
- [x] New discoveries default to review-required and are not publicly listed
- [ ] Provenance and license review workflow
- [ ] Search, filtering, aliases and model capability metadata
- [ ] Connector health and last-verified timestamps
- [ ] Admin-only model ingestion and review interface
- [ ] Additional verified model source connectors

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
