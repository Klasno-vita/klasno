from dataclasses import dataclass
import os

from services.ingestion.transform.bigquery_client import BigQueryTransformStore
from services.ingestion.transform.file_selection import select_unprocessed_objects
from services.ingestion.transform.gcs_client import GcsRawStore
from services.ingestion.transform.metrics import attach_delta_boundaries
from services.ingestion.transform.models import MetricPoint, ProcessedObject, RawObject, SleepRow
from services.ingestion.transform.parser import parse_raw_payload
from services.ingestion.transform.sleep import upsert_sleep_rows


@dataclass(frozen=True)
class TransformConfig:
    raw_bucket: str
    raw_prefix: str
    batch_limit: int
    gcp_project: str
    bq_dataset: str
    control_table: str
    metric_table: str
    metric_staging_table: str
    sleep_table: str
    sleep_staging_table: str
    student_id: str

    @classmethod
    def from_env(cls) -> "TransformConfig":
        return cls(
            raw_bucket=_required_env("KLASNO_RAW_BUCKET"),
            raw_prefix=os.getenv("KLASNO_RAW_PREFIX", ""),
            batch_limit=int(os.getenv("KLASNO_TRANSFORM_BATCH_LIMIT", "500")),
            gcp_project=_required_env("KLASNO_GCP_PROJECT"),
            bq_dataset=_required_env("KLASNO_BQ_DATASET"),
            control_table=os.getenv("KLASNO_TRANSFORM_CONTROL_TABLE", "transform_control"),
            metric_table=os.getenv("KLASNO_BQ_METRIC_TABLE", "metric_points"),
            metric_staging_table=os.getenv("KLASNO_BQ_METRIC_STAGING_TABLE", "stg_metric_points"),
            sleep_table=os.getenv("KLASNO_BQ_SLEEP_TABLE", "sleep_sessions"),
            sleep_staging_table=os.getenv("KLASNO_BQ_SLEEP_STAGING_TABLE", "stg_sleep_sessions"),
            student_id=os.getenv("KLASNO_DEFAULT_STUDENT_ID", "default-student"),
        )


@dataclass(frozen=True)
class TransformPlan:
    selected_objects: list[RawObject]
    metric_rows: int
    sleep_rows: int


def build_transform_plan(
    raw_objects: list[RawObject],
    processed_objects: list[ProcessedObject],
    metric_points: list[MetricPoint],
    existing_sleep_rows: list[SleepRow],
    incoming_sleep_rows: list[SleepRow],
    *,
    prefix: str,
    limit: int,
) -> TransformPlan:
    selected = select_unprocessed_objects(
        raw_objects,
        processed_objects,
        prefix=prefix,
        limit=limit,
    )
    metric_rows = attach_delta_boundaries(metric_points)
    sleep_rows = upsert_sleep_rows(existing_sleep_rows, incoming_sleep_rows)
    return TransformPlan(
        selected_objects=selected,
        metric_rows=len(metric_rows),
        sleep_rows=len(sleep_rows),
    )


def parse_selected_payloads(
    raw_payloads: dict[str, object],
    selected_objects: list[RawObject],
    *,
    student_id: str,
) -> tuple[list[MetricPoint], list[SleepRow]]:
    metric_points: list[MetricPoint] = []
    sleep_rows: list[SleepRow] = []

    for raw_object in selected_objects:
        payload = raw_payloads.get(raw_object.object_key)
        if payload is None:
            continue
        parsed = parse_raw_payload(
            payload,
            source_object_key=raw_object.object_key,
            student_id=student_id,
            raw_updated_at=raw_object.updated_at,
        )
        metric_points.extend(parsed.metric_points)
        sleep_rows.extend(parsed.sleep_rows)

    return metric_points, sleep_rows


def main() -> None:
    config = TransformConfig.from_env()
    run_transform(config)


def run_transform(config: TransformConfig) -> TransformPlan:
    from google.cloud import bigquery, storage

    raw_store = GcsRawStore(storage.Client(project=config.gcp_project), config.raw_bucket)
    bq_store = BigQueryTransformStore(
        bigquery.Client(project=config.gcp_project),
        project_id=config.gcp_project,
        dataset=config.bq_dataset,
    )

    bq_store.ensure_control_table(config.control_table)
    raw_objects = raw_store.list_raw_objects(prefix=config.raw_prefix)
    processed_objects = bq_store.list_processed_objects(config.control_table)
    selected_objects = select_unprocessed_objects(
        raw_objects,
        processed_objects,
        prefix=config.raw_prefix,
        limit=config.batch_limit,
    )
    raw_payloads = raw_store.read_json_payloads(selected_objects)
    metric_points, incoming_sleep_rows = parse_selected_payloads(
        raw_payloads,
        selected_objects,
        student_id=config.student_id,
    )
    metric_rows = attach_delta_boundaries(metric_points)
    sleep_rows = upsert_sleep_rows([], incoming_sleep_rows)

    bq_store.stage_metric_rows(metric_rows, config.metric_staging_table)
    bq_store.stage_sleep_rows(sleep_rows, config.sleep_staging_table)
    bq_store.merge_metric_rows(
        target_table=config.metric_table,
        staging_table=config.metric_staging_table,
    )
    bq_store.merge_sleep_rows(
        target_table=config.sleep_table,
        staging_table=config.sleep_staging_table,
    )
    bq_store.mark_objects_successful(
        selected_objects,
        config.control_table,
        metric_rows=len(metric_rows),
        sleep_rows=len(sleep_rows),
    )

    return TransformPlan(
        selected_objects=selected_objects,
        metric_rows=len(metric_rows),
        sleep_rows=len(sleep_rows),
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


if __name__ == "__main__":
    main()
