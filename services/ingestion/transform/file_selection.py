from collections.abc import Iterable
from datetime import date
import re

from services.ingestion.transform.models import ProcessedObject, RawObject

TERMINAL_SUCCESS_STATUSES = frozenset({"success", "succeeded", "processed"})
START_DATE_RE = re.compile(r"/start=(\d{4}-\d{2}-\d{2})(?:/|$)")


def select_unprocessed_objects(
    raw_objects: Iterable[RawObject],
    processed_objects: Iterable[ProcessedObject],
    *,
    prefix: str | None = None,
    limit: int | None = None,
) -> list[RawObject]:
    """Return raw objects that still need transformation.

    Failed or in-progress control-table records are intentionally not terminal;
    the next job run can retry those files.
    """

    processed_keys = {
        item.object_key
        for item in processed_objects
        if item.status.lower() in TERMINAL_SUCCESS_STATUSES
    }

    selected = [
        item
        for item in raw_objects
        if item.object_key not in processed_keys and (prefix is None or item.name.startswith(prefix))
    ]
    selected.sort(key=lambda item: (_start_date(item.name), item.name, item.generation))

    if limit is None:
        return selected
    return selected[:limit]


def _start_date(object_name: str) -> date:
    match = START_DATE_RE.search(f"/{object_name}")
    if match is None:
        return date.max
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return date.max
