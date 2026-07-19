# Architecture

Klasno uses a modular monolith for product APIs and separate scheduled jobs for
data ingestion. Architecture decisions are recorded under `docs/adr`.

## Components

- `services/api`: FastAPI modular monolith with users, health, ERP, analytics,
  and assistant modules. Modules share SQLAlchemy models and Alembic history.
- `services/ingestion`: Cloud Run Jobs for health sync, transformation, OAuth
  token refresh, and ERP ingestion.
- `web`: React and Vite SPA. It communicates only with `services/api`.
- `services/llm`: deferred vLLM deployment stub. The assistant initially uses a
  hosted provider through a provider-independent adapter.
- `infra`: Terraform modules and dev, staging, and production stacks.

## Data flow

```text
Health API -> Cloud Run puller -> GCS raw JSON -> Cloud Run transform
                                             -> BigQuery metrics and marts

School ERP -> API/file ingestion -> Cloud SQL operational records

React SPA -> FastAPI -> Cloud SQL / BigQuery marts / assistant tools
```

Cloud SQL Postgres is the source of truth for tenants, users, roles, consent,
OAuth state, ERP records, and application state. BigQuery owns immutable raw
health data, transformed metrics, derived wellness features, and aggregate
marts. BigQuery transformations must not write operational state to Postgres.

## Assistant boundary

The assistant calls only whitelisted application tools. It never queries a
database directly. Provider credentials remain in Secret Manager, and the
provider adapter must allow a future move to the deferred vLLM service without
changing assistant tools.

## Privacy and safety

- Enforce tenant and role filtering at every API query boundary.
- Treat wellness and stress outputs as non-diagnostic signals.
- Avoid student PII in analytics marts when aggregates are sufficient.
- Do not log OAuth tokens, health payloads, or unnecessary identifiers.
- Track guardian consent and support deletion across Postgres, GCS, and
  BigQuery before a school pilot.
- Use `asia-south1` for new production student-data resources. Existing
  `us-central1` resources are migrated through an explicit rollout plan.

## Delivery and environments

CI validates repository structure, Python quality, and Compose configuration.
Staging deploys from `main` and production deploys from approved version tags
after runnable services and Terraform stacks are available.
