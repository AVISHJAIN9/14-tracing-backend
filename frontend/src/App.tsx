import React, { useState } from 'react';
import { TraceExplorer } from './pages/TraceExplorer';
import { TraceDetail } from './pages/TraceDetail';
import { ServiceMap } from './pages/ServiceMap';
import { Activity, Search, ShieldCheck, Network } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'explorer' | 'map'>('explorer');
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);

  const handleSelectTrace = (tid: string) => {
    setSelectedTraceId(tid);
  };

  const handleBackToExplorer = () => {
    setSelectedTraceId(null);
    setActiveTab('explorer');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navigation Shell */}
      <header className="glass-panel" style={{
        margin: '16px 24px',
        padding: '12px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        borderRadius: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            background: 'linear-gradient(135deg, #38bdf8, #2563eb)',
            borderRadius: 8,
            padding: 8,
            display: 'flex'
          }}>
            <Activity size={22} color="white" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.1rem', fontWeight: 700, letterSpacing: '-0.02em' }}>
              Distributed Tracing Engine
            </h1>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              OpenTelemetry Observability Console
            </div>
          </div>
        </div>

        <nav style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            className={`nav-link ${activeTab === 'explorer' && !selectedTraceId ? 'active' : ''}`}
            onClick={() => {
              setSelectedTraceId(null);
              setActiveTab('explorer');
            }}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
          >
            <Search size={16} /> Trace Explorer
          </button>

          <button
            className={`nav-link ${activeTab === 'map' ? 'active' : ''}`}
            onClick={() => {
              setSelectedTraceId(null);
              setActiveTab('map');
            }}
            style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
          >
            <Network size={16} /> Service Map
          </button>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.2)',
            padding: '4px 10px',
            borderRadius: 9999,
            fontSize: '0.75rem',
            color: '#34d399',
            fontWeight: 600
          }}>
            <ShieldCheck size={14} /> Live System
          </div>
        </nav>
      </header>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: '0 24px 32px' }}>
        {selectedTraceId ? (
          <TraceDetail
            traceId={selectedTraceId}
            onBack={handleBackToExplorer}
          />
        ) : activeTab === 'map' ? (
          <ServiceMap />
        ) : (
          <TraceExplorer
            onSelectTrace={handleSelectTrace}
          />
        )}
      </main>
    </div>
  );
};
