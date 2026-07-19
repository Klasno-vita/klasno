# Analytics Data Dictionary

This document records the current transformed health fields and planned derived
wellness fields. Final table schemas will be versioned with transformation code.

## Current transformed metrics

| Metric | Core fields | Notes |
| --- | --- | --- |
| Steps | `start_ist`, `end_ist`, `steps`, `duration` | Interval step count |
| Heart rate | `date_ist`, `time_ist`, `bpm`, `delta_from_prev` | Continuous signal where available |
| HRV | `date_ist`, `time_ist`, `rmssd_ms`, `delta_from_prev` | Intermittent recovery signal |
| Daily resting heart rate | `date_ist`, `bpm` | Daily baseline input |
| Daily HRV | `date_ist`, `rmssd_ms` | Daily recovery input |
| Active minutes | `start_ist`, `end_ist`, `duration`, `minutes` | Activity duration |
| Active zone minutes | `start_ist`, `end_ist`, `duration`, `zone`, `azm` | Intensity-zone activity |
| Active energy | `start_ist`, `end_ist`, `duration`, `kcal` | Energy expenditure |
| Activity level | `level`, `start_ist`, `end_ist` | Activity classification interval |
| Sedentary period | `start_ist`, `end_ist`, `duration`, `minutes` | Sedentary behavior signal |

## Planned daily wellness features

| Feature group | Candidate fields | Safety rule |
| --- | --- | --- |
| Heart rate | resting estimate, elevated duration, spike count | Compare with personal baseline |
| HRV | daily average, availability hours, missing-duration flag | Never assume missing HRV is zero |
| Sleep | duration, timing, consistency, debt, quality score | Retain source-quality flags |
| Activity | steps, active minutes, sedentary duration, calories | Preserve metric coverage |
| Stress v1 | score, level, contributing factors, confidence | Wellness signal, not diagnosis |

Stress v1 will combine deviations from a student's rolling baseline for heart
rate, HRV, sleep, recovery, and sedentary behavior. A score must include data
coverage and confidence so missing HRV does not silently produce a false result.
