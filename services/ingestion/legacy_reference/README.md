# Legacy Reference

Old Dataproc transformation files exported from Cloud Shell.

These files are reference only:

- `health_transform_to_bq.py`
- `submit_all_health_jobs.sh`

Do not redeploy Dataproc from this folder. The Spark parser is useful because it
documents the raw Google Health JSON shape and the previous BigQuery table
fields. The new implementation target is `services/ingestion/transform`, backed
by Cloud Run Jobs and BigQuery `MERGE` operations.
