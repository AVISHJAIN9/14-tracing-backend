import React from 'react';
import { AlertCircle, TrendingUp, Activity, GitFork, GitCommit, Search } from 'lucide-react';

export interface TraceAnomalyItem {
  trace_id: string;
  is_anomaly: boolean;
  anomaly_score: number;
  reasons: string[];
}

export interface LatencyAnomalyItem {
  service: string;
  operation: string;
  duration_ms: number;
  baseline_median_ms: number;
  modified_z_score: number;
  is_anomaly: boolean;
  seasonality_note?: string;
}

export interface ErrorSpikeItem {
  service: string;
  is_error_spike: boolean;
  cusum_statistic: number;
  threshold: number;
  baseline_mean_errors: number;
  recent_mean_errors: number;
  poisson_p_value: number;
}

export interface RootCauseItem {
  span_id: string;
  service_name: string;
  name: string;
  root_cause_score: number;
  self_time_ms: number;
  is_critical_path: boolean;
  has_error: boolean;
  reasons: string[];
}

export interface DependencyAnomalyItem {
  edge: string;
  caller: string;
  callee: string;
  anomaly_type: string;
  severity: string;
  details: string;
}

export interface PerformanceRegressionItem {
  is_regression: boolean;
  p_value: number;
  effect_size: number;
  baseline_median_ms: number;
  canary_median_ms: number;
  median_delta_ms: number;
  median_delta_pct: number;
}

interface AnomaliesViewerProps {
  traceAnomalies?: TraceAnomalyItem[];
  latencyAnomalies?: LatencyAnomalyItem[];
  errorSpikes?: ErrorSpikeItem[];
  rootCauses?: RootCauseItem[];
  dependencyAnomalies?: DependencyAnomalyItem[];
  regression?: PerformanceRegressionItem | null;
  onSelectTrace?: (traceId: string) => void;
}

