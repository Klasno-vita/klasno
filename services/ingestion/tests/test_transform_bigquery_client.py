from datetime import UTC, date, datetime, time

import pytest

from services.ingestion.transform.bigquery_client import INSERT_CHUNK_SIZE, BigQueryTransformStore
from services.ingestion.transform.bigquery_sql import metric_merge_sql, sleep_merge_sql
from services.ingestion.transform.table_routing import target_table_for_source
from services.ingestion.transform.models import MetricRow, RawObject, SleepRow


class FakeJob:
    def __init__(self, rows: list[dict[str, object]] | None = None) -> None:
        self._rows = rows or []

    def result(self) -> list[dict[str, object]]:
        return self._rows


class FakeBigQueryClient:
    def __init__(self) -> None:
        self.queries: list[str] = []
        self.inserted: dict[str, list[dict[str, object]]] = {}
        self.insert_calls: list[tuple[str, int]] = []
        self.insert_errors: list[object] = []

    def query(self, query: str) -> FakeJob:
        self.queries.append(query)
        if "SELECT object_key, status" in query:
            return FakeJob([{"object_key": "gs://bucket/file.json#1", "status": "success"}])
        return FakeJob()

    def insert_rows_json(self, table: str, json_rows: list[dict[str, object]]) -> list[object]:
        self.inserted.setdefault(table, []).extend(json_rows)
        self.insert_calls.append((table, len(json_rows)))
        return self.insert_errors


def test_lists_processed_objects_from_control_table() -> None:
    client = FakeBigQueryClient()
    store = BigQueryTransformStore(client, project_id="project", dataset="health_raw")

    rows = store.list_processed_objects("transform_control")

    assert rows[0].object_key == "gs://bucket/file.json#1"
    assert rows[0].status == "success"
    assert "`project.health_raw.transform_control`" in client.queries[0]


def test_stages_metric_rows_as_json() -> None:
    client = FakeBigQueryClient()
    store = BigQueryTransformStore(client, project_id="project", dataset="health_raw")
    row = MetricRow(
        student_id="student-a",
        metric="heart_rate",
        local_date=date(2026, 7, 17),
        local_time=time(10, 0),
        value=72,
        delta_from_prev=None,
        source_object_key="gs://bucket/hr.json#1",
        metadata={"zone": "out_of_range"},
    )

    count = store.stage_metric_rows([row], "stg_metric_points")

    assert count == 1
    assert client.inserted["project.health_raw.stg_metric_points"][0]["metric"] == "heart_rate"
    assert client.inserted["project.health_raw.stg_metric_points"][0]["metadata_json"] == (
        '{"zone":"out_of_range"}'
    )


def test_stages_metric_rows_in_chunks() -> None:
    client = FakeBigQueryClient()
    store = BigQueryTransformStore(client, project_id="project", dataset="health_raw")
    rows = [
        MetricRow(
            student_id="student-a",
            metric="heart_rate",
            local_date=date(2026, 7, 17),
            local_time=time(hour=index % 24, minute=index % 60),
            value=72,
            delta_from_prev=None,
            source_object_key=f"gs://bucket/hr.json#{index}",
        )
        for index in range(INSERT_CHUNK_SIZE + 1)
    ]

    count = store.stage_metric_rows(rows, "stg_metric_points")

    assert count == INSERT_CHUNK_SIZE + 1
    assert client.insert_calls == [
        ("project.health_raw.stg_metric_points", INSERT_CHUNK_SIZE),
        ("project.health_raw.stg_metric_points", 1),
    ]


def test_staging_raises_on_bigquery_insert_errors() -> None:
    client = FakeBigQueryClient()
    client.insert_errors = [{"index": 0, "errors": ["bad row"]}]
    store = BigQueryTransformStore(client, project_id="project", dataset="health_raw")
    row = SleepRow(
        student_id="student-a",
        sleep_date=date(2026, 7, 17),
        log_id="sleep-1",
        start_time=datetime(2026, 7, 16, 22, 0, tzinfo=UTC),
        end_time=datetime(2026, 7, 17, 5, 0, tzinfo=UTC),
        duration_minutes=420,
        efficiency=92.0,
        source_object_key="gs://bucket/sleep.json#1",
        updated_at=datetime(2026, 7, 17, 5, 5, tzinfo=UTC),
    )

    with pytest.raises(RuntimeError, match="BigQuery sleep staging failed"):
        store.stage_sleep_rows([row], "stg_sleep_sessions")


def test_marks_raw_objects_successful_in_control_table() -> None:
    client = FakeBigQueryClient()
    store = BigQueryTransformStore(client, project_id="project", dataset="health_raw")
    raw_object = RawObject(
        bucket="raw-bucket",
        name="health-data/raw/heart-rate/file.json",
        generation="7",
        updated_at=datetime(2026, 7, 17, 10, 0, tzinfo=UTC),
    )

    count = store.mark_objects_successful(
        [raw_object],
        "transform_control",
        metric_rows=5,
        sleep_rows=0,
    )

    assert count == 1
    row = client.inserted["project.health_raw.transform_control"][0]
    assert row["object_key"] == raw_object.object_key
    assert row["status"] == "success"
    assert row["metric_rows"] == 5


def test_merge_sql_uses_expected_keys() -> None:
    metric_sql = metric_merge_sql("project.health_raw.metric_points", "project.health_raw.stg")
    sleep_sql = sleep_merge_sql("project.health_raw.sleep_sessions", "project.health_raw.stg_sleep")

    assert "target.student_id = source.student_id" in metric_sql
    assert "target.metric = source.metric" in metric_sql
    assert "target.local_date = source.local_date" in metric_sql
    assert "target.local_time = source.local_time" in metric_sql
    assert "target.sleep_date = source.sleep_date" in sleep_sql
    assert "target.log_id = source.log_id" in sleep_sql
    assert "source.updated_at >= target.updated_at" in sleep_sql


def test_routes_metric_rows_by_source_folder() -> None:
    assert (
        target_table_for_source(
            "gs://bucket/health-data/raw/heart-rate-variability/start=2026-06-23/file.json#1"
        )
        == "heart_rate_variability_points"
    )
    assert (
        target_table_for_source("gs://bucket/health-data/raw/steps/start=2026-06-23/file.json#1")
        == "steps_points"
    )
