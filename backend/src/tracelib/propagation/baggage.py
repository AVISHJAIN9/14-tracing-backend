"""
tracelib.propagation.baggage — W3C Baggage Model and Propagator.
Compliant with W3C Baggage Specification (https://www.w3.org/TR/baggage/).
"""

import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Tuple
from tracelib.propagation.w3c import default_getter, default_setter, GetterFunc, SetterFunc

BAGGAGE_HEADER = "baggage"
KEY_PATTERN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9a-zA-Z]+$")

def validate_baggage_key(key: str) -> None:
    if not isinstance(key, str):
        raise TypeError("Baggage key must be a string")
    if not key or not KEY_PATTERN.match(key):
        raise ValueError(f"invalid baggage key: '{key}'")

def validate_baggage_value(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("Baggage value must be a string")
    # Disallow delimiter characters in raw value
    if any(c in value for c in (",", ";")):
        raise ValueError(f"invalid characters in baggage value: '{value}'")

@dataclass(frozen=True)
class BaggageEntry:
    key: str
    value: str
    metadata: Optional[str] = None

    def to_header_member(self) -> str:
        if self.metadata:
            return f"{self.key}={self.value};{self.metadata}"
        return f"{self.key}={self.value}"

class Baggage:
    """Immutable W3C Baggage container."""

    def __init__(self, entries: Optional[Tuple[BaggageEntry, ...]] = None):
        self._entries: Tuple[BaggageEntry, ...] = entries or ()

    def __len__(self) -> int:
        return len(self._entries)

    def get_entry(self, key: str) -> Optional[BaggageEntry]:
        validate_baggage_key(key)
        for entry in self._entries:
            if entry.key == key:
                return entry
        return None

    def get(self, key: str) -> Optional[str]:
        entry = self.get_entry(key)
        return entry.value if entry else None

    def set(self, key: str, value: str, metadata: Optional[str] = None) -> "Baggage":
        validate_baggage_key(key)
        validate_baggage_value(value)
        new_entry = BaggageEntry(key=key, value=value, metadata=metadata)
        # Replace if existing, otherwise append
        filtered = [e for e in self._entries if e.key != key]
        filtered.append(new_entry)
        return Baggage(entries=tuple(filtered))

    def delete(self, key: str) -> "Baggage":
        validate_baggage_key(key)
        filtered = [e for e in self._entries if e.key != key]
        return Baggage(entries=tuple(filtered))

    def to_header(self) -> str:
        return ",".join(e.to_header_member() for e in self._entries)

    @classmethod
    def from_header(cls, header_val: Any) -> "Baggage":
        if not isinstance(header_val, str) or not header_val.strip():
            return cls()

        entries: List[BaggageEntry] = []
        members = [m.strip() for m in header_val.split(",") if m.strip()]

        for member in members:
            parts = member.split(";")
            kv = parts[0].strip()
            if "=" not in kv:
                continue
            k, v = kv.split("=", 1)
            k = k.strip()
            v = v.strip()
            try:
                validate_baggage_key(k)
                validate_baggage_value(v)
            except (ValueError, TypeError):
                continue

            metadata = ";".join(p.strip() for p in parts[1:]) if len(parts) > 1 else None
            # Do not duplicate keys in parse; first appearance wins
            if not any(e.key == k for e in entries):
                entries.append(BaggageEntry(key=k, value=v, metadata=metadata))

        return cls(entries=tuple(entries))

class W3CBaggagePropagator:
    """Propagator for W3C Baggage headers."""

    def inject(
        self,
        baggage: Baggage,
        carrier: MutableMapping[str, str],
        setter: SetterFunc = default_setter,
    ) -> None:
        if baggage is None or len(baggage) == 0:
            return
        header = baggage.to_header()
        if header:
            setter(carrier, BAGGAGE_HEADER, header)

    def extract(
        self,
        carrier: Any,
        getter: GetterFunc = default_getter,
    ) -> Optional[Baggage]:
        raw = getter(carrier, BAGGAGE_HEADER)
        if not raw:
            return None
        return Baggage.from_header(raw)
