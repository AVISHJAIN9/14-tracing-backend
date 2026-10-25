import React from 'react';
import { ArrowRight, Network } from 'lucide-react';

export interface DependencyEdge {
  caller: string;
  callee: string;
  call_count: number;
  error_count?: number;
  avg_duration_ms?: number;
}

interface DependencyGraphProps {
  dependencies: DependencyEdge[];
  onSelectEdge?: (edge: DependencyEdge) => void;
}

export const DependencyGraph: React.FC<DependencyGraphProps> = ({ dependencies, onSelectEdge }) => {
  if (dependencies.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
        <Network size={36} style={{ marginBottom: 10, opacity: 0.5 }} />
        <p>No dependency interactions recorded between services.</p>
      </div>
    );
  }

  // Calculate unique nodes
  const nodes = Array.from(new Set([
    ...dependencies.map((d) => d.caller),
    ...dependencies.map((d) => d.callee)
  ]));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Topology summary stats */}
      <div style={{ display: 'flex', gap: 20, fontSize: '0.875rem', color: 'var(--text-muted)' }}>
        <div>
          <span>Total Services: </span>
          <strong style={{ color: 'var(--text-main)' }}>{nodes.length}</strong>
        </div>
        <div>
          <span>Dependency Edges: </span>
          <strong style={{ color: 'var(--text-main)' }}>{dependencies.length}</strong>
        </div>
      </div>

      {/* Dependency Links Matrix / List */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
        {dependencies.map((edge, idx) => (
          <div
            key={`${edge.caller}-${edge.callee}-${idx}`}
            onClick={() => onSelectEdge && onSelectEdge(edge)}
            className="glass-panel"
            style={{
              padding: '14px 18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: onSelectEdge ? 'pointer' : 'default',
              transition: 'transform 0.15s ease, border-color 0.15s ease'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontWeight: 600, color: 'var(--accent-blue)', fontSize: '0.9rem' }}>
                {edge.caller}
              </span>
              <ArrowRight size={14} color="var(--text-muted)" />
              <span style={{ fontWeight: 600, color: 'var(--accent-purple)', fontSize: '0.9rem' }}>
                {edge.callee}
              </span>
            </div>

            <div style={{ textAlign: 'right' }}>
              <span className="badge" style={{ background: 'rgba(56, 189, 248, 0.1)', color: 'var(--accent-blue)' }}>
                {edge.call_count} calls
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
