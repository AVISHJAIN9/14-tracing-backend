# Quality Engineering, Testing & Operations

## Automated Test Suite Audit

The codebase includes an extensive automated test suite located in `backend/tests/`:

```
========================= TEST EXECUTION SUMMARY =========================
Test Engine: Pytest 8.3+ with AsyncIO support
Test Files: 141 files in backend/tests/
Total Tests: 313 unit and integration tests
Pass Rate: 100% (313 passed in 54.44s)
==========================================================================
```

### Key Test Categories Covered
- **Collector Resilience**: Validates backpressure behavior, buffer overflows, and malformed OTLP payloads.
- **Sampling Correctness**: Verifies that 100% of error spans survive tail sampling while healthy spans conform to probabilistic sampling ratios.
- **Graph Assembly**: Tests DAG generation under simulated out-of-order span arrival and inter-host clock skew.
- **Security & PII**: Asserts that sensitive attributes (passwords, tokens, credit cards) are 100% scrubbed.

---

## CI/CD & Operations

- **CI Pipeline**: Automated GitHub Actions workflow running `pytest`, `flake8` linting, and `tsc` frontend type-checking on every push.
- **Containerization**: Includes `Dockerfile` and `docker-compose.yml` defining the complete stack (FastAPI collector, ClickHouse, Redis, and React UI).
- **Graceful Shutdown**: The FastAPI app listens for `SIGTERM` and drains the in-memory span queue before exiting, preventing telemetry loss during deployments.
