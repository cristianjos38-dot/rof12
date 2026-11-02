from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generic, List, Mapping, TypeVar


class TrustLevel(str, Enum):
    UNTRUSTED = "UNTRUSTED"
    FULLY_RECONCILED = "FULLY_RECONCILED"


class ReconciliationError(ValueError):
    """Raised when an untrusted value does not exactly match internal truth."""


T = TypeVar("T")


@dataclass(frozen=True)
class TaintedValue(Generic[T]):
    value: T
    source_id: str
    is_tainted: bool = True
    trust_level: TrustLevel = TrustLevel.UNTRUSTED

    @classmethod
    def external(cls, value: T, source_id: str) -> "TaintedValue[T]":
        return cls(value=value, source_id=source_id, is_tainted=True, trust_level=TrustLevel.UNTRUSTED)

    @classmethod
    def trusted(cls, value: T, source_id: str = "internal") -> "TaintedValue[T]":
        return cls(value=value, source_id=source_id, is_tainted=False, trust_level=TrustLevel.FULLY_RECONCILED)

    def transform(self, fn, operation: str = "transform") -> "TaintedValue":
        return TaintedValue(
            value=fn(self.value),
            source_id="%s:%s" % (self.source_id, operation),
            is_tainted=self.is_tainted,
            trust_level=self.trust_level,
        )

    def __add__(self, other):
        if isinstance(other, TaintedValue):
            value, tainted = self.value + other.value, self.is_tainted or other.is_tainted
            source = "%s+%s" % (self.source_id, other.source_id)
        else:
            value, tainted, source = self.value + other, self.is_tainted, self.source_id
        return TaintedValue(value, source, tainted, TrustLevel.UNTRUSTED if tainted else TrustLevel.FULLY_RECONCILED)

    def __radd__(self, other):
        return self.__add__(other)


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    source_type: str
    fragment_hash: str


class SourceRegistry:
    def __init__(self):
        self._records: Dict[str, SourceRecord] = {}

    def register_external(self, source_id: str, source_type: str, fragment_hash: str) -> SourceRecord:
        record = SourceRecord(source_id, source_type, fragment_hash)
        self._records[source_id] = record
        return record

    def get(self, source_id: str) -> SourceRecord:
        return self._records[source_id]


class ProvenanceTracker:
    def __init__(self, registry: SourceRegistry = None):
        self.registry = registry or SourceRegistry()
        self._events: List[Dict[str, Any]] = []

    def extract(self, value: T, source_id: str, source_type: str = "external", fragment_hash: str = "") -> TaintedValue[T]:
        self.registry.register_external(source_id, source_type, fragment_hash)
        result = TaintedValue.external(value, source_id)
        self._events.append({"source_id": source_id, "is_tainted": True, "trust_level": TrustLevel.UNTRUSTED.value})
        return result

    def reconcile(self, candidate: TaintedValue[T], internal_value: T) -> TaintedValue[T]:
        if candidate.value != internal_value:
            raise ReconciliationError("deterministic reconciliation mismatch")
        return TaintedValue.trusted(internal_value, source_id="reconciled:%s" % candidate.source_id)

    @property
    def events(self) -> tuple:
        return tuple(self._events)

