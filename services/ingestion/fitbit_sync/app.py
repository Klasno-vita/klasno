import os
import json
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, request, redirect, jsonify
from google.cloud import storage

app = Flask(__name__)

BUCKET_NAME = os.environ["BUCKET_NAME"]
CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = os.environ["REDIRECT_URI"]

# Keep these scopes matching what you selected in Google Auth Platform Data Access.
SCOPES = [
    "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
    "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
    "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
]

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
HEALTH_BASE_URL = "https://health.googleapis.com/v4"

# Metrics that MUST have data for a scheduled pull to count as successful.
# Other metrics (weight, body-fat, vo2-max...) can legitimately be empty.
KEY_METRICS = ["heart-rate", "heart-rate-variability", "sleep", "steps"]

# Google Health API data types.
DATA_TYPES = [
    # Health metrics and measurements
    {"endpoint_name": "heart-rate", "filter_name": "heart_rate", "kind": "sample"},
    {"endpoint_name": "heart-rate-variability", "filter_name": "heart_rate_variability", "kind": "sample"},
    {"endpoint_name": "daily-heart-rate-variability", "filter_name": "dailyHeartRateVariability", "kind": "daily"},
    {"endpoint_name": "daily-resting-heart-rate", "filter_name": "dailyRestingHeartRate", "kind": "daily"},
    {"endpoint_name": "daily-heart-rate-zones", "filter_name": "dailyHeartRateZones", "kind": "daily"},
    {"endpoint_name": "daily-oxygen-saturation", "filter_name": "dailyOxygenSaturation", "kind": "daily"},
    {"endpoint_name": "daily-respiratory-rate", "filter_name": "dailyRespiratoryRate", "kind": "daily"},
    {"endpoint_name": "daily-sleep-temperature-derivations", "filter_name": "dailySleepTemperatureDerivations", "kind": "daily"},
    {"endpoint_name": "oxygen-saturation", "filter_name": "oxygen_saturation", "kind": "sample"},
    {"endpoint_name": "respiratory-rate-sleep-summary", "filter_name": "respiratory_rate_sleep_summary", "kind": "sample"},
    {"endpoint_name": "weight", "filter_name": "weight", "kind": "sample"},
    {"endpoint_name": "body-fat", "filter_name": "body_fat", "kind": "sample"},
    # Activity and fitness
    {"endpoint_name": "steps", "filter_name": "steps", "kind": "interval"},
    {"endpoint_name": "distance", "filter_name": "distance", "kind": "interval"},
    {"endpoint_name": "active-minutes", "filter_name": "active_minutes", "kind": "interval"},
    {"endpoint_name": "active-zone-minutes", "filter_name": "active_zone_minutes", "kind": "interval"},
    {"endpoint_name": "active-energy-burned", "filter_name": "active_energy_burned", "kind": "interval"},
    {"endpoint_name": "activity-level", "filter_name": "activity_level", "kind": "interval"},
    {"endpoint_name": "sedentary-period", "filter_name": "sedentary_period", "kind": "interval"},
    {"endpoint_name": "time-in-heart-rate-zone", "filter_name": "time_in_heart_rate_zone", "kind": "interval"},
    {"endpoint_name": "daily-vo2-max", "filter_name": "dailyVo2Max", "kind": "daily"},
    {"endpoint_name": "vo2-max", "filter_name": "vo2_max", "kind": "sample"},
    {"endpoint_name": "exercise", "filter_name": "exercise", "kind": "session"},
    # Sleep
    {"endpoint_name": "sleep", "filter_name": "sleep", "kind": "sleep"},
]


def upload_to_gcs(data, file_path):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(file_path)
    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json"
    )


def gcs_blob_exists(file_path):
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    return bucket.blob(file_path).exists()


def read_tokens_from_gcs():
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob("oauth/tokens.json")
    token_text = blob.download_as_text()
    return json.loads(token_text)


def get_access_token_from_refresh_token(refresh_token):
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    response = requests.post(TOKEN_URL, data=payload)
    response.raise_for_status()
    return response.json()["access_token"]


def build_filter(data_type, start_dt, end_dt):
    kind = data_type["kind"]
    field = data_type["filter_name"]

    start_ts = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_ts = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")

    if kind == "sample":
        return f'{field}.sample_time.physical_time >= "{start_ts}" AND {field}.sample_time.physical_time < "{end_ts}"'
    if kind == "interval":
        return f'{field}.interval.start_time >= "{start_ts}" AND {field}.interval.start_time < "{end_ts}"'
    if kind == "daily":
        return f'{field}.date >= "{start_date}" AND {field}.date < "{end_date}"'
    if kind == "session":
        return f'{field}.interval.civil_start_time >= "{start_date}" AND {field}.interval.civil_start_time < "{end_date}"'
    if kind == "sleep":
        return f'sleep.interval.end_time >= "{start_ts}" AND sleep.interval.end_time < "{end_ts}"'
    return None


