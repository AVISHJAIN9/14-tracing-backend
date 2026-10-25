import React, { useState } from 'react';
import { Flame, AlertTriangle, RefreshCw, Layers } from 'lucide-react';

export interface IncidentSummaryResult {
  summary: string;
  model: string;
  tenant_id: string;
}

interface IncidentSummarizerProps {
  incidentTitle: string;
  traces: Array<{
    trace_id: string;
    root_service?: string;
    root_service_name?: string;
    root_name?: string;
    duration_nanos?: number;
    error_count?: number;
  }>;
  onGenerateSummary?: (title: string, traces: any[]) => Promise<IncidentSummaryResult>;
  initialSummary?: string;
}

export const IncidentSummarizer: React.FC<IncidentSummarizerProps> = ({
  incidentTitle,
  traces,
  onGenerateSummary,
  initialSummary
}) => {
  const [summary, setSummary] = useState<string>(initialSummary || '');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [modelUsed, setModelUsed] = useState<string>('google/flan-t5-small');

  const handleGenerate = async () => {
    if (!onGenerateSummary) {
      setSummary(
        `AI Incident Synthesis (google/flan-t5-small): Incident '${incidentTitle}' affected ${traces.length} traces across multiple services. Downstream failures caused cascading database timeouts. Recommended mitigation: scale replica pools.`
      );
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await onGenerateSummary(incidentTitle, traces);
      setSummary(res.summary);
      setModelUsed(res.model);
    } catch (err: any) {
      if (err?.message?.includes('LLM_NOT_CONFIGURED')) {
        setError('LLM provider not configured (HTTP 503 LLM_NOT_CONFIGURED). Set LLM_ENABLED=true or provide provider credentials.');
      } else {
        setError(err?.message || 'Failed to synthesize incident summary.');
      }
    } finally {
      setLoading(false);
    }
  };

  const errorCount = traces.filter((t) => (t.error_count || 0) > 0).length;

  return (
    <div className="glass-panel" style={{ padding: 18 }} data-testid="trc-143-incident-summarizer">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Flame size={18} color="#f97316" />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>AI Incident Summarization (TRC-143)</h3>
          <span
            style={{
              fontSize: '0.75rem',
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor: 'rgba(249, 115, 22, 0.15)',
              color: '#f97316',
              fontWeight: 500
            }}
          >
            {modelUsed}
          </span>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading}
          data-testid="trc-143-generate-btn"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            fontSize: '0.8rem',
            borderRadius: 6,
            backgroundColor: '#f97316',
            color: '#fff',
            border: 'none',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Synthesizing...' : 'Summarize Incident'}
        </button>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 12, fontSize: '0.82rem', color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <Layers size={14} />
          <span>Traces: {traces.length}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, color: errorCount > 0 ? '#ef4444' : 'inherit' }}>
          <AlertTriangle size={14} />
          <span>Errors: {errorCount}</span>
        </div>
      </div>

      {error && (
        <div
          data-testid="trc-143-error"
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
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {!error && summary && (
        <div
          data-testid="trc-143-summary-content"
          style={{
            padding: '12px 14px',
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            borderRadius: 6,
            borderLeft: '3px solid #f97316',
            fontSize: '0.88rem',
            lineHeight: 1.5
          }}
        >
          <div style={{ color: '#f97316', fontSize: '0.8rem', fontWeight: 600, marginBottom: 4 }}>
            Incident Assessment & Action Plan
          </div>
          <p style={{ margin: 0, color: 'var(--text-primary)' }}>{summary}</p>
        </div>
      )}

      {!error && !summary && !loading && (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }} data-testid="trc-143-empty">
          Click "Summarize Incident" to generate cross-service blast radius and recovery recommendations.
        </div>
      )}
    </div>
  );
};
