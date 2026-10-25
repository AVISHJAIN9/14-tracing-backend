import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import { DependencyGraph, DependencyEdge } from '../components/DependencyGraph';
import { Network, Server, RefreshCw } from 'lucide-react';

export const ServiceMap: React.FC = () => {
  const [services, setServices] = useState<string[]>([]);
  const [dependencies, setDependencies] = useState<DependencyEdge[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    setError(null);

    Promise.all([
      apiClient.listServices(),
      apiClient.getDependencies()
    ])
      .then(([svcs, deps]) => {
        setServices(svcs);
        setDependencies(deps);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || 'Failed to load service map');
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header bar */}
      <div className="glass-panel" style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Network size={20} color="var(--accent-purple)" />
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Architecture Service Map</h2>
        </div>
        <button className="btn btn-secondary" onClick={loadData} style={{ padding: '6px 12px' }}>
          <RefreshCw size={14} /> Refresh Map
        </button>
      </div>

      {loading && (
        <div className="glass-panel" style={{ padding: 40, textAlign: 'center', color: 'var(--accent-blue)' }}>
          Computing service dependency topology...
        </div>
      )}

      {error && (
        <div className="glass-panel" style={{ padding: 30, textAlign: 'center', color: 'var(--accent-rose)' }}>
          Error: {error}
        </div>
      )}

      {!loading && !error && (
        <>
          {/* Active Services Grid */}
          <div className="glass-panel" style={{ padding: 20 }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: 14, color: 'var(--text-muted)' }}>
              Registered Cluster Services ({services.length})
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
              {services.map((svc) => (
                <div
                  key={svc}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-color)',
                    padding: '8px 14px',
                    borderRadius: 8,
                    fontSize: '0.85rem'
                  }}
                >
                  <Server size={14} color="var(--accent-blue)" />
                  <span style={{ fontWeight: 600 }}>{svc}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Interactive Topology Graph */}
          <div className="glass-panel" style={{ padding: 20 }}>
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: 14, color: 'var(--text-muted)' }}>
              Inter-Service Dependency Invocations
            </h3>
            <DependencyGraph dependencies={dependencies} />
          </div>
        </>
      )}
    </div>
  );
};
