# Architecture Decision Records

## ADR-001: Public platform, gated launch
**Decision:** AlphaAI is designed for public users, but public inference remains gated until authentication, tenant isolation, quotas, cost controls, abuse protection and operational response are tested.

**Reason:** Public access without resource controls exposes compute and provider budgets to exhaustion and creates security risk.

## ADR-002: Separate control plane and data plane
**Decision:** Identity, catalog, policy, jobs and usage metadata live in the control plane; inference and training workloads run in separately managed data-plane workers.

**Reason:** Enables independent scaling, workload isolation and safer public access.

## ADR-003: Catalog breadth is not runtime availability
**Decision:** Every model record has explicit source, license, access, verification and runtime states.

**Reason:** A discoverable model may be gated, API-only, unavailable, incompatible or license-restricted.

## ADR-004: Local development is not production inference
**Decision:** Ollama may support local development; high-throughput production serving targets vLLM or another measured compatible runtime.

**Reason:** Different workloads require different serving and scheduling strategies.

## ADR-005: No unlimited-free compute promise
**Decision:** Product messaging states compute limits and actual cost conditions transparently.

**Reason:** GitHub and free hosting tiers do not provide guaranteed unlimited GPU capacity or lifetime uptime.
