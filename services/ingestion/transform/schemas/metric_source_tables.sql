CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.heart_rate_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY local_date
CLUSTER BY student_id, metric;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.heart_rate_variability_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY local_date
CLUSTER BY student_id, metric;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.daily_heart_rate_variability_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY local_date
CLUSTER BY student_id, metric;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.steps_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY local_date
CLUSTER BY student_id, metric;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.active_minutes_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY local_date
CLUSTER BY student_id, metric;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.active_zone_minutes_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY local_date
CLUSTER BY student_id, metric;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.active_energy_burned_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY local_date
CLUSTER BY student_id, metric;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.activity_level_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY local_date
CLUSTER BY student_id, metric;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.sedentary_period_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY local_date
CLUSTER BY student_id, metric;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.daily_resting_heart_rate_points` (
  student_id STRING NOT NULL,
  metric STRING NOT NULL,
  local_date DATE NOT NULL,
  local_time TIME NOT NULL,
  value FLOAT64,
  delta_from_prev FLOAT64,
  source_object_key STRING NOT NULL,
  metadata_json JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY local_date
CLUSTER BY student_id, metric;

CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_heart_rate_points` LIKE `{project_id}.{dataset}.heart_rate_points`;
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_heart_rate_variability_points` LIKE `{project_id}.{dataset}.heart_rate_variability_points`;
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_daily_heart_rate_variability_points` LIKE `{project_id}.{dataset}.daily_heart_rate_variability_points`;
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_steps_points` LIKE `{project_id}.{dataset}.steps_points`;
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_active_minutes_points` LIKE `{project_id}.{dataset}.active_minutes_points`;
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_active_zone_minutes_points` LIKE `{project_id}.{dataset}.active_zone_minutes_points`;
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_active_energy_burned_points` LIKE `{project_id}.{dataset}.active_energy_burned_points`;
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_activity_level_points` LIKE `{project_id}.{dataset}.activity_level_points`;
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_sedentary_period_points` LIKE `{project_id}.{dataset}.sedentary_period_points`;
CREATE TABLE IF NOT EXISTS `{project_id}.{dataset}.stg_daily_resting_heart_rate_points` LIKE `{project_id}.{dataset}.daily_resting_heart_rate_points`;
