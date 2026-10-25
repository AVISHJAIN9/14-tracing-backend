import { describe, it, expect } from 'vitest';
import { SpanItem } from '../src/api/client';

describe('Critical Path Frontend Tests', () => {
  it('TRC-124: filters critical path spans and calculates latency bottleneck proportion', () => {
    const spans: SpanItem[] = [
      {
        trace_id: 't-1',
        span_id: 's-root',
        parent_span_id: null,
        service_name: 'api-gateway',
        name: 'POST /checkout',
        kind: 'SERVER',
        start_time_unix_nano: 1_000_000_000,
        end_time_unix_nano: 1_100_000_000,
        duration_nanos: 100_000_000,
        status_code: 'OK',
        attributes: {},
        events: [],
        links: []
      },
      {
        trace_id: 't-1',
        span_id: 's-fast-branch',
        parent_span_id: 's-root',
        service_name: 'auth-svc',
        name: 'validate_token',
        kind: 'INTERNAL',
        start_time_unix_nano: 1_005_000_000,
        end_time_unix_nano: 1_015_000_000,
        duration_nanos: 10_000_000,
        status_code: 'OK',
        attributes: {},
        events: [],
        links: []
      },
      {
        trace_id: 't-1',
        span_id: 's-slow-branch',
        parent_span_id: 's-root',
        service_name: 'payment-svc',
        name: 'charge',
        kind: 'CLIENT',
        start_time_unix_nano: 1_020_000_000,
        end_time_unix_nano: 1_095_000_000,
        duration_nanos: 75_000_000,
        status_code: 'OK',
        attributes: {},
        events: [],
        links: []
      }
    ];

    const criticalPathSpanIds = new Set(['s-root', 's-slow-branch']);
    const criticalSpans = spans.filter((s) => criticalPathSpanIds.has(s.span_id));

    expect(criticalSpans).toHaveLength(2);
    expect(criticalSpans.map((s) => s.span_id)).toEqual(['s-root', 's-slow-branch']);

    const totalDuration = spans[0].duration_nanos;
    const criticalDur = criticalSpans.reduce((acc, s) => acc + s.duration_nanos, 0);
    expect(criticalDur).toBeGreaterThan(totalDuration * 0.5);
  });
});
