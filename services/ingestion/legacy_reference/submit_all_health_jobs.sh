#!/bin/bash

set -e

PROJECT_ID="my-dataproc-project-501019"
REGION="us-central1"
CLUSTER="health-dataproc-cluster"
SCRIPT_URI="gs://health-api-raw-data-prem/scripts/health_transform_to_bq.py"
TEMP_BUCKET="health-api-bq-temp-prem"
BQ_DATASET="health_raw"

echo "Starting all health metric Dataproc jobs..."

submit_job () {
  METRIC=$1
  INPUT_URI=$2
  TABLE_NAME=$3

  echo "Submitting job for metric: $METRIC"

  gcloud dataproc jobs submit pyspark "$SCRIPT_URI" \
    --cluster="$CLUSTER" \
    --region="$REGION" \
    -- \
    --input_uri="$INPUT_URI" \
    --metric="$METRIC" \
    --output_table="$PROJECT_ID.$BQ_DATASET.$TABLE_NAME" \
    --temp_bucket="$TEMP_BUCKET" \
    --write_mode="overwrite"

  echo "Completed job for metric: $METRIC"
  echo "---------------------------------------"
}

submit_job "steps" \
"gs://health-api-raw-data-prem/health-data/raw/steps/start=2026-06-29/end=2026-07-04/pulled_at=2026-07-04T09-01-55Z.json" \
"steps"

submit_job "heart-rate" \
"gs://health-api-raw-data-prem/health-data/raw/heart-rate/start=2026-06-29/end=2026-07-04/pulled_at=2026-07-04T09-01-55Z.json" \
"heart_rate"

submit_job "heart-rate-variability" \
"gs://health-api-raw-data-prem/health-data/raw/heart-rate-variability/start=2026-06-29/end=2026-07-04/pulled_at=2026-07-04T09-01-55Z.json" \
"heart_rate_variability"

submit_job "active-zone-minutes" \
"gs://health-api-raw-data-prem/health-data/raw/active-zone-minutes/start=2026-06-29/end=2026-07-04/pulled_at=2026-07-04T09-01-55Z.json" \
"active_zone_minutes"

submit_job "active-energy-burned" \
"gs://health-api-raw-data-prem/health-data/raw/active-energy-burned/start=2026-06-29/end=2026-07-04/pulled_at=2026-07-04T09-01-55Z.json" \
"active_energy_burned"

submit_job "activity-level" \
"gs://health-api-raw-data-prem/health-data/raw/activity-level/start=2026-06-29/end=2026-07-04/pulled_at=2026-07-04T09-01-55Z.json" \
"activity_level"

echo "All health metric jobs completed."
