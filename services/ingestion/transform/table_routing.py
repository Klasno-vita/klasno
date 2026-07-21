from services.ingestion.transform.parser import infer_endpoint_from_object_key

ENDPOINT_TARGET_TABLES = {
    "active-energy-burned": "active_energy_burned_points",
    "active-minutes": "active_minutes_points",
    "active-zone-minutes": "active_zone_minutes_points",
    "activity-level": "activity_level_points",
    "daily-heart-rate-variability": "daily_heart_rate_variability_points",
    "daily-resting-heart-rate": "daily_resting_heart_rate_points",
    "heart-rate": "heart_rate_points",
    "heart-rate-variability": "heart_rate_variability_points",
    "sedentary-period": "sedentary_period_points",
    "steps": "steps_points",
}


def target_table_for_source(source_object_key: str) -> str | None:
    endpoint = infer_endpoint_from_object_key(source_object_key)
    if endpoint is None:
        return None
    return ENDPOINT_TARGET_TABLES.get(endpoint)


def staging_table_for_target(target_table: str) -> str:
    return f"stg_{target_table}"
