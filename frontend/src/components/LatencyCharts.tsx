import React from 'react';
import { TrendingUp } from 'lucide-react';

export interface LatencyStats {
  p50_ms: number;
  p90_ms: number;
  p99_ms: number;
  avg_ms: number;
  min_ms: number;
  max_ms: number;
}

interface LatencyChartsProps {
  stats: LatencyStats;
}

export const LatencyCharts: React.FC<LatencyChartsProps> = ({ stats }) => {
  const percentiles = [
    { label: 'p50 (Median)', value: stats.p50_ms, color: 'var(--accent-blue)', width: '50%' },
    { label: 'p90', value: stats.p90_ms, color: 'var(--accent-amber)', width: '85%' },
    { label: 'p99 (Tail)', value: stats.p99_ms, color: 'var(--accent-rose)', width: '100%' }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Top summary row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12 }}>
        <div className="glass-panel" style={{ padding: '12px 16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Average Latency</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
            {stats.avg_ms.toFixed(2)} ms
          </div>
        </div>
        <div className="glass-panel" style={{ padding: '12px 16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Min Latency</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
            {stats.min_ms.toFixed(2)} ms
          </div>
        </div>
        <div className="glass-panel" style={{ padding: '12px 16px' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Max Latency</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-rose)' }}>
            {stats.max_ms.toFixed(2)} ms
          </div>
        </div>
      </div>

      {/* Latency Percentile Distribution Bars */}
      <div className="glass-panel" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <TrendingUp size={18} color="var(--accent-blue)" />
          <h4 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Latency Percentile Breakdown</h4>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {percentiles.map((p) => (
            <div key={p.label}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
                <span style={{ color: 'var(--text-muted)' }}>{p.label}</span>
                <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)' }}>{p.value.toFixed(2)} ms</span>
              </div>
              <div style={{ height: 8, background: 'rgba(255, 255, 255, 0.05)', borderRadius: 4, overflow: 'hidden' }}>
                <div style={{ height: '100%', width: p.width, background: p.color, borderRadius: 4 }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