export const AnomaliesViewer: React.FC<AnomaliesViewerProps> = ({
  traceAnomalies = [],
  latencyAnomalies = [],
  errorSpikes = [],
  rootCauses = [],
  dependencyAnomalies = [],
  regression = null,
  onSelectTrace
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Trace Anomalies (Isolation Forest) */}
      <div className="glass-panel" style={{ padding: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Activity size={18} color="var(--accent-purple)" />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
            Trace Topology Anomalies (Isolation Forest)
          </h3>
        </div>

        {traceAnomalies.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No trace topology anomalies detected in current window.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {traceAnomalies.map((ta) => (
              <div
                key={ta.trace_id}
                onClick={() => onSelectTrace && onSelectTrace(ta.trace_id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  background: ta.is_anomaly ? 'rgba(239, 68, 68, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: ta.is_anomaly ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid var(--border-color)',
                  borderRadius: 6,
                  cursor: onSelectTrace ? 'pointer' : 'default'
                }}
              >
                <div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--accent-blue)' }}>
                    Trace: {ta.trace_id}
                  </div>
                  {ta.reasons.length > 0 && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                      {ta.reasons.join(' · ')}
                    </div>
                  )}
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: ta.is_anomaly ? 'var(--accent-red)' : 'var(--accent-green)',
                      background: ta.is_anomaly ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                      padding: '2px 8px',
                      borderRadius: 4
                    }}
                  >
                    Score: {ta.anomaly_score.toFixed(3)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Latency Anomalies (Robust MAD / EWMA) */}
      <div className="glass-panel" style={{ padding: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <TrendingUp size={18} color="var(--accent-blue)" />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
            Latency Outliers (MAD / EWMA Baselines)
          </h3>
        </div>

        {latencyAnomalies.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No latency anomalies exceeding modified Z-score threshold.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {latencyAnomalies.map((la, idx) => (
              <div
                key={`${la.service}-${la.operation}-${idx}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  background: la.is_anomaly ? 'rgba(245, 158, 11, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: la.is_anomaly ? '1px solid rgba(245, 158, 11, 0.3)' : '1px solid var(--border-color)',
                  borderRadius: 6
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                    <span style={{ color: 'var(--accent-blue)', marginRight: 6 }}>{la.service}</span>
                    <span>{la.operation}</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    Observed: {la.duration_ms.toFixed(1)}ms | Baseline Median: {la.baseline_median_ms.toFixed(1)}ms
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-orange)' }}>
                    Z-score: +{la.modified_z_score.toFixed(2)}σ
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Error-Spike Detection (CUSUM / Poisson) */}
      <div className="glass-panel" style={{ padding: 18 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <AlertCircle size={18} color="var(--accent-red)" />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
            Error-Rate Change Points (CUSUM & Poisson Test)
          </h3>
        </div>

        {errorSpikes.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No service error rate spikes detected.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {errorSpikes.map((es, idx) => (
              <div
                key={`${es.service}-${idx}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  background: es.is_error_spike ? 'rgba(239, 68, 68, 0.1)' : 'rgba(255, 255, 255, 0.02)',
                  border: es.is_error_spike ? '1px solid rgba(239, 68, 68, 0.35)' : '1px solid var(--border-color)',
                  borderRadius: 6
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>{es.service}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    CUSUM Stat: {es.cusum_statistic.toFixed(2)} (Threshold: {es.threshold}) | Poisson p-value: {es.poisson_p_value}
                  </div>
                </div>

                <div>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: es.is_error_spike ? 'var(--accent-red)' : 'var(--accent-green)',
                      background: es.is_error_spike ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.15)',
                      padding: '4px 10px',
                      borderRadius: 4
                    }}
                  >
                    {es.is_error_spike ? 'Error Spike Active' : 'Normal'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Root-Cause Candidates */}
      {rootCauses.length > 0 && (
        <div className="glass-panel" style={{ padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <Search size={18} color="var(--accent-red)" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
              Ranked Root-Cause Candidates
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {rootCauses.map((rc, idx) => (
              <div
                key={`${rc.span_id}-${idx}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 14px',
                  background: rc.has_error ? 'rgba(239, 68, 68, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                  border: rc.has_error ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid var(--border-color)',
                  borderRadius: 6
                }}
              >
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                    <span style={{ color: 'var(--accent-blue)', marginRight: 6 }}>{rc.service_name}</span>
                    <span>{rc.name}</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
                    Span: {rc.span_id} | Self-time: {rc.self_time_ms}ms {rc.is_critical_path && '(Critical Path)'}
                  </div>
                  {rc.reasons.length > 0 && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--accent-red)', marginTop: 4 }}>
                      {rc.reasons.join(' · ')}
                    </div>
                  )}
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span
                    style={{
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      color: 'var(--accent-red)',
                      background: 'rgba(239, 68, 68, 0.15)',
                      padding: '4px 10px',
                      borderRadius: 4
                    }}
                  >
                    Score: {rc.root_cause_score.toFixed(3)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Service Dependency Anomalies */}
      {dependencyAnomalies.length > 0 && (
        <div className="glass-panel" style={{ padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <GitFork size={18} color="var(--accent-purple)" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
              Service Dependency Topology Anomalies
            </h3>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {dependencyAnomalies.map((da, idx) => (
              <div
                key={`${da.edge}-${idx}`}
                style={{
                  padding: '10px 14px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 6
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
                    {da.caller} → {da.callee}
                  </span>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      color: da.severity === 'CRITICAL' ? 'var(--accent-red)' : 'var(--accent-orange)',
                      background: da.severity === 'CRITICAL' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                      padding: '2px 8px',
                      borderRadius: 4
                    }}
                  >
                    {da.anomaly_type}
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {da.details}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Performance Regression (Mann-Whitney U) */}
      {regression && (
        <div className="glass-panel" style={{ padding: 18 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <GitCommit size={18} color="var(--accent-blue)" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>
              Release Performance Regression (Mann-Whitney U Test)
            </h3>
          </div>

          <div
            style={{
              padding: '12px 16px',
              background: regression.is_regression ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 185, 129, 0.08)',
              border: regression.is_regression ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
              borderRadius: 6,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}
          >
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', color: regression.is_regression ? 'var(--accent-red)' : 'var(--accent-green)' }}>
                {regression.is_regression ? 'Statistically Significant Regression Detected' : 'No Significant Performance Shift'}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                p-value: {regression.p_value} (α = 0.05) | Effect Size (Cliff's Delta): {regression.effect_size.toFixed(2)}
              </div>
            </div>

            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '0.9rem', fontWeight: 700 }}>
                {regression.median_delta_ms > 0 ? `+${regression.median_delta_ms.toFixed(1)}ms` : `${regression.median_delta_ms.toFixed(1)}ms`}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                {regression.median_delta_pct > 0 ? `+${regression.median_delta_pct.toFixed(1)}%` : `${regression.median_delta_pct.toFixed(1)}%`}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
