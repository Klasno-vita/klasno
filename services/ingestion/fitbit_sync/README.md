# Fitbit Sync

Current Cloud Run puller exported from Cloud Shell.

It serves:

- `/connect`
- `/oauth2callback`
- `/pull-health-data`
- `/scheduled-pull`

The scheduled route is already used by Cloud Scheduler around the 10 AM pull
window. It writes raw Google Health / Fitbit JSON into GCS and uses
`health-data/raw/_daily_success/date=YYYY-MM-DD.json` as the success marker.

Required environment variables:

- `BUCKET_NAME`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `REDIRECT_URI`

Next cleanup step: move OAuth token storage from raw GCS objects toward Secret
Manager or an encrypted operational store before any pilot data is onboarded.
