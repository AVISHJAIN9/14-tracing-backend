import React from 'react';
import { ExternalLink, Link2 } from 'lucide-react';

export interface SpanLinkItem {
  trace_id: string;
  span_id: string;
  attributes?: Record<string, any>;
}

interface TraceLinksViewerProps {
  links: SpanLinkItem[];
  onNavigateTrace?: (traceId: string) => void;
}

export const TraceLinksViewer: React.FC<TraceLinksViewerProps> = ({ links, onNavigateTrace }) => {
  if (!links || links.length === 0) {
    return (
      <div style={{ padding: 14, color: 'var(--text-muted)', fontSize: '0.85rem' }}>
        No external trace links attached to this span.
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', fontWeight: 600 }}>
        <Link2 size={16} color="var(--accent-purple)" />
        <span>Cross-Trace Links ({links.length})</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {links.map((link, idx) => (
          <div
            key={`${link.trace_id}-${link.span_id}-${idx}`}
            style={{
              padding: '10px 14px',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-color)',
              borderRadius: 8,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.8rem'
            }}
          >
            <div>
              <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)', marginBottom: 2 }}>
                Trace: {link.trace_id}
              </div>
              <div style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                Span: {link.span_id}
              </div>
            </div>

            {onNavigateTrace && (
              <button
                className="btn btn-secondary"
                onClick={() => onNavigateTrace(link.trace_id)}
                style={{ padding: '4px 10px', fontSize: '0.75rem' }}
              >
                <ExternalLink size={12} /> View Linked Trace
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
