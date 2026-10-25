# Technical Glossary

- **Span**: A named, timed operation representing a single unit of work within a trace.
- **Trace**: A Directed Acyclic Graph (DAG) of spans representing end-to-end request execution across microservices.
- **Critical Path**: The longest sequential chain of dependent operations in a trace DAG that directly dictated total request latency.
- **W3C TraceContext**: The standard specification for distributed context propagation via `traceparent` and `tracestate` HTTP headers.
- **OTLP**: OpenTelemetry Protocol, the vendor-neutral telemetry transport standard over gRPC and HTTP.
- **Head Sampling**: A sampling policy evaluated at the initial gateway before request processing occurs.
- **Tail Sampling**: A sampling policy evaluated after request completion, retaining traces based on errors or latency anomalies.
- **Columnar Storage**: A database architecture storing data by column rather than row, enabling extreme compression and ultra-fast aggregations.
- **Clock Skew**: The time divergence between independent physical server clocks across a distributed cluster.
