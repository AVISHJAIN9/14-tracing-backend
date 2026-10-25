"""
backend/tests/test_traceparent_parsing.py
Comprehensive test suite for TRC-016: W3C traceparent parsing specification conformance.
"""

import pytest
from tracelib.propagation.traceparent import Traceparent, parse_traceparent_header

def test_traceparent_valid_version_00():
    raw = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    tp = parse_traceparent_header(raw)
    assert tp is not None
    assert tp.version == "00"
    assert tp.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert tp.parent_id == "00f067aa0ba902b7"
    assert tp.trace_flags == 0x01
    assert tp.is_sampled is True
    assert tp.to_header() == raw

def test_traceparent_all_zero_trace_id_invalid():
    raw = "00-00000000000000000000000000000000-00f067aa0ba902b7-01"
    assert parse_traceparent_header(raw) is None

def test_traceparent_all_zero_parent_id_invalid():
    raw = "00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01"
    assert parse_traceparent_header(raw) is None

def test_traceparent_version_ff_invalid():
    raw = "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert parse_traceparent_header(raw) is None

def test_traceparent_version_00_extra_fields_invalid():
    raw = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01-extra"
    assert parse_traceparent_header(raw) is None

def test_traceparent_future_version_supported():
    # Future version (e.g. 01) allows extra forward-compatible fields
    raw = "01-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01-routing-data"
    tp = parse_traceparent_header(raw)
    assert tp is not None
    assert tp.version == "01"
    assert tp.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert tp.parent_id == "00f067aa0ba902b7"
    assert tp.trace_flags == 0x01

def test_traceparent_invalid_lengths_and_chars():
    # Not enough fields
    assert parse_traceparent_header("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7") is None
    # Short trace ID
    assert parse_traceparent_header("00-4bf92f35-00f067aa0ba902b7-01") is None
    # Invalid characters
    assert parse_traceparent_header("00-4bf92f3577b34da6a3ce929d0e0e47zz-00f067aa0ba902b7-01") is None
    # Invalid flags
    assert parse_traceparent_header("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-0g") is None
    # Non-string input
    assert parse_traceparent_header(None) is None
    assert parse_traceparent_header(12345) is None

def test_traceparent_case_normalization():
    raw = "00-4BF92F3577B34DA6A3CE929D0E0E4736-00F067AA0BA902B7-01"
    tp = parse_traceparent_header(raw)
    assert tp is not None
    assert tp.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert tp.parent_id == "00f067aa0ba902b7"
    assert tp.to_header() == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
