from datetime import UTC, datetime

from services.ingestion.transform.gcs_client import GcsRawStore


class FakeBlob:
    def __init__(self, name: str, payload: str, *, generation: str = "1") -> None:
        self.name = name
        self._payload = payload
        self.generation = generation
        self.updated = datetime(2026, 7, 17, 10, 0, tzinfo=UTC)

    def download_as_text(self) -> str:
        return self._payload


class FakeBucket:
    name = "raw-bucket"

    def __init__(self) -> None:
        self._blobs = {
            "health-data/raw/heart-rate/file.json": FakeBlob(
                "health-data/raw/heart-rate/file.json",
                '{"success": true, "dataPoints": []}',
            ),
            "health-data/raw/": FakeBlob("health-data/raw/", "{}"),
        }

    def list_blobs(self, prefix: str | None = None) -> list[FakeBlob]:
        blobs = list(self._blobs.values())
        if prefix is None:
            return blobs
        return [blob for blob in blobs if blob.name.startswith(prefix)]

    def blob(self, blob_name: str) -> FakeBlob:
        return self._blobs[blob_name]


class FakeClient:
    def __init__(self) -> None:
        self.bucket_instance = FakeBucket()

    def bucket(self, bucket_name: str) -> FakeBucket:
        assert bucket_name == "raw-bucket"
        return self.bucket_instance


def test_lists_raw_objects_and_skips_directory_markers() -> None:
    store = GcsRawStore(FakeClient(), "raw-bucket")

    objects = store.list_raw_objects(prefix="health-data/raw/")

    assert len(objects) == 1
    assert objects[0].object_key == "gs://raw-bucket/health-data/raw/heart-rate/file.json#1"


def test_reads_json_payload_by_raw_object_name() -> None:
    store = GcsRawStore(FakeClient(), "raw-bucket")
    raw_object = store.list_raw_objects(prefix="health-data/raw/")[0]

    payload = store.read_json_payload(raw_object)

    assert payload == {"success": True, "dataPoints": []}
