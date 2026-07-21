# Cloud Run Transform Runbook

Use this after the puller has written raw JSON into GCS and after the transform
code has been merged to `main`.

## Variables

Set these in Cloud Shell:

```bash
export PROJECT_ID="my-dataproc-project-501019"
export REGION="asia-south1"
export BQ_LOCATION="US"
export DATASET="health_raw"
export RAW_BUCKET="health-api-raw-data-prem"
export RAW_PREFIX="health-data/raw/"
export IMAGE="asia-south1-docker.pkg.dev/${PROJECT_ID}/klasno/transform:latest"
```

For a tiny replay, narrow `RAW_PREFIX` first, for example:

```bash
export RAW_PREFIX="health-data/raw/heart-rate/start=2026-07-17/"
```

## Create BigQuery Dataset

```bash
bq --location="${BQ_LOCATION}" mk --dataset "${PROJECT_ID}:${DATASET}" || true
```

## Clean Test Transform Tables

Use this before a clean backfill when replacing the first test schema. This
deletes only the transform tables created by the early test job.

```bash
for table in \
  metric_points \
  sleep_sessions \
  stg_metric_points \
  stg_sleep_sessions \
  transform_control
do
  bq rm -f -t "${PROJECT_ID}:${DATASET}.${table}" || true
done
```

## Apply Tables

```bash
python -m pip install -r services/ingestion/transform/requirements.txt
python services/ingestion/transform/apply_schemas.py \
  --project-id "${PROJECT_ID}" \
  --dataset "${DATASET}" \
  --location "${BQ_LOCATION}"
```

## Build Image

Create the Artifact Registry repository once:

```bash
gcloud artifacts repositories create klasno \
  --repository-format=docker \
  --location="${REGION}" \
  --description="Klasno Cloud Run images" || true
```

Build from the repository root:

```bash
cat > /tmp/klasno-transform-cloudbuild.yaml <<EOF
steps:
- name: gcr.io/cloud-builders/docker
  args:
  - build
  - -f
  - services/ingestion/transform/Dockerfile
  - -t
  - ${IMAGE}
  - .
images:
- ${IMAGE}
EOF

gcloud builds submit . \
  --config /tmp/klasno-transform-cloudbuild.yaml \
  --project="${PROJECT_ID}"
```

## Deploy Job

```bash
gcloud run jobs deploy klasno-transform \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --set-env-vars="KLASNO_GCP_PROJECT=${PROJECT_ID},KLASNO_RAW_BUCKET=${RAW_BUCKET},KLASNO_RAW_PREFIX=${RAW_PREFIX},KLASNO_BQ_DATASET=${DATASET},KLASNO_TRANSFORM_BATCH_LIMIT=200,KLASNO_DEFAULT_STUDENT_ID=default-student"
```

## Execute Tiny Replay

```bash
gcloud run jobs execute klasno-transform \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --wait
```

## Verify BigQuery Output

```bash
bq query --use_legacy_sql=false \
"SELECT 'heart_rate_points' AS table_name, COUNT(*) AS row_count FROM \`${PROJECT_ID}.${DATASET}.heart_rate_points\`
 UNION ALL SELECT 'heart_rate_variability_points', COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.heart_rate_variability_points\`
 UNION ALL SELECT 'daily_heart_rate_variability_points', COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.daily_heart_rate_variability_points\`
 UNION ALL SELECT 'steps_points', COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.steps_points\`
 UNION ALL SELECT 'active_minutes_points', COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.active_minutes_points\`
 UNION ALL SELECT 'active_zone_minutes_points', COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.active_zone_minutes_points\`
 UNION ALL SELECT 'active_energy_burned_points', COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.active_energy_burned_points\`
 UNION ALL SELECT 'activity_level_points', COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.activity_level_points\`
 UNION ALL SELECT 'sedentary_period_points', COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.sedentary_period_points\`
 UNION ALL SELECT 'daily_resting_heart_rate_points', COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.daily_resting_heart_rate_points\`
 UNION ALL SELECT 'sleep_sessions', COUNT(*) FROM \`${PROJECT_ID}.${DATASET}.sleep_sessions\`
 ORDER BY row_count DESC"
```

```bash
bq query --use_legacy_sql=false \
"SELECT status, COUNT(*) AS files
 FROM \`${PROJECT_ID}.${DATASET}.transform_control\`
 GROUP BY status"
```

Run the job repeatedly until the control-table count stops increasing. Each run
skips files already marked `success` and continues through the oldest remaining
`start=YYYY-MM-DD` paths first.
