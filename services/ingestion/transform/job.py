from dataclasses import dataclass
import os

from services.ingestion.transform.file_selection import select_unprocessed_objects
from services.ingestion.transform.metrics import attach_delta_boundaries
from services.ingestion.transform.models import MetricPoint, ProcessedObject, RawObject, SleepRow
from services.ingestion.transform.parser import parse_raw_payload
from services.ingestion.transform.sleep import upsert_sleep_rows


@dataclass(frozen=True)
class TransformConfig:
    raw_bucket: str
    raw_prefix: str
    batch_limit: int
    bq_dataset: str
    control_table: str

    @classmethod
    def from_env(cls) -> "TransformConfig":
        return cls(
            raw_bucket=_required_env("KLASNO_RAW_BUCKET"),
            raw_prefix=os.getenv("KLASNO_RAW_PREFIX", ""),
            batch_limit=int(os.getenv("KLASNO_TRANSFORM_BATCH_LIMIT", "500")),
            bq_dataset=_required_env("KLASNO_BQ_DATASET"),
            control_table=os.getenv("KLASNO_TRANSFORM_CONTROL_TABLE", "transform_control"),
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
    raise NotImplementedError(
        "GCS and BigQuery adapters are not imported yet. "
        f"Configured bucket={config.raw_bucket!r}, dataset={config.bq_dataset!r}."
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


if __name__ == "__main__":
    main()
