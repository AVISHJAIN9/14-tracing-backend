# Project Pitch: Distributed Tracing & Observability Platform

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
