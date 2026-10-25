import React, { useState } from 'react';
import { SpanItem } from '../api/client';
import { Hash, Search } from 'lucide-react';

interface TraceTagsViewerProps {
  spans: SpanItem[];
}

export const TraceTagsViewer: React.FC<TraceTagsViewerProps> = ({ spans }) => {
  const [filterQuery, setFilterQuery] = useState<string>('');

  // Collect and aggregate unique tags across all spans
  const tagMap = new Map<string, Set<string>>();
  spans.forEach((span) => {
    Object.entries(span.attributes || {}).forEach(([k, v]) => {
      const existing = tagMap.get(k) || new Set<string>();
      existing.add(typeof v === 'object' ? JSON.stringify(v) : String(v));
      tagMap.set(k, existing);
    });
  });

  const allTags = Array.from(tagMap.entries())
    .map(([key, valSet]) => ({
      key,
      values: Array.from(valSet)
    }))
    .filter((t) =>
      t.key.toLowerCase().includes(filterQuery.toLowerCase()) ||
      t.values.some((v) => v.toLowerCase().includes(filterQuery.toLowerCase()))
    );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Search Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', fontWeight: 600 }}>
          <Hash size={16} color="var(--accent-emerald)" />
          <span>Aggregated Trace Tags ({tagMap.size})</span>
        </div>
        <div style={{ position: 'relative', width: 220 }}>
          <Search size={14} style={{ position: 'absolute', left: 8, top: 9, color: 'var(--text-muted)' }} />
          <input
            type="text"
            aria-label="Filter trace tags"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            style={{
              width: '100%',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              borderRadius: 6,
              padding: '6px 8px 6px 28px',
              fontSize: '0.75rem',
              color: 'var(--text-main)'
            }}
          />
        </div>
      </div>

      {allTags.length === 0 ? (
        <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No trace tags found.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
          {allTags.map((tag) => (
            <div
              key={tag.key}
              style={{
                padding: '10px 14px',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-color)',
                borderRadius: 8,
                fontSize: '0.8rem'
              }}
            >
              <div style={{ fontWeight: 600, color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)', marginBottom: 4 }}>
                {tag.key}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {tag.values.map((v, i) => (
                  <span
                    key={`${v}-${i}`}
                    className="badge"
                    style={{ background: 'rgba(255, 255, 255, 0.06)', fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}
                  >
                    {v}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
