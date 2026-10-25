# Security Audit & OWASP Top 10 Mapping

| OWASP Vulnerability | Risk in Tracing Platform | Implemented Defense |
| :--- | :--- | :--- |
| **A01: Broken Access Control** | Unauthorized access to tenant traces | Tenant ID validation middleware (`security/tenant.py`) and RBAC scope enforcement. |
| **A02: Cryptographic Failures** | Eavesdropping on trace telemetry | Mandatory TLS 1.3 in transit; mTLS for inter-service collector communication. |
| **A03: Injection** | SQL/NoSQL injection via span tags | Parameterized SQLAlchemy queries; strict Pydantic payload validation. |
| **A04: Insecure Design** | Unbounded memory consumption by large traces | Maximum span payload limiter (`security/payload_limiter.py`) capped at 1MB. |
| **A05: Security Misconfiguration** | Leaked database credentials or keys | All secrets injected via environment variables; none committed to source control. |
| **A06: Vulnerable Components** | Outdated third-party packages | Regular `pip-audit` checks in CI/CD pipeline. |
| **A07: Identification / Auth Failures** | Spoofed trace ingestion | Cryptographic API key validation with rate limiting (`security/api_key.py`). |
| **A08: Software / Data Integrity** | Tampered span timestamps or trace IDs | Strict W3C traceparent 128-bit hex format validation. |
| **A09: Logging & Monitoring Failures** | Undetected collector outages | Self-monitoring Prometheus metrics (`/metrics`) tracking ingestion rate and drop rate. |
| **A10: Server-Side Request Forgery** | Malicious webhook triggers in alert routing | Outbound webhook URLs restricted to approved private subnets. |

---

### PII Redaction Engine
Located in `backend/src/security/pii_filter.py`:
- Redacts credit card numbers (Luhn algorithm match).
- Redacts Social Security Numbers (SSN regex).
- Redacts JWT tokens and authorization bearer strings in span attributes before persistence.
