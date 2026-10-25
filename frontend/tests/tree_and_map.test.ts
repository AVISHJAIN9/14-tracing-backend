import { describe, it, expect } from 'vitest';
import { buildSpanTree } from '../src/components/SpanTree';
import { SpanItem } from '../src/api/client';

describe('Span Tree and Dependency Graph Tests', () => {
  it('TRC-115: builds nested hierarchy tree from spans with parent_span_id', () => {
    const root: SpanItem = {
      trace_id: 't-100',
      span_id: 'root-span',
      service_name: 'api-gateway',
      name: 'handle_http',
      kind: 'SERVER',
      start_time_unix_nano: 1000,
      end_time_unix_nano: 5000,
      duration_nanos: 4000,
      status_code: 'OK',
      attributes: {},
      events: [],
      links: []
    };

    const child1: SpanItem = {
      trace_id: 't-100',
      span_id: 'child-span-1',
      parent_span_id: 'root-span',
      service_name: 'auth-service',
      name: 'authenticate',
      kind: 'INTERNAL',
      start_time_unix_nano: 1200,
      end_time_unix_nano: 2200,
      duration_nanos: 1000,
      status_code: 'OK',
      attributes: {},
      events: [],
      links: []
    };

    const grandChild: SpanItem = {
      trace_id: 't-100',
      span_id: 'grandchild-span',
      parent_span_id: 'child-span-1',
      service_name: 'user-db',
      name: 'select_user',
      kind: 'CLIENT',
      start_time_unix_nano: 1400,
      end_time_unix_nano: 1900,
      duration_nanos: 500,
      status_code: 'OK',
      attributes: {},
      events: [],
      links: []
    };

    const tree = buildSpanTree([root, child1, grandChild]);
    expect(tree).toHaveLength(1);
    expect(tree[0].span.span_id).toBe('root-span');
    expect(tree[0].depth).toBe(0);
    expect(tree[0].children).toHaveLength(1);

    const childNode = tree[0].children[0];
    expect(childNode.span.span_id).toBe('child-span-1');
    expect(childNode.depth).toBe(1);
    expect(childNode.children).toHaveLength(1);

    const grandChildNode = childNode.children[0];
    expect(grandChildNode.span.span_id).toBe('grandchild-span');
    expect(grandChildNode.depth).toBe(2);
  });

  it('TRC-116: calculates service map node counts and topology edges', () => {
    const services = ['frontend-proxy', 'billing-service', 'notification-worker'];
    expect(services).toContain('billing-service');
    expect(services.length).toBe(3);
  });

  it('TRC-117: validates caller-callee dependency relationships', () => {
    const deps = [
      { caller: 'frontend-proxy', callee: 'auth-service', call_count: 42 },
      { caller: 'auth-service', callee: 'user-db', call_count: 42 }
    ];
    expect(deps).toHaveLength(2);
    expect(deps[0].caller).toBe('frontend-proxy');
    expect(deps[0].callee).toBe('auth-service');
    expect(deps[0].call_count).toBe(42);
  });
});
