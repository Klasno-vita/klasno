from services.ingestion.transform.models import MetricRow, ProcessedObject, RawObject, SleepRow


def control_table_ddl(table_id: str) -> str:
    return f"""
CREATE TABLE IF NOT EXISTS `{table_id}` (
  object_key STRING NOT NULL,
  bucket STRING NOT NULL,
  object_name STRING NOT NULL,
  generation STRING NOT NULL,
  status STRING NOT NULL,
  selected_at TIMESTAMP,
  processed_at TIMESTAMP,
  error_message STRING,
  metric_rows INT64,
  sleep_rows INT64
)
""".strip()


def processed_objects_query(control_table_id: str) -> str:
    return f"""
SELECT object_key, status
FROM `{control_table_id}`
WHERE status IN ('success', 'succeeded', 'processed')
""".strip()


def metric_merge_sql(target_table_id: str, staging_table_id: str) -> str:
    return f"""
MERGE `{target_table_id}` AS target
USING `{staging_table_id}` AS source
ON target.student_id = source.student_id
  AND target.metric = source.metric
  AND target.local_date = source.local_date
  AND target.local_time = source.local_time
WHEN MATCHED THEN UPDATE SET
  value = source.value,
  delta_from_prev = source.delta_from_prev,
  source_object_key = source.source_object_key,
  metadata_json = source.metadata_json,
  updated_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (
  student_id,
  metric,
  local_date,
  local_time,
  value,
  delta_from_prev,
  source_object_key,
  metadata_json,
  created_at,
  updated_at
) VALUES (
  source.student_id,
  source.metric,
  source.local_date,
  source.local_time,
  source.value,
  source.delta_from_prev,
  source.source_object_key,
  source.metadata_json,
  CURRENT_TIMESTAMP(),
  CURRENT_TIMESTAMP()
)
""".strip()


def sleep_merge_sql(target_table_id: str, staging_table_id: str) -> str:
    return f"""
MERGE `{target_table_id}` AS target
USING `{staging_table_id}` AS source
ON target.student_id = source.student_id
  AND target.sleep_date = source.sleep_date
  AND target.log_id = source.log_id
WHEN MATCHED AND source.updated_at >= target.updated_at THEN UPDATE SET
  start_time = source.start_time,
  end_time = source.end_time,
  duration_minutes = source.duration_minutes,
  efficiency = source.efficiency,
  source_object_key = source.source_object_key,
  updated_at = source.updated_at,
  is_nap = source.is_nap,
  minutes_awake = source.minutes_awake,
  light_sleep_minutes = source.light_sleep_minutes,
  deep_sleep_minutes = source.deep_sleep_minutes,
  rem_sleep_minutes = source.rem_sleep_minutes,
  stages_status = source.stages_status
WHEN NOT MATCHED THEN INSERT (
  student_id,
  sleep_date,
  log_id,
  start_time,
  end_time,
  duration_minutes,
  efficiency,
  source_object_key,
  updated_at,
  is_nap,
  minutes_awake,
  light_sleep_minutes,
  deep_sleep_minutes,
  rem_sleep_minutes,
  stages_status
) VALUES (
  source.student_id,
  source.sleep_date,
  source.log_id,
  source.start_time,
  source.end_time,
  source.duration_minutes,
  source.efficiency,
  source.source_object_key,
  source.updated_at,
  source.is_nap,
  source.minutes_awake,
  source.light_sleep_minutes,
  source.deep_sleep_minutes,
  source.rem_sleep_minutes,
  source.stages_status
)
""".strip()


def control_success_row(
    raw_object: RawObject,
    *,
    metric_rows: int,
    sleep_rows: int,
) -> dict[str, object]:
    return {
        "object_key": raw_object.object_key,
        "bucket": raw_object.bucket,
        "object_name": raw_object.name,
        "generation": raw_object.generation,
        "status": "success",
        "metric_rows": metric_rows,
        "sleep_rows": sleep_rows,
    }


def metric_row_to_bq(row: MetricRow) -> dict[str, object]:
    return {
        "student_id": row.student_id,
        "metric": row.metric,
        "local_date": row.local_date.isoformat(),
        "local_time": row.local_time.isoformat(),
        "value": row.value,
        "delta_from_prev": row.delta_from_prev,
        "source_object_key": row.source_object_key,
        "metadata_json": row.metadata,
    }


def sleep_row_to_bq(row: SleepRow) -> dict[str, object]:
    return {
        "student_id": row.student_id,
        "sleep_date": row.sleep_date.isoformat(),
        "log_id": row.log_id,
        "start_time": row.start_time.isoformat(),
        "end_time": row.end_time.isoformat(),
        "duration_minutes": row.duration_minutes,
        "efficiency": row.efficiency,
        "source_object_key": row.source_object_key,
        "updated_at": row.updated_at.isoformat(),
        "is_nap": row.is_nap,
        "minutes_awake": row.minutes_awake,
        "light_sleep_minutes": row.light_sleep_minutes,
        "deep_sleep_minutes": row.deep_sleep_minutes,
        "rem_sleep_minutes": row.rem_sleep_minutes,
        "stages_status": row.stages_status,
    }


def processed_object_from_bq(row: dict[str, object]) -> ProcessedObject:
    return ProcessedObject(object_key=str(row["object_key"]), status=str(row["status"]))
