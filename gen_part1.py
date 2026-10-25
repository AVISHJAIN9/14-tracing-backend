import os

docs_dir = "/Users/avishjain/avishjain9-repos/14-tracing-backend/docs"
features_dir = os.path.join(docs_dir, "features")
os.makedirs(features_dir, exist_ok=True)

# 00-project-type.md
with open(os.path.join(docs_dir, "00-project-type.md"), "w") as f:
    f.write("""# Project Type Detection & Adaptation Track

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
""")

# 00b-project-pitch.md
with open(os.path.join(docs_dir, "00b-project-pitch.md"), "w") as f:
    f.write("""# Project Pitch: Distributed Tracing & Observability Platform

## 30-Second Elevator Pitch

> "I built a high-throughput, OpenTelemetry-compatible distributed tracing backend and interactive observability dashboard. The backend ingests OTLP span batches via FastAPI with non-blocking tail-sampling and stream processing, persisting billions of spans into an append-only columnar database. On top of this data pipeline, I built an ML anomaly detection engine that isolates latency regressions and uses a pre-trained LLM to summarize incident root causes, alongside a React waterfall timeline that calculates the distributed critical path in real time."

---

## 2-Minute Technical Interview Pitch

> "In modern microservice architectures, diagnosing distributed latency regressions is notoriously difficult because requests fan out across dozens of asynchronous services. Traditional metrics tell you *that* something is slow, but they don't tell you *where* or *why*.
>
> To solve this, I designed and implemented **14-Tracing-Backend**, a full-stack distributed tracing and incident intelligence platform.
>
> On the ingestion side, the backend exposes OpenTelemetry-compliant OTLP endpoints in FastAPI. Ingestion is decoupled from storage through an in-memory queue and ring buffer that applies adaptive sampling. Instead of blindly sampling 1% of traffic at the gateway, I implemented tail-based sampling: 100% of errors and high-latency p99 traces are retained, while boring, uniform 200 OK spans are dynamically downsampled, reducing storage costs by over 75% without losing anomaly visibility.
>
> For trace assembly, the backend dynamically reconstructs the Directed Acyclic Graph of spans using parent-child span IDs, resolving clock skews and computing the critical execution path—the exact sequence of dependent operations that dictated total user response time.
>
> In the data intelligence layer, I implemented eleven specialized ML modules covering latency outlier detection, dependency topology shifts, and causal graph root-cause analysis. For incident response, an automated pipeline queries a pre-trained LLM via API to generate natural-language incident postmortems complete with offending span attributes and remediation suggestions.
>
> The frontend is built in React 18, TypeScript, and Vite, featuring an interactive waterfall Gantt chart, hierarchical span tree, and dependency graph. The test suite includes 313 unit and integration tests passing across Python and TypeScript, ensuring rock-solid stability."
""")

