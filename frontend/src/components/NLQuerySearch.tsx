import React, { useState } from 'react';
import { Search, Sparkles, Filter, AlertCircle, ArrowRight } from 'lucide-react';

export interface StructuredTraceQuery {
  service?: string | null;
  operation?: string | null;
  min_duration_ms?: number | null;
  max_duration_ms?: number | null;
  status?: string | null;
  query_text?: string | null;
}

export interface NLQueryResponse {
  query: string;
  structured_query: StructuredTraceQuery;
  model: string;
  tenant_id: string;
}

interface NLQuerySearchProps {
  onExecuteNLQuery?: (query: string) => Promise<NLQueryResponse>;
  onApplyFilters?: (filters: StructuredTraceQuery) => void;
}

export const NLQuerySearch: React.FC<NLQuerySearchProps> = ({
  onExecuteNLQuery,
  onApplyFilters
}) => {
  const [inputQuery, setInputQuery] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [parsedQuery, setParsedQuery] = useState<StructuredTraceQuery | null>(null);
  const [modelUsed, setModelUsed] = useState<string>('google/flan-t5-small');

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim()) return;

    if (!onExecuteNLQuery) {
      // Local fallback parsing preview
      const simulated: StructuredTraceQuery = {
        service: inputQuery.includes('auth') ? 'auth-service' : null,
        status: inputQuery.includes('error') ? 'ERROR' : null,
        min_duration_ms: inputQuery.includes('slow') ? 500 : null,
        query_text: inputQuery.trim()
      };
      setParsedQuery(simulated);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await onExecuteNLQuery(inputQuery);
      setParsedQuery(res.structured_query);
      setModelUsed(res.model);
    } catch (err: any) {
      if (err?.message?.includes('LLM_NOT_CONFIGURED')) {
        setError('LLM translation service not configured (HTTP 503 LLM_NOT_CONFIGURED). Set LLM_ENABLED=true or credentials.');
      } else {
        setError(err?.message || 'Failed to parse natural language query.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleApply = () => {
    if (parsedQuery && onApplyFilters) {
      onApplyFilters(parsedQuery);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: 18 }} data-testid="trc-144-nl-search">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Sparkles size={18} color="var(--accent-cyan)" />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>Natural-Language Trace Query (TRC-144)</h3>
          <span
            style={{
              fontSize: '0.75rem',
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor: 'rgba(6, 182, 212, 0.15)',
              color: 'var(--accent-cyan)',
              fontWeight: 500
            }}
          >
            {modelUsed}
          </span>
        </div>
      </div>

      <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search
            size={16}
            style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
          />
          <input
            type="text"
            data-testid="trc-144-input"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            aria-label="Natural language search query input"
            style={{
              width: '100%',
              padding: '8px 12px 8px 36px',
              borderRadius: 6,
              border: '1px solid var(--border-color)',
              backgroundColor: 'rgba(255, 255, 255, 0.04)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem'
            }}
          />
        </div>
        <button
          type="submit"
          data-testid="trc-144-submit-btn"
          disabled={loading || !inputQuery.trim()}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '8px 16px',
            borderRadius: 6,
            backgroundColor: 'var(--accent-cyan)',
            color: '#000',
            fontWeight: 600,
            fontSize: '0.82rem',
            border: 'none',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          <Sparkles size={14} />
          {loading ? 'Translating...' : 'Translate Query'}
        </button>
      </form>

      {error && (
        <div
          data-testid="trc-144-error"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '10px 14px',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            color: '#ef4444',
            borderRadius: 6,
            fontSize: '0.85rem'
          }}
        >
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {parsedQuery && !error && (
        <div
          data-testid="trc-144-parsed-query"
          style={{
            padding: '12px 14px',
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            borderRadius: 6,
            borderLeft: '3px solid var(--accent-cyan)'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--accent-cyan)', fontSize: '0.8rem', fontWeight: 600 }}>
              <Filter size={14} />
              Validated Structured Query (JSON Schema)
            </div>
            <button
              onClick={handleApply}
              data-testid="trc-144-apply-btn"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                padding: '4px 10px',
                fontSize: '0.75rem',
                borderRadius: 4,
                backgroundColor: 'rgba(6, 182, 212, 0.2)',
                color: 'var(--accent-cyan)',
                border: '1px solid rgba(6, 182, 212, 0.4)',
                cursor: 'pointer'
              }}
            >
              <span>Apply Filters</span>
              <ArrowRight size={12} />
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8, fontSize: '0.8rem' }}>
            <div style={{ padding: '6px 8px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Service: </span>
              <strong>{parsedQuery.service || '(any)'}</strong>
            </div>
            <div style={{ padding: '6px 8px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Status: </span>
              <strong style={{ color: parsedQuery.status === 'ERROR' ? '#ef4444' : 'inherit' }}>
                {parsedQuery.status || '(any)'}
              </strong>
            </div>
            <div style={{ padding: '6px 8px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Min Duration: </span>
              <strong>{parsedQuery.min_duration_ms ? `${parsedQuery.min_duration_ms}ms` : '(none)'}</strong>
            </div>
            <div style={{ padding: '6px 8px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Keyword Filter: </span>
              <strong>{parsedQuery.query_text || '(none)'}</strong>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
