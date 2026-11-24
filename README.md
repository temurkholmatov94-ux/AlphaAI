# AlphaAI — The Intelligence Universe

A public, multi-model AI infrastructure platform for model discovery, orchestration, inference, evaluation, fine-tuning, and deployment.

Founder direction: public platform, performance-first compute, and simultaneous pursuit of intelligence breadth, ownership, and scale.

## Non-negotiable realities

- GitHub is source control and CI, not an unlimited GPU host.
- Free unlimited compute or lifetime free 24/7 hosting cannot be guaranteed.
- Proprietary hosted models such as Claude, ChatGPT, and Grok are accessed only through authorized provider APIs or agreements. Their private weights are not assumed available for self-hosting or independent training.
- Open-weight models have individual licenses, hardware requirements, and usage conditions.
- Public inference requires authentication, quotas, rate limits, abuse controls, and cost ceilings before launch.
- An API subscription does not grant rights to train the provider's underlying model.

## Product pillars

1. Model Universe: searchable registry, metadata ingestion, provenance, license checks, capability tags, provider connectors, and health.
2. Intelligence Router: task-aware model selection, fallbacks, routing policies, evaluations, and cost/latency/quality tradeoffs.
3. Multi-Agent Workbench: controlled delegation, tool permissions, traceability, and human approval for consequential actions.
4. Training & Evaluation Lab: dataset governance, fine-tuning jobs, reproducible experiments, evaluations, versioning, and rollback.
5. Compute Fabric: local and cloud GPU workers, scheduling, capacity accounting, isolation, and autoscaling.
6. Inference & Deployment: OpenAI-compatible gateway, versioned endpoints, API keys, observability, and traffic controls.
7. Public Platform: identity, organizations, roles, quotas, usage metering, abuse prevention, and admin operations.

## Technology direction

- Web: Next.js and TypeScript.
- Control plane: Python and FastAPI.
- System of record: PostgreSQL.
- Coordination and cache: Redis.
- Model gateway: LiteLLM or equivalent behind AlphaAI policy enforcement.
- High-throughput self-hosted inference: vLLM.
- Local developer runtime: Ollama.
- Training: PyTorch, Transformers, TRL, and PEFT.
- Packaging: Docker; Kubernetes when measured scale justifies it.
- Discovery: Hugging Face Hub APIs and provider catalogs, with license and provenance verification.
- Telemetry: OpenTelemetry-compatible traces, metrics, and structured logs.

## Model status terminology

A catalog entry is not a promise that a model is downloadable, free, licensed for hosting, or accessible.

- Catalogued: metadata is known.
- Accessible: a verified provider API or downloadable artifact is available.
- Runnable: runtime, weights, license and hardware are compatible.
- Trainable: the license and format permit the intended fine-tuning workflow.

## Identity foundation (implemented; not yet public-launch ready)

- Email/password registration with Argon2id password hashing.
- Email verification records store only token digests; tokens expire after 24 hours and are single-use.
- Short-lived signed access tokens with issuer, audience and expiry checks.
- User-owned starter workspace and membership role.
- Scoped API keys are generated randomly, stored only as HMAC digests, shown once, and can be revoked or expired.
- Audit events for registration, verification, login and API-key lifecycle.
- Development/test-only verification token response; production never returns the token.

Important: an email delivery provider, resend flow, login/registration rate limiting, MFA, session revocation, recovery flow and security review are not implemented yet. Do not open public account registration until email delivery and abuse controls are live.

## Usage and budget foundation (implemented; budgets default to disabled)

- Every new workspace receives a usage account with zero budget and spending disabled.
- Atomic spend reservations are committed before provider calls.
- Idempotency keys prevent duplicate reservations.
- Settlements create immutable usage events and reconcile reserved versus actual spend.
- Failed-before-send requests can release reservations; ambiguous timeouts must be reconciled, not blindly released.
- An actual provider charge above its estimate is recorded as an overage and blocks later reservations until budget is adjusted.

The pricing estimator now requires a current, verified, versioned price record and adds a conservative safety margin. It rejects missing or stale pricing and accepts only bounded server-side token estimates. Operator-only pricing/budget provisioning and a trusted tokenizer are still outstanding, so the usage ledger is not yet connected to an inference endpoint.

## Pricing foundation (implemented; no prices are fabricated)

- Versioned provider/model pricing records include official source URL, verification time and effective dates.
- The estimator uses integer arithmetic, bounded token counts and a 15% safety margin by default.
- Missing, future, expired or more-than-30-day-old prices fail closed.
- No provider/model price is pre-populated without checking the provider's official pricing source.

## Provider gateway foundation (implemented; inference endpoint intentionally not exposed)

- Provider-neutral request/response and error contracts.
- OpenAI Chat Completions-compatible adapter (supports provider-configured base URLs).
- Anthropic Messages API adapter.
- Optional xAI adapter using the OpenAI-compatible protocol.
- Server-side credentials and explicit public-model-to-upstream-model routing.
- Timeouts, normalized errors, token usage extraction and mocked HTTP contract tests.
- No automatic retry: retries can duplicate provider charges when request outcome is ambiguous.

Provider credentials belong only in local environment files or a production secret manager. The ALPHAAI_MODEL_ROUTES setting is a JSON array, for example: ["alpha-fast=openai:gpt-model-id"]. A route is omitted unless its provider credential exists.

**Important safety boundary:** these adapters are an internal foundation, not a public inference endpoint. Public inference remains disabled until persistent usage accounting, atomic quota/spend reservations, rate limits, output limits, a hard global budget ceiling and an emergency kill switch are implemented and tested.

## Model Universe administration (implemented; bootstrap admin only)

- Protected review queue for discovered, review-required and degraded model records.
- Explicit server-side admin email allowlist; ordinary users cannot review or publish catalog entries.
- Review action records the before/after decision in the audit log.
- Publishing requires a verified or not-applicable license status and a known access method.
- Discovery does not overwrite human review decisions.

Set `ALPHAAI_ADMIN_EMAILS` to a JSON array of administrator email addresses in the server environment. This bootstrap allowlist is intentionally simple; production needs managed admin roles, MFA and audited admin lifecycle.

## Implemented foundation

- FastAPI control-plane skeleton and health endpoint.
- PostgreSQL/SQLite-compatible SQLAlchemy model registry schema.
- Alembic migrations for the registry and identity.
- Read-only public registry endpoints with search, provider/task filters, pagination and slash-containing model IDs.
- Public visibility requires an available record, verified/not-applicable license status, and known access method.
- CI runs database migrations, automated tests and Docker image build.

The registry intentionally starts empty. We will not publish invented model availability or mark a model license as verified without evidence. Catalog ingestion is the next implementation step.

## Local development

Requirements: Docker Engine or Docker Desktop with Compose.

1. Copy .env.example to .env.
2. Replace local placeholder passwords and secrets.
3. Run docker compose up --build.
4. Open http://localhost:8000/health.
5. Explore http://localhost:8000/docs.
6. To discover public Hub models into the internal review queue, run: docker compose exec api python -m scripts.discover_huggingface --limit 50 --pipeline-tag text-generation.

New discoveries remain unapproved and hidden from public listings until a human verifies license and runtime access. Never commit real credentials, private datasets, user data, or model weights.

See docs/MASTER_ARCHITECTURE.md, docs/THREAT_MODEL.md, and docs/ROADMAP.md.
