# klasno

Health + ERP platform: a modular monolith API, scheduled ingestion jobs, a self-hosted LLM, and a React SPA.

See ARCHITECTURE.md for the full design and docs/adr for decision records.

## Repository layout

```text
services/api        FastAPI modular monolith (users, health, erp, analytics, assistant)
services/ingestion  Cloud Run Jobs (Fitbit sync, transform, token refresh, ERP processing)
services/llm        vLLM serving an open model (Cloud Run GPU)
web                 React (Vite) SPA
infra               Terraform modules + per-env stacks (dev, staging, prod)
docs                ADRs, runbooks, data dictionary
```

## Local development

Run the full local stack (api + postgres + web):

```bash
docker compose up
```

See docker-compose.yml for details.
