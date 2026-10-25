import React from 'react';
import { SpanItem } from '../api/client';

interface WaterfallTimelineProps {
  spans: SpanItem[];
  totalDurationNanos: number;
  traceStartNano: number;
  onSelectSpan?: (span: SpanItem) => void;
  selectedSpanId?: string | null;
}

export const WaterfallTimeline: React.FC<WaterfallTimelineProps> = ({
  spans,
  totalDurationNanos,
  traceStartNano,
  onSelectSpan,
  selectedSpanId
}) => {
  const safeDuration = totalDurationNanos > 0 ? totalDurationNanos : 1;

  return (
    <div className="waterfall-container" style={{ width: '100%', overflowX: 'auto' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '280px 1fr 100px',
        padding: '10px 14px',
        fontWeight: 600,
        fontSize: '0.75rem',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        color: 'var(--text-muted)',
        borderBottom: '1px solid var(--border-color)'
      }}>
        <span>Service & Operation</span>
        <span>Timeline Overview</span>
        <span style={{ textAlign: 'right' }}>Duration</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {spans.map((span) => {
          const offsetNanos = Math.max(0, span.start_time_unix_nano - traceStartNano);
          const leftPercent = Math.min(100, Math.max(0, (offsetNanos / safeDuration) * 100));
          const widthPercent = Math.min(
            100 - leftPercent,
            Math.max(1, (span.duration_nanos / safeDuration) * 100)
          );
          const isError = span.status_code === 'ERROR';
          const isSelected = selectedSpanId === span.span_id;
          const durationMs = (span.duration_nanos / 1_000_000).toFixed(2);

          return (
            <div
              key={span.span_id}
              className="waterfall-row"
              onClick={() => onSelectSpan && onSelectSpan(span)}
              style={{
                cursor: 'pointer',
                background: isSelected ? 'rgba(56, 189, 248, 0.1)' : undefined
              }}
            >
              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <span style={{
                  fontWeight: 600,
                  color: isError ? 'var(--accent-rose)' : 'var(--accent-blue)',
                  marginRight: 6
                }}>
                  {span.service_name}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>{span.name}</span>
              </div>

              <div className="waterfall-track">
                <div
                  className={`waterfall-bar ${isError ? 'error' : ''}`}
                  style={{
                    left: `${leftPercent}%`,
                    width: `${widthPercent}%`
                  }}
                  title={`${span.service_name}: ${span.name} (${durationMs}ms)`}
                />
              </div>

              <div style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                {durationMs} ms
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
