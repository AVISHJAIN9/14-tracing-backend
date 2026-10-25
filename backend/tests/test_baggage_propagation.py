"""
backend/tests/test_baggage_propagation.py
Comprehensive test suite for TRC-018: W3C Baggage propagation.
"""

import pytest
from tracelib.propagation.baggage import Baggage, BaggageEntry, W3CBaggagePropagator

def test_baggage_model_basic():
    bag = Baggage()
    bag2 = bag.set("userId", "12345")
    assert bag.get("userId") is None  # Immutability check
    assert bag2.get("userId") == "12345"
    assert len(bag2) == 1

def test_baggage_with_properties():
    bag = Baggage().set("userId", "12345", metadata="role=admin")
    entry = bag.get_entry("userId")
    assert entry is not None
    assert entry.value == "12345"
    assert entry.metadata == "role=admin"
    header = bag.to_header()
    assert header == "userId=12345;role=admin"

def test_baggage_to_header_and_from_header_roundtrip():
    raw = "userId=12345;role=admin,tenantId=acme"
    bag = Baggage.from_header(raw)
    assert len(bag) == 2
    assert bag.get("userId") == "12345"
    assert bag.get_entry("userId").metadata == "role=admin"
    assert bag.get("tenantId") == "acme"

    header = bag.to_header()
    assert "userId=12345;role=admin" in header
    assert "tenantId=acme" in header

def test_baggage_propagator_inject_and_extract():
    bag = Baggage().set("region", "us-east-1").set("env", "prod")
    propagator = W3CBaggagePropagator()
    carrier = {}
    propagator.inject(bag, carrier)
    assert "baggage" in carrier

    extracted = propagator.extract(carrier)
    assert extracted is not None
    assert extracted.get("region") == "us-east-1"
    assert extracted.get("env") == "prod"

def test_baggage_case_insensitive_header():
    carrier = {"Baggage": "service=auth,tier=gold"}
    propagator = W3CBaggagePropagator()
    extracted = propagator.extract(carrier)
    assert extracted is not None
    assert extracted.get("service") == "auth"
    assert extracted.get("tier") == "gold"

def test_baggage_delete():
    bag = Baggage().set("k1", "v1").set("k2", "v2")
    bag2 = bag.delete("k1")
    assert bag2.get("k1") is None
    assert bag2.get("k2") == "v2"
    assert len(bag2) == 1

def test_baggage_invalid_keys_and_values():
    bag = Baggage()
    with pytest.raises(ValueError):
        bag.set("invalid key with space", "v1")
    with pytest.raises(ValueError):
        bag.set("k1", "invalid,value,with,commas")
