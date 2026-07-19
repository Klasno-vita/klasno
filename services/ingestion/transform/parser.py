from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

from services.ingestion.transform.models import MetricPoint, SleepRow

IST = timezone(timedelta(hours=5, minutes=30))

RAW_ENDPOINT_TO_METRIC = {
    "active-energy-burned": "active_energy_burned_kcal",
    "active-minutes": "active_minutes",
    "active-zone-minutes": "active_zone_minutes",
    "activity-level": "activity_level",
    "daily-heart-rate-variability": "daily_hrv_rmssd",
    "daily-resting-heart-rate": "daily_resting_heart_rate",
    "heart-rate": "heart_rate",
    "heart-rate-variability": "hrv_rmssd",
    "sedentary-period": "sedentary_minutes",
    "steps": "steps",
}


@dataclass(frozen=True)
class ParsedRawPayload:
    metric_points: list[MetricPoint]
    sleep_rows: list[SleepRow]


def parse_raw_payload(
    payload: Any,
    *,
    source_object_key: str,
    student_id: str,
    raw_updated_at: datetime,
    endpoint_name: str | None = None,
) -> ParsedRawPayload:
    endpoint = endpoint_name or infer_endpoint_from_object_key(source_object_key)
    points = normalize_payload(payload)

    if isinstance(payload, dict) and payload.get("success") is False:
        return ParsedRawPayload(metric_points=[], sleep_rows=[])

    if endpoint == "heart-rate":
        return ParsedRawPayload(
            metric_points=_parse_heart_rate(points, student_id, source_object_key),
            sleep_rows=[],
        )
    if endpoint == "heart-rate-variability":
        return ParsedRawPayload(
            metric_points=_parse_hrv(points, student_id, source_object_key),
            sleep_rows=[],
        )
    if endpoint == "steps":
        return ParsedRawPayload(
            metric_points=_parse_interval_metric(
                points,
                student_id,
                source_object_key,
                payload_key="steps",
                metric="steps",
                value_key="count",
            ),
            sleep_rows=[],
        )
    if endpoint == "active-minutes":
        return ParsedRawPayload(
            metric_points=_parse_interval_metric(
                points,
                student_id,
                source_object_key,
                payload_key="activeMinutes",
                metric="active_minutes",
                value_key="minutes",
            ),
            sleep_rows=[],
        )
    if endpoint == "active-energy-burned":
        return ParsedRawPayload(
            metric_points=_parse_interval_metric(
                points,
                student_id,
                source_object_key,
                payload_key="activeEnergyBurned",
                metric="active_energy_burned_kcal",
                value_key="kcal",
            ),
            sleep_rows=[],
        )
    if endpoint == "active-zone-minutes":
        return ParsedRawPayload(
            metric_points=_parse_interval_metric(
                points,
                student_id,
                source_object_key,
                payload_key="activeZoneMinutes",
                metric="active_zone_minutes",
                value_key="activeZoneMinutes",
                metadata_keys=("heartRateZone",),
            ),
            sleep_rows=[],
        )
    if endpoint == "activity-level":
        return ParsedRawPayload(
            metric_points=_parse_activity_level(points, student_id, source_object_key),
            sleep_rows=[],
        )
    if endpoint == "sedentary-period":
        return ParsedRawPayload(
            metric_points=_parse_sedentary_period(points, student_id, source_object_key),
            sleep_rows=[],
        )
    if endpoint == "daily-resting-heart-rate":
        return ParsedRawPayload(
            metric_points=_parse_daily_metric(
                points,
                student_id,
                source_object_key,
                payload_key="dailyRestingHeartRate",
                metric="daily_resting_heart_rate",
                value_key="beatsPerMinute",
            ),
            sleep_rows=[],
        )
    if endpoint == "daily-heart-rate-variability":
        return ParsedRawPayload(
            metric_points=_parse_daily_metric(
                points,
                student_id,
                source_object_key,
                payload_key="dailyHeartRateVariability",
                metric="daily_hrv_rmssd",
                value_key="rootMeanSquareOfSuccessiveDifferencesMilliseconds",
            ),
            sleep_rows=[],
        )
    if endpoint == "sleep":
        return ParsedRawPayload(
            metric_points=[],
            sleep_rows=_parse_sleep(points, student_id, source_object_key, raw_updated_at),
        )

    return ParsedRawPayload(metric_points=[], sleep_rows=[])


def infer_endpoint_from_object_key(source_object_key: str) -> str | None:
    normalized = source_object_key.removeprefix("gs://").split("#", maxsplit=1)[0]
    parts = normalized.split("/")
    if "raw" not in parts:
        return None
    raw_index = parts.index("raw")
    if raw_index + 1 >= len(parts):
        return None
    return parts[raw_index + 1]


