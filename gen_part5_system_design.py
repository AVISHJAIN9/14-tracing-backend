import os

sd_dir = "/Users/avishjain/avishjain9-repos/14-tracing-backend/docs/system-design"
os.makedirs(sd_dir, exist_ok=True)

# index.md
with open(os.path.join(sd_dir, "index.md"), "w") as f:
    f.write("""# System Design Deep Dive: Distributed Observability Architecture

This section provides an exhaustive, interview-grade system design analysis for **14-Tracing-Backend**, modeling the requirements, capacity, bottlenecks, and evolutionary scaling up to 100,000 spans per second.

---

## System Design Chapters
1. [14.1 Requirements & Capacity Estimation](./14.1-requirements-and-estimation.md)
2. [14.2 Architecture Styles & Ingestion Decomposition](./14.2-architecture-styles.md)
3. [14.3 Networking, Protocols & OTLP Transport](./14.3-networking-and-communication.md)
4. [14.4 Load Balancing, Partitioning & Autoscaling](./14.4-load-balancing-and-scaling.md)
5. [14.5 Databases & Columnar Storage Engine](./14.5-databases-and-storage.md)
6. [14.6 Caching & Span Ring Buffers](./14.6-caching.md)
7. [14.7 Messaging, Ingestion Queues & Stream Leveling](./14.7-messaging-and-queues.md)
8. [14.8 Consistency, Concurrency & Clock Skew](./14.8-consistency-and-concurrency.md)
9. [14.9 Reliability, Circuit Breakers & Backpressure](./14.9-reliability-and-resilience.md)
10. [14.10 API Gateway & Ingestion Rate Limiting](./14.10-api-design-and-rate-limiting.md)
11. [14.11 Security, Multi-Tenancy & PII Redaction](./14.11-security-architecture.md)
12. [14.12 Search, Vector Embeddings & AI Architecture](./14.12-search-and-ai-architecture.md)
13. [14.13 Real-Time Streaming & WebSocket Updates](./14.13-real-time-systems.md)
14. [14.14 Observability, OpenTelemetry & Self-Monitoring](./14.14-observability-and-operations.md)
15. [14.15 Performance Engineering & Memory Overhead](./14.15-performance-engineering.md)
16. [14.16 Cost Modeling & Capacity Projections](./14.16-cost-and-trade-offs.md)
17. [14.17 Classic System Design Problems Applied to Tracing](./14.17-classic-system-design.md)
18. [Architecture Decisions Record (ADR Log)](./decisions.md)
""")

# 14.1-requirements-and-estimation.md
with open(os.path.join(sd_dir, "14.1-requirements-and-estimation.md"), "w") as f:
    f.write("""# 14.1 Requirements & Capacity Estimation

## Functional Requirements
- Ingest OpenTelemetry OTLP Protobuf and JSON span batches over HTTP/gRPC.
- Execute tail-based sampling to retain 100% of error and latency outlier traces while downsampling nominal traces.
- Reconstruct span DAGs on demand and compute the critical execution path.
- Provide sub-second multi-dimensional search over billions of stored spans.
- Run statistical anomaly detection and generate automated LLM incident postmortems.

## Non-Functional Requirements
- **High Ingestion Availability**: 99.99% ingestion uptime; ingestion failure must never crash instrumented upstream services.
- **Low Query Latency**: p95 trace retrieval under 500ms for traces containing up to 5,000 spans.
- **Data Durability**: Zero telemetry loss during graceful rolling collector restarts.

---

## Capacity Estimation Arithmetic

### Ingestion Volume
- **Target Scale**: 10,000 requests/second across upstream microservices.
- **Spans Per Request**: Average 15 spans generated per distributed transaction.
- **Gross Span Ingestion Rate**: $10,000 \\times 15 = 150,000\\text{ spans/second}$.

### Data Storage Volume
- **Average Uncompressed Span Size**: ~500 bytes (service name, span name, tags, timestamps).
- **Gross Ingestion Bandwidth**: $150,000 \\times 500\\text{ bytes} = 75\\text{ MB/second} = 600\\text{ Mbps}$.
- **Tail Sampling Reduction**: 90% of healthy nominal traffic is discarded; 10% retained.
- **Net Ingestion Rate to Storage**: $15,000\\text{ spans/second} = 7.5\\text{ MB/second}$.
- **ClickHouse Columnar Compression**: 6x compression ratio using ZSTD on timestamps and dictionary encoding on strings.
- **Net Disk Write Rate**: $\\frac{7.5\\text{ MB/s}}{6} = 1.25\\text{ MB/second} \\approx 108\\text{ GB/day}$.
- **30-Day Retention Disk Requirement**: $108\\text{ GB/day} \\times 30\\text{ days} \\approx 3.24\\text{ TB}$ of storage.

### 30-Second Spoken Interview Answer
> "When designing capacity for this tracing engine, I modeled 10,000 user requests per second with an average fanout of 15 spans, generating 150,000 spans per second. Rather than storing every nominal span—which would require 6.5 terabytes per day—our tail sampling engine retains 100% of errors and p99 outliers while downsampling nominal traces to 10%. Combined with ClickHouse's 6x columnar compression, we write just 1.25 megabytes per second to disk, storing 30 days of high-fidelity incident history in under 3.3 terabytes."
""")

