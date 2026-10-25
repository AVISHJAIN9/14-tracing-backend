# Step-by-Step Build Order & Implementation Guide

This guide details the exact chronological sequence to reconstruct **14-Tracing-Backend** from scratch.

---

## Phase 1: Core Foundation & Data Modeling
1. **Initialize Database Schema**: Define the primary `spans` and `traces` tables using SQLAlchemy models (`backend/src/storage/models.py`). Index `trace_id`, `service_name`, and `start_time_us`.
2. **FastAPI Application Setup**: Scaffold `backend/src/api/app.py` with standard middleware, health probes (`/healthz`, `/readyz`), and centralized HTTP error formatting.
3. **Trace Context Propagation**: Implement W3C `traceparent` parsing in `backend/src/tracelib/core/` to extract `trace_id`, `span_id`, and sampling flags.

---

## Phase 2: Ingestion & Collector Pipeline
4. **OTLP Ingestion Endpoints**: Build `api/routes/ingestion.py` supporting OpenTelemetry Protobuf and JSON payloads.
5. **PII Sanitizer & Security Redaction**: Implement regex and key-name scanners in `security/pii_filter.py` to strip passwords, credit card numbers, and authorization tokens.
6. **Asynchronous Ring Buffer**: Implement bounded queue management in `collector/queue_buffer.py` with background batch-flushing workers.

---

## Phase 3: Adaptive Sampling Engine
7. **Tail-Sampling Sliding Window**: Build `sampling/tail_window.py` holding uncompleted trace spans for up to 30 seconds.
8. **Error & Latency Evaluators**: Wire `sampling/error_aware.py` and `sampling/tail.py` to promote traces with HTTP errors or duration exceeding p99 thresholds.

---

## Phase 4: Query Engine & Graph Traversal
9. **Trace Reconstruction**: Build `query/trace_lookup.py` to assemble unordered spans into an execution tree.
10. **Critical Path Calculation**: Implement DAG topological sorting in `query/critical_path.py` to isolate blocking sequential spans.

---

## Phase 5: Machine Learning & LLM Integration
11. **Anomaly Detectors**: Implement `ml/latency_anomaly.py` and `ml/dependency_anomaly.py` using statistical z-scores.
12. **Pre-trained LLM Postmortem Engine**: Connect `ml/llm_engine.py` to external LLM API with strict JSON schema parsing.

---

## Phase 6: Frontend Visualization (React 18 + Vite)
13. **Vite Scaffold**: Set up React 18, TypeScript, and Tailwind CSS in `frontend/`.
14. **Gantt Waterfall & DAG Tree**: Implement `WaterfallTimeline.tsx` and `SpanTree.tsx` to visualize parallel and critical path execution.
