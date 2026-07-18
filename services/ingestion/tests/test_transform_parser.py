from datetime import UTC, datetime

from services.ingestion.transform.parser import infer_endpoint_from_object_key, parse_raw_payload


def test_infers_endpoint_from_raw_gcs_object_key() -> None:
    endpoint = infer_endpoint_from_object_key(
        "gs://health-api-raw-data-prem/health-data/raw/heart-rate/start=2026-07-17/data.json#1"
    )

    assert endpoint == "heart-rate"


def test_parses_heart_rate_points_to_metric_rows_in_ist() -> None:
    parsed = parse_raw_payload(
        {
            "success": True,
            "dataPoints": [
                {
                    "heartRate": {
                        "sampleTime": {"physicalTime": "2026-07-17T04:30:00Z"},
                        "beatsPerMinute": "72",
                    }
                }
            ],
        },
        source_object_key="gs://bucket/health-data/raw/heart-rate/file.json#1",
        student_id="student-a",
        raw_updated_at=datetime(2026, 7, 17, tzinfo=UTC),
    )

    assert len(parsed.metric_points) == 1
    point = parsed.metric_points[0]
    assert point.student_id == "student-a"
    assert point.metric == "heart_rate"
    assert point.local_date.isoformat() == "2026-07-17"
    assert point.local_time.isoformat() == "10:00:00"
    assert point.value == 72


def test_parses_hrv_rmssd_points() -> None:
    parsed = parse_raw_payload(
        {
            "dataPoints": [
                {
                    "heartRateVariability": {
                        "sampleTime": {"physicalTime": "2026-07-17T05:00:00Z"},
                        "rootMeanSquareOfSuccessiveDifferencesMilliseconds": 31.5,
                    }
                }
            ]
        },
        source_object_key="gs://bucket/health-data/raw/heart-rate-variability/file.json#1",
        student_id="student-a",
        raw_updated_at=datetime(2026, 7, 17, tzinfo=UTC),
    )

    assert [(point.metric, point.value) for point in parsed.metric_points] == [("hrv_rmssd", 31.5)]


def test_parses_steps_with_interval_metadata() -> None:
    parsed = parse_raw_payload(
        {
            "dataPoints": [
                {
                    "steps": {
                        "interval": {
                            "startTime": "2026-07-17T04:30:00Z",
                            "endTime": "2026-07-17T04:45:00Z",
                        },
                        "count": "250",
                    }
                }
            ]
        },
        source_object_key="gs://bucket/health-data/raw/steps/file.json#1",
        student_id="student-a",
        raw_updated_at=datetime(2026, 7, 17, tzinfo=UTC),
    )

    point = parsed.metric_points[0]
    assert point.metric == "steps"
    assert point.value == 250
    assert point.metadata == {
        "end_local": "2026-07-17T10:15:00+05:30",
        "duration_seconds": 900,
    }


def test_parses_sleep_and_keeps_latest_duplicate_session() -> None:
    parsed = parse_raw_payload(
        {
            "dataPoints": [
                {
                    "sleep": {
                        "interval": {
                            "startTime": "2026-07-16T17:00:00Z",
                            "endTime": "2026-07-17T00:00:00Z",
                        },
                        "updateTime": "2026-07-17T00:05:00Z",
                        "metadata": {"externalId": "sleep-1", "stagesStatus": "COMPLETE"},
                        "summary": {
                            "minutesInSleepPeriod": "420",
                            "minutesAsleep": "390",
                            "minutesAwake": "30",
                            "stagesSummary": [
                                {"type": "LIGHT", "minutes": "220"},
                                {"type": "DEEP", "minutes": "90"},
                                {"type": "REM", "minutes": "80"},
                            ],
                        },
                    }
                },
                {
                    "sleep": {
                        "interval": {
                            "startTime": "2026-07-16T17:00:00Z",
                            "endTime": "2026-07-17T00:00:00Z",
                        },
                        "updateTime": "2026-07-17T00:01:00Z",
                        "metadata": {"externalId": "sleep-1"},
                        "summary": {"minutesInSleepPeriod": "420", "minutesAsleep": "360"},
                    }
                },
            ]
        },
        source_object_key="gs://bucket/health-data/raw/sleep/file.json#1",
        student_id="student-a",
        raw_updated_at=datetime(2026, 7, 17, tzinfo=UTC),
    )

    assert len(parsed.sleep_rows) == 1
    row = parsed.sleep_rows[0]
    assert row.log_id == "sleep-1"
    assert row.sleep_date.isoformat() == "2026-07-16"
    assert row.duration_minutes == 390
    assert row.efficiency == 92.86
    assert row.minutes_awake == 30
    assert row.deep_sleep_minutes == 90
    assert row.rem_sleep_minutes == 80