# 14.5-databases-and-storage.md
with open(os.path.join(sd_dir, "14.5-databases-and-storage.md"), "w") as f:
    f.write("""# 14.5 Databases & Columnar Storage Engine

## Storage Engine Architecture

Distributed tracing telemetry has unique database access patterns:
1. **Append-Only Ingestion**: Spans are written once in batches; individual updates and in-place mutations never occur.
2. **Column-Selective Aggregations**: Queries almost always filter by `service_name`, `time_range`, and `duration`, ignoring 90% of other attributes.
3. **Time-Bound TTL**: Telemetry expires after 14-30 days.

```mermaid
flowchart TD
    Spans[Ingested Spans Batch] --> Partitioner[Date Partitioner toYYYYMMDD]
    Partitioner --> PrimaryKey[Sparse Primary Index]
    PrimaryKey --> MergeTree[ClickHouse MergeTree Engine]
    MergeTree --> CompressedParts[Compressed Column Files (.bin + .mrk)]
    CompressedParts --> TTL[Automated Drop After 30 Days]
```

### Table Schema Definition
```sql
CREATE TABLE spans (
    tenant_id LowCardinality(String),
    service_name LowCardinality(String),
    span_name LowCardinality(String),
    trace_id String,
    span_id String,
    parent_span_id String,
    start_time DateTime64(6, 'UTC'),
    duration_us UInt64,
    status_code UInt8,
    error_message String,
    attributes Map(String, String)
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(start_time)
ORDER BY (tenant_id, service_name, status_code, start_time, trace_id, span_id)
TTL start_time + INTERVAL 30 DAY;
```

---

## Comparison: ClickHouse vs Alternatives

| Database | Fit for Tracing | Compression | Aggregation Speed | Why Rejected |
| :--- | :---: | :---: | :---: | :--- |
| **ClickHouse** | **Optimal** | **6x - 10x** | **Sub-second over billions** | **Chosen storage engine** |
| **PostgreSQL** | Poor | 1.3x | Degrades $>10M$ rows | Row storage causes disk IO bottleneck on bulk inserts. |
| **Elasticsearch**| Moderate | 1.5x | Fast search, high RAM | Inverted index overhead consumes 3x more disk/RAM. |
| **MongoDB** | Poor | 1.2x | Slow aggregation | Unindexed JSON fields require full document scans. |
| **Cassandra** | Fair | 2x | High write, weak query | Ad-hoc multi-dimensional trace queries are unsupported. |
""")

# decisions.md
with open(os.path.join(sd_dir, "decisions.md"), "w") as f:
    f.write("""# Architecture Decisions Record (ADR Log)

This log documents every major technical decision made across **14-Tracing-Backend**.

| Decision ID | Area | Chosen Option | Alternatives Considered | Deciding Factors | Trade-Off Accepted | Revisit Trigger |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **ADR-001** | Backend Runtime | FastAPI (Python 3.13) | Go, Rust, Node.js | Direct integration with ML libraries (NumPy, PyTorch, LLM APIs) alongside async I/O. | Higher memory footprint per worker than Go/Rust. | If single-node ingestion exceeds 50,000 spans/s. |
| **ADR-002** | Telemetry Storage | ClickHouse MergeTree | PostgreSQL, Elasticsearch, Cassandra | 6x-10x compression on append-only time series; sub-second aggregations. | Eventual consistency during background part merges. | If complex full-text phrase searches dominate query volume. |
| **ADR-003** | Sampling Strategy | Tail-Based Sliding Window | 1% Head Sampling, Uniform Sampling | Retains 100% of error traces and p99 latency spikes; eliminates blind drops. | In-memory buffer requirement for in-flight 30s traces. | If active concurrent trace memory exceeds 16GB. |
| **ADR-004** | AI Integration | Pre-trained LLM API | Custom Trained Fine-tuned Transformer | Instant zero-shot reasoning; zero GPU hardware maintenance; immediate incident postmortems. | Dependency on external API availability and network latency. | If prompt API cost exceeds $5,000/month at high incident volume. |
| **ADR-005** | UI Architecture | React 18 + Vite | Next.js SSR, Vue 3 | Concurrent rendering for virtualized SVG Gantt charts with 2,000+ span elements. | Client-side bundle size; initial CSR load. | If public SEO indexing of trace permalinks is required. |
""")

print("Part 5 system design files written successfully.")
