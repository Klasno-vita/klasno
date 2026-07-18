from datetime import UTC, date, datetime, timedelta

from services.ingestion.transform.models import SleepRow
from services.ingestion.transform.sleep import upsert_sleep_rows


def sleep_row(log_id: str, duration_minutes: int, updated_at: datetime) -> SleepRow:
    start_time = datetime(2026, 7, 16, 22, 30, tzinfo=UTC)
    return SleepRow(
        student_id="student-a",
        sleep_date=date(2026, 7, 17),
        log_id=log_id,
        start_time=start_time,
        end_time=start_time + timedelta(minutes=duration_minutes),
        duration_minutes=duration_minutes,
        efficiency=92.0,
        source_object_key="gs://raw/sleep.json#1",
        updated_at=updated_at,
    )


def test_sleep_upsert_replaces_existing_row_when_incoming_is_newer() -> None:
    existing = sleep_row("sleep-1", 420, datetime(2026, 7, 17, 5, 0, tzinfo=UTC))
    incoming = sleep_row("sleep-1", 450, datetime(2026, 7, 17, 5, 5, tzinfo=UTC))

    rows = upsert_sleep_rows([existing], [incoming])

    assert rows == [incoming]


def test_sleep_upsert_ignores_stale_replay() -> None:
    existing = sleep_row("sleep-1", 450, datetime(2026, 7, 17, 5, 5, tzinfo=UTC))
    replay = sleep_row("sleep-1", 420, datetime(2026, 7, 17, 5, 0, tzinfo=UTC))

    rows = upsert_sleep_rows([existing], [replay])

    assert rows == [existing]
