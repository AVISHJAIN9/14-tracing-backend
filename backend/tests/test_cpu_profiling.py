import time
from security.redaction import AttributeRedactor
from security.pii_filter import PiiFilter
from observability.profiler import CpuProfiler

def test_TRC_133_cpu_profiling():
    redactor = AttributeRedactor()
    pii_filter = PiiFilter()
    iterations = 300

    def _cpu_intensive_workload():
        sanitized_count = 0
        for i in range(iterations):
            attrs = {
                "auth.header": f"Bearer secret_token_{i}",
                "user.email": f"customer_{i}@corporate.domain.com",
                "normal.key": f"value_{i}",
                "password": f"p4ssw0rd!_{i}"
            }
            # Execute redaction and PII sanitization pipeline
            redacted = redactor.redact_span_attributes(attrs)
            filtered = pii_filter.sanitize_data(redacted)
            if filtered:
                sanitized_count += 1
        return sanitized_count

    count, report = CpuProfiler.profile_execution(_cpu_intensive_workload, top_n=5)

    assert count == iterations
    assert report.total_time_seconds > 0
    assert report.total_calls > 0
    assert len(report.top_functions) > 0
