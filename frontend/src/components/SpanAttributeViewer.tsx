import React, { useState } from 'react';
import { Tag, Search, Copy, Check } from 'lucide-react';

interface SpanAttributeViewerProps {
  attributes: Record<string, any>;
}

export const SpanAttributeViewer: React.FC<SpanAttributeViewerProps> = ({ attributes }) => {
  const [filterQuery, setFilterQuery] = useState<string>('');
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const keys = Object.keys(attributes || {}).filter((k) =>
    k.toLowerCase().includes(filterQuery.toLowerCase()) ||
    String(attributes[k]).toLowerCase().includes(filterQuery.toLowerCase())
  );

  const handleCopy = (key: string, val: any) => {
    navigator.clipboard?.writeText(JSON.stringify(val));
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  const getTypeBadge = (val: any) => {
    if (typeof val === 'string') return <span className="badge" style={{ background: 'rgba(56, 189, 248, 0.1)', color: 'var(--accent-blue)' }}>string</span>;
    if (typeof val === 'number') return <span className="badge" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-emerald)' }}>number</span>;
    if (typeof val === 'boolean') return <span className="badge" style={{ background: 'rgba(168, 85, 247, 0.1)', color: 'var(--accent-purple)' }}>bool</span>;
    return <span className="badge" style={{ background: 'rgba(255, 255, 255, 0.1)', color: 'var(--text-muted)' }}>json</span>;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {/* Search Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', fontWeight: 600 }}>
          <Tag size={16} color="var(--accent-blue)" />
          <span>Span Attributes ({Object.keys(attributes || {}).length})</span>
        </div>
        <div style={{ position: 'relative', width: 200 }}>
          <Search size={14} style={{ position: 'absolute', left: 8, top: 9, color: 'var(--text-muted)' }} />
          <input
            type="text"
            aria-label="Filter span attributes"
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

      {/* Attributes Table */}
      {keys.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 20, color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          No attributes found matching filter.
        </div>
      ) : (
        <div style={{ border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(255, 255, 255, 0.02)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '8px 12px' }}>Attribute Key</th>
                <th style={{ padding: '8px 12px' }}>Type</th>
                <th style={{ padding: '8px 12px' }}>Value</th>
                <th style={{ padding: '8px 12px', textAlign: 'right' }}>Copy</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                  <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>
                    {k}
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    {getTypeBadge(attributes[k])}
                  </td>
                  <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}>
                    {typeof attributes[k] === 'object' ? JSON.stringify(attributes[k]) : String(attributes[k])}
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                    <button
                      onClick={() => handleCopy(k, attributes[k])}
                      style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                      aria-label="Copy attribute value"
                    >
                      {copiedKey === k ? <Check size={14} color="var(--accent-emerald)" /> : <Copy size={14} />}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
