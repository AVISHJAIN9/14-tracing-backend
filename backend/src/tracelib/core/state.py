"""
tracelib.core.state — W3C TraceState Model and Parser.
Invariants:
- Max 32 list-members.
- Key and value grammar per W3C specification.
- Order preserved: set() moves/prepends to front; oldest dropped if > 32.
"""

import re
from typing import Optional, Tuple, Dict, List

SIMPLE_KEY_PATTERN = re.compile(r"^[a-z0-9_\-*/]{1,256}$")
TENANT_KEY_PATTERN = re.compile(r"^[a-z0-9_\-*/]{1,241}@[a-z0-9_\-*/]{1,14}$")

def validate_key(key: str) -> None:
    if not isinstance(key, str):
        raise TypeError("tracestate key must be a string")
    if not key or not (SIMPLE_KEY_PATTERN.match(key) or TENANT_KEY_PATTERN.match(key)):
        raise ValueError(f"invalid tracestate key: '{key}'")

def validate_value(value: str) -> None:
    if not isinstance(value, str):
        raise TypeError("tracestate value must be a string")
    if not value or len(value) > 256:
        raise ValueError(f"tracestate value length must be 1-256 characters: got {len(value)}")
    # ASCII 0x20 to 0x7E, no comma or equals
    for char in value:
        code = ord(char)
        if code < 0x20 or code > 0x7E or char in (",", "="):
            raise ValueError(f"invalid tracestate value character: '{char}'")

class TraceState:
    """Immutable representation of W3C TraceState with max 32 entries."""

    def __init__(self, entries: Optional[Tuple[Tuple[str, str], ...]] = None):
        self._entries: Tuple[Tuple[str, str], ...] = entries or ()

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, key: str) -> Optional[str]:
        validate_key(key)
        for k, v in self._entries:
            if k == key:
                return v
        return None

    def set(self, key: str, value: str) -> "TraceState":
        """Prepend or update key-value pair, preserving max 32 entries."""
        validate_key(key)
        validate_value(value)

        # Filter out existing key if present
        filtered = [pair for pair in self._entries if pair[0] != key]
        # Prepend to front
        new_entries = [(key, value)] + filtered
        # Truncate to max 32 members per spec
        return TraceState(entries=tuple(new_entries[:32]))

    def delete(self, key: str) -> "TraceState":
        """Remove key from tracestate."""
        validate_key(key)
        filtered = [pair for pair in self._entries if pair[0] != key]
        return TraceState(entries=tuple(filtered))

    def to_header(self) -> str:
        """Serialize tracestate to W3C header value."""
        return ",".join(f"{k}={v}" for k, v in self._entries)

    @classmethod
    def from_header(cls, header_val: str) -> "TraceState":
        """Parse W3C tracestate header string."""
        if not header_val or not isinstance(header_val, str):
            return cls()

        clean_header = header_val.strip()
        if not clean_header:
            return cls()

        parsed_pairs: List[Tuple[str, str]] = []
        members = [m.strip() for m in clean_header.split(",") if m.strip()]

        for member in members:
            if "=" not in member:
                continue
            k, v = member.split("=", 1)
            k = k.strip()
            v = v.strip()
            try:
                validate_key(k)
                validate_value(v)
                # Avoid duplicate keys in initial parse: keep first occurrence
                if not any(existing[0] == k for existing in parsed_pairs):
                    parsed_pairs.append((k, v))
            except (ValueError, TypeError):
                continue # Skip malformed member per W3C tolerant parsing

        return cls(entries=tuple(parsed_pairs[:32]))
