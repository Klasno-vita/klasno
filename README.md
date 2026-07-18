# Klasno

Klasno is a student wellness and academic intelligence platform for schools in
India. It combines wearable health data, school ERP data, privacy-aware
analytics, and role-based experiences for students, guardians, teachers, and
administrators.

The repository currently contains the architecture foundation. The existing
GCP ingestion and transformation workloads will be migrated here incrementally.

## Repository layout

```text
services/api        FastAPI modular monolith
services/ingestion  Cloud Run ingestion and transformation jobs
services/llm        Deferred self-hosted LLM deployment stub
web                 React and Vite SPA
infra               Terraform modules and environment stacks
docs                ADRs, runbooks, and the analytics data dictionary
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for component and data boundaries.

## Local foundation

Install Python development tooling with [uv](https://docs.astral.sh/uv/):

```bash
uv sync --extra dev
```

Start the local Postgres dependency:

```bash
docker compose up -d postgres
```

The API and web containers will be added when those applications become
runnable. Copy `.env.example` to `.env` for local values; never commit secrets.

## Delivery order

1. Migrate and validate the existing Cloud Run transformation job.
2. Migrate the working health-data puller and scheduler behavior.
3. Build daily wellness features and BigQuery marts.
4. Expose tenant-safe analytics through the API and frontend.
5. Add consent, deletion, audit, and school-pilot workflows.
