import time
import traceback
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union
from tracelib.core.context import TraceContext, TraceFlags, HEX_CHARS
from tracelib.core.ids import generate_trace_id, generate_span_id
from tracelib.core.events import SpanEvent
from tracelib.core.links import SpanLink

class StatusCode(Enum):
    UNSET = 0
    OK = 1
    ERROR = 2

@dataclass(frozen=True)
class Status:
    status_code: StatusCode = StatusCode.UNSET
    description: Optional[str] = None

def validate_attribute_value(val: Any) -> None:
    if isinstance(val, (str, bool, int, float)):
        return
    if isinstance(val, (list, tuple)):
        if not val:
            return
        first_t = type(val[0])
        if first_t not in (str, bool, int, float):
            raise TypeError(f"unsupported attribute sequence element type: {first_t}")
        for item in val:
            if not isinstance(item, first_t):
                raise TypeError(f"heterogeneous sequence not supported in attributes: {type(item)} != {first_t}")
        return
    raise TypeError(f"unsupported attribute value type: {type(val)}")

class Span:
    """Represents a single operation within a trace."""

    def __init__(
        self,
        name: str,
        context: TraceContext,
        parent_span_id: Optional[str] = None,
        start_time_unix_nano: Optional[int] = None,
        attributes: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
    ):
        if not name or not isinstance(name, str):
            raise ValueError("Span name must be a non-empty string")
        if not isinstance(context, TraceContext):
            raise TypeError("context must be an instance of TraceContext")

        effective_parent = parent_span_id if parent_span_id is not None else parent_id
        clean_parent = None
        if effective_parent is not None:
            if not isinstance(effective_parent, str):
                raise TypeError("parent_span_id must be a string or None")
            clean_parent = effective_parent.strip().lower()
            if len(clean_parent) != 16 or not all(c in HEX_CHARS for c in clean_parent) or clean_parent == "0" * 16:
                raise ValueError(f"invalid parent_span_id: '{effective_parent}'")

        if start_time_unix_nano is not None:
            if not isinstance(start_time_unix_nano, int) or isinstance(start_time_unix_nano, bool):
                raise TypeError("start_time_unix_nano must be an integer")
            if start_time_unix_nano <= 0:
                raise ValueError("start_time_unix_nano must be a positive integer")
            start_ns = start_time_unix_nano
        else:
            start_ns = time.time_ns()

        self._name = name
        self._context = context
        self._parent_span_id = clean_parent
        self._start_time_unix_nano: int = start_ns
        self._end_time_unix_nano: Optional[int] = None
        self._status: Status = Status(status_code=StatusCode.UNSET, description=None)
        self._attributes: Dict[str, Any] = {}
        self._events: List[SpanEvent] = []
        self._links: List[SpanLink] = []

        if attributes:
            self.set_attributes(attributes)

    @property
    def attributes(self) -> Dict[str, Any]:
        return dict(self._attributes)

    @property
    def events(self) -> List[SpanEvent]:
        return list(self._events)

    @property
    def links(self) -> List[SpanLink]:
        return list(self._links)

    def add_link(
        self,
        context: TraceContext,
        attributes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a link to another span context. No-op if span has ended."""
        if self.is_ended:
            return
        if not isinstance(context, TraceContext):
            raise TypeError("context must be a TraceContext")

        clean_attrs = {}
        if attributes:
            if not isinstance(attributes, dict):
                raise TypeError("link attributes must be a dict")
            for k, v in attributes.items():
                if not isinstance(k, str) or not k:
                    raise ValueError("link attribute keys must be non-empty strings")
                validate_attribute_value(v)
                clean_attrs[k] = v

        self._links.append(SpanLink(context=context, attributes=clean_attrs))

    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        timestamp_unix_nano: Optional[int] = None
    ) -> None:
        """Add a timestamped event to the span. No-op if span has ended."""
        if self.is_ended:
            return
        if not isinstance(name, str):
            raise TypeError("event name must be a string")
        if not name:
            raise ValueError("event name must not be empty")

        clean_attrs = {}
        if attributes:
            if not isinstance(attributes, dict):
                raise TypeError("event attributes must be a dict")
            for k, v in attributes.items():
                if not isinstance(k, str) or not k:
                    raise ValueError("event attribute keys must be non-empty strings")
                validate_attribute_value(v)
                clean_attrs[k] = v

        ts = timestamp_unix_nano if timestamp_unix_nano is not None else time.time_ns()
        self._events.append(SpanEvent(name=name, timestamp_unix_nano=ts, attributes=clean_attrs))

    def record_exception(
        self,
        exception: BaseException,
        attributes: Optional[Dict[str, Any]] = None,
        timestamp_unix_nano: Optional[int] = None
    ) -> None:
        """Record an exception as a span event and optionally mark status as ERROR."""
        if self.is_ended:
            return
        attrs = {
            "exception.type": type(exception).__name__,
            "exception.message": str(exception),
            "exception.stacktrace": traceback.format_exc()
        }
        if attributes:
            attrs.update(attributes)
        self.add_event(name="exception", attributes=attrs, timestamp_unix_nano=timestamp_unix_nano)

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute. No-op if span has ended."""
        if self.is_ended:
            return
        if not isinstance(key, str):
            raise TypeError(f"attribute key must be a string, got {type(key)}")
        if not key:
            raise ValueError("attribute key must not be empty")
        validate_attribute_value(value)
        self._attributes[key] = value

    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """Set multiple attributes. No-op if span has ended."""
        if self.is_ended:
            return
        if not isinstance(attributes, dict):
            raise TypeError("attributes must be a dict")
        for k, v in attributes.items():
            self.set_attribute(k, v)

    @property
    def status(self) -> Status:
        return self._status

    @property
    def is_error(self) -> bool:
        return self._status.status_code == StatusCode.ERROR

    def set_status(self, status: Union[Status, StatusCode], description: Optional[str] = None) -> None:
        """Set span status. No-op if span is ended."""
        if self.is_ended:
            return
        if isinstance(status, StatusCode):
            self._status = Status(status_code=status, description=description)
        elif isinstance(status, Status):
            self._status = status
        else:
            raise TypeError("status must be a Status or StatusCode")

    @property
    def name(self) -> str:
        return self._name

    @property
    def context(self) -> TraceContext:
        return self._context

    @property
    def parent_span_id(self) -> Optional[str]:
        return self._parent_span_id

    @property
    def parent_id(self) -> Optional[str]:
        return self._parent_span_id

    @property
    def is_root(self) -> bool:
        return self._parent_span_id is None

    @property
    def start_time_unix_nano(self) -> int:
        return self._start_time_unix_nano

    @property
    def end_time_unix_nano(self) -> Optional[int]:
        return self._end_time_unix_nano

    @property
    def duration_nano(self) -> Optional[int]:
        if self._end_time_unix_nano is None:
            return None
        return self._end_time_unix_nano - self._start_time_unix_nano

    @property
    def duration_ms(self) -> Optional[float]:
        if self.duration_nano is None:
            return None
        return self.duration_nano / 1_000_000.0

    @property
    def is_ended(self) -> bool:
        return self._end_time_unix_nano is not None

    @property
    def is_recording(self) -> bool:
        return not self.is_ended

    def end(self, end_time_unix_nano: Optional[int] = None) -> None:
        """End the span lifecycle. Idempotent."""
        if self.is_ended:
            return
        if end_time_unix_nano is not None:
            if not isinstance(end_time_unix_nano, int) or isinstance(end_time_unix_nano, bool):
                raise TypeError("end_time_unix_nano must be an integer")
            if end_time_unix_nano < self._start_time_unix_nano:
                raise ValueError("end_time_unix_nano must be an integer >= start_time_unix_nano")
            self._end_time_unix_nano = end_time_unix_nano
        else:
            now_nano = time.time_ns()
            self._end_time_unix_nano = max(now_nano, self._start_time_unix_nano)

    def __enter__(self) -> "Span":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end()

    @classmethod
    def start_root(
        cls,
        name: str,
        trace_flags: int = TraceFlags.SAMPLED,
        start_time_unix_nano: Optional[int] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> "Span":
        """Factory method to start a new root span with generated trace_id and span_id."""
        trace_id = generate_trace_id()
        span_id = generate_span_id()
        context = TraceContext(trace_id=trace_id, span_id=span_id, trace_flags=trace_flags)
        return cls(
            name=name,
            context=context,
            parent_span_id=None,
            start_time_unix_nano=start_time_unix_nano,
            attributes=attributes
        )

    def create_child(
        self,
        name: str,
        start_time_unix_nano: Optional[int] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> "Span":
        """Create a child span linked to this span as parent."""
        child_span_id = generate_span_id()
        child_context = TraceContext(
            trace_id=self._context.trace_id,
            span_id=child_span_id,
            trace_flags=self._context.trace_flags,
            trace_state=self._context.trace_state,
            is_remote=False
        )
        return Span(
            name=name,
            context=child_context,
            parent_span_id=self._context.span_id,
            start_time_unix_nano=start_time_unix_nano,
            attributes=attributes
        )
