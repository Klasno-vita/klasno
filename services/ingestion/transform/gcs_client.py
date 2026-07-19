import json
from collections.abc import Iterable
from typing import Any, Protocol

from services.ingestion.transform.models import RawObject


class GcsBlob(Protocol):
    name: str
    generation: int | str | None
    updated: object

    def download_as_text(self) -> str: ...


class GcsBucket(Protocol):
    name: str

    def list_blobs(self, prefix: str | None = None) -> Iterable[GcsBlob]: ...

    def blob(self, blob_name: str) -> GcsBlob: ...


class GcsStorageClient(Protocol):
    def bucket(self, bucket_name: str) -> GcsBucket: ...


class GcsRawStore:
    def __init__(self, client: GcsStorageClient, bucket_name: str) -> None:
        self._bucket = client.bucket(bucket_name)

    def list_raw_objects(self, *, prefix: str = "") -> list[RawObject]:
        objects: list[RawObject] = []
        for blob in self._bucket.list_blobs(prefix=prefix or None):
            if blob.name.endswith("/"):
                continue
            if blob.generation is None:
                continue
            objects.append(
                RawObject(
                    bucket=self._bucket.name,
                    name=blob.name,
                    generation=str(blob.generation),
                    updated_at=blob.updated,
                )
            )
        return objects

    def read_json_payload(self, raw_object: RawObject) -> Any:
        blob = self._bucket.blob(raw_object.name)
        return json.loads(blob.download_as_text())

    def read_json_payloads(self, raw_objects: Iterable[RawObject]) -> dict[str, Any]:
        return {raw_object.object_key: self.read_json_payload(raw_object) for raw_object in raw_objects}
