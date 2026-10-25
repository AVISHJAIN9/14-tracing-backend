"""
tracelib.core.ids — Cryptographically secure Trace and Span ID generators.
Invariants:
- trace_id: 16 random bytes (32 hex lowercase), all-zero is invalid.
- Uses CSPRNG (os.urandom).
"""

import os

INVALID_TRACE_ID = "0" * 32
INVALID_SPAN_ID = "0" * 16

def generate_trace_id() -> str:
    """Generate a valid 16-byte (32-hex) trace ID using CSPRNG."""
    while True:
        raw_bytes = os.urandom(16)
        tid = raw_bytes.hex().lower()
        if tid != INVALID_TRACE_ID:
            return tid

def generate_span_id() -> str:
    """Generate a valid 8-byte (16-hex) span ID using CSPRNG."""
    while True:
        raw_bytes = os.urandom(8)
        sid = raw_bytes.hex().lower()
        if sid != INVALID_SPAN_ID:
            return sid
