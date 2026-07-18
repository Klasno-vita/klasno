from datetime import UTC, datetime

from services.ingestion.transform.file_selection import select_unprocessed_objects
from services.ingestion.transform.models import ProcessedObject, RawObject


def test_selects_only_unprocessed_objects_in_stable_order() -> None:
    older = RawObject(
        bucket="raw-bucket",
        name="fitbit/student-a/hr/2026-07-16.json",
        generation="1",
        updated_at=datetime(2026, 7, 16, 10, 0, tzinfo=UTC),
    )
    newer = RawObject(
        bucket="raw-bucket",
        name="fitbit/student-a/hrv/2026-07-16.json",
        generation="1",
        updated_at=datetime(2026, 7, 16, 10, 5, tzinfo=UTC),
    )
    already_processed = ProcessedObject(object_key=older.object_key, status="success")

    selected = select_unprocessed_objects([newer, older], [already_processed], prefix="fitbit/")

    assert selected == [newer]


def test_failed_control_rows_are_retryable() -> None:
    raw_object = RawObject(
        bucket="raw-bucket",
        name="fitbit/student-a/sleep/2026-07-16.json",
        generation="2",
        updated_at=datetime(2026, 7, 16, 10, 10, tzinfo=UTC),
    )
    failed_record = ProcessedObject(object_key=raw_object.object_key, status="failed")

    selected = select_unprocessed_objects([raw_object], [failed_record], prefix="fitbit/")

    assert selected == [raw_object]
