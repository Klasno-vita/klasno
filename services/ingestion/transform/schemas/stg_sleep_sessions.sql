CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_sleep_sessions` (
  student_id STRING NOT NULL,
  sleep_date DATE NOT NULL,
  log_id STRING NOT NULL,
  start_time TIMESTAMP NOT NULL,
  end_time TIMESTAMP NOT NULL,
  duration_minutes INT64,
  efficiency FLOAT64,
  source_object_key STRING NOT NULL,
  updated_at TIMESTAMP NOT NULL,
  is_nap BOOL,
  minutes_awake INT64,
  light_sleep_minutes INT64,
  deep_sleep_minutes INT64,
  rem_sleep_minutes INT64,
  stages_status STRING
)
PARTITION BY sleep_date
CLUSTER BY student_id, log_id;
