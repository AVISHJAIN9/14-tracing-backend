# Complete API Reference

All endpoints are hosted under `/api/v1` and return standard JSON responses.

---

## Ingestion Endpoints

### 1. Ingest Span Batch
- **Method**: `POST`
- **Path**: `/api/v1/traces/ingest`
- **Auth**: API Key (`X-API-Key`) or Bearer Token
- **Request Body**:
```json
{
  "resourceSpans": [
    {
      "resource": {
        "attributes": [{ "key": "service.name", "value": { "stringValue": "payment-service" } }]
      },
      "scopeSpans": [
        {
          "spans": [
            {
              "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
              "spanId": "00f067aa0ba902b7",
              "parentSpanId": "5fb397be34d23b0f",
              "name": "POST /charge",
              "kind": 1,
              "startTimeUnixNano": "1719200000000000000",
              "endTimeUnixNano": "1719200000250000000",
              "status": { "code": 1 }
            }
          ]
        }
      ]
    }
  ]
}
```
- **Response**: `202 Accepted` with `{ "ingested_spans": 1, "status": "queued" }`
- **Error Codes**: `400 Bad Request` (invalid schema), `429 Too Many Requests` (buffer full).

---

## Query Endpoints

### 2. Fetch Trace Detail & Spans
- **Method**: `GET`
- **Path**: `/api/v1/traces/{trace_id}`
- **Response**: `200 OK` with full list of spans, metadata, and root span summary.

### 3. Compute Critical Path
- **Method**: `GET`
- **Path**: `/api/v1/traces/{trace_id}/critical-path`
- **Response**: `200 OK` with ordered list of critical path span IDs and total critical duration.

### 4. Service Dependency Graph
- **Method**: `GET`
- **Path**: `/api/v1/dependencies`
- **Response**: `200 OK` with adjacency matrix: caller, callee, call count, and p95 latency.

---

## Machine Learning & AI Endpoints

### 5. Anomaly Detection
- **Method**: `GET`
- **Path**: `/api/v1/ml/anomalies?window_minutes=60`
- **Response**: `200 OK` with list of flagged services, baseline latency, observed latency, and z-score.

### 6. Automated Incident Summary
- **Method**: `POST`
- **Path**: `/api/v1/ml/summarize-incident`
- **Request Body**: `{ "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736" }`
- **Response**: `200 OK` with executive summary, root cause analysis, and actionable remediation steps.
