import pytest
from tracelib.core.context import TraceFlags, parse_trace_flags, format_trace_flags

def test_trace_flags_constants():
    assert TraceFlags.NONE == 0x00
    assert TraceFlags.SAMPLED == 0x01
    assert (TraceFlags.SAMPLED & 0x01) == 0x01

def test_format_trace_flags():
    assert format_trace_flags(0) == "00"
    assert format_trace_flags(1) == "01"
    assert format_trace_flags(TraceFlags.SAMPLED) == "01"
    assert format_trace_flags(255) == "ff"
    assert format_trace_flags(16) == "10"

def test_parse_trace_flags_valid():
    assert parse_trace_flags("00") == 0
    assert parse_trace_flags("01") == 1
    assert parse_trace_flags("ff") == 255
    assert parse_trace_flags("FF") == 255
    assert parse_trace_flags("0a") == 10

def test_parse_trace_flags_invalid():
    with pytest.raises(ValueError, match="trace_flags hex must be exactly 2 characters"):
        parse_trace_flags("1")
    with pytest.raises(ValueError, match="trace_flags hex must be exactly 2 characters"):
        parse_trace_flags("001")
    with pytest.raises(ValueError, match="invalid hex in trace_flags"):
        parse_trace_flags("0g")
    with pytest.raises(TypeError, match="trace_flags must be a string"):
        parse_trace_flags(1)

def test_format_trace_flags_invalid():
    with pytest.raises(ValueError, match="trace_flags must be an integer between 0 and 255"):
        format_trace_flags(-1)
    with pytest.raises(ValueError, match="trace_flags must be an integer between 0 and 255"):
        format_trace_flags(256)
    with pytest.raises(TypeError, match="trace_flags must be an integer"):
        format_trace_flags("01")
