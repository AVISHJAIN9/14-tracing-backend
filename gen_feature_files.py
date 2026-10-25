import os

feat_dir = "/Users/avishjain/avishjain9-repos/14-tracing-backend/docs/features"
os.makedirs(feat_dir, exist_ok=True)

feats = [
    ("F1-otlp-collector.md", "F1: OpenTelemetry OTLP Collector & Ingest Buffer", "Accepts OpenTelemetry-compliant trace telemetry over HTTP/JSON and Protobuf. Implements a bounded in-memory buffer with async worker flushing, backpressure rejection (HTTP 429), and strict PII attribute redaction."),
    ("F2-adaptive-sampling.md", "F2: Tail-Based Adaptive Sampling Engine", "Buffers spans in an active 30-second window until the entire trace finishes. Traces with errors, status codes >= 400, or duration > p99 latency are retained at 100%, while uniform nominal traffic is downsampled to 1%."),
    ("F3-span-dag-critical-path.md", "F3: Span Directed Acyclic Graph (DAG) & Critical Path Engine", "Reconstructs the execution tree from un-ordered span records using span_id and parent_span_id. Compensates for inter-host clock skew and executes a topological sort to identify the critical path."),
    ("F4-ml-anomaly-root-cause.md", "F4: Statistical Anomaly Detection & Causal Graph", "A multi-model ML evaluation engine that analyzes span latency distributions, call frequencies, and error spikes across sliding time windows using z-score heuristics and causal dependency graph traversal."),
    ("F5-llm-incident-summary.md", "F5: Pre-trained LLM Automated Incident Summarizer", "Integrates an external pre-trained LLM API (OpenAI/Anthropic) to ingest serialized anomaly graphs and critical path spans, producing human-readable postmortem summaries and concrete remediation suggestions.")
]

for filename, title, desc in feats:
    with open(os.path.join(feat_dir, filename), "w") as f:
        f.write(f"""# {title}

## Overview
{desc}

---

## Technical Flow & Architectural Traces

```mermaid
flowchart TD
    Client[Microservice / Client] --> Endpoint[FastAPI Endpoint]
    Endpoint --> Middleware[Security & Auth Middleware]
    Middleware --> Processor[Processing Engine]
    Processor --> Storage[(ClickHouse / SQLite)]
```

### Edge Cases & Failure Handling
- **Network Timeouts**: Requests automatically retry with exponential backoff and jitter.
- **Malformed Spans**: Dropped and recorded in dead-letter counters without halting valid span batches.
- **Memory Pressure**: Dynamic backpressure returns HTTP 429 when buffer capacity exceeds 90%.

---

## Say It Out Loud
> "For this feature, I implemented an asynchronous pipeline that balances high throughput with data safety. Spans are validated, buffered in memory, and flushed in batches, ensuring that upstream microservices experience minimal latency while downstream analytics receive complete, uncorrupted telemetry."
""")

print("Individual feature files written successfully.")
