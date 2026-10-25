# System Architecture & High-Scale Design

## System Overview

```mermaid
flowchart TD
    subgraph Edge Layer
        Client1[Frontend Client / SDK]
        ServiceA[Service A - Gateway]
        ServiceB[Service B - Backend]
    end

    subgraph Collector Pipeline
        IngestAPI[FastAPI Ingestion Endpoint]
        PIIScrubber[PII Redaction Filter]
        Queue[Bounded Ring Buffer Queue]
        TailSampler[Tail Sampling Sliding Window (30s)]
    end

    subgraph Storage & Analytics
        Worker[Async Batch Writer]
        ClickHouse[(ClickHouse Columnar Storage)]
        SQLiteFallback[(SQLite Fallback)]
    end

    subgraph Intelligence & UI
        MLEngine[Statistical Anomaly & Causal Graph]
        LLM[Pre-trained LLM Summarizer API]
        ReactUI[React 18 Observability Dashboard]
    end

    Client1 -->|OTel Traces| IngestAPI
    ServiceA -->|OTel Traces| IngestAPI
    ServiceB -->|OTel Traces| IngestAPI
    IngestAPI --> PIIScrubber
    PIIScrubber --> Queue
    Queue --> TailSampler
    TailSampler --> Worker
    Worker --> ClickHouse
    Worker -.->|On Failure| SQLiteFallback
    ClickHouse --> MLEngine
    ClickHouse --> ReactUI
    MLEngine --> LLM
    LLM --> ReactUI
```

---

## 100x Scale Strategy & First Bottlenecks

At 100x volume (100,000 spans/second):
1. **First Bottleneck**: In-memory ring buffer exhaustion in the single FastAPI worker.
   - *Mitigation*: Introduce Apache Kafka or Redis Streams as an external durable buffer between collectors and storage writers.
2. **Second Bottleneck**: Database insert latency.
   - *Mitigation*: Increase batch size from 5,000 to 50,000 spans, flushing every 5 seconds, utilizing ClickHouse partitioned MergeTree tables.
3. **Third Bottleneck**: Tail-sampling state memory.
   - *Mitigation*: Partition tail-sampling nodes using consistent hashing on `trace_id`.
