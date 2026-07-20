from collections.abc import Iterable
from typing import Protocol

from services.ingestion.transform.bigquery_sql import (
    control_success_row,
    control_table_ddl,
    metric_merge_sql,
    metric_row_to_bq,
    processed_object_from_bq,
    processed_objects_query,
    sleep_merge_sql,
    sleep_row_to_bq,
)
from services.ingestion.transform.models import MetricRow, ProcessedObject, RawObject, SleepRow

INSERT_CHUNK_SIZE = 500


class BigQueryJob(Protocol):
    def result(self) -> object: ...


class BigQueryClient(Protocol):
    def query(self, query: str) -> BigQueryJob: ...

    def insert_rows_json(self, table: str, json_rows: list[dict[str, object]]) -> list[object]: ...


class BigQueryTransformStore:
    def __init__(self, client: BigQueryClient, *, project_id: str, dataset: str) -> None:
        self._client = client
        self.project_id = project_id
        self.dataset = dataset

    def table_id(self, table_name: str) -> str:
        return f"{self.project_id}.{self.dataset}.{table_name}"

    def _insert_json_rows(self, table: str, json_rows: list[dict[str, object]]) -> None:
        table_id = self.table_id(table)
        for start in range(0, len(json_rows), INSERT_CHUNK_SIZE):
            chunk = json_rows[start : start + INSERT_CHUNK_SIZE]
            errors = self._client.insert_rows_json(table_id, chunk)
            if errors:
                raise RuntimeError(f"BigQuery insert failed for {table}: {errors}")

    def ensure_control_table(self, control_table: str) -> None:
        self._client.query(control_table_ddl(self.table_id(control_table))).result()

    def list_processed_objects(self, control_table: str) -> list[ProcessedObject]:
        rows = self._client.query(processed_objects_query(self.table_id(control_table))).result()
        return [processed_object_from_bq(dict(row)) for row in rows]

    def stage_metric_rows(self, rows: Iterable[MetricRow], staging_table: str) -> int:
        json_rows = [metric_row_to_bq(row) for row in rows]
        if not json_rows:
            return 0
        try:
            self._insert_json_rows(staging_table, json_rows)
        except RuntimeError as exc:
            raise RuntimeError(f"BigQuery metric staging failed: {exc}") from exc
        return len(json_rows)

    def stage_sleep_rows(self, rows: Iterable[SleepRow], staging_table: str) -> int:
        json_rows = [sleep_row_to_bq(row) for row in rows]
        if not json_rows:
            return 0
        try:
            self._insert_json_rows(staging_table, json_rows)
        except RuntimeError as exc:
            raise RuntimeError(f"BigQuery sleep staging failed: {exc}") from exc
        return len(json_rows)

    def merge_metric_rows(self, *, target_table: str, staging_table: str) -> None:
        self._client.query(
            metric_merge_sql(self.table_id(target_table), self.table_id(staging_table))
        ).result()

    def merge_sleep_rows(self, *, target_table: str, staging_table: str) -> None:
        self._client.query(
            sleep_merge_sql(self.table_id(target_table), self.table_id(staging_table))
        ).result()

    def mark_objects_successful(
        self,
        raw_objects: Iterable[RawObject],
        control_table: str,
        *,
        metric_rows: int,
        sleep_rows: int,
    ) -> int:
        json_rows = [
            control_success_row(raw_object, metric_rows=metric_rows, sleep_rows=sleep_rows)
            for raw_object in raw_objects
        ]
        if not json_rows:
            return 0
        try:
            self._insert_json_rows(control_table, json_rows)
        except RuntimeError as exc:
            raise RuntimeError(f"BigQuery control-table insert failed: {exc}") from exc
        return len(json_rows)
