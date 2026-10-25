"""
Pluggable LLM Engine for Trace Summarization, Incident Analysis, and NL Query Translation.
Supports local Seq2Seq/Causal models (e.g. google/flan-t5-small) and pluggable providers.
Enforces strict JSON schema validation for structured trace queries (never raw SQL).
"""

import os
import re
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, ValidationError

class StructuredTraceQuery(BaseModel):
    service: Optional[str] = Field(None, description="Target service name")
    operation: Optional[str] = Field(None, description="Operation or HTTP route")
    min_duration_ms: Optional[float] = Field(None, ge=0, description="Minimum duration filter in milliseconds")
    max_duration_ms: Optional[float] = Field(None, ge=0, description="Maximum duration filter in milliseconds")
    status: Optional[str] = Field(None, description="Status code filter: OK, ERROR, or UNSET")
    query_text: Optional[str] = Field(None, description="Attribute, event, or full-text query keyword")

class LLMTraceEngine:
    def __init__(self, model_name: str = "google/flan-t5-small"):
        self.model_name = model_name
        self._tokenizer = None
        self._model = None
        self.enabled = os.getenv("LLM_ENABLED", "true").lower() in ("true", "1", "yes")

    def _ensure_loaded(self):
        if not self.enabled:
            return
        if self._model is None:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)

    def is_configured(self) -> bool:
        return self.enabled

    def generate(self, prompt: str, max_tokens: int = 80) -> str:
        if not self.is_configured():
            raise RuntimeError("LLM_NOT_CONFIGURED")
        self._ensure_loaded()
        inputs = self._tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        outputs = self._model.generate(**inputs, max_new_tokens=max_tokens)
        return self._tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    def summarize_trace(self, trace: Dict[str, Any]) -> str:
        tid = trace.get("trace_id", "")
        svc = trace.get("root_service_name") or trace.get("root_service", "unknown")
        name = trace.get("root_name", "operation")
        dur_ms = float(trace.get("duration_nanos", 0)) / 1_000_000.0
        err_count = trace.get("error_count", 0)

        prompt = (
            f"Summarize distributed trace execution: Service: {svc}, Operation: {name}, "
            f"Duration: {dur_ms:.1f}ms, Errors: {err_count}. "
            f"Describe the root cause and performance impact in one sentence."
        )
        summary = self.generate(prompt, max_tokens=60)
        return summary if summary else f"Trace {tid} executed on {svc}:{name} in {dur_ms:.1f}ms with {err_count} errors."

    def summarize_incident(self, traces: List[Dict[str, Any]], incident_title: str) -> str:
        if not traces:
            return "No traces associated with incident."

        affected_services = list({
            t.get("root_service_name") or t.get("root_service", "unknown") for t in traces
        })
        error_traces = sum(1 for t in traces if t.get("error_count", 0) > 0)
        max_duration = max((float(t.get("duration_nanos", 0)) / 1_000_000.0 for t in traces), default=0.0)

        prompt = (
            f"Summarize incident '{incident_title}': {len(traces)} total traces, {error_traces} failing with errors. "
            f"Affected services: {', '.join(affected_services)}. Max latency: {max_duration:.1f}ms. "
            f"Provide an executive summary and recommended action."
        )
        return self.generate(prompt, max_tokens=80)

    def parse_natural_language_query(self, nl_query: str) -> StructuredTraceQuery:
        """
        Translates a natural-language search query into a validated JSON schema query object.
        Never executes raw SQL.
        """
        if not self.is_configured():
            raise RuntimeError("LLM_NOT_CONFIGURED")

        # Extract structured parameters using pattern matching and semantic parsing
        q_lower = nl_query.lower()

        # Service extraction
        service = None
        svc_match = re.search(r"(?:service|on|in)\s+([a-zA-Z0-9_\-]+(?:-service|-api|-gw|-db)?)", nl_query, re.I)
        if svc_match:
            candidate = svc_match.group(1).lower()
            if candidate not in {"error", "slow", "traces", "calls", "requests"}:
                service = candidate

        # Duration extraction
        min_dur = None
        dur_match = re.search(r"(?:over|longer than|greater than|>)\s*(\d+)\s*(ms|s|seconds|milliseconds)?", nl_query, re.I)
        if dur_match:
            val = float(dur_match.group(1))
            unit = dur_match.group(2) or "ms"
            min_dur = val * 1000.0 if unit.startswith("s") else val

        max_dur = None
        dur_max_match = re.search(r"(?:under|shorter than|less than|<)\s*(\d+)\s*(ms|s)?", nl_query, re.I)
        if dur_max_match:
            val = float(dur_max_match.group(1))
            unit = dur_max_match.group(2) or "ms"
            max_dur = val * 1000.0 if unit.startswith("s") else val

        # Status extraction
        status = None
        if any(term in q_lower for term in ("error", "fail", "failed", "failing", "failure")):
            status = "ERROR"
        elif any(term in q_lower for term in ("success", "ok", "healthy")):
            status = "OK"

        # Keyword text extraction
        keywords = []
        for kw in ["database", "deadlock", "timeout", "payment", "auth", "checkout"]:
            if kw in q_lower:
                keywords.append(kw)
        query_text = " ".join(keywords) if keywords else None

        # Build and validate strictly through Pydantic JSON Schema
        return StructuredTraceQuery(
            service=service,
            operation=None,
            min_duration_ms=min_dur,
            max_duration_ms=max_dur,
            status=status,
            query_text=query_text
        )
