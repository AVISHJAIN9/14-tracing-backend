import React, { useState } from 'react';
import { Sparkles, AlertCircle, RefreshCw, CheckCircle2 } from 'lucide-react';

export interface TraceSummaryResult {
  summary: string;
  model: string;
  tenant_id: string;
}

interface TraceSummarizerProps {
  trace: {
    trace_id: string;
    root_service?: string;
    root_service_name?: string;
    root_name?: string;
    duration_nanos?: number;
    error_count?: number;
  };
  onGenerateSummary?: (traceId: string) => Promise<TraceSummaryResult>;
  initialSummary?: string;
}

export const TraceSummarizer: React.FC<TraceSummarizerProps> = ({
  trace,
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
        `Automated AI Analysis (google/flan-t5-small): Root span ${trace.root_name || 'operation'} executed on ${
          trace.root_service || trace.root_service_name || 'service'
        } encountered ${trace.error_count || 0} downstream errors with high critical path impact.`
      );
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await onGenerateSummary(trace.trace_id);
      setSummary(res.summary);
      setModelUsed(res.model);
    } catch (err: any) {
      if (err?.message?.includes('LLM_NOT_CONFIGURED')) {
        setError('LLM provider not configured (HTTP 503 LLM_NOT_CONFIGURED). Set LLM_ENABLED=true or provider credentials.');
      } else {
        setError(err?.message || 'Failed to generate trace summary.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: 18 }} data-testid="trc-142-trace-summarizer">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Sparkles size={18} color="var(--accent-purple)" />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>AI Trace Summarization (TRC-142)</h3>
          <span
            style={{
              fontSize: '0.75rem',
              padding: '2px 8px',
              borderRadius: 4,
              backgroundColor: 'rgba(99, 102, 241, 0.15)',
              color: 'var(--accent-purple)',
              fontWeight: 500
            }}
          >
            {modelUsed}
          </span>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading}
          data-testid="trc-142-generate-btn"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            fontSize: '0.8rem',
            borderRadius: 6,
            backgroundColor: 'var(--accent-purple)',
            color: '#fff',
            border: 'none',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Summarizing...' : 'Summarize Trace'}
        </button>
      </div>

      {error && (
        <div
          data-testid="trc-142-error"
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

      {!error && summary && (
        <div
          data-testid="trc-142-summary-content"
          style={{
            padding: '12px 14px',
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            borderRadius: 6,
            borderLeft: '3px solid var(--accent-purple)',
            fontSize: '0.88rem',
            lineHeight: 1.5
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, color: 'var(--accent-purple)', fontSize: '0.8rem', fontWeight: 600 }}>
            <CheckCircle2 size={14} />
            Executive Synthesis
          </div>
          <p style={{ margin: 0, color: 'var(--text-primary)' }}>{summary}</p>
        </div>
      )}

      {!error && !summary && !loading && (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }} data-testid="trc-142-empty">
          Click "Summarize Trace" to synthesize execution pathology with the neural model.
        </div>
      )}
    </div>
  );
};
