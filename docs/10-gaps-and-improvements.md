# Gaps, Technical Debt & Roadmap Improvements

This document tracks known limitations and technical debt in **14-Tracing-Backend**, ranked by engineering priority.

---

## Ranked Technical Debt Log

| Rank | Area | Gap Description | Technical Risk | Remediation Plan |
| :---: | :--- | :--- | :--- | :--- |
| **P0** | Ingestion Buffer | In-memory ring buffer drops spans if worker process terminates unexpectedly. | Ephemeral telemetry loss during node crashes. | Integrate Apache Kafka or Redis Streams as an external persistent buffer. |
| **P1** | Tail Sampling State | Tail sampling state is held in single-node RAM, limiting horizontal scaling. | Traces spanning multiple collector instances cannot be correlated for tail decisions. | Implement trace-ID consistent hashing across collector nodes or use Redis cluster for shared tail state. |
| **P2** | Clock Skew Accuracy | Clock skew compensation assumes symmetrical network latency. | Asymmetrical latency can introduce microsecond timestamp inaccuracies. | Incorporate TrueTime API or hardware PTP (Precision Time Protocol) timestamps. |
| **P3** | Multi-Tenancy Quotas | Rate limiting is per-API-key rather than tiered consumption quotas. | Potential for a noisy tenant to starve shared collector queue. | Implement token-bucket tier quotas in Redis backed by sliding-window rate limiters. |
