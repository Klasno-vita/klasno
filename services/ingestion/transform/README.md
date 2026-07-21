# Transform

Cloud Run Job package for converting raw health JSON from GCS into BigQuery
metric tables and derived analytics.

This first repo version contains the testable transform core:

- select only raw objects not successfully recorded in the control table
- keep failed or in-progress control-table rows retryable
- dedupe metric rows using BigQuery-style merge keys
- calculate HR and HRV deltas without crossing student, metric, or date boundaries
- upsert sleep rows by `(student_id, sleep_date, log_id)`
- parse raw puller JSON for heart rate, HRV, steps, sleep, activity, sedentary,
  daily resting heart rate, and daily HRV
- list and read raw JSON directly from GCS
- route metric rows into one transformed BigQuery table per raw source folder
- prepare BigQuery control-table rows and metric/sleep `MERGE` statements
- package the transform as a Cloud Run Job container

The job processes the oldest unprocessed `start=YYYY-MM-DD` raw paths first.
After backfill catches up, later runs skip already successful files and continue
with fresh raw files.

Schema SQL lives in `schemas/`. Use `apply_schemas.py` before deploying the
Cloud Run Job.

Supported raw folders:

- `heart-rate`
- `heart-rate-variability`
- `steps`
- `sleep`
- `active-minutes`
- `active-zone-minutes`
- `active-energy-burned`
- `activity-level`
- `sedentary-period`
- `daily-resting-heart-rate`
- `daily-heart-rate-variability`

Transformed metric table names use the source folder plus `_points`, for
example `heart_rate_points`, `heart_rate_variability_points`, and
`active_energy_burned_points`.
