import pytest
from tracelib.core.state import TraceState

def test_tracestate_empty():
    ts = TraceState()
    assert len(ts) == 0
    assert ts.to_header() == ""
    assert ts.get("congo") is None

def test_tracestate_from_header():
    header = "congo=t61rcWkgMzE,rojo=00f067aa0ba902b7"
    ts = TraceState.from_header(header)
    assert len(ts) == 2
    assert ts.get("congo") == "t61rcWkgMzE"
    assert ts.get("rojo") == "00f067aa0ba902b7"
    assert ts.to_header() == header

def test_tracestate_mutation_order_preserved():
    # Adding moves to front
    ts = TraceState.from_header("congo=val1,rojo=val2")
    ts2 = ts.set("rojo", "new_val") # update moves to front
    assert ts2.to_header() == "rojo=new_val,congo=val1"

    ts3 = ts2.set("vendor", "v_val") # new key prepends
    assert ts3.to_header() == "vendor=v_val,rojo=new_val,congo=val1"

def test_tracestate_delete():
    ts = TraceState.from_header("a=1,b=2,c=3")
    ts2 = ts.delete("b")
    assert ts2.to_header() == "a=1,c=3"

def test_tracestate_max_32_members():
    ts = TraceState()
    for i in range(35):
        ts = ts.set(f"k{i}", f"v{i}")
    # Hard invariant: max 32 list-members
    assert len(ts) == 32
    # Most recent keys must be present (k34 down to k3)
    assert ts.get("k34") == "v34"
    assert ts.get("k0") is None # oldest dropped

def test_tracestate_invalid_keys():
    ts = TraceState()
    with pytest.raises(ValueError, match="invalid tracestate key"):
        ts.set("INVALID_KEY_UPPERCASE", "val")
    with pytest.raises(ValueError, match="invalid tracestate key"):
        ts.set("", "val")

def test_tracestate_invalid_values():
    ts = TraceState()
    with pytest.raises(ValueError, match="invalid tracestate value"):
        ts.set("key", "val=contains_equals")
    with pytest.raises(ValueError, match="invalid tracestate value"):
        ts.set("key", "val,contains_comma")
