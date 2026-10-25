import React from 'react';
import { Bell, Clock } from 'lucide-react';

export interface SpanEventItem {
  name: string;
  time_unix_nano?: number;
  attributes?: Record<string, any>;
}

interface SpanEventViewerProps {
  events: SpanEventItem[];
  spanStartNano?: number;
}

export const SpanEventViewer: React.FC<SpanEventViewerProps> = ({ events, spanStartNano = 0 }) => {
  if (!events || events.length === 0) {
    return (
      <div style={{ padding: 14, color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        No recorded events for this span.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', fontWeight: 600 }}>
        <Bell size={16} color="var(--accent-amber)" />
        <span>Span Events ({events.length})</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {events.map((evt, idx) => {
          const offsetMs = evt.time_unix_nano && spanStartNano > 0
            ? Math.max(0, (evt.time_unix_nano - spanStartNano) / 1_000_000).toFixed(2)
            : '0.00';

          return (
            <div
              key={`${evt.name}-${idx}`}
              style={{
                padding: '10px 14px',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-color)',
                borderRadius: 8,
                fontSize: '0.8rem'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontWeight: 600, color: 'var(--accent-amber)' }}>{evt.name}</span>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  <Clock size={12} /> +{offsetMs} ms
                </span>
              </div>

              {evt.attributes && Object.keys(evt.attributes).length > 0 && (
                <div style={{
                  marginTop: 6,
                  padding: 8,
                  background: 'rgba(0, 0, 0, 0.3)',
                  borderRadius: 6,
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  overflowX: 'auto'
                }}>
                  {JSON.stringify(evt.attributes, null, 2)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
