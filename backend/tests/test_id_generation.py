import pytest
import re
from tracelib.core.ids import generate_trace_id, generate_span_id

HEX_PATTERN = re.compile(r"^[0-9a-f]{32}$")
SPAN_HEX_PATTERN = re.compile(r"^[0-9a-f]{16}$")

def test_generate_trace_id_format():
    tid = generate_trace_id()
    assert isinstance(tid, str)
    assert len(tid) == 32
    assert HEX_PATTERN.match(tid) is not None
    assert tid != "0" * 32

def test_generate_trace_id_uniqueness():
    count = 10000
    ids = {generate_trace_id() for _ in range(count)}
    assert len(ids) == count
    assert "0" * 32 not in ids

def test_generate_trace_id_uses_csprng(monkeypatch):
    # Verify that os.urandom or secrets is called
    import os
    called = []
    orig_urandom = os.urandom

    def mock_urandom(n):
        called.append(n)
        return orig_urandom(n)

    monkeypatch.setattr(os, "urandom", mock_urandom)
    tid = generate_trace_id()
    assert len(called) > 0
    assert 16 in called

def test_generate_span_id_format():
    sid = generate_span_id()
    assert isinstance(sid, str)
    assert len(sid) == 16
    assert SPAN_HEX_PATTERN.match(sid) is not None
    assert sid != "0" * 16

def test_generate_span_id_uniqueness():
    count = 10000
    ids = {generate_span_id() for _ in range(count)}
    assert len(ids) == count
    assert "0" * 16 not in ids

def test_generate_span_id_uses_csprng(monkeypatch):
    import os
    called = []
    orig_urandom = os.urandom

    def mock_urandom(n):
        called.append(n)
        return orig_urandom(n)

    monkeypatch.setattr(os, "urandom", mock_urandom)
    sid = generate_span_id()
    assert len(called) > 0
    assert 8 in called
