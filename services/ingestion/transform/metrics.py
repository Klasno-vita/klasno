from collections.abc import Iterable

from services.ingestion.transform.models import MetricPoint, MetricRow


def dedupe_metric_points(points: Iterable[MetricPoint]) -> list[MetricPoint]:
    """Keep the latest point encountered for each BigQuery MERGE key."""

    by_key: dict[tuple, MetricPoint] = {}
    for point in points:
        by_key[point.merge_key] = point
    return sorted(
        by_key.values(),
        key=lambda point: (point.student_id, point.metric, point.local_date, point.local_time),
    )


def attach_delta_boundaries(points: Iterable[MetricPoint]) -> list[MetricRow]:
    """Calculate deltas without leaking across students, metrics, or dates."""

    deduped = dedupe_metric_points(points)
    previous_value_by_boundary: dict[tuple[str, str, object], float] = {}
    rows: list[MetricRow] = []

    for point in deduped:
        boundary = (point.student_id, point.metric, point.local_date)
        previous_value = previous_value_by_boundary.get(boundary)
        delta = None if previous_value is None else point.value - previous_value
        previous_value_by_boundary[boundary] = point.value
        rows.append(
            MetricRow(
                student_id=point.student_id,
                metric=point.metric,
                local_date=point.local_date,
                local_time=point.local_time,
                value=point.value,
                delta_from_prev=delta,
                source_object_key=point.source_object_key,
                metadata=point.metadata,
            )
        )

    return rows
