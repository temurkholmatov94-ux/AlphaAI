# AlphaAI Master Architecture

**Product direction:** public platform, performance-first compute, and simultaneous pursuit of intelligence breadth, ownership, and scale.

## 1. Product definition

AlphaAI is a public multi-model AI platform and control plane. It discovers and catalogs models, connects authorized inference providers, routes tasks, coordinates agents, orchestrates fine-tuning, and manages deployments.

Every model must distinguish:
- **Catalogued:** metadata is known; no inference availability implied.
- **Accessible:** a verified provider API or downloadable artifact is available.
- **Runnable:** weights, license, runtime and hardware are compatible.
- **Trainable:** license and format permit the intended fine-tuning workflow.

A catalog entry must never imply all four.

## 2. High-level topology

```text
Public Web / SDK / API Clients
            |
       Edge / WAF / TLS
            |
   AlphaAI API Gateway
            |
   Identity + Org + Policy
            |
   Quotas / Rate Limits / Spend Guard
            |
   Intelligence Router ---- Model Registry & Catalog Sync
            |
   Provider Adapters / Model Gateway
       /           |             \
Hosted APIs    Inference Pool    Agent Runtime
               (vLLM etc.)       (tools gated)
                    |
             GPU Worker Scheduler
                    |
        Training / Evaluation Workers
                    |
        Artifact Registry + Object Store

System of record: PostgreSQL
Coordination/cache: Redis
Telemetry: traces + metrics + structured logs
```

## 3. Control plane vs data plane

**Control plane** owns identity, organizations, policies, model metadata, provider configuration, job scheduling, deployment definitions, quotas, audit records and usage ledgers.

**Data plane** handles inference traffic, model workers, GPU scheduling, training execution and artifact transfer. It scales independently from the control plane.

Never place provider master keys or unrestricted GPU runtime endpoints in the browser.

## 4. Core services

1. Identity & Organizations: accounts, verification, sessions, organizations, roles, service accounts and API key lifecycle.
2. Model Universe: registry, discovery connectors, model cards, source URLs, licenses, weights availability, modalities, context limits, benchmark provenance, provider status and compatibility.
3. Provider Integration: adapter contract for hosted APIs and self-hosted runtimes; retries, timeouts, circuit breakers, health and cost metadata.
4. Intelligence Router: task requirements, capability filtering, policy checks, model selection, fallback, routing explanation and outcome evaluation.
5. Agent Runtime: agent definitions, tool allowlists, execution traces, step budgets, sandboxing, approval gates and cancellation.
6. Training Lab: dataset registration, consent/provenance, validation, job specs, worker scheduling, checkpoints, metrics and reproducibility manifests.
7. Evaluation Service: curated tests, quality/safety metrics, latency and cost measurement, regression gates and benchmark provenance.
8. Deployment Manager: immutable model versions, rollout strategies, health checks, autoscaling policy, endpoint credentials and rollback.
9. Usage & Quota Service: request/token accounting, per-user/org/model limits, reservations for concurrency, spend caps and fair-use policy.
10. Admin & Trust: abuse reports, moderation policy, incident controls, audit logs, support and platform status.

## 5. Technology choices

| Layer | Initial choice | Scale path |
|---|---|---|
| Web | Next.js + TypeScript | CDN + independently scaled web tier |
| API/control plane | FastAPI + Python | Stateless replicas |
| System of record | PostgreSQL | Managed HA Postgres, read replicas |
| Coordination | Redis | Managed Redis / clustered coordination |
| Provider gateway | LiteLLM behind AlphaAI policy layer | Replaceable gateway adapter |
| GPU inference | vLLM for supported high-throughput models | Separate pools, batching, parallelism |
| Local developer runtime | Ollama | Not public production serving tier |
| Training | PyTorch + Transformers + TRL + PEFT | Queue-backed GPU workers |
| Artifacts | S3-compatible object storage | Versioned object store and lifecycle policies |
| Packaging | Docker Compose for development | Kubernetes when operationally justified |
| Observability | OpenTelemetry conventions | Metrics, traces, logs and alerting |

The gateway is not AlphaAI's source of truth. AlphaAI owns policy, identities, quotas, catalog metadata and routing decisions. Gateway budgets must be verified against persistent state with fail-closed behavior.

## 6. Model discovery and registry

Use provider catalogs and model hubs as discovery inputs, not unquestioned truth. Every model record should include canonical ID, aliases, owner/provider, source URL, license identifier and verification status, weight availability, access method, supported tasks/modalities, verified limits, runtime compatibility, hardware estimate and confidence, benchmark provenance, pricing source, last verification time, and lifecycle state.

Lifecycle states: discovered, review-required, verified, available, degraded, retired.

Respect source terms, rate limits, licenses and takedown requests.

## 7. Public access and performance policy

Public registration does not mean unrestricted compute. Before public inference:
- verified identity and abuse controls
- API keys stored hashed where possible and shown once
- organization and project isolation
- per-key, per-user, per-model and global RPM/TPM/concurrency limits
- token and cost estimation/reservation before provider calls
- hard global spend ceiling and kill switch
- request body and output limits
- queue backpressure and worker admission control
- fair-use quotas and transparent model availability
- audit events and anomaly detection

For high-cost hosted providers, require explicit platform budget allocation. Never offer unlimited free inference backed by unrestricted provider credentials.

## 8. Compute architecture

Classify workloads: CPU/lightweight inference, single-GPU inference, multi-GPU inference, fine-tuning/training, and evaluation/batch processing.

The scheduler accounts for GPU memory, accelerator type, VRAM, model size, quantization, concurrency, queue depth, tenant quota and worker health. Training workers are isolated from public inference workers.

Use vLLM for supported production inference workloads; retain Ollama for local development. Never expose worker ports directly to the public internet.

## 9. Multi-agent safety

Agents receive only tools required for a task. Enforce tool allowlists, per-run token/time/step/cost budgets, isolated execution for untrusted code, approval before external side effects, secrets unavailable to prompts, prompt-injection-aware retrieval, traces, cancellation, and human review before production deployment.

## 10. Training lifecycle

Dataset intake -> provenance/consent/license validation -> schema and quality checks -> split and deduplication -> training job spec -> isolated worker -> checkpoint and metrics -> evaluation gates -> model card and artifact manifest -> human approval -> versioned deployment -> monitoring and rollback.

Initial focus is reproducible LoRA/QLoRA fine-tuning of compatible, properly licensed open-weight models, not claiming to train frontier foundation models from scratch.

## 11. Reliability and scaling

Stateless API replicas; idempotent job creation; retry-safe workers; database migrations and tested backups; queue-based long-running work; health/readiness checks; circuit breakers; autoscaling from measured metrics; canary deployments and rollback.

Do not introduce Kubernetes, service meshes or multi-region complexity until metrics justify them. Interfaces should permit that future.

## 12. Release gates

A: repository, CI, config, API, database/Redis health, tests, architecture and threat model.
B: migrations, identity, organizations, RBAC, API keys, audit events and quota schema.
C: discovery ingestion, provenance/license workflow, search, model detail and connector health.
D: provider adapters, gateway, usage accounting, hard quotas, cost guard and routing.
E: security review, load tests, abuse handling, admin kill switch, privacy/terms and incident runbook.
F: datasets, GPU workers, fine-tuning, evaluations, artifacts and versioning.
G: GPU pools, autoscaling, advanced routing and multi-region when justified.
