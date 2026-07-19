CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_metric_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON
)
PARTITION BY local_date
CLUSTER BY student_id, metric;
