import React from 'react';
import { Zap, AlertTriangle, ArrowRight } from 'lucide-react';
import { SpanItem } from '../api/client';

export interface CriticalPathResult {
  critical_path_span_ids: string[];
  critical_path_duration_nanos: number;
  segments: Array<{
    span_id: string;
    service_name: string;
    name: string;
    duration_nanos: number;
  }>;
}

interface CriticalPathHighlightProps {
  spans: SpanItem[];
  criticalPathSpanIds: Set<string>;
  onSelectSpan?: (span: SpanItem) => void;
}

export const CriticalPathHighlight: React.FC<CriticalPathHighlightProps> = ({
  spans,
  criticalPathSpanIds,
  onSelectSpan
}) => {
  const criticalSpans = spans.filter((s) => criticalPathSpanIds.has(s.span_id));
  const totalTraceDuration = Math.max(...spans.map((s) => s.duration_nanos), 1);
  const criticalPathDuration = criticalSpans.reduce((acc, s) => acc + s.duration_nanos, 0);

  if (criticalSpans.length === 0) {
    return (
      <div style={{ padding: 16, color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        No critical path identified for this trace.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          background: 'rgba(239, 68, 68, 0.08)',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          borderRadius: 8
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Zap size={20} color="var(--accent-red)" />
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
              Critical Path Execution Chain
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {criticalSpans.length} sequential execution segments determining latency bottleneck
            </div>
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-red)' }}>
            {(criticalPathDuration / 1_000_000).toFixed(2)} ms
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {((criticalPathDuration / totalTraceDuration) * 100).toFixed(1)}% of trace duration
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {criticalSpans.map((span, idx) => {
          const isBottleneck = span.duration_nanos > totalTraceDuration * 0.3;
          return (
            <div
              key={span.span_id}
              onClick={() => onSelectSpan && onSelectSpan(span)}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'rgba(255, 255, 255, 0.02)',
                border: isBottleneck ? '1px solid rgba(239, 68, 68, 0.4)' : '1px solid var(--border-color)',
                borderRadius: 6,
                cursor: onSelectSpan ? 'pointer' : 'default',
                transition: 'background 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: '50%',
                    background: 'rgba(255, 255, 255, 0.06)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    color: 'var(--text-muted)'
                  }}
                >
                  {idx + 1}
                </span>

                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                    <span style={{ color: 'var(--accent-blue)', marginRight: 6 }}>{span.service_name}</span>
                    <span style={{ color: 'var(--text-primary)' }}>{span.name}</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {span.span_id}
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {isBottleneck && (
                  <span
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      fontSize: '0.75rem',
                      color: 'var(--accent-red)',
                      background: 'rgba(239, 68, 68, 0.15)',
                      padding: '2px 8px',
                      borderRadius: 4
                    }}
                  >
                    <AlertTriangle size={12} /> Bottleneck
                  </span>
                )}

                <span style={{ fontWeight: 600, fontSize: '0.85rem', fontFamily: 'var(--font-mono)' }}>
                  {(span.duration_nanos / 1_000_000).toFixed(2)} ms
                </span>

                {onSelectSpan && <ArrowRight size={14} color="var(--text-muted)" />}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
