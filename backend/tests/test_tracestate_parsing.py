"""
backend/tests/test_tracestate_parsing.py
Comprehensive test suite for TRC-017: W3C tracestate header parsing.
"""

import pytest
from tracelib.propagation.tracestate import parse_tracestate_header, parse_tracestate_headers

def test_parse_tracestate_single_header():
    raw = "congo=t61rcWkgMzE,rojo=00f067aa0ba902b7"
    ts = parse_tracestate_header(raw)
    assert len(ts) == 2
    assert ts.get("congo") == "t61rcWkgMzE"
    assert ts.get("rojo") == "00f067aa0ba902b7"
    assert ts.to_header() == raw

def test_parse_tracestate_multiple_headers():
    headers = [
        "congo=123",
        "rojo=456,vendor=789"
    ]
    ts = parse_tracestate_headers(headers)
    assert len(ts) == 3
    assert ts.get("congo") == "123"
    assert ts.get("rojo") == "456"
    assert ts.get("vendor") == "789"
    assert ts.to_header() == "congo=123,rojo=456,vendor=789"

def test_parse_tracestate_whitespace_handling():
    raw = "  congo = 123  ,  rojo = 456  "
    ts = parse_tracestate_header(raw)
    assert len(ts) == 2
    assert ts.get("congo") == "123"
    assert ts.get("rojo") == "456"

def test_parse_tracestate_skips_malformed_members():
    raw = "congo=123,invalid_no_equals,INVALID_UPPERCASE=1,rojo=456,=novalue,nokey="
    ts = parse_tracestate_header(raw)
    assert len(ts) == 2
    assert ts.get("congo") == "123"
    assert ts.get("rojo") == "456"

def test_parse_tracestate_deduplicates_keeping_first():
    raw = "congo=first,rojo=456,congo=second"
    ts = parse_tracestate_header(raw)
    assert len(ts) == 2
    assert ts.get("congo") == "first"
    assert ts.get("rojo") == "456"

def test_parse_tracestate_truncates_at_32():
    entries = [f"k{i}={i}" for i in range(40)]
    raw = ",".join(entries)
    ts = parse_tracestate_header(raw)
    assert len(ts) == 32
    assert ts.get("k0") == "0"
    assert ts.get("k31") == "31"
    assert ts.get("k32") is None

def test_parse_tracestate_tenant_keys():
    raw = "vendor@system=val1,tenant-123/sub@sys=val2"
    ts = parse_tracestate_header(raw)
    assert len(ts) == 2
    assert ts.get("vendor@system") == "val1"
    assert ts.get("tenant-123/sub@sys") == "val2"

def test_parse_tracestate_empty_or_invalid_types():
    assert len(parse_tracestate_header("")) == 0
    assert len(parse_tracestate_header("   ")) == 0
    assert len(parse_tracestate_header(None)) == 0
    assert len(parse_tracestate_headers([])) == 0
    assert len(parse_tracestate_headers(None)) == 0
