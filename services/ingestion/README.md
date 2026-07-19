# Ingestion

This service owns scheduled Cloud Run workloads and their shared GCP clients.
Each workload will be independently executable while sharing configuration,
logging, validation, and BigQuery helpers.

Current workloads and references:

- `fitbit_sync`: exported Cloud Run health API puller now in source control.
- `transform`: Cloud Run Job transform core under active development.
- `legacy_reference`: old Dataproc parser and submit script for reference only.
- `token_refresh`: refresh OAuth credentials without exposing token values.
- `erp_sync`: ingest supported ERP exports and uploaded files.

The next implementation task is connecting `transform` to GCS and BigQuery. It
must process only new GCS objects, record outcomes in a BigQuery control table,
use idempotent writes, and preserve correct HR and HRV delta boundaries.
