# Transform

Cloud Run Job package for converting raw health JSON from GCS into BigQuery
metric tables and derived analytics.

This first repo version contains the testable transform core:

- select only raw objects not successfully recorded in the control table
- keep failed or in-progress control-table rows retryable
- dedupe metric rows using BigQuery-style merge keys
- calculate HR and HRV deltas without crossing student, metric, or date boundaries
- upsert sleep rows by `(student_id, sleep_date, log_id)`
- parse raw puller JSON for heart rate, HRV, steps, and sleep

The next adapter step is to connect this package to GCS object listing, raw JSON
downloads, BigQuery `MERGE` statements, and the transform control table.
