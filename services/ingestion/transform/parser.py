from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from services.ingestion.transform.models import MetricPoint, SleepRow

IST = timezone(timedelta(hours=5, minutes=30))

RAW_ENDPOINT_TO_METRIC = {
    "heart-rate": "heart_rate",
    "heart-rate-variability": "hrv_rmssd",
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
            metric_points=_parse_steps(points, student_id, source_object_key),
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


def _parse_steps(
    points: list[dict[str, Any]],
    student_id: str,
    source_object_key: str,
) -> list[MetricPoint]:
    rows: list[MetricPoint] = []
    for entry in points:
        steps = _get_any(entry, ("steps",))
        if not isinstance(steps, dict):
            continue

        interval = steps.get("interval") or {}
        start = _to_local_datetime(_get_any(interval, ("startTime", "starttime")))
        end = _to_local_datetime(_get_any(interval, ("endTime", "endtime")))
        count = _to_float(_get_any(steps, ("count",)))
        if start is None or count is None:
            continue

        metadata: dict[str, Any] = {}
        if end is not None:
            metadata["end_local"] = end.isoformat()
            metadata["duration_seconds"] = int((end - start).total_seconds())

        rows.append(
            MetricPoint(
                student_id=student_id,
                metric="steps",
                local_date=start.date(),
                local_time=start.time().replace(tzinfo=None),
                value=count,
                source_object_key=source_object_key,
                metadata=metadata or None,
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
