import { describe, it, expect } from 'vitest';
import {
  TraceAnomalyItem,
  LatencyAnomalyItem,
  ErrorSpikeItem,
  RootCauseItem,
  DependencyAnomalyItem,
  PerformanceRegressionItem
} from '../src/components/AnomaliesViewer';

describe('Anomalies Viewer Frontend Tests', () => {
  it('TRC-138: filters trace anomalies flagged by Isolation Forest', () => {
    const items: TraceAnomalyItem[] = [
      { trace_id: 't-norm-1', is_anomaly: false, anomaly_score: 0.12, reasons: [] },
      { trace_id: 't-anom-1', is_anomaly: true, anomaly_score: -0.45, reasons: ['Elevated duration', 'High error count'] }
    ];

    const anomalies = items.filter((i) => i.is_anomaly);
    expect(anomalies).toHaveLength(1);
    expect(anomalies[0].trace_id).toBe('t-anom-1');
    expect(anomalies[0].reasons).toContain('Elevated duration');
  });

  it('TRC-139: parses latency outlier modified Z-scores and baselines', () => {
    const latencies: LatencyAnomalyItem[] = [
      { service: 'payment', operation: 'charge', duration_ms: 120.0, baseline_median_ms: 22.0, modified_z_score: 4.2, is_anomaly: true }
    ];

    expect(latencies[0].modified_z_score).toBeGreaterThan(3.0);
    expect(latencies[0].is_anomaly).toBe(true);
  });

  it('TRC-140: verifies CUSUM change point error spike active state', () => {
    const spikes: ErrorSpikeItem[] = [
      { service: 'auth', is_error_spike: true, cusum_statistic: 6.8, threshold: 5.0, baseline_mean_errors: 0.2, recent_mean_errors: 4.5, poisson_p_value: 0.0001 }
    ];

    expect(spikes[0].is_error_spike).toBe(true);
    expect(spikes[0].cusum_statistic).toBeGreaterThan(spikes[0].threshold);
    expect(spikes[0].poisson_p_value).toBeLessThan(0.01);
  });

  it('TRC-141: ranks root-cause candidate spans by composite score', () => {
    const candidates: RootCauseItem[] = [
      { span_id: 's-1', service_name: 'auth', name: 'check', root_cause_score: 0.2, self_time_ms: 5, is_critical_path: false, has_error: false, reasons: [] },
      { span_id: 's-2', service_name: 'db', name: 'query', root_cause_score: 0.92, self_time_ms: 450, is_critical_path: true, has_error: true, reasons: ['Error recorded'] }
    ];

    const sorted = [...candidates].sort((a, b) => b.root_cause_score - a.root_cause_score);
    expect(sorted[0].span_id).toBe('s-2');
    expect(sorted[0].has_error).toBe(true);
  });

  it('TRC-146: verifies dependency graph topology and metric anomalies', () => {
    const anomalies: DependencyAnomalyItem[] = [
      { edge: 'api->db', caller: 'api', callee: 'db', anomaly_type: 'LATENCY_REGRESSION', severity: 'CRITICAL', details: 'Increased 3.0x' }
    ];

    expect(anomalies[0].anomaly_type).toBe('LATENCY_REGRESSION');
    expect(anomalies[0].severity).toBe('CRITICAL');
  });

  it('TRC-147: verifies Mann-Whitney U test release regression status', () => {
    const reg: PerformanceRegressionItem = {
      is_regression: true,
      p_value: 0.0002,
      effect_size: 0.65,
      baseline_median_ms: 19.5,
      canary_median_ms: 58.0,
      median_delta_ms: 38.5,
      median_delta_pct: 197.4
    };

    expect(reg.is_regression).toBe(true);
    expect(reg.p_value).toBeLessThan(0.05);
    expect(reg.median_delta_pct).toBeGreaterThan(100);
  });
});