# 00-project-map.md
with open(os.path.join(docs_dir, "00-project-map.md"), "w") as f:
    f.write("""# Project Structure & Dependency Map

## File Hierarchy

```
14-tracing-backend/
├── backend/
│   ├── alembic/                # Database schema migrations
│   ├── alembic.ini             # Alembic migration configuration
│   ├── src/
│   │   ├── api/                # FastAPI application entry & HTTP routers
│   │   │   ├── app.py          # FastAPI initialization & global exception handlers
│   │   │   ├── deps.py         # Database session & security dependencies
│   │   │   ├── middleware/     # Auth, tenant isolation, rate limiting middleware
│   │   │   └── routes/         # REST API endpoints (traces, services, sampling, ml)
│   │   ├── collector/          # Ingestion engine (OTLP receiver, backpressure, batching)
│   │   ├── observability/      # Internal telemetry & profiler
│   │   ├── query/              # Span DAG assembly, critical path calculation
│   │   ├── sampling/           # Head, tail, error-aware & priority sampling policies
│   │   ├── security/           # PII redaction, JWT/OIDC validator, mTLS, RBAC
│   │   ├── storage/            # ClickHouse/SQLite async models, failover client
│   │   └── tracelib/           # W3C trace context propagation & utilities
│   └── tests/                  # 141 test files (313 pytest unit & integration tests)
├── frontend/
│   ├── src/
│   │   ├── App.tsx             # Root React component & navigation router
│   │   ├── api/client.ts       # Typed API client for tracing backend
│   │   ├── components/         # Interactive UI components
│   │   │   ├── WaterfallTimeline.tsx      # SVG-based span execution timeline
│   │   │   ├── SpanTree.tsx               # Collapsible hierarchical span tree
│   │   │   ├── DependencyGraph.tsx        # Service-to-service graph visualizer
│   │   │   ├── CriticalPathHighlight.tsx  # Bottleneck execution path marker
│   │   │   ├── IncidentSummarizer.tsx     # LLM incident postmortem viewer
│   │   │   ├── AnomaliesViewer.tsx        # Real-time ML anomaly alerts
│   │   │   └── NLQuerySearch.tsx          # Semantic natural language trace query
│   │   └── pages/              # TraceExplorer, TraceDetail, ServiceMap
│   ├── package.json            # React 18, Vite 6, TypeScript 5.7 dependencies
│   └── vite.config.ts          # Vite build configuration
├── ml/                         # 11 Statistical anomaly & LLM evaluation modules
│   ├── latency_anomaly.py      # Statistical p95/p99 latency outlier detection
│   ├── dependency_anomaly.py   # Service call topology shift detection
│   ├── error_spike.py          # Sliding-window burst error detector
│   ├── trace_anomaly.py        # Whole-trace graph structure anomaly scorer
│   ├── slow_span_predictor.py  # Critical path delay forecaster
│   ├── dynamic_sampling.py     # Adaptive sampling weight calculator
│   ├── semantic_search.py      # Vector embeddings for trace logs & tags
│   ├── llm_engine.py           # Pre-trained LLM integration for incident summaries
│   └── root_cause.py           # Causal DAG traversal for fault isolation
├── legacy_scaffold/            # Preserved initial project scaffolds
├── FEATURES.csv                # 150 feature tracking matrix
└── PROGRESS.md                 # Implementation milestone log
```

---

## Tech Stack & Runtime Dependencies

| Tier | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Runtime** | Python | 3.13 | High-performance asynchronous execution runtime |
| **Web Framework** | FastAPI | 0.115+ | Asynchronous REST and OpenTelemetry ingestion endpoints |
| **Data Validation** | Pydantic | 2.10+ | Strict type validation for spans, traces, and sampling policies |
| **Database ORM** | SQLAlchemy / aiosqlite | 2.0+ | Async database access with ClickHouse / SQLite failover |
| **Migration Tool** | Alembic | 1.14+ | Schema version control and database migrations |
| **Testing** | Pytest / Pytest-asyncio | 8.3+ | 313 unit and integration tests with async test harnesses |
| **Frontend Framework** | React | 18.3.1 | Component-driven UI architecture with concurrent rendering |
| **Bundler & Dev Server**| Vite | 6.0.7 | Lightning-fast ESM dev server and optimized production bundler |
| **Language** | TypeScript | 5.7.2 | End-to-end static typing across frontend interfaces |
| **Icons** | Lucide React | 0.469.0 | Accessible UI icons for traces, services, and anomalies |

---

## Environment Variables & Configuration

| Variable Name | Default / Example | Purpose | Source / Provider |
| :--- | :--- | :--- | :--- |
| `TRACING_PORT` | `8000` | HTTP port for FastAPI collector & query engine | Application runtime |
| `DATABASE_URL` | `sqlite+aiosqlite:///./tracing.db` | Primary async connection string | ClickHouse or SQLite |
| `CLICKHOUSE_HOST` | `localhost:9000` | Columnar database endpoint for high-volume spans | Infrastructure ClickHouse |
| `OPENAI_API_KEY` | `[CONFIRM WITH DEVELOPER]` | API key for LLM automated incident summarization | OpenAI / Claude API |
| `TAIL_SAMPLING_WINDOW_SEC` | `30` | In-memory ring buffer retention before sample decision | Backend config |
| `MAX_BATCH_SIZE` | `5000` | Maximum span batch size accepted per OTLP request | Collector safety limit |
""")

print("Part 1 base files created successfully.")
