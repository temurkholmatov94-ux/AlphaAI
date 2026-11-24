# Deployment guide

## Free visual preview (Render)

The repository includes a preview-only Render Blueprint at `render.yaml`.

1. Sign in to Render and choose **New → Blueprint**.
2. Connect the GitHub repository `temurkholmatov94-ux/AlphaAI`.
3. Select the `main` branch and review the Blueprint before applying it.
4. Render will ask for `ALPHAAI_ADMIN_EMAILS`. For a public visual preview, leave the value empty unless an administrator account has already been safely provisioned.
5. Confirm the service is on the **Free** plan before applying. Do not approve any paid resources.
6. After the first deploy is healthy, open the service URL. The homepage is `/`, the model explorer is `/models`, and API docs are `/docs`.

The Blueprint is configured with manual deploys (`autoDeployTrigger: off`) so later commits do not automatically change the public preview.

### Preview limitations — read before deploying

- The free web service may spin down after inactivity and can take about a minute to start again.
- Free web-service filesystems are ephemeral. This Blueprint uses SQLite only to make a disposable preview possible; database records can disappear on restart/redeploy. Do not store real users, API keys, model metadata, or business data in this preview.
- Free Render Postgres databases expire after 30 days and are not an acceptable permanent production database.
- Public account onboarding is not launch-ready: transactional email delivery and verification resend are not implemented. Production registration does not expose development verification tokens.
- Public inference remains disabled. Provider credentials must never be placed in frontend code or committed to GitHub.
- The preview is not a production SLA, GPU host, or permanent free hosting promise.

## Before a real public beta

Use a persistent managed PostgreSQL database (paid or an existing durable provider), configure transactional email delivery, set the platform administrator allowlist, verify TLS and secret handling, and complete the remaining Gate B, D and E security controls in `docs/ROADMAP.md`. Do not expose inference until quotas, atomic budget reservations, rate limits, a global kill switch, provider-health handling, abuse controls and a security review are complete.

## Container port behavior

The API container honors the hosting platform's `PORT` environment variable and runs Alembic migrations before starting Uvicorn. The `/ready` endpoint checks database connectivity and is used as the deployment readiness probe.