def fetch_all_pages(access_token, data_type, start_dt, end_dt):
    endpoint_name = data_type["endpoint_name"]
    filter_expr = build_filter(data_type, start_dt, end_dt)

    url = f"{HEALTH_BASE_URL}/users/me/dataTypes/{endpoint_name}/dataPoints"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    page_size = 25 if endpoint_name in ["sleep", "exercise"] else 10000

    all_points = []
    page_token = None

    while True:
        params = {
            "pageSize": page_size,
            "filter": filter_expr,
        }
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            return {
                "data_type": endpoint_name,
                "success": False,
                "status_code": response.status_code,
                "error": response.text,
                "filter": filter_expr,
                "dataPoints": [],
            }

        payload = response.json()
        points = payload.get("dataPoints", [])
        all_points.extend(points)

        page_token = payload.get("nextPageToken")
        if not page_token:
            break

    return {
        "data_type": endpoint_name,
        "success": True,
        "filter": filter_expr,
        "count": len(all_points),
        "dataPoints": all_points,
    }


def run_pull(days):
    """Pull all data types for the last N days into GCS. Returns (summary, summary_path)."""
    if days > 90:
        days = 90

    tokens = read_tokens_from_gcs()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("Refresh token not found. Open /connect again.")

    access_token = get_access_token_from_refresh_token(refresh_token)

    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)

    run_time = end_dt.strftime("%Y-%m-%dT%H-%M-%SZ")
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")

    summary = {
        "status": "completed",
        "days_requested": days,
        "start_time_utc": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end_time_utc": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "results": []
    }

    for data_type in DATA_TYPES:
        endpoint_name = data_type["endpoint_name"]
        result = fetch_all_pages(access_token, data_type, start_dt, end_dt)

        file_path = (
            f"health-data/raw/{endpoint_name}/"
            f"start={start_date}/end={end_date}/"
            f"pulled_at={run_time}.json"
        )
        upload_to_gcs(result, file_path)

        summary["results"].append({
            "data_type": endpoint_name,
            "success": result.get("success"),
            "count": result.get("count", 0),
            "status_code": result.get("status_code"),
            "saved_to": f"gs://{BUCKET_NAME}/{file_path}"
        })

    summary_path = (
        f"health-data/raw/_summary/"
        f"start={start_date}/end={end_date}/"
        f"summary_pulled_at={run_time}.json"
    )
    upload_to_gcs(summary, summary_path)

    return summary, summary_path


@app.route("/")
def home():
    return """
    <h2>Google Health API Puller</h2>
    <p><a href="/connect">Connect Google Health / Fitbit Account</a></p>
    <p><a href="/pull-health-data?days=15">Pull last 15 days health data</a></p>
    <p><a href="/pull-health-data?days=30">Pull last 30 days health data</a></p>
    <p><a href="/scheduled-pull?days=2">Scheduled pull test (2 days, with success check)</a></p>
    """


@app.route("/connect")
def connect():
    scope_string = " ".join(SCOPES)
    auth_redirect_url = (
        f"{AUTH_URL}"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scope_string}"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return redirect(auth_redirect_url)


@app.route("/oauth2callback")
def oauth2callback():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No authorization code received"}), 400

    payload = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    token_response = requests.post(TOKEN_URL, data=payload)
    token_response.raise_for_status()
    tokens = token_response.json()

    upload_to_gcs(tokens, "oauth/tokens.json")

    return jsonify({
        "status": "connected",
        "message": "OAuth completed. Token saved to Cloud Storage.",
        "has_refresh_token": "refresh_token" in tokens,
        "scopes_requested": SCOPES
    })


@app.route("/pull-health-data")
def pull_health_data():
    days = int(request.args.get("days", "15"))

    try:
        summary, summary_path = run_pull(days)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status": "completed",
        "summary_saved_to": f"gs://{BUCKET_NAME}/{summary_path}",
        "summary": summary
    })


@app.route("/scheduled-pull")
def scheduled_pull():
    """Route for Cloud Scheduler.

    Returns HTTP 200 ONLY if every KEY_METRIC saved successfully with >0
    records. Returns HTTP 500 otherwise, so Cloud Scheduler keeps retrying.
    """
    days = int(request.args.get("days", "2"))

    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    marker_path = f"health-data/raw/_daily_success/date={today_utc}.json"
    if gcs_blob_exists(marker_path):
        return jsonify({
            "status": "success",
            "reason": "already pulled successfully today, skipping",
            "marker": marker_path,
        }), 200

    try:
        summary, summary_path = run_pull(days)
    except Exception as e:
        return jsonify({
            "status": "failed",
            "reason": "pull crashed before completing",
            "error": str(e),
        }), 500

    by_type = {r["data_type"]: r for r in summary["results"]}

    failed = []
    for metric in KEY_METRICS:
        r = by_type.get(metric)
        if r is None:
            failed.append({"metric": metric, "reason": "not pulled"})
        elif not r.get("success"):
            failed.append({
                "metric": metric,
                "reason": "api error",
                "status_code": r.get("status_code"),
            })
        elif (r.get("count") or 0) <= 0:
            failed.append({"metric": metric, "reason": "0 records"})

    if failed:
        return jsonify({
            "status": "failed",
            "reason": "key metrics missing data",
            "failed_key_metrics": failed,
            "summary_saved_to": f"gs://{BUCKET_NAME}/{summary_path}",
        }), 500

    upload_to_gcs({
        "date": today_utc,
        "completed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "days": days,
    }, marker_path)

    return jsonify({
        "status": "success",
        "days": days,
        "key_metrics_ok": KEY_METRICS,
        "summary_saved_to": f"gs://{BUCKET_NAME}/{summary_path}",
    }), 200
