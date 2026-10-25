# Project Type Detection & Adaptation Track

## Step 0 Pre-Check: Architecture & Track Classification

This document records the formal codebase inspection and classification of `14-tracing-backend`.

---

### Detection Evidence

A comprehensive inspection of the repository `/Users/avishjain/avishjain9-repos/14-tracing-backend` was conducted:

| Artifact Checked | Findings / Content | Classification Evidence |
| :--- | :--- | :--- |
| **Directory Name** | `14-tracing-backend` | Distributed tracing observability platform. |
| **Backend Manifest** | `backend/alembic.ini`, `backend/src/api/app.py` | Python 3.13, FastAPI, SQLAlchemy, Alembic, ClickHouse/Async SQLite, Pydantic. |
| **Frontend Manifest** | `frontend/package.json`, `frontend/vite.config.ts` | React 18, Vite 6, TypeScript 5.7, Tailwind CSS, Lucide icons. |
| **ML Engine** | `ml/` (11 Python modules) | Outlier latency anomaly detectors, dependency anomaly scorers, and LLM incident summary engine. |
| **Test Suite** | `backend/tests/` (141 test files) | 313 passing unit/integration tests running via `pytest`. |

---

### Formal Classification

- **Primary Classification**: **Track A (Full Stack Polyglot / Systems Observability Platform)**
- **Sub-tracks**:
  - High-throughput asynchronous backend (FastAPI, asyncio, ClickHouse columnar storage)
  - Interactive data-visualization frontend (React 18, Vite, Span DAG Explorer)
  - Production ML & AI anomaly detection engine (statistical heuristics, causal graphs, pre-trained LLM summarization API)

---

### Adaptation Rules for This Project

1. **Backend Sections**: Focus on asynchronous ingestion pipelines, tail-sampling ring buffers, span DAG reconstruction algorithms, critical path graph traversal, and columnar ClickHouse indexing.
2. **Frontend Sections**: Focus on React component tree reconciliation, SVG waterfall timelines, canvas dependency graphs, virtualized span trees, and sub-millisecond telemetry search.
3. **Database Sections**: Compare ClickHouse columnar database vs PostgreSQL vs Elasticsearch vs Cassandra for append-only span storage.
4. **AI & ML Sections**: Document the 11 ML models (latency outliers, causal root cause graphs, vector semantic trace search, and pre-trained LLM incident summarizer).
5. **Interview Focus**: Distributed tracing standards (W3C TraceContext, OpenTelemetry OTLP), sampling strategies (head vs tail vs adaptive), and scaling to 100,000 spans/sec.
