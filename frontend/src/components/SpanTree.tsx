import React, { useState } from 'react';
import { SpanItem } from '../api/client';
import { ChevronRight, ChevronDown, CircleDot } from 'lucide-react';

export interface SpanTreeNode {
  span: SpanItem;
  children: SpanTreeNode[];
  depth: number;
}

export function buildSpanTree(spans: SpanItem[]): SpanTreeNode[] {
  const nodeMap = new Map<string, SpanTreeNode>();
  const roots: SpanTreeNode[] = [];

  spans.forEach((span) => {
    nodeMap.set(span.span_id, { span, children: [], depth: 0 });
  });

  spans.forEach((span) => {
    const node = nodeMap.get(span.span_id)!;
    if (span.parent_span_id && nodeMap.has(span.parent_span_id)) {
      const parent = nodeMap.get(span.parent_span_id)!;
      node.depth = parent.depth + 1;
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  });

  // Recursively update depth for deep trees
  function setDepth(node: SpanTreeNode, d: number) {
    node.depth = d;
    node.children.forEach((c) => setDepth(c, d + 1));
  }
  roots.forEach((r) => setDepth(r, 0));

  return roots;
}

interface SpanTreeProps {
  spans: SpanItem[];
  onSelectSpan?: (span: SpanItem) => void;
  selectedSpanId?: string | null;
}

export const SpanTree: React.FC<SpanTreeProps> = ({ spans, onSelectSpan, selectedSpanId }) => {
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());
  const treeRoots = buildSpanTree(spans);

  const toggleCollapse = (spanId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCollapsedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(spanId)) next.delete(spanId);
      else next.add(spanId);
      return next;
    });
  };

  const renderNode = (node: SpanTreeNode) => {
    const { span, children, depth } = node;
    const isCollapsed = collapsedNodes.has(span.span_id);
    const hasChildren = children.length > 0;
    const isSelected = selectedSpanId === span.span_id;
    const isError = span.status_code === 'ERROR';
    const durationMs = (span.duration_nanos / 1_000_000).toFixed(2);

    return (
      <div key={span.span_id} style={{ display: 'flex', flexDirection: 'column' }}>
        <div
          onClick={() => onSelectSpan && onSelectSpan(span)}
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '8px 12px',
            paddingLeft: `${14 + depth * 24}px`,
            borderBottom: '1px solid var(--border-color)',
            background: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
            cursor: 'pointer',
            transition: 'background 0.15s ease'
          }}
        >
          {hasChildren ? (
            <button
              onClick={(e) => toggleCollapse(span.span_id, e)}
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                marginRight: 6,
                display: 'flex'
              }}
              aria-label={isCollapsed ? "Expand node" : "Collapse node"}
            >
              {isCollapsed ? <ChevronRight size={16} /> : <ChevronDown size={16} />}
            </button>
          ) : (
            <span style={{ width: 16, marginRight: 6, display: 'inline-flex', justifyContent: 'center' }}>
              <CircleDot size={8} color="var(--text-muted)" />
            </span>
          )}

          <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              fontWeight: 600,
              color: isError ? 'var(--accent-rose)' : 'var(--accent-blue)',
              fontSize: '0.85rem'
            }}>
              {span.service_name}
            </span>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{span.name}</span>
            <span className={`badge ${isError ? 'badge-error' : 'badge-ok'}`} style={{ fontSize: '0.7rem' }}>
              {span.status_code}
            </span>
          </div>

          <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {durationMs} ms
          </div>
        </div>

        {!isCollapsed && hasChildren && (
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {children.map(renderNode)}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ width: '100%', border: '1px solid var(--border-color)', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{
        padding: '10px 14px',
        fontWeight: 600,
        fontSize: '0.75rem',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        color: 'var(--text-muted)',
        background: 'rgba(255, 255, 255, 0.02)',
        borderBottom: '1px solid var(--border-color)'
      }}>
        Hierarchical Call Tree
      </div>
      {treeRoots.map(renderNode)}
    </div>
  );
};
