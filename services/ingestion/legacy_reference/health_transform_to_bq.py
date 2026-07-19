import argparse
import json
from datetime import datetime, timezone, timedelta

from pyspark.sql import SparkSession, Row
from pyspark.sql.types import (
    StructType, StructField,
    StringType, IntegerType, DoubleType, BooleanType
)


IST = timezone(timedelta(hours=5, minutes=30))


def get_any(d, keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d:
            return d[k]
    return None


def to_ist(ts):
    if not ts:
        return None
    raw = str(ts).upper().replace("Z", "+00:00")
    return datetime.fromisoformat(raw).astimezone(IST)


def fmt_dt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def fmt_date(dt):
    return dt.strftime("%Y-%m-%d") if dt else None


def fmt_time(dt):
    return dt.strftime("%H:%M:%S") if dt else None


def fmt_dur(seconds):
    secs = int(seconds)
    h, rem = divmod(secs, 3600)
    m, s = divmod(rem, 60)
    return (f"{h}h " if h else "") + (f"{m}m " if (h or m) else "") + f"{s}s"


def to_int(v):
    # Google Health API returns int64 values as strings
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def normalize_payload(payload):
    if isinstance(payload, dict):
        for key in ["dataPoints", "data_points", "data", "items", "results"]:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return [payload]

    if isinstance(payload, list):
        return payload

    return []


def parse_steps(points):
    rows = []

    for entry in points:
        st = get_any(entry, ["steps"])
        if not st:
            continue

        iv = st.get("interval", {})
        start = to_ist(get_any(iv, ["startTime", "starttime"]))
        end = to_ist(get_any(iv, ["endTime", "endtime"]))
        count = int(get_any(st, ["count"]))

        rows.append({
            "start_ist": fmt_dt(start),
            "end_ist": fmt_dt(end),
            "steps": count,
            "duration": fmt_dur((end - start).total_seconds()) if start and end else None,
        })

    rows.sort(key=lambda r: r["start_ist"] or "")
    schema = StructType([
        StructField("start_ist", StringType(), True),
        StructField("end_ist", StringType(), True),
        StructField("steps", IntegerType(), True),
        StructField("duration", StringType(), True),
    ])
    return rows, schema


def parse_active_zone_minutes(points):
    rows = []

    for entry in points:
        azm = get_any(entry, ["activeZoneMinutes", "activezoneminutes"])
        if not azm:
            continue

        iv = azm.get("interval", {})
        start = to_ist(get_any(iv, ["startTime", "starttime"]))
        end = to_ist(get_any(iv, ["endTime", "endtime"]))

        rows.append({
            "start_ist": fmt_dt(start),
            "end_ist": fmt_dt(end),
            "duration": fmt_dur((end - start).total_seconds()) if start and end else None,
            "zone": get_any(azm, ["heartRateZone", "heartratezone"]),
            "azm": int(get_any(azm, ["activeZoneMinutes", "activezoneminutes"])),
        })

    rows.sort(key=lambda r: r["start_ist"] or "")
    schema = StructType([
        StructField("start_ist", StringType(), True),
        StructField("end_ist", StringType(), True),
        StructField("duration", StringType(), True),
        StructField("zone", StringType(), True),
        StructField("azm", IntegerType(), True),
    ])
    return rows, schema


def parse_active_energy_burned(points):
    rows = []

    for entry in points:
        e = get_any(entry, ["activeEnergyBurned", "activeenergyburned"])
        if not e:
            continue

        iv = e.get("interval", {})
        start = to_ist(get_any(iv, ["startTime", "starttime"]))
        end = to_ist(get_any(iv, ["endTime", "endtime"]))
        kcal = e.get("kcal")

        rows.append({
            "start_ist": fmt_dt(start),
            "end_ist": fmt_dt(end),
            "duration": fmt_dur((end - start).total_seconds()) if start and end else None,
            "kcal": round(float(kcal), 4) if kcal is not None else None,
        })

    rows.sort(key=lambda r: r["start_ist"] or "")
    schema = StructType([
        StructField("start_ist", StringType(), True),
        StructField("end_ist", StringType(), True),
        StructField("duration", StringType(), True),
        StructField("kcal", DoubleType(), True),
    ])
    return rows, schema


def parse_activity_level(points):
    rows = []

    for entry in points:
        act = get_any(entry, ["activityLevel", "activitylevel"])
        if not act:
            continue

        iv = act.get("interval", {})
        start = to_ist(get_any(iv, ["startTime", "starttime"]))
        end = to_ist(get_any(iv, ["endTime", "endtime"]))

        rows.append({
            "level": get_any(act, ["activityLevelType", "activityleveltype"]),
            "start_ist": fmt_dt(start),
            "end_ist": fmt_dt(end),
        })

    rows.sort(key=lambda r: r["start_ist"] or "")
    schema = StructType([
        StructField("level", StringType(), True),
        StructField("start_ist", StringType(), True),
        StructField("end_ist", StringType(), True),
    ])
    return rows, schema


def parse_heart_rate(points):
    parsed = []

    for entry in points:
        hr = get_any(entry, ["heartRate", "heartrate"])
        if not hr:
            continue

        sample = get_any(hr, ["sampleTime", "sampletime"]) or {}
        ts = get_any(sample, ["physicalTime", "physicaltime"])
        ist = to_ist(ts)
        bpm = int(get_any(hr, ["beatsPerMinute", "beatsperminute"]))

        parsed.append({"ist": ist, "bpm": bpm})

    parsed.sort(key=lambda p: p["ist"])

    rows = []
    prev = None

    for p in parsed:
        if prev is None:
            diff = "-"
        else:
            diff = fmt_dur((p["ist"] - prev).total_seconds())

        rows.append({
            "date_ist": fmt_date(p["ist"]),
            "time_ist": fmt_time(p["ist"]),
            "bpm": p["bpm"],
            "delta_from_prev": diff,
        })

        prev = p["ist"]

    schema = StructType([
        StructField("date_ist", StringType(), True),
        StructField("time_ist", StringType(), True),
        StructField("bpm", IntegerType(), True),
        StructField("delta_from_prev", StringType(), True),
    ])
    return rows, schema


def parse_hrv(points):
    parsed = []

    for entry in points:
        hrv = get_any(entry, ["heartRateVariability", "heartratevariability"])
        if not hrv:
            continue

        sample = get_any(hrv, ["sampleTime", "sampletime"]) or {}
        ts = get_any(sample, ["physicalTime", "physicaltime"])
        ist = to_ist(ts)
        rmssd = get_any(
            hrv,
            [
                "rootMeanSquareOfSuccessiveDifferencesMilliseconds",
                "rootmeansquareofsuccessivedifferencesmilliseconds",
            ],
        )

        parsed.append({
            "ist": ist,
            "rmssd_ms": float(rmssd) if rmssd is not None else None,
        })

    parsed.sort(key=lambda p: p["ist"])

    rows = []
    prev = None

    for p in parsed:
        if prev is None:
            diff = "-"
        else:
            total_min = int((p["ist"] - prev).total_seconds() / 60)
            h, m = divmod(total_min, 60)
            diff = f"{h}h {m}m" if h else f"{m}m"

        rows.append({
            "date_ist": fmt_date(p["ist"]),
            "time_ist": fmt_time(p["ist"]),
            "rmssd_ms": p["rmssd_ms"],
            "delta_from_prev": diff,
        })

        prev = p["ist"]

    schema = StructType([
        StructField("date_ist", StringType(), True),
        StructField("time_ist", StringType(), True),
        StructField("rmssd_ms", DoubleType(), True),
        StructField("delta_from_prev", StringType(), True),
    ])
    return rows, schema


def parse_sleep(entries_with_source):
    # entries_with_source: list of (source_file_path, data_point_dict)
    # Sleep raw files overlap, so the same session appears in many objects.
    # Dedupe by unique session, keep the most recently pulled/updated version.

    best = {}

    for source_file, entry in entries_with_source:
        s = get_any(entry, ["sleep"])
        if not s:
            continue

        iv = s.get("interval", {}) or {}
        start_raw = get_any(iv, ["startTime", "starttime"])
        if not start_raw:
            continue

        meta = s.get("metadata", {}) or {}

        # unique session key: externalId if present, else the UTC start time
        key = meta.get("externalId") or start_raw

        # version rank: latest updateTime first, then latest pulled file
        rank = (s.get("updateTime") or "", source_file or "")

        if key not in best or rank > best[key][0]:
            best[key] = (rank, s)

    rows = []

    for _, s in best.values():
        iv = s.get("interval", {}) or {}
        start_ist = to_ist(get_any(iv, ["startTime", "starttime"]))
        end_ist = to_ist(get_any(iv, ["endTime", "endtime"]))

        meta = s.get("metadata", {}) or {}
        summ = s.get("summary", {}) or {}

        total_period = to_int(get_any(summ, ["minutesInSleepPeriod", "minutesinsleepperiod"]))
        minutes_asleep = to_int(get_any(summ, ["minutesAsleep", "minutesasleep"]))
        minutes_awake = to_int(get_any(summ, ["minutesAwake", "minutesawake"]))

        stage_minutes = {}
        for st in (get_any(summ, ["stagesSummary", "stagessummary"]) or []):
            st_type = str(st.get("type") or "").upper()
            stage_minutes[st_type] = to_int(st.get("minutes"))

        light_min = stage_minutes.get("LIGHT")
        deep_min = stage_minutes.get("DEEP")
        rem_min = stage_minutes.get("REM")
        awake_min = stage_minutes.get("AWAKE")

        efficiency = None
        if minutes_asleep is not None and total_period:
            efficiency = round(minutes_asleep * 100.0 / total_period, 2)

        def pct(stage):
            if stage is None or not minutes_asleep:
                return None
            return round(stage * 100.0 / minutes_asleep, 2)

        rows.append({
            "sleep_date": fmt_date(start_ist),
            "is_nap": bool(meta.get("nap", False)),
            "sleep_start_local": fmt_dt(start_ist),
            "sleep_end_local": fmt_dt(end_ist),
            "total_sleep_period_minutes": total_period,
            "minutes_asleep": minutes_asleep,
            "minutes_awake": minutes_awake,
            "sleep_efficiency": efficiency,
            "light_sleep_minutes": light_min,
            "deep_sleep_minutes": deep_min,
            "rem_sleep_minutes": rem_min,
            "awake_stage_minutes": awake_min,
            "light_sleep_percent": pct(light_min),
            "deep_sleep_percent": pct(deep_min),
            "rem_sleep_percent": pct(rem_min),
            "stages_status": meta.get("stagesStatus"),
        })

    rows.sort(key=lambda r: r["sleep_start_local"] or "")

    schema = StructType([
        StructField("sleep_date", StringType(), True),
        StructField("is_nap", BooleanType(), True),
        StructField("sleep_start_local", StringType(), True),
        StructField("sleep_end_local", StringType(), True),
        StructField("total_sleep_period_minutes", IntegerType(), True),
        StructField("minutes_asleep", IntegerType(), True),
        StructField("minutes_awake", IntegerType(), True),
        StructField("sleep_efficiency", DoubleType(), True),
        StructField("light_sleep_minutes", IntegerType(), True),
        StructField("deep_sleep_minutes", IntegerType(), True),
        StructField("rem_sleep_minutes", IntegerType(), True),
        StructField("awake_stage_minutes", IntegerType(), True),
        StructField("light_sleep_percent", DoubleType(), True),
        StructField("deep_sleep_percent", DoubleType(), True),
        StructField("rem_sleep_percent", DoubleType(), True),
        StructField("stages_status", StringType(), True),
    ])
    return rows, schema


def transform(metric, points):
    if metric == "steps":
        return parse_steps(points)

    if metric == "active-zone-minutes":
        return parse_active_zone_minutes(points)

    if metric == "active-energy-burned":
        return parse_active_energy_burned(points)

    if metric == "activity-level":
        return parse_activity_level(points)

    if metric == "heart-rate":
        return parse_heart_rate(points)

    if metric == "heart-rate-variability":
        return parse_hrv(points)

    raise ValueError(f"Unsupported metric: {metric}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_uri", required=True)
    parser.add_argument("--metric", required=True)
    parser.add_argument("--output_table", required=True)
    parser.add_argument("--write_mode", default="append")
    parser.add_argument("--temp_bucket", default="health-api-bq-temp-prem")

    args = parser.parse_args()

    spark = SparkSession.builder.appName(f"health-transform-{args.metric}").getOrCreate()
    sc = spark.sparkContext

    files = sc.wholeTextFiles(args.input_uri).collect()

    if not files:
        raise RuntimeError(f"No file found at {args.input_uri}")

    if args.metric == "sleep":
        # sleep needs cross-file dedupe (overlapping pull date ranges)
        entries = []
        for file_path, text in files:
            payload = json.loads(text)
            for point in normalize_payload(payload):
                entries.append((file_path, point))

        all_rows, schema = parse_sleep(entries)
        print(f"sleep: {len(entries)} raw entries -> {len(all_rows)} unique sessions")
    else:
        all_rows = []
        schema = None

        for file_path, text in files:
            payload = json.loads(text)
            points = normalize_payload(payload)
            rows, schema = transform(args.metric, points)
            all_rows.extend(rows)

    if not all_rows:
        print(f"No rows parsed for metric={args.metric}")
        return

    df = spark.createDataFrame([Row(**r) for r in all_rows], schema=schema)

    (
        df.write
        .format("bigquery")
        .option("table", args.output_table)
        .option("temporaryGcsBucket", args.temp_bucket)
        .mode(args.write_mode)
        .save()
    )

    print(f"Wrote {df.count()} rows to {args.output_table}")


if __name__ == "__main__":
    main()