def normalize_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        for key in ("dataPoints", "data_points", "data", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return [payload]

    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    return []


def _parse_heart_rate(
    points: list[dict[str, Any]],
    student_id: str,
    source_object_key: str,
) -> list[MetricPoint]:
    rows: list[MetricPoint] = []
    for entry in points:
        heart_rate = _get_any(entry, ("heartRate", "heartrate"))
        if not isinstance(heart_rate, dict):
            continue

        sample_time = _get_any(heart_rate, ("sampleTime", "sampletime")) or {}
        timestamp = _to_local_datetime(_get_any(sample_time, ("physicalTime", "physicaltime")))
        bpm = _to_float(_get_any(heart_rate, ("beatsPerMinute", "beatsperminute")))
        if timestamp is None or bpm is None:
            continue

        rows.append(
            MetricPoint(
                student_id=student_id,
                metric="heart_rate",
                local_date=timestamp.date(),
                local_time=timestamp.time().replace(tzinfo=None),
                value=bpm,
                source_object_key=source_object_key,
            )
        )
    return rows


def _parse_hrv(
    points: list[dict[str, Any]],
    student_id: str,
    source_object_key: str,
) -> list[MetricPoint]:
    rows: list[MetricPoint] = []
    for entry in points:
        hrv = _get_any(entry, ("heartRateVariability", "heartratevariability"))
        if not isinstance(hrv, dict):
            continue

        sample_time = _get_any(hrv, ("sampleTime", "sampletime")) or {}
        timestamp = _to_local_datetime(_get_any(sample_time, ("physicalTime", "physicaltime")))
        rmssd = _to_float(
            _get_any(
                hrv,
                (
                    "rootMeanSquareOfSuccessiveDifferencesMilliseconds",
                    "rootmeansquareofsuccessivedifferencesmilliseconds",
                ),
            )
        )
        if timestamp is None or rmssd is None:
            continue

        rows.append(
            MetricPoint(
                student_id=student_id,
                metric="hrv_rmssd",
                local_date=timestamp.date(),
                local_time=timestamp.time().replace(tzinfo=None),
                value=rmssd,
                source_object_key=source_object_key,
            )
        )
    return rows


def _parse_interval_metric(
    points: list[dict[str, Any]],
    student_id: str,
    source_object_key: str,
    *,
    payload_key: str,
    metric: str,
    value_key: str,
    metadata_keys: tuple[str, ...] = (),
) -> list[MetricPoint]:
    rows: list[MetricPoint] = []
    for entry in points:
        payload = _get_any(entry, _case_keys(payload_key))
        if not isinstance(payload, dict):
            continue

        interval = payload.get("interval") or {}
        start = _to_local_datetime(_get_any(interval, ("startTime", "starttime")))
        end = _to_local_datetime(_get_any(interval, ("endTime", "endtime")))
        value = _to_float(_get_any(payload, _case_keys(value_key)))
        if start is None or value is None:
            continue

        metadata: dict[str, Any] = {}
        if end is not None:
            metadata["end_local"] = end.isoformat()
            metadata["duration_seconds"] = int((end - start).total_seconds())
        for key in metadata_keys:
            metadata[key] = _get_any(payload, _case_keys(key))

        rows.append(
            MetricPoint(
                student_id=student_id,
                metric=metric,
                local_date=start.date(),
                local_time=start.time().replace(tzinfo=None),
                value=value,
                source_object_key=source_object_key,
                metadata=metadata or None,
            )
        )
    return rows


def _parse_activity_level(
    points: list[dict[str, Any]],
    student_id: str,
    source_object_key: str,
) -> list[MetricPoint]:
    rows: list[MetricPoint] = []
    for entry in points:
        activity = _get_any(entry, ("activityLevel", "activitylevel"))
        if not isinstance(activity, dict):
            continue

        interval = activity.get("interval") or {}
        start = _to_local_datetime(_get_any(interval, ("startTime", "starttime")))
        end = _to_local_datetime(_get_any(interval, ("endTime", "endtime")))
        level = _get_any(activity, ("activityLevelType", "activityleveltype"))
        if start is None or level is None:
            continue

        metadata: dict[str, Any] = {"level": level}
        if end is not None:
            metadata["end_local"] = end.isoformat()
            metadata["duration_seconds"] = int((end - start).total_seconds())

        rows.append(
            MetricPoint(
                student_id=student_id,
                metric=f"activity_level_{str(level).lower()}",
                local_date=start.date(),
                local_time=start.time().replace(tzinfo=None),
                value=1,
                source_object_key=source_object_key,
                metadata=metadata,
            )
        )
    return rows


def _parse_sedentary_period(
    points: list[dict[str, Any]],
    student_id: str,
    source_object_key: str,
) -> list[MetricPoint]:
    rows: list[MetricPoint] = []
    for entry in points:
        sedentary = _get_any(entry, ("sedentaryPeriod", "sedentaryperiod"))
        if not isinstance(sedentary, dict):
            continue

        interval = sedentary.get("interval") or {}
        start = _to_local_datetime(_get_any(interval, ("startTime", "starttime")))
        end = _to_local_datetime(_get_any(interval, ("endTime", "endtime")))
        if start is None or end is None:
            continue

        duration_seconds = int((end - start).total_seconds())
        rows.append(
            MetricPoint(
                student_id=student_id,
                metric="sedentary_minutes",
                local_date=start.date(),
                local_time=start.time().replace(tzinfo=None),
                value=round(duration_seconds / 60, 4),
                source_object_key=source_object_key,
                metadata={
                    "end_local": end.isoformat(),
                    "duration_seconds": duration_seconds,
                },
            )
        )
    return rows


def _parse_daily_metric(
    points: list[dict[str, Any]],
    student_id: str,
    source_object_key: str,
    *,
    payload_key: str,
    metric: str,
    value_key: str,
) -> list[MetricPoint]:
    rows: list[MetricPoint] = []
    for entry in points:
        payload = _get_any(entry, _case_keys(payload_key))
        if not isinstance(payload, dict):
            continue

        local_date = _parse_date(_get_any(payload, ("date",)))
        value = _to_float(_get_any(payload, _case_keys(value_key)))
        if local_date is None or value is None:
            continue

        rows.append(
            MetricPoint(
                student_id=student_id,
                metric=metric,
                local_date=local_date,
                local_time=datetime.min.time(),
                value=value,
                source_object_key=source_object_key,
            )
        )
    return rows


def _parse_sleep(
    points: list[dict[str, Any]],
    student_id: str,
    source_object_key: str,
    raw_updated_at: datetime,
) -> list[SleepRow]:
    best_by_log_id: dict[str, tuple[datetime, SleepRow]] = {}

    for entry in points:
        sleep = _get_any(entry, ("sleep",))
        if not isinstance(sleep, dict):
            continue

        interval = sleep.get("interval") or {}
        start_raw = _get_any(interval, ("startTime", "starttime"))
        start = _to_local_datetime(start_raw)
        end = _to_local_datetime(_get_any(interval, ("endTime", "endtime")))
        if start is None or end is None:
            continue

        metadata = sleep.get("metadata") or {}
        summary = sleep.get("summary") or {}
        log_id = str(metadata.get("externalId") or start_raw)
        updated_at = _to_utc_datetime(sleep.get("updateTime")) or raw_updated_at.astimezone(UTC)

        total_period = _to_int(
            _get_any(summary, ("minutesInSleepPeriod", "minutesinsleepperiod"))
        )
        minutes_asleep = _to_int(_get_any(summary, ("minutesAsleep", "minutesasleep")))
        minutes_awake = _to_int(_get_any(summary, ("minutesAwake", "minutesawake")))
        stage_minutes = _stage_minutes(summary)

        duration_minutes = minutes_asleep or total_period or int((end - start).total_seconds() / 60)
        efficiency = None
        if minutes_asleep is not None and total_period:
            efficiency = round(minutes_asleep * 100.0 / total_period, 2)

        row = SleepRow(
            student_id=student_id,
            sleep_date=start.date(),
            log_id=log_id,
            start_time=start,
            end_time=end,
            duration_minutes=duration_minutes,
            efficiency=efficiency,
            source_object_key=source_object_key,
            updated_at=updated_at,
            is_nap=bool(metadata.get("nap", False)),
            minutes_awake=minutes_awake,
            light_sleep_minutes=stage_minutes.get("LIGHT"),
            deep_sleep_minutes=stage_minutes.get("DEEP"),
            rem_sleep_minutes=stage_minutes.get("REM"),
            stages_status=metadata.get("stagesStatus"),
        )

        current = best_by_log_id.get(log_id)
        if current is None or updated_at >= current[0]:
            best_by_log_id[log_id] = (updated_at, row)

    return sorted(
        (row for _, row in best_by_log_id.values()),
        key=lambda row: (row.student_id, row.sleep_date, row.log_id),
    )


def _stage_minutes(summary: dict[str, Any]) -> dict[str, int | None]:
    rows: dict[str, int | None] = {}
    for stage in _get_any(summary, ("stagesSummary", "stagessummary")) or []:
        if not isinstance(stage, dict):
            continue
        stage_type = str(stage.get("type") or "").upper()
        rows[stage_type] = _to_int(stage.get("minutes"))
    return rows


def _get_any(mapping: Any, keys: tuple[str, ...]) -> Any:
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _case_keys(key: str) -> tuple[str, ...]:
    return (key, key[:1].lower() + key[1:], key.lower())


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _to_local_datetime(value: Any) -> datetime | None:
    parsed = _to_utc_datetime(value)
    if parsed is None:
        return None
    return parsed.astimezone(IST)


def _to_utc_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    raw = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
