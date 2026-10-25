# Project Structure & Dependency Map

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
