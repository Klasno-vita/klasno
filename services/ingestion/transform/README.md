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
- list and read raw JSON directly from GCS
- prepare BigQuery control-table rows and metric/sleep `MERGE` statements
- package the transform as a Cloud Run Job container

The next production step is to create the BigQuery target and staging table
schemas, run the job against a tiny GCS prefix, and compare output with the
legacy Dataproc reference before scheduling it after the daily pull.
