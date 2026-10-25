import React, { useEffect, useState } from 'react';
import { apiClient, TraceDetailResponse, SpanItem } from '../api/client';
import { WaterfallTimeline } from '../components/WaterfallTimeline';
import { SpanTree } from '../components/SpanTree';
import { LatencyCharts } from '../components/LatencyCharts';
import { ErrorRateCharts } from '../components/ErrorRateCharts';
import { SpanAttributeViewer } from '../components/SpanAttributeViewer';
import { SpanEventViewer } from '../components/SpanEventViewer';
import { TraceTagsViewer } from '../components/TraceTagsViewer';
import { TraceLinksViewer } from '../components/TraceLinksViewer';
import { CriticalPathHighlight } from '../components/CriticalPathHighlight';
import { ArrowLeft, Clock, Layers, AlertCircle, Server, GitBranch, AlignLeft, BarChart2, Hash, Zap } from 'lucide-react';

interface TraceDetailProps {
  traceId: string;
  onBack: () => void;
}

export const TraceDetail: React.FC<TraceDetailProps> = ({ traceId, onBack }) => {
  const [data, setData] = useState<TraceDetailResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<SpanItem | null>(null);
  const [viewMode, setViewMode] = useState<'waterfall' | 'tree' | 'metrics' | 'tags' | 'critical-path'>('waterfall');
  const [criticalPathIds, setCriticalPathIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);

    apiClient.getTrace(traceId)
      .then((res) => {
        if (mounted) {
          setData(res);
          if (res.spans.length > 0) setSelectedSpan(res.spans[0]);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(err.message || 'Failed to load trace detail');
          setLoading(false);
        }
      });

    apiClient.getCriticalPath(traceId)
      .then((cp) => {
        if (mounted) setCriticalPathIds(new Set(cp.critical_path_span_ids));
      })
      .catch(() => {});

    return () => { mounted = false; };
  }, [traceId]);

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: 40, textAlign: 'center' }}>
        <div style={{ color: 'var(--accent-blue)', marginBottom: 12 }}>Loading trace details...</div>
        <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>Retrieving spans from storage</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="glass-panel" style={{ padding: 32, textAlign: 'center' }}>
        <AlertCircle size={40} color="var(--accent-rose)" style={{ marginBottom: 12 }} />
        <h3 style={{ marginBottom: 8 }}>Trace Not Found</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: 20 }}>{error || 'The requested trace ID was not found.'}</p>
        <button className="btn btn-secondary" onClick={onBack}>
          <ArrowLeft size={16} /> Back to Search
        </button>
      </div>
    );
  }

  const durationMs = (data.duration_nanos / 1_000_000).toFixed(2);
  const minStartNano = data.spans.length > 0
    ? Math.min(...data.spans.map(s => s.start_time_unix_nano))
    : 0;

  // Latency metrics calculation
  const durationsMs = data.spans.map(s => s.duration_nanos / 1_000_000).sort((a, b) => a - b);
  const minMs = durationsMs[0] || 0;
  const maxMs = durationsMs[durationsMs.length - 1] || 0;
  const avgMs = durationsMs.reduce((acc, v) => acc + v, 0) / (durationsMs.length || 1);
  const p50Ms = durationsMs[Math.floor(durationsMs.length * 0.5)] || 0;
  const p90Ms = durationsMs[Math.floor(durationsMs.length * 0.9)] || 0;
  const p99Ms = durationsMs[Math.floor(durationsMs.length * 0.99)] || 0;

  const latencyStats = { min_ms: minMs, max_ms: maxMs, avg_ms: avgMs, p50_ms: p50Ms, p90_ms: p90Ms, p99_ms: p99Ms };

  // Error rates per service
  const svcMap = new Map<string, { total: number; error: number }>();
  data.spans.forEach(s => {
    const cur = svcMap.get(s.service_name) || { total: 0, error: 0 };
    cur.total += 1;
    if (s.status_code === 'ERROR') cur.error += 1;
    svcMap.set(s.service_name, cur);
  });
  const serviceStats = Array.from(svcMap.entries()).map(([svc, stats]) => ({
    service_name: svc,
    total_calls: stats.total,
    error_calls: stats.error,
    error_rate: stats.total > 0 ? stats.error / stats.total : 0
  }));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Top Header Card */}
      <div className="glass-panel" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <button className="btn btn-secondary" onClick={onBack} style={{ padding: '6px 12px' }}>
            <ArrowLeft size={16} /> Back
          </button>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
            Trace ID: <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{data.trace_id}</span>
          </div>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 16,
          paddingTop: 12,
          borderTop: '1px solid var(--border-color)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Server size={20} color="var(--accent-blue)" />
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Root Service</div>
              <div style={{ fontWeight: 600 }}>{data.root_service}</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Clock size={20} color="var(--accent-emerald)" />
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Duration</div>
              <div style={{ fontWeight: 600 }}>{durationMs} ms</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Layers size={20} color="var(--accent-purple)" />
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Spans</div>
              <div style={{ fontWeight: 600 }}>{data.span_count}</div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <AlertCircle size={20} color={data.error_count > 0 ? "var(--accent-rose)" : "var(--accent-emerald)"} />
            <div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Errors</div>
              <div style={{
                fontWeight: 600,
                color: data.error_count > 0 ? "var(--accent-rose)" : "var(--text-main)"
              }}>
                {data.error_count}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Execution View Panel */}
      <div className="glass-panel" style={{ padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Execution Breakdown</h3>
          <div style={{ display: 'flex', gap: 6, background: 'var(--bg-tertiary)', padding: 4, borderRadius: 8 }}>
            <button
              className="btn"
              onClick={() => setViewMode('waterfall')}
              style={{
                padding: '4px 10px',
                fontSize: '0.8rem',
                background: viewMode === 'waterfall' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                color: viewMode === 'waterfall' ? 'var(--accent-blue)' : 'var(--text-muted)'
              }}
            >
              <AlignLeft size={14} /> Waterfall
            </button>
            <button
              className="btn"
              onClick={() => setViewMode('tree')}
              style={{
                padding: '4px 10px',
                fontSize: '0.8rem',
                background: viewMode === 'tree' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                color: viewMode === 'tree' ? 'var(--accent-blue)' : 'var(--text-muted)'
              }}
            >
              <GitBranch size={14} /> Span Tree
            </button>
            <button
              className="btn"
              onClick={() => setViewMode('metrics')}
              style={{
                padding: '4px 10px',
                fontSize: '0.8rem',
                background: viewMode === 'metrics' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                color: viewMode === 'metrics' ? 'var(--accent-blue)' : 'var(--text-muted)'
              }}
            >
              <BarChart2 size={14} /> Latency & Error Charts
            </button>
            <button
              className="btn"
              onClick={() => setViewMode('tags')}
              style={{
                padding: '4px 10px',
                fontSize: '0.8rem',
                background: viewMode === 'tags' ? 'rgba(56, 189, 248, 0.2)' : 'transparent',
                color: viewMode === 'tags' ? 'var(--accent-blue)' : 'var(--text-muted)'
              }}
            >
              <Hash size={14} /> Trace Tags
            </button>
            <button
              className="btn"
              onClick={() => setViewMode('critical-path')}
              style={{
                padding: '4px 10px',
                fontSize: '0.8rem',
                background: viewMode === 'critical-path' ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
                color: viewMode === 'critical-path' ? 'var(--accent-red)' : 'var(--text-muted)'
              }}
            >
              <Zap size={14} /> Critical Path
            </button>
          </div>
        </div>

        {viewMode === 'waterfall' && (
          <WaterfallTimeline
            spans={data.spans}
            totalDurationNanos={data.duration_nanos}
            traceStartNano={minStartNano}
            onSelectSpan={(s) => setSelectedSpan(s)}
            selectedSpanId={selectedSpan?.span_id}
          />
        )}

        {viewMode === 'tree' && (
          <SpanTree
            spans={data.spans}
            onSelectSpan={(s) => setSelectedSpan(s)}
            selectedSpanId={selectedSpan?.span_id}
          />
        )}

        {viewMode === 'metrics' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: 20 }}>
            <LatencyCharts stats={latencyStats} />
            <ErrorRateCharts
              totalTraces={data.span_count}
              errorTraces={data.error_count}
              serviceStats={serviceStats}
            />
          </div>
        )}

        {viewMode === 'tags' && (
          <TraceTagsViewer spans={data.spans} />
        )}

        {viewMode === 'critical-path' && (
          <CriticalPathHighlight
            spans={data.spans}
            criticalPathSpanIds={criticalPathIds}
            onSelectSpan={(s) => setSelectedSpan(s)}
          />
        )}
      </div>

      {/* Selected Span Details Drawer */}
      {selectedSpan && (
        <div className="glass-panel" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 16 }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
            <span>Selected Span:</span>
            <span style={{ color: 'var(--accent-blue)', fontFamily: 'var(--font-mono)' }}>{selectedSpan.name}</span>
            <span className={`badge ${selectedSpan.status_code === 'ERROR' ? 'badge-error' : 'badge-ok'}`}>
              {selectedSpan.status_code}
            </span>
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Span ID: </span>
              <code style={{ fontSize: '0.8rem' }}>{selectedSpan.span_id}</code>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Service: </span>
              <strong>{selectedSpan.service_name}</strong>
            </div>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Duration: </span>
              <span>{(selectedSpan.duration_nanos / 1_000_000).toFixed(2)} ms</span>
            </div>
          </div>

          <SpanAttributeViewer attributes={selectedSpan.attributes} />
          <SpanEventViewer events={selectedSpan.events as any} spanStartNano={selectedSpan.start_time_unix_nano} />
          <TraceLinksViewer links={selectedSpan.links as any} onNavigateTrace={(tid) => alert(`Link to trace: ${tid}`)} />
        </div>
      )}
    </div>
  );
};
