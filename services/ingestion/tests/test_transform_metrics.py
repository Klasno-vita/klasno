from datetime import date, time

from services.ingestion.transform.metrics import attach_delta_boundaries
from services.ingestion.transform.models import MetricPoint


def point(
    student_id: str,
    metric: str,
    local_date: date,
    local_time: time,
    value: float,
) -> MetricPoint:
    return MetricPoint(
        student_id=student_id,
        metric=metric,
        local_date=local_date,
        local_time=local_time,
        value=value,
        source_object_key="gs://raw/source.json#1",
    )


def test_hr_delta_resets_at_date_boundary() -> None:
    rows = attach_delta_boundaries(
        [
            point("student-a", "heart_rate", date(2026, 7, 16), time(23, 59), 80),
            point("student-a", "heart_rate", date(2026, 7, 17), time(0, 1), 82),
            point("student-a", "heart_rate", date(2026, 7, 17), time(0, 2), 85),
        ]
    )

    assert [row.delta_from_prev for row in rows] == [None, None, 3]


def test_hrv_delta_resets_at_metric_and_student_boundaries() -> None:
    rows = attach_delta_boundaries(
        [
            point("student-a", "heart_rate", date(2026, 7, 17), time(9, 0), 80),
            point("student-a", "hrv_rmssd", date(2026, 7, 17), time(9, 0), 35),
            point("student-a", "hrv_rmssd", date(2026, 7, 17), time(9, 5), 31),
            point("student-b", "hrv_rmssd", date(2026, 7, 17), time(9, 5), 50),
        ]
    )

    assert [row.delta_from_prev for row in rows] == [None, None, -4, None]


def test_duplicate_metric_points_keep_last_value_for_merge_key() -> None:
    rows = attach_delta_boundaries(
        [
            point("student-a", "heart_rate", date(2026, 7, 17), time(9, 0), 80),
            point("student-a", "heart_rate", date(2026, 7, 17), time(9, 0), 81),
        ]
    )

    assert len(rows) == 1
    assert rows[0].value == 81
    assert rows[0].delta_from_prev is None
