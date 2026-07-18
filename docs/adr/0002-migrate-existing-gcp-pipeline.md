# ADR-0002: Migrate the existing GCP pipeline incrementally

- Status: Accepted
- Date: 2026-07-17

## Context

The health puller, scheduler, raw GCS storage, Dataproc transformation, and
BigQuery tables were created directly in GCP. The pull path works, while the
replacement Cloud Run transformation job is built but not yet deployed. The
target architecture requires source-controlled services and Terraform-managed
resources in `asia-south1`.

## Decision

Preserve the working pipeline while migrating one workload at a time. First,
place the Cloud Run transformation source in `services/ingestion/transform` and
validate it against the existing Dataproc output. Next, migrate the puller and
scheduler configuration. Terraform adoption and regional migration follow only
after behavior and data parity are verified.

## Consequences

- Existing daily data collection remains available during migration.
- Temporary `us-central1` resources are documented technical debt.
- Every migrated workload requires idempotency, structured logs, reconciliation,
  and a rollback path before replacing the existing workload.
- The exposed OAuth client secret must be rotated during puller migration.
