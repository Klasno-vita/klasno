# ingestion jobs

Cloud Run Jobs (scheduled, not serving):

- `fitbit_sync.py` — pull Fitbit data -> GCS -> BigQuery raw
- `transform.py` — raw -> metrics -> marts
- `token_refresh.py` — refresh expiring OAuth tokens
- `erp_processor.py` — process uploaded ERP files
