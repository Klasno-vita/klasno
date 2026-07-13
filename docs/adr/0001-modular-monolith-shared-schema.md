# ADR-0001: Modular monolith with a single shared schema

- Status: Accepted
- Date: 2026-07-13

## Context

The backend (`services/api`) is a modular monolith split into modules (users, health, erp, analytics, assistant). The scheduled `services/ingestion` jobs also read from and write to the same data stores. We need to decide how SQLAlchemy models and Alembic migrations are owned and shared.

## Decision

Use one shared SQLAlchemy schema under `services/api/app/models/`, with a single Alembic migration history in `services/api/alembic/`. Modules import from the shared models package rather than defining their own tables. Ingestion jobs depend on the same schema.

## Consequences

- Simpler: one source of truth for the schema and one migration history.
- Coupling: modules are not isolated at the database level; enforce boundaries in code (service layer), not by separate schemas.
- If a module later needs independence, extract it into its own service with its own schema and a migration to split the data.

## Alternatives considered

- Schema-per-module: more isolation, more overhead; premature for current scale.
- Separate models packages per module: risks divergence and duplicated migration tooling.
