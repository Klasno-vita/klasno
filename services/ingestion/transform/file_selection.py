from collections.abc import Iterable

from services.ingestion.transform.models import ProcessedObject, RawObject

TERMINAL_SUCCESS_STATUSES = frozenset({"success", "succeeded", "processed"})


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
    selected.sort(key=lambda item: (item.updated_at, item.name, item.generation))

    if limit is None:
        return selected
    return selected[:limit]
