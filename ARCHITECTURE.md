# Architecture

> High-level overview of the Klasno system. Keep this in sync with the code; record decisions as ADRs under `docs/adr/`.

## Overview

Klasno is a modular monolith backend (`services/api`) with scheduled ingestion jobs (`services/ingestion`), a self-hosted LLM (`services/llm`), and a React SPA (`web`). Infrastructure is managed with Terraform (`infra`).

## Components

- **services/api** — FastAPI modular monolith. Modules: users, health, erp, analytics, assistant. One shared SQLAlchemy schema; migrations via Alembic.
- **services/ingestion** — Cloud Run Jobs (scheduled): Fitbit sync, transform (raw -> metrics -> marts), OAuth token refresh, ERP file processing.
- **services/llm** — vLLM serving an open model on Cloud Run GPU.
- **web** — React (Vite) SPA.
- **infra** — Terraform modules + per-env stacks (dev, staging, prod).

## Data

Postgres (transactional, via Cloud SQL) + BigQuery (analytics: raw -> metrics -> marts).

## CI/CD

- `ci.yml` — lint + test on every PR
- `deploy-staging.yml` — auto-deploy main to staging
- `deploy-production.yml` — tag v* to production (manual approval)

## Sections (to expand)

- §19 Assistant: tool-calling loop and whitelisted tools
- §19.2 LLM serving
