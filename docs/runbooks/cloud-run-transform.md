# Cloud Run Transform Runbook

Use this after the puller has written raw JSON into GCS and after the transform
code has been merged to `main`.

## Variables

Set these in Cloud Shell:

```bash
export PROJECT_ID="my-dataproc-project-501019"
export REGION="asia-south1"
export BQ_LOCATION="asia-south1"
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
gcloud builds submit . --tag "${IMAGE}" \
  --project="${PROJECT_ID}"
```

## Deploy Job

```bash
gcloud run jobs deploy klasno-transform \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --set-env-vars="KLASNO_GCP_PROJECT=${PROJECT_ID},KLASNO_RAW_BUCKET=${RAW_BUCKET},KLASNO_RAW_PREFIX=${RAW_PREFIX},KLASNO_BQ_DATASET=${DATASET},KLASNO_TRANSFORM_BATCH_LIMIT=20,KLASNO_DEFAULT_STUDENT_ID=default-student"
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
"SELECT metric, COUNT(*) AS rows
 FROM \`${PROJECT_ID}.${DATASET}.metric_points\`
 GROUP BY metric
 ORDER BY rows DESC"
```

```bash
bq query --use_legacy_sql=false \
"SELECT status, COUNT(*) AS files
 FROM \`${PROJECT_ID}.${DATASET}.transform_control\`
 GROUP BY status"
```

Only widen `RAW_PREFIX` after the tiny replay looks correct.
