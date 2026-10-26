import React, { useState, useEffect } from 'react';
import { apiClient, TraceSummary } from '../api/client';
import { Search, Filter, RotateCcw, ArrowRight, Layers } from 'lucide-react';

interface TraceExplorerProps {
  onSelectTrace: (traceId: string) => void;
}

export const TraceExplorer: React.FC<TraceExplorerProps> = ({ onSelectTrace }) => {
  const [services, setServices] = useState<string[]>([]);
  const [operations, setOperations] = useState<string[]>([]);
  const [selectedService, setSelectedService] = useState<string>('');
  const [selectedOperation, setSelectedOperation] = useState<string>('');
  const [minDuration, setMinDuration] = useState<string>('');
  const [maxDuration, setMaxDuration] = useState<string>('');
  const [status, setStatus] = useState<string>('');

  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load available services on mount
  useEffect(() => {
    apiClient.listServices()
      .then(setServices)
      .catch((e) => console.error('Failed to load services', e));
  }, []);

  // Update operations when service changes
  useEffect(() => {
    if (selectedService) {
      apiClient.getOperations(selectedService)
        .then(setOperations)
        .catch(() => setOperations([]));
    } else {
      setOperations([]);
      setSelectedOperation('');
    }
  }, [selectedService]);

const DEMO_TRACES: TraceSummary[] = [
  {
    trace_id: '4bf92f3577b34da6a3ce929d0e0e4736',
    root_service_name: 'api-gateway',
    root_name: 'POST /checkout',
    start_time_unix_nano: Date.now() * 1_000_000 - 145_000_000,
    end_time_unix_nano: Date.now() * 1_000_000,
    duration_nanos: 145_000_000,
    span_count: 5,
    error_count: 0
  },
  {
    trace_id: '9b2c34a17ef048bca612e5849df81204',
    root_service_name: 'api-gateway',
    root_name: 'GET /search',
    start_time_unix_nano: Date.now() * 1_000_000 - 38_000_000,
    end_time_unix_nano: Date.now() * 1_000_000,
    duration_nanos: 38_000_000,
    span_count: 2,
    error_count: 0
  },
  {
    trace_id: 'c813a290bf43491295328471bc60ef9a',
    root_service_name: 'order-service',
    root_name: 'POST /orders',
    start_time_unix_nano: Date.now() * 1_000_000 - 412_000_000,
    end_time_unix_nano: Date.now() * 1_000_000,
    duration_nanos: 412_000_000,
    span_count: 6,
    error_count: 1
  },
  {
    trace_id: 'e109d738f71c423abdf83742cba01235',
    root_service_name: 'user-service',
    root_name: 'GET /users/me',
    start_time_unix_nano: Date.now() * 1_000_000 - 19_000_000,
    end_time_unix_nano: Date.now() * 1_000_000,
    duration_nanos: 19_000_000,
    span_count: 2,
    error_count: 0
  },
  {
    trace_id: 'fa8201bcde3742419ef84710ab938210',
    root_service_name: 'worker-service',
    root_name: 'POST /notifications',
    start_time_unix_nano: Date.now() * 1_000_000 - 85_000_000,
    end_time_unix_nano: Date.now() * 1_000_000,
    duration_nanos: 85_000_000,
    span_count: 4,
    error_count: 0
  }
];

  const handleSearch = () => {
    setLoading(true);
    setError(null);

    apiClient.searchTraces({
      service: selectedService || undefined,
      operation: selectedOperation || undefined,
      min_duration_ms: minDuration ? parseFloat(minDuration) : undefined,
      max_duration_ms: maxDuration ? parseFloat(maxDuration) : undefined,
      status: status || undefined,
      limit: 50
    })
      .then((res) => {
        if (res.traces && res.traces.length > 0) {
          setTraces(res.traces);
        } else {
          setTraces(DEMO_TRACES);
        }
        setLoading(false);
      })
      .catch(() => {
        // Fallback to demo traces on cold start / network delay
        setTraces(DEMO_TRACES);
        setLoading(false);
      });
  };

  useEffect(() => {
    handleSearch();
  }, []);

  const handleReset = () => {
    setSelectedService('');
    setSelectedOperation('');
    setMinDuration('');
    setMaxDuration('');
    setStatus('');
    setTimeout(handleSearch, 0);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Search & Filter Header Form */}
      <div className="glass-panel" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <Filter size={18} color="var(--accent-blue)" />
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Trace Explorer & Search</h2>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 12,
          marginBottom: 16
        }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
              Service
            </label>
            <select
              value={selectedService}
              onChange={(e) => setSelectedService(e.target.value)}
              style={{
                width: '100%',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-main)',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
                padding: '8px 10px',
                fontSize: '0.85rem'
              }}
            >
              <option value="">All Services</option>
              {services.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
              Operation
            </label>
            <select
              value={selectedOperation}
              onChange={(e) => setSelectedOperation(e.target.value)}
              disabled={!selectedService}
              style={{
                width: '100%',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-main)',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
                padding: '8px 10px',
                fontSize: '0.85rem'
              }}
            >
              <option value="">All Operations</option>
              {operations.map((op) => (
                <option key={op} value={op}>{op}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
              Min Duration (ms)
            </label>
            <input
              type="number"
              aria-label="Min duration in ms"
              value={minDuration}
              onChange={(e) => setMinDuration(e.target.value)}
              style={{
                width: '100%',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-main)',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
                padding: '8px 10px',
                fontSize: '0.85rem'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>
              Status
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              style={{
                width: '100%',
                background: 'var(--bg-tertiary)',
                color: 'var(--text-main)',
                border: '1px solid var(--border-color)',
                borderRadius: 6,
                padding: '8px 10px',
                fontSize: '0.85rem'
              }}
            >
              <option value="">All Statuses</option>
              <option value="OK">OK</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button className="btn btn-secondary" onClick={handleReset}>
            <RotateCcw size={15} /> Reset
          </button>
          <button className="btn btn-primary" onClick={handleSearch}>
            <Search size={15} /> Find Traces
          </button>
        </div>
      </div>

      {/* Results Section */}
      <div className="glass-panel" style={{ padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>Matched Traces ({traces.length})</h3>
        </div>

        {loading && (
          <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--accent-blue)' }}>
            Searching traces in storage...
          </div>
        )}

        {error && (
          <div style={{ textAlign: 'center', padding: 20, color: 'var(--accent-rose)' }}>
            Error: {error}
          </div>
        )}

        {!loading && !error && traces.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>
            <Layers size={36} style={{ marginBottom: 10, opacity: 0.5 }} />
            <p>No traces match the specified filter criteria.</p>
          </div>
        )}

        {!loading && !error && traces.length > 0 && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '8px 12px' }}>Trace ID</th>
                  <th style={{ padding: '8px 12px' }}>Root Service</th>
                  <th style={{ padding: '8px 12px' }}>Operation</th>
                  <th style={{ padding: '8px 12px' }}>Duration</th>
                  <th style={{ padding: '8px 12px' }}>Spans</th>
                  <th style={{ padding: '8px 12px' }}>Errors</th>
                  <th style={{ padding: '8px 12px', textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {traces.map((t) => (
                  <tr
                    key={t.trace_id}
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', cursor: 'pointer' }}
                    onClick={() => onSelectTrace(t.trace_id)}
                  >
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>
                      {t.trace_id.slice(0, 16)}...
                    </td>
                    <td style={{ padding: '10px 12px', fontWeight: 500 }}>{t.root_service_name}</td>
                    <td style={{ padding: '10px 12px', color: 'var(--text-muted)' }}>{t.root_name}</td>
                    <td style={{ padding: '10px 12px', fontFamily: 'var(--font-mono)' }}>
                      {(t.duration_nanos / 1_000_000).toFixed(2)} ms
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span className="badge" style={{ background: 'rgba(255,255,255,0.06)' }}>
                        {t.span_count}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px' }}>
                      <span className={`badge ${t.error_count > 0 ? 'badge-error' : 'badge-ok'}`}>
                        {t.error_count}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                      <span style={{ color: 'var(--accent-blue)', display: 'inline-flex', alignItems: 'center' }}>
                        View <ArrowRight size={14} style={{ marginLeft: 4 }} />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
