# Technology Choices & Exhaustive Trade-Off Comparisons

## 1. Backend Ingestion: FastAPI vs Go vs Rust vs Node.js

| Factor | FastAPI (Python) [Chosen] | Go (net/http) | Rust (Axum / Actix) | Node.js (Express) |
| :--- | :--- | :--- | :--- | :--- |
| **Throughput / Latency** | High (uvloop async) | Extremely High (goroutines)| Maximum (zero cost) | Moderate (single-threaded) |
| **ML & AI Integration** | **Native (NumPy, PyTorch, LLM APIs)** | Clunky (Cgo / Python microservice) | Verbose (Candle / ONNX bindings) | Moderate (JS SDKs) |
| **Developer Velocity** | **Very Rapid (Pydantic, automatic docs)**| Rapid | Slower (strict borrow checker) | Rapid |
| **Memory Footprint** | Moderate (~80MB base) | Very Low (~15MB) | Minimal (~5MB) | Moderate (~70MB) |

- **Why I Used FastAPI**: The distributed tracing platform requires deep coupling between high-speed ingestion and complex statistical machine learning (anomaly scoring, causal graph analysis, LLM incident postmortems). Python provides the richest ecosystem for these ML algorithms while FastAPI's async runtime delivers thousands of requests per second. [CONFIRM WITH DEVELOPER]
- **Trade-off Accepted**: Slightly higher per-core memory usage than Go/Rust, mitigated by horizontal worker scaling.

---

## 2. Telemetry Storage: ClickHouse vs Elasticsearch vs PostgreSQL vs MongoDB

| Factor | ClickHouse (Columnar) [Chosen Architecture] | Elasticsearch | PostgreSQL | MongoDB |
| :--- | :--- | :--- | :--- | :--- |
| **Data Model** | Column-oriented relational | Document / Inverted Index | Row-oriented relational | Document (JSON) |
| **Compression Ratio** | **5x - 10x (ZSTD / Gorilla)** | 1.5x - 2x | 1.2x - 1.5x | 1.1x - 1.3x |
| **Aggregation Speed** | **Sub-second over billions of rows** | Fast for search, slow for math | Slow over 100M+ rows | Slow over 100M+ rows |
| **Write Throughput** | **1,000,000+ rows/sec bulk inserts** | High CPU overhead on Lucene merge | Moderate | Moderate |

- **Why ClickHouse**: Distributed traces are append-only time-series records. Query patterns always aggregate specific columns (e.g., `avg(duration) WHERE service_name = 'auth'`). Columnar storage stores identical columns together, allowing extreme compression and vector instructions (SIMD) for aggregations.
- **Why Not Elasticsearch**: Elasticsearch's inverted index consumes enormous RAM and storage overhead (often 2x the raw data size). ClickHouse achieves 5x-10x compression on trace data.
