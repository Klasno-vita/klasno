from collections.abc import Iterable

from services.ingestion.transform.models import SleepRow


def upsert_sleep_rows(existing_rows: Iterable[SleepRow], incoming_rows: Iterable[SleepRow]) -> list[SleepRow]:
    """Apply sleep upserts using the same key BigQuery MERGE will use."""

    rows_by_key = {row.upsert_key: row for row in existing_rows}
    for row in incoming_rows:
        current = rows_by_key.get(row.upsert_key)
        if current is None or row.updated_at >= current.updated_at:
            rows_by_key[row.upsert_key] = row

    return sorted(rows_by_key.values(), key=lambda row: (row.student_id, row.sleep_date, row.log_id))
