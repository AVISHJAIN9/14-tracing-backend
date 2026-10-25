# Say It Out Loud: Consolidated Spoken Interview Scripts

This page aggregates all first-person spoken interview scripts for **14-Tracing-Backend**. Rehearse each aloud without notes.

---

## Feature 1: OpenTelemetry OTLP Ingestion Collector
> "I built the OpenTelemetry ingestion collector using FastAPI and an asynchronous queue buffer. When microservices emit telemetry, they POST span batches to our OTLP endpoint. Rather than performing synchronous database writes on the request thread, I validate the payload schema, scrub sensitive header and tag attributes using our regex PII filter, and push the batch into a bounded in-memory ring buffer. Background workers drain this buffer using batch inserts into ClickHouse. If downstream storage slows down, the collector applies backpressure and returns a 429 status code with a Retry-After header, preventing out-of-memory crashes."

---

## Feature 2: Tail-Based Intelligent Sampling
> "One of the most impactful systems I implemented is our tail-based sampling engine. If you use standard 1% head-based sampling at the gateway, you end up throwing away 99% of your catastrophic failures and latency anomalies because you don't know the request failed until it finishes. My tail sampler holds spans in an in-memory sliding window for 30 seconds. When the root span closes, the engine inspects the entire trace tree: if any child span recorded an unhandled exception or breached our p99 latency threshold, the trace is promoted for permanent storage. Otherwise, it is probabilistically downsampled. This cut storage footprint by over 75% while maintaining 100% visibility into incident regressions."

---

## Feature 3: Span Directed Acyclic Graph & Critical Path
> "To help developers pinpoint why a trace took two seconds, I wrote the critical path graph traversal engine. When a trace is opened in the UI, my backend fetches all associated spans and constructs a Directed Acyclic Graph based on parent-child IDs. It normalizes clock drift between microservices and performs a topological traversal to compute the true critical path—the exact chain of blocking operations that directly dictated the total response time. Parallel spans that completed while waiting for a slower query are filtered out. The critical path spans are returned to our React frontend and illuminated in bright red on the waterfall Gantt chart."

---

## Feature 4: Statistical Anomaly Detection & Causal Graph
> "I developed an anomaly detection engine that continuously analyzes incoming telemetry without requiring heavy offline model training. It uses moving-window z-score calculations and service dependency graph traversal. When a service's latency deviates by more than three standard deviations from its rolling hourly baseline, or if a service suddenly introduces a novel downstream RPC call, an anomaly alert is raised. The root cause module traverses the dependency tree backward from the symptom to the origin, successfully distinguishing between victim services that were merely waiting and the culprit service holding the lock."

---

## Feature 5: Pre-trained LLM Automated Incident Summarizer
> "I integrated a pre-trained LLM into our incident triage workflow to turn raw span trees into plain-English incident postmortems. When an engineer clicks 'Summarize Incident', my backend extracts the critical path spans, error messages, and anomaly scores, scrubs any potential secrets or PII, and sends a strictly structured prompt to the model API. The LLM returns a parsed JSON payload explaining what failed, which downstream resource was bottlenecked, and suggested fixes—like adding a database index or tuning a connection pool. I used zero custom ML model training; everything is grounded in exact telemetry data to prevent hallucinations."

---

## Rehearsal Checklist

- [ ] F1: OTLP Ingestion Collector (under 60 seconds)
- [ ] F2: Tail-Based Adaptive Sampling (under 75 seconds)
- [ ] F3: Span DAG & Critical Path Engine (under 60 seconds)
- [ ] F4: Statistical Anomaly Detection (under 60 seconds)
- [ ] F5: Pre-trained LLM Incident Summarizer (under 60 seconds)
