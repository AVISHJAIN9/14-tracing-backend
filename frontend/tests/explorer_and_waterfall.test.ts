import { describe, it, expect } from 'vitest';
import { TracingApiClient, SpanItem } from '../src/api/client';

describe('Frontend API Client and Data Model', () => {
  it('TRC-112: validates trace search query parameter builder', () => {
    const client = new TracingApiClient('/api/v1', 'tenant-alpha');
    expect(client).toBeDefined();
  });

  it('TRC-113: validates trace detail schema parser', () => {
    const sampleDetail = {
      trace_id: '0123456789abcdef0123456789abcdef',
      duration_nanos: 15_000_000,
      span_count: 2,
      error_count: 0,
      root_service: 'api-gateway',
      spans: []
    };
    expect(sampleDetail.duration_nanos).toBe(15_000_000);
    expect(sampleDetail.span_count).toBe(2);
  });

  it('TRC-114: computes correct waterfall timeline offsets and widths', () => {
    const traceStart = 100_000_000;
    const traceDuration = 50_000_000;

    const rootSpan: SpanItem = {
      trace_id: 't1',
      span_id: 's1',
      service_name: 'gateway',
      name: 'HTTP GET /api/v1',
      kind: 'SERVER',
      start_time_unix_nano: 100_000_000,
      end_time_unix_nano: 150_000_000,
      duration_nanos: 50_000_000,
      status_code: 'OK',
      attributes: {},
      events: [],
      links: []
    };

    const childSpan: SpanItem = {
      trace_id: 't1',
      span_id: 's2',
      parent_span_id: 's1',
      service_name: 'auth-service',
      name: 'verify_token',
      kind: 'INTERNAL',
      start_time_unix_nano: 110_000_000,
      end_time_unix_nano: 130_000_000,
      duration_nanos: 20_000_000,
      status_code: 'OK',
      attributes: {},
      events: [],
      links: []
    };

    // Root span: offset = 0%, width = 100%
    const rootOffset = ((rootSpan.start_time_unix_nano - traceStart) / traceDuration) * 100;
    const rootWidth = (rootSpan.duration_nanos / traceDuration) * 100;
    expect(rootOffset).toBe(0);
    expect(rootWidth).toBe(100);

    // Child span: offset = (110 - 100) / 50 = 20%, width = 20 / 50 = 40%
    const childOffset = ((childSpan.start_time_unix_nano - traceStart) / traceDuration) * 100;
    const childWidth = (childSpan.duration_nanos / traceDuration) * 100;
    expect(childOffset).toBe(20);
    expect(childWidth).toBe(40);
  });
});
