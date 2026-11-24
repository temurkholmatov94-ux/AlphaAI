# AlphaAI Threat Model

## Assets
- Provider API credentials and platform signing secrets
- User credentials, prompts, uploaded files and datasets
- Model artifacts and private checkpoints
- GPU capacity, cloud accounts and spend limits
- Organization data, API keys, usage records and audit logs
- Platform integrity and availability

## Threats
- Anonymous abuse exhausting free inference/GPU capacity
- Stolen user or service API keys
- Prompt injection through user input, retrieved documents or tool outputs
- Malicious or compromised model artifacts and datasets
- Cross-tenant data exposure
- Resource exhaustion through oversized prompts, output, concurrency or training jobs
- Dependency/container supply-chain compromise
- Misconfigured worker ports, object storage or admin endpoints
- Runaway agents or recursive tool loops
- Provider outages, rate-limit exhaustion or unexpected price changes

## Required controls before public beta
- Authentication, verified account lifecycle, RBAC and organization isolation
- Hashed API keys, scoped permissions, rotation and revocation
- Server-side secret manager; no secrets in browser bundles or logs
- Strict request size, context, output, time, concurrency and queue limits
- Per-tenant and global rate/spend quotas with atomic reservations
- Fail-closed behavior if quota/budget state is unavailable
- Private networking for model workers; TLS and edge protection at ingress
- No direct public exposure of vLLM/Ollama/worker admin endpoints
- Sandboxed untrusted code execution and explicit agent tool allowlists
- Dataset/model provenance, license checks, scanning and artifact hashes
- Audit logs for admin, key, model, dataset and deployment changes
- Dependency and container scanning, pinned versions and CI tests
- Backups, restore drills, incident response and emergency kill switch

## vLLM-specific deployment caution

Do not assume the inference server's own API-key option protects every route. Place it behind an authenticated reverse proxy/gateway, restrict network access to the worker, and verify the current upstream security documentation for the exact version deployed.

## Release rule

The starter API is not a public inference service. Do not deploy it as an unrestricted public endpoint. Public registration and inference remain blocked until the controls above are implemented and independently tested.
