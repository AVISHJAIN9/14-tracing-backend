"""
tracelib.propagation — Context and Baggage Propagation Package
"""

from tracelib.propagation.w3c import W3CTraceContextPropagator
from tracelib.propagation.traceparent import Traceparent, parse_traceparent_header
from tracelib.propagation.tracestate import parse_tracestate_header, parse_tracestate_headers
from tracelib.propagation.baggage import Baggage, BaggageEntry, W3CBaggagePropagator
from tracelib.propagation.http import HttpHeaderPropagator, normalize_http_headers
from tracelib.propagation.grpc import GrpcMetadataPropagator, normalize_grpc_metadata
from tracelib.propagation.websocket import WebSocketPropagator
from tracelib.propagation.async_context import (
    get_current_span,
    attach_span,
    detach_span,
    use_span,
)
from tracelib.propagation.thread_context import (
    wrap_callable_with_context,
    ContextThreadPoolExecutor,
)
from tracelib.propagation.extract import (
    extract_context,
    ContextExtractor,
    ExtractedContext,
    DictGetter,
)
from tracelib.propagation.inject import (
    inject_context,
    ContextInjector,
)
from tracelib.propagation.fallback import (
    extract_or_create_root,
)
from tracelib.propagation.carrier import (
    start_span_from_carrier,
)

__all__ = [
    "W3CTraceContextPropagator",
    "Traceparent",
    "parse_traceparent_header",
    "parse_tracestate_header",
    "parse_tracestate_headers",
    "Baggage",
    "BaggageEntry",
    "W3CBaggagePropagator",
    "HttpHeaderPropagator",
    "normalize_http_headers",
    "GrpcMetadataPropagator",
    "normalize_grpc_metadata",
    "WebSocketPropagator",
    "get_current_span",
    "attach_span",
    "detach_span",
    "use_span",
    "wrap_callable_with_context",
    "ContextThreadPoolExecutor",
    "extract_context",
    "ContextExtractor",
    "ExtractedContext",
    "DictGetter",
    "inject_context",
    "ContextInjector",
    "extract_or_create_root",
    "start_span_from_carrier",
]
