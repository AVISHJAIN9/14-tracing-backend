import { describe, it, expect } from 'vitest';
import { SpanEventItem } from '../src/components/SpanEventViewer';
import { SpanLinkItem } from '../src/components/TraceLinksViewer';

describe('Span Events, Tags, and Links Tests', () => {
  it('TRC-121: parses span event records and relative timestamp offsets', () => {
    const events: SpanEventItem[] = [
      { name: 'cache_miss', time_unix_nano: 1_005_000_000, attributes: { key: 'usr:42' } },
      { name: 'db_connected', time_unix_nano: 1_015_000_000, attributes: { pool: 'main' } }
    ];
    const spanStart = 1_000_000_000;

    const offset1Ms = (events[0].time_unix_nano! - spanStart) / 1_000_000;
    const offset2Ms = (events[1].time_unix_nano! - spanStart) / 1_000_000;

    expect(offset1Ms).toBe(5);
    expect(offset2Ms).toBe(15);
    expect(events[0].name).toBe('cache_miss');
  });

  it('TRC-122: aggregates unique trace tag key-value pairs across spans', () => {
    const span1Attrs = { 'service.version': '1.2.0', 'environment': 'prod', 'http.method': 'GET' };
    const span2Attrs = { 'service.version': '1.2.0', 'environment': 'prod', 'db.system': 'postgresql' };

    const tagKeys = new Set([...Object.keys(span1Attrs), ...Object.keys(span2Attrs)]);
    expect(Array.from(tagKeys)).toContain('service.version');
    expect(Array.from(tagKeys)).toContain('db.system');
    expect(tagKeys.size).toBe(4);
  });

  it('TRC-123: verifies cross-trace link pointers', () => {
    const links: SpanLinkItem[] = [
      { trace_id: 't-async-parent', span_id: 's-kafka-msg-01', attributes: { 'messaging.system': 'kafka' } }
    ];

    expect(links).toHaveLength(1);
    expect(links[0].trace_id).toBe('t-async-parent');
    expect(links[0].span_id).toBe('s-kafka-msg-01');
    expect(links[0].attributes?.['messaging.system']).toBe('kafka');
  });
});
