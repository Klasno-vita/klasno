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


def test_parses_activity_interval_metrics_needed_for_wellness() -> None:
    cases = [
        ("active-minutes", "activeMinutes", "minutes", "active_minutes", "20"),
        ("active-energy-burned", "activeEnergyBurned", "kcal", "active_energy_burned_kcal", "45.5"),
        ("active-zone-minutes", "activeZoneMinutes", "activeZoneMinutes", "active_zone_minutes", "8"),
    ]

    for endpoint, payload_key, value_key, metric, value in cases:
        parsed = parse_raw_payload(
            {
                "dataPoints": [
                    {
                        payload_key: {
                            "interval": {
                                "startTime": "2026-07-17T04:30:00Z",
                                "endTime": "2026-07-17T04:45:00Z",
                            },
                            value_key: value,
                            "heartRateZone": "CARDIO",
                        }
                    }
                ]
            },
            source_object_key=f"gs://bucket/health-data/raw/{endpoint}/file.json#1",
            student_id="student-a",
            raw_updated_at=datetime(2026, 7, 17, tzinfo=UTC),
        )

        point = parsed.metric_points[0]
        assert point.metric == metric
        assert point.value == float(value)
        assert point.metadata["duration_seconds"] == 900


def test_parses_activity_level_as_categorical_metric() -> None:
    parsed = parse_raw_payload(
        {
            "dataPoints": [
                {
                    "activityLevel": {
                        "interval": {
                            "startTime": "2026-07-17T04:30:00Z",
                            "endTime": "2026-07-17T05:00:00Z",
                        },
                        "activityLevelType": "LIGHT",
                    }
                }
            ]
        },
        source_object_key="gs://bucket/health-data/raw/activity-level/file.json#1",
        student_id="student-a",
        raw_updated_at=datetime(2026, 7, 17, tzinfo=UTC),
    )

    point = parsed.metric_points[0]
    assert point.metric == "activity_level_light"
    assert point.value == 1
    assert point.metadata["level"] == "LIGHT"


def test_parses_sedentary_period_as_minutes() -> None:
    parsed = parse_raw_payload(
        {
            "dataPoints": [
                {
                    "sedentaryPeriod": {
                        "interval": {
                            "startTime": "2026-07-17T04:30:00Z",
                            "endTime": "2026-07-17T05:30:00Z",
                        }
                    }
                }
            ]
        },
        source_object_key="gs://bucket/health-data/raw/sedentary-period/file.json#1",
        student_id="student-a",
        raw_updated_at=datetime(2026, 7, 17, tzinfo=UTC),
    )

    point = parsed.metric_points[0]
    assert point.metric == "sedentary_minutes"
    assert point.value == 60


def test_parses_daily_resting_hr_and_daily_hrv() -> None:
    cases = [
        (
            "daily-resting-heart-rate",
            "dailyRestingHeartRate",
            "beatsPerMinute",
            "daily_resting_heart_rate",
            62,
        ),
        (
            "daily-heart-rate-variability",
            "dailyHeartRateVariability",
            "rootMeanSquareOfSuccessiveDifferencesMilliseconds",
            "daily_hrv_rmssd",
            34.2,
        ),
    ]

    for endpoint, payload_key, value_key, metric, value in cases:
        parsed = parse_raw_payload(
            {"dataPoints": [{payload_key: {"date": "2026-07-17", value_key: value}}]},
            source_object_key=f"gs://bucket/health-data/raw/{endpoint}/file.json#1",
            student_id="student-a",
            raw_updated_at=datetime(2026, 7, 17, tzinfo=UTC),
        )

        point = parsed.metric_points[0]
        assert point.metric == metric
        assert point.local_date.isoformat() == "2026-07-17"
        assert point.local_time.isoformat() == "00:00:00"
        assert point.value == value


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
