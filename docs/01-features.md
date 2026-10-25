# Feature Inventory & Architecture Traces

This document details the core capabilities of **14-Tracing-Backend**. Every feature includes user behavior, code references, complexity, failure modes, and interview rehearsal scripts.

---

## F1: OpenTelemetry OTLP Collector & Non-blocking Ingest

### Technical Description
Accepts OpenTelemetry-compliant trace telemetry over HTTP/JSON and Protobuf. Implements a bounded in-memory buffer with async worker flushing, backpressure rejection (HTTP 429), and strict PII attribute redaction.

- **Primary Source**: `backend/src/collector/otlp.py`, `backend/src/collector/queue_buffer.py`
- **Data Models**: `backend/src/storage/models.py` (`SpanRecord`, `TraceSummary`)
- **Key Algorithms**: Ring-buffer queue with sliding drop policy when memory threshold exceeds 90%.

### Say It Out Loud
> "I built the OpenTelemetry ingestion collector using FastAPI and an asynchronous queue buffer. When microservices emit telemetry, they POST span batches to our OTLP endpoint. Rather than performing synchronous database writes on the request thread, I validate the payload schema, scrub sensitive header and tag attributes using our regex PII filter, and push the batch into a bounded in-memory ring buffer. Background workers drain this buffer using batch inserts into ClickHouse. If downstream storage slows down, the collector applies backpressure and returns a 429 status code with a Retry-After header, preventing out-of-memory crashes."

---

## F2: Tail-Based Intelligent Sampling

### Technical Description
Unlike naive head sampling at the API gateway which drops requests before execution finishes, tail sampling buffers spans in an active 30-second window until the entire trace finishes. Traces with errors, status codes $\ge 400$, or duration $> p99$ latency are retained at 100%, while uniform nominal traffic is downsampled to 1%.

- **Primary Source**: `backend/src/sampling/tail.py`, `backend/src/sampling/tail_window.py`
- **Memory Complexity**: $O(B)$ where $B$ is the active trace volume within the 30-second window.

### Say It Out Loud
> "One of the most impactful systems I implemented is our tail-based sampling engine. If you use standard 1% head-based sampling at the gateway, you end up throwing away 99% of your catastrophic failures and latency anomalies because you don't know the request failed until it finishes. My tail sampler holds spans in an in-memory sliding window for 30 seconds. When the root span closes, the engine inspects the entire trace tree: if any child span recorded an unhandled exception or breached our p99 latency threshold, the trace is promoted for permanent storage. Otherwise, it is probabilistically downsampled. This cut storage footprint by over 75% while maintaining 100% visibility into incident regressions."

---

## F3: Span Directed Acyclic Graph (DAG) & Critical Path Engine

### Technical Description
Reconstructs the execution tree from un-ordered span records using `span_id` and `parent_span_id`. Compensates for inter-host clock skew and executes a topological sort to identify the critical path—the longest path of un-overlapped sequential operations that determined overall latency.

- **Primary Source**: `backend/src/query/critical_path.py`, `backend/src/query/trace_lookup.py`
- **Time Complexity**: $O(V + E)$ where $V$ is spans and $E$ is parent-child links.

### Say It Out Loud
> "To help developers pinpoint why a trace took two seconds, I wrote the critical path graph traversal engine. When a trace is opened in the UI, my backend fetches all associated spans and constructs a Directed Acyclic Graph based on parent-child IDs. It normalizes clock drift between microservices and performs a topological traversal to compute the true critical path—the exact chain of blocking operations that directly dictated the total response time. Parallel spans that completed while waiting for a slower query are filtered out. The critical path spans are returned to our React frontend and illuminated in bright red on the waterfall Gantt chart."

---

## F4: Statistical Anomaly Detection & Causal Graph

### Technical Description
A multi-model ML evaluation engine that analyzes span latency distributions, call frequencies, and error spikes across sliding time windows using z-score heuristics and causal dependency graph traversal.

- **Primary Source**: `ml/latency_anomaly.py`, `ml/dependency_anomaly.py`, `ml/root_cause.py`
- **Output**: Ranked anomaly score $(0.0 - 1.0)$ and likely culprit service node.

### Say It Out Loud
> "I developed an anomaly detection engine that continuously analyzes incoming telemetry without requiring heavy offline model training. It uses moving-window z-score calculations and service dependency graph traversal. When a service's latency deviates by more than three standard deviations from its rolling hourly baseline, or if a service suddenly introduces a novel downstream RPC call, an anomaly alert is raised. The root cause module traverses the dependency tree backward from the symptom to the origin, successfully distinguishing between victim services that were merely waiting and the culprit service holding the lock."

---

## F5: Pre-trained LLM Automated Incident Summarizer

### Technical Description
Integrates an external pre-trained LLM API (OpenAI/Anthropic) to ingest serialized anomaly graphs and critical path spans, producing human-readable postmortem summaries and concrete remediation suggestions.

- **Primary Source**: `ml/llm_engine.py`, `api/routes/ml.py`
- **Security**: System prompts enforce strict JSON output schemas; all PII and credentials are sanitized before API dispatch.

### Say It Out Loud
> "I integrated a pre-trained LLM into our incident triage workflow to turn raw span trees into plain-English incident postmortems. When an engineer clicks 'Summarize Incident', my backend extracts the critical path spans, error messages, and anomaly scores, scrubs any potential secrets or PII, and sends a strictly structured prompt to the model API. The LLM returns a parsed JSON payload explaining what failed, which downstream resource was bottlenecked, and suggested fixes—like adding a database index or tuning a connection pool. I used zero custom ML model training; everything is grounded in exact telemetry data to prevent hallucinations."
