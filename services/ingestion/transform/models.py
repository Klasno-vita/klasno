from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any


@dataclass(frozen=True)
class RawObject:
    """A raw health object discovered in GCS."""

    bucket: str
    name: str
    generation: str
    updated_at: datetime

    @property
    def object_key(self) -> str:
        return f"gs://{self.bucket}/{self.name}#{self.generation}"


@dataclass(frozen=True)
class ProcessedObject:
    """A raw object that has already reached a terminal transform state."""

    object_key: str
    status: str


@dataclass(frozen=True)
class MetricPoint:
    student_id: str
    metric: str
    local_date: date
    local_time: time
    value: float
    source_object_key: str
    metadata: dict[str, Any] | None = None

    @property
    def merge_key(self) -> tuple[str, str, date, time]:
        return (self.student_id, self.metric, self.local_date, self.local_time)


@dataclass(frozen=True)
class MetricRow:
    student_id: str
    metric: str
    local_date: date
    local_time: time
    value: float
    delta_from_prev: float | None
    source_object_key: str
    metadata: dict[str, Any] | None = None

    @property
    def merge_key(self) -> tuple[str, str, date, time]:
        return (self.student_id, self.metric, self.local_date, self.local_time)


@dataclass(frozen=True)
class SleepRow:
    student_id: str
    sleep_date: date
    log_id: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    efficiency: float | None
    source_object_key: str
    updated_at: datetime
    is_nap: bool = False
    minutes_awake: int | None = None
    light_sleep_minutes: int | None = None
    deep_sleep_minutes: int | None = None
    rem_sleep_minutes: int | None = None
    stages_status: str | None = None

    @property
    def upsert_key(self) -> tuple[str, date, str]:
        return (self.student_id, self.sleep_date, self.log_id)
