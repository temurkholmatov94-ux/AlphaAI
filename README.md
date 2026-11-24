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

## Current status

This repository is establishing architecture and development controls. The starter API is not a public inference service. Public access remains blocked until security and resource controls are implemented and tested.

## Local development

Requirements: Docker Engine or Docker Desktop with Compose.

1. Copy .env.example to .env.
2. Replace local placeholder passwords and secrets.
3. Run docker compose up --build.
4. Open http://localhost:8000/health.

Never commit real credentials, private datasets, user data, or model weights.

See docs/MASTER_ARCHITECTURE.md, docs/THREAT_MODEL.md, and docs/ROADMAP.md.
