# Architecture Decisions Record (ADR Log)

This log documents every major technical decision made across **14-Tracing-Backend**.

| Decision ID | Area | Chosen Option | Alternatives Considered | Deciding Factors | Trade-Off Accepted | Revisit Trigger |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **ADR-001** | Backend Runtime | FastAPI (Python 3.13) | Go, Rust, Node.js | Direct integration with ML libraries (NumPy, PyTorch, LLM APIs) alongside async I/O. | Higher memory footprint per worker than Go/Rust. | If single-node ingestion exceeds 50,000 spans/s. |
| **ADR-002** | Telemetry Storage | ClickHouse MergeTree | PostgreSQL, Elasticsearch, Cassandra | 6x-10x compression on append-only time series; sub-second aggregations. | Eventual consistency during background part merges. | If complex full-text phrase searches dominate query volume. |
| **ADR-003** | Sampling Strategy | Tail-Based Sliding Window | 1% Head Sampling, Uniform Sampling | Retains 100% of error traces and p99 latency spikes; eliminates blind drops. | In-memory buffer requirement for in-flight 30s traces. | If active concurrent trace memory exceeds 16GB. |
| **ADR-004** | AI Integration | Pre-trained LLM API | Custom Trained Fine-tuned Transformer | Instant zero-shot reasoning; zero GPU hardware maintenance; immediate incident postmortems. | Dependency on external API availability and network latency. | If prompt API cost exceeds $5,000/month at high incident volume. |
| **ADR-005** | UI Architecture | React 18 + Vite | Next.js SSR, Vue 3 | Concurrent rendering for virtualized SVG Gantt charts with 2,000+ span elements. | Client-side bundle size; initial CSR load. | If public SEO indexing of trace permalinks is required. |
