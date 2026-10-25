"""
backend/tests/test_invalid_context_handling.py
Comprehensive test suite for TRC-026: Invalid context handling and graceful fallback.
"""

import pytest
from tracelib.core.context import TraceContext
from tracelib.propagation.fallback import extract_or_create_root

def test_invalid_traceparent_all_zeros_starts_new_root():
    carrier = {
        "traceparent": "00-00000000000000000000000000000000-0000000000000000-01"
    }
    ctx = extract_or_create_root(carrier)
    assert ctx is not None
    assert ctx.is_valid is True
    assert ctx.trace_id != "0" * 32
    assert ctx.span_id != "0" * 16
    assert ctx.is_remote is False

def test_invalid_traceparent_version_ff_starts_new_root():
    carrier = {
        "traceparent": "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    }
    ctx = extract_or_create_root(carrier)
    assert ctx is not None
    assert ctx.is_valid is True
    assert ctx.trace_id != "4bf92f3577b34da6a3ce929d0e0e4736"
    assert ctx.is_remote is False

def test_invalid_traceparent_corrupted_characters_starts_new_root():
    carrier = {
        "traceparent": "00-garbage_not_hex_chars_at_all-00f067aa0ba902b7-01"
    }
    ctx = extract_or_create_root(carrier)
    assert ctx is not None
    assert ctx.is_valid is True
    assert ctx.is_remote is False

def test_invalid_context_never_crashes_with_random_types():
    assert extract_or_create_root(None).is_valid is True
    assert extract_or_create_root(12345).is_valid is True
    assert extract_or_create_root({"traceparent": None}).is_valid is True
    assert extract_or_create_root({"traceparent": 99999}).is_valid is True
    assert extract_or_create_root({"traceparent": ""}).is_valid is True
    assert extract_or_create_root({"traceparent": "too-short"}).is_valid is True

def test_invalid_context_fresh_ids_are_valid_csprng():
    ctx1 = extract_or_create_root({"traceparent": "invalid-1"})
    ctx2 = extract_or_create_root({"traceparent": "invalid-2"})
    assert ctx1.trace_id != ctx2.trace_id
    assert ctx1.span_id != ctx2.span_id
    assert len(ctx1.trace_id) == 32
    assert len(ctx1.span_id) == 16
