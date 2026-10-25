# DECISIONS.md — Architecture & Engineering Decision Records (ADR)

## ADR-001: Architecture & Technology Stack for Project 14
- **Date:** 2026-10-24
- **Status:** Accepted
- **Context:** Building OpenTelemetry-compatible distributed tracing backend from scratch supporting OTLP/gRPC and OTLP/HTTP.
- **Decision:**
  - Instrumentation & Core (`tracelib`): Python 3.13, ContextVars, W3C Trace Context spec compliant (traceparent, tracestate, baggage).
  - Backend Storage: PostgreSQL 16 partitioned by day, indexed by tenant_id, trace_id, span_id, service, operation, and start_time.
  - Collector Queue: Redis 7 streams with backpressure.
  - Query API: FastAPI + SQLAlchemy 2.0 (asyncpg).
  - Frontend: React 18 + Vite + TypeScript.
