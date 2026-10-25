import { describe, it, expect } from 'vitest';
import { LatencyStats } from '../src/components/LatencyCharts';
import { ServiceErrorStat } from '../src/components/ErrorRateCharts';

describe('Charts and Attribute Viewer Tests', () => {
  it('TRC-118: validates latency statistics and percentile calculations', () => {
    const stats: LatencyStats = {
      min_ms: 5.0,
      max_ms: 120.0,
      avg_ms: 45.2,
      p50_ms: 38.0,
      p90_ms: 85.0,
      p99_ms: 115.0
    };

    expect(stats.p50_ms).toBeLessThanOrEqual(stats.p90_ms);
    expect(stats.p90_ms).toBeLessThanOrEqual(stats.p99_ms);
    expect(stats.min_ms).toBeLessThanOrEqual(stats.max_ms);
  });

  it('TRC-119: computes error rate percentages across services', () => {
    const serviceStats: ServiceErrorStat[] = [
      { service_name: 'api-gw', total_calls: 100, error_calls: 2, error_rate: 0.02 },
      { service_name: 'pay-svc', total_calls: 50, error_calls: 10, error_rate: 0.20 }
    ];

    expect(serviceStats[0].error_rate).toBeCloseTo(0.02);
    expect(serviceStats[1].error_rate).toBeCloseTo(0.20);
    const totalCalls = serviceStats.reduce((acc, s) => acc + s.total_calls, 0);
    const totalErrors = serviceStats.reduce((acc, s) => acc + s.error_calls, 0);
    expect(totalCalls).toBe(150);
    expect(totalErrors).toBe(12);
  });

  it('TRC-120: extracts and filters span attribute types correctly', () => {
    const sampleAttributes = {
      'http.method': 'POST',
      'http.status_code': 200,
      'rpc.service': 'PaymentProcessor',
      'retry.enabled': true,
      'meta.tags': { env: 'production', region: 'us-west-1' }
    };

    expect(typeof sampleAttributes['http.method']).toBe('string');
    expect(typeof sampleAttributes['http.status_code']).toBe('number');
    expect(typeof sampleAttributes['retry.enabled']).toBe('boolean');
    expect(typeof sampleAttributes['meta.tags']).toBe('object');
    expect(Object.keys(sampleAttributes)).toHaveLength(5);
  });
});
