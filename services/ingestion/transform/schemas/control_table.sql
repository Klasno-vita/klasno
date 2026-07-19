CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.transform_control` (
  object_key STRING NOT NULL,
  bucket STRING NOT NULL,
  object_name STRING NOT NULL,
  generation STRING NOT NULL,
  status STRING NOT NULL,
  selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  error_message STRING,
  metric_rows INT64,
  sleep_rows INT64
)
PARTITION BY DATE(processed_at)
CLUSTER BY status, object_name;
