import React from 'react';
import { AlertCircle, CheckCircle, ShieldAlert } from 'lucide-react';

export interface ServiceErrorStat {
  service_name: string;
  total_calls: number;
  error_calls: number;
  error_rate: number;
}

interface ErrorRateChartsProps {
  totalTraces: number;
  errorTraces: number;
  serviceStats?: ServiceErrorStat[];
}

export const ErrorRateCharts: React.FC<ErrorRateChartsProps> = ({
  totalTraces,
  errorTraces,
  serviceStats = []
}) => {
  const successTraces = Math.max(0, totalTraces - errorTraces);
  const errorRatePercent = totalTraces > 0 ? ((errorTraces / totalTraces) * 100).toFixed(1) : '0.0';
  const successRatePercent = totalTraces > 0 ? ((successTraces / totalTraces) * 100).toFixed(1) : '100.0';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Top summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 12 }}>
          <AlertCircle size={28} color={errorTraces > 0 ? 'var(--accent-rose)' : 'var(--text-muted)'} />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Error Rate</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: errorTraces > 0 ? 'var(--accent-rose)' : 'var(--text-main)' }}>
              {errorRatePercent}%
            </div>
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '14px 18px', display: 'flex', alignItems: 'center', gap: 12 }}>
          <CheckCircle size={28} color="var(--accent-emerald)" />
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Success Rate</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
              {successRatePercent}%
            </div>
          </div>
        </div>
      </div>

      {/* Stacked Ratio Bar */}
      <div className="glass-panel" style={{ padding: 20 }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: 12 }}>Overall Request Health Ratio</h4>
        <div style={{ height: 16, background: 'rgba(255, 255, 255, 0.05)', borderRadius: 8, display: 'flex', overflow: 'hidden' }}>
          <div
            style={{
              width: `${successRatePercent}%`,
              background: 'linear-gradient(90deg, #10b981, #059669)',
              transition: 'width 0.3s ease'
            }}
            title={`Success: ${successRatePercent}%`}
          />
          <div
            style={{
              width: `${errorRatePercent}%`,
              background: 'linear-gradient(90deg, #f43f5e, #e11d48)',
              transition: 'width 0.3s ease'
            }}
            title={`Error: ${errorRatePercent}%`}
          />
        </div>
      </div>

      {/* Per-Service Error Breakdown */}
      {serviceStats.length > 0 && (
        <div className="glass-panel" style={{ padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <ShieldAlert size={16} color="var(--accent-rose)" />
            <h4 style={{ fontSize: '0.9rem', fontWeight: 600 }}>Service Error Rates</h4>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {serviceStats.map((s) => (
              <div key={s.service_name} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                  <span style={{ fontWeight: 600 }}>{s.service_name}</span>
                  <span style={{ color: s.error_calls > 0 ? 'var(--accent-rose)' : 'var(--text-muted)' }}>
                    {s.error_calls} / {s.total_calls} errors ({(s.error_rate * 100).toFixed(1)}%)
                  </span>
                </div>
                <div style={{ height: 6, background: 'rgba(255,255,255,0.05)', borderRadius: 3, overflow: 'hidden' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${Math.min(100, s.error_rate * 100)}%`,
                      background: 'var(--accent-rose)'
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
