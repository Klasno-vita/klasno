# Klasno Task Roadmap

## Current Milestone Status

- Phase 1 repository foundation: completed locally on `codex/foundation-hardening`.
- Phase 2 Cloud Run puller source: imported locally in `services/ingestion/fitbit_sync`.
- Phase 3 transform core: added locally in `services/ingestion/transform`.
- Next task: connect the transform core to GCS listing, raw JSON parsing,
  BigQuery `MERGE` statements, and the transform control table.

## Current Context

Klasno is an AI-powered student wellness and academic intelligence platform for schools in India. The project combines wearable health data, school ERP data, analytics, and role-based dashboards for students, parents, teachers, and administrators.

The current working GCP pipeline already pulls Fitbit / Google Health data and stores raw files in Cloud Storage. The immediate engineering goal is to bring that work into the locked monorepo architecture, then continue the transformations beyond raw metric loading into wellness analytics such as stress, recovery, sleep quality, and school-level insights.

## Architecture Guardrails

- Backend: FastAPI modular monolith in `services/api`.
- Ingestion: Cloud Run Jobs in `services/ingestion`.
- Analytics storage: BigQuery for raw, transformed metrics, and marts.
- Operational storage: Cloud SQL Postgres for users, tenants, roles, consent, tokens, and app state.
- Frontend: React Vite app in `web`.
- Infra: Terraform in `infra`, not manually managed console resources long term.
- Region target: `asia-south1` for student data residency.
- AI: wellness insights only, not medical diagnosis.

## Work Already Done In GCP

- Cloud Run puller is working.
- `/scheduled-pull?days=2` route is working.
- Cloud Scheduler fires every 5 minutes from 10:00 to 10:55 AM New York time.
- Success marker stops repeated pulls after first successful run.
- Key metric success check validates:
  - heart rate
  - HRV
  - sleep
  - steps
- Failure alerting exists through log-based metric plus email alert if the full retry hour fails.
- Cost check completed:
  - credits cover current usage
  - Dataproc cluster stopped
  - nothing unnecessary is running
- Cloud Run Job transform has been built but not deployed.
- Transform job design includes:
  - process only new files
  - control table
  - BigQuery `MERGE` dedup
  - sleep upsert
  - correct delta boundaries
- Current Cloud Run puller source has been exported from Cloud Shell into
  `services/ingestion/fitbit_sync`.
- Old Dataproc PySpark transform has been exported into
  `services/ingestion/legacy_reference` for parser/schema reference only.

## Next Task Sequence

### Phase 1: Stabilize Repo Foundation

Goal: make the local repo match the Klasno architecture so future work has a real home.

Tasks:

1. Scaffold monorepo folders:
   - `services/api`
   - `services/ingestion`
   - `services/llm`
   - `web`
   - `infra`
   - `docs/adr`
   - `docs/runbooks`
2. Add project-level docs:
   - `README.md`
   - `ARCHITECTURE.md`
   - `docs/data-dictionary.md`
3. Add baseline local dev files:
   - `docker-compose.yml`
   - `.env.example`
   - `.gitignore`
4. Add ADR for current console-built GCP pipeline and planned migration.

### Phase 2: Move GCP Puller Into `services/ingestion`

Goal: migrate the working Cloud Run puller from console/local scripts into source control.

Tasks:

1. Add `services/ingestion/fitbit_sync`. Complete locally.
2. Preserve working routes. Mostly complete locally:
   - `/connect`
   - `/oauth2callback`
   - `/pull-health-data`
   - `/scheduled-pull`
   - `/pull-one-metric` still needs to be recovered or rebuilt if required.
3. Add config through environment variables. Complete locally.
4. Add Secret Manager references for OAuth credentials.
5. Add structured logs for:
   - pull attempt started
   - metric success/failure
   - success marker written
   - full retry-window failure
6. Add tests for success-marker behavior and key-metric validation.

### Phase 3: Deploy Cloud Run Transform Job

Goal: replace Dataproc with the already-built Cloud Run Job transform.

Tasks:

1. Add `services/ingestion/transform`.
2. Create or verify BigQuery control table.
3. Process only new raw GCS files.
4. Write transformed metric tables with dedup.
5. Upsert sleep records safely.
6. Preserve correct delta boundaries for HR and HRV.
7. Run the job on a small date range.
8. Compare output with earlier Dataproc output.
9. Schedule transform after successful daily pull.

### Phase 4: Add Post-Transform Wellness Features

Goal: move beyond raw transformed tables into real wellness analytics.

Initial derived features:

1. Heart-rate features:
   - resting heart rate estimate
   - elevated HR duration
   - HR variability from BPM gaps where appropriate
   - abnormal spike flags
2. HRV features:
   - daily HRV average
   - HRV availability hours
   - HRV missing-duration flag
   - low-HRV recovery flag
3. Sleep features:
   - total sleep duration
   - sleep start/end
   - sleep consistency
   - sleep debt
   - sleep-quality score
4. Activity features:
   - steps total
   - active minutes
   - sedentary duration
   - calories burned
5. Stress feature v1:
   - elevated HR compared to baseline
   - low HRV compared to baseline
   - poor sleep / sleep debt
   - low recovery score
   - high sedentary time
   - optional school-day context later

Important rule: stress output must be framed as a wellness risk signal, not a diagnosis.

### Phase 5: BigQuery Marts

Goal: create dashboard-ready analytics tables.

Candidate marts:

1. `mart_student_daily_wellness`
   - one row per student per day
   - sleep, HR, HRV, activity, stress score
2. `mart_student_weekly_wellness`
   - weekly trends and rolling baselines
3. `mart_school_wellness_summary`
   - tenant-level aggregate only
   - no unnecessary PII
4. `mart_data_quality`
   - missing metrics
   - ingestion status
   - HRV availability
   - device/data freshness

### Phase 6: API Integration

Goal: expose analytics safely through the FastAPI app.

Tasks:

1. Build `services/api/app/modules/health`.
2. Build `services/api/app/modules/analytics`.
3. Enforce tenant and role filters on every query.
4. Add endpoints for:
   - student daily wellness
   - student trend
   - admin aggregate dashboard
   - data quality status
5. Add tests for role and tenant isolation.

### Phase 7: Consent, Users, And Pilot Readiness

Goal: prepare for a real school pilot in India.

Tasks:

1. Add tenant model.
2. Add user roles:
   - student
   - parent
   - teacher
   - admin
3. Add guardian consent tracking.
4. Add data deletion workflow.
5. Add access audit logging.
6. Add runbook for onboarding one school.

## Immediate Next Step

Connect `services/ingestion/transform` to GCP adapters:

1. list raw GCS objects from `KLASNO_RAW_BUCKET`
2. read transform control rows from BigQuery
3. parse raw Fitbit / Google Health JSON into metric and sleep rows
4. write BigQuery `MERGE` statements for metric tables and sleep upserts
5. record transform outcomes in the control table
6. run a small replay and compare against earlier Dataproc output
