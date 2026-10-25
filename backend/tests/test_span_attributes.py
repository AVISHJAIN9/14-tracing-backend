import pytest
from tracelib.core.span import Span

def test_span_attributes_initial():
    span = Span.start_root(name="attr_test")
    assert span.attributes == {}

def test_span_set_attribute_primitives():
    span = Span.start_root(name="attr_test")
    span.set_attribute("http.method", "GET")
    span.set_attribute("http.status_code", 200)
    span.set_attribute("net.peer.port", 8080)
    span.set_attribute("rpc.rate", 12.5)
    span.set_attribute("is_cached", True)
    span.set_attribute("tags", ["prod", "us-east-1"])

    assert span.attributes["http.method"] == "GET"
    assert span.attributes["http.status_code"] == 200
    assert span.attributes["net.peer.port"] == 8080
    assert span.attributes["rpc.rate"] == 12.5
    assert span.attributes["is_cached"] is True
    assert span.attributes["tags"] == ["prod", "us-east-1"]

def test_span_set_attributes_batch():
    span = Span.start_root(name="attr_test")
    span.set_attributes({
        "service.name": "checkout",
        "service.version": "1.2.0"
    })
    assert span.attributes["service.name"] == "checkout"
    assert span.attributes["service.version"] == "1.2.0"

def test_span_attributes_invalid_keys():
    span = Span.start_root(name="attr_test")
    with pytest.raises(TypeError, match="attribute key must be a string"):
        span.set_attribute(123, "val")
    with pytest.raises(ValueError, match="attribute key must not be empty"):
        span.set_attribute("", "val")

def test_span_attributes_invalid_value_type():
    span = Span.start_root(name="attr_test")
    with pytest.raises(TypeError, match="unsupported attribute value type"):
        span.set_attribute("complex", {"nested": "dict"})

def test_span_attributes_immutable_after_end():
    span = Span.start_root(name="attr_test")
    span.set_attribute("before_end", "yes")
    span.end()
    span.set_attribute("after_end", "no")

    assert "before_end" in span.attributes
    assert "after_end" not in span.attributes
