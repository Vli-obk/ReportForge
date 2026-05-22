'use client';

import { useEffect, useRef, useState } from 'react';

type Node = {
  id: string;
  label: string;
  x: number;
  y: number;
  category: string;
  color: string;
};

type Edge = {
  from: string;
  to: string;
  type: 'compatible' | 'conflict' | 'neutral';
};

const nodes: Node[] = [
  { id: 'tesseract', label: 'Tesseract', x: 50, y: 50, category: 'OCR', color: '#FF6B2B' },
  { id: 'pandas', label: 'Pandas', x: 200, y: 30, category: 'Data', color: '#FF6B2B' },
  { id: 'llm', label: 'LLM', x: 340, y: 70, category: 'AI', color: '#7A9CFF' },
  { id: 'opencv', label: 'OpenCV', x: 180, y: 140, category: 'Vision', color: '#88FF88' },
  { id: 'pdfplumber', label: 'pdfplumber', x: 310, y: 160, category: 'Extract', color: '#88FF88' },
  { id: 'textract', label: 'Textract', x: 80, y: 170, category: 'Cloud', color: '#D0D0D8' },
  { id: 'spacy', label: 'Spacy', x: 240, y: 220, category: 'NLP', color: '#A78BFA' },
  { id: 'huggingface', label: 'HF Models', x: 400, y: 230, category: 'AI', color: '#FCA5A5' },
  { id: 'postgres', label: 'Postgres', x: 130, y: 260, category: 'DB', color: '#67E8F9' },
];

const edges: Edge[] = [
  { from: 'tesseract', to: 'pandas', type: 'compatible' },
  { from: 'pandas', to: 'llm', type: 'compatible' },
  { from: 'opencv', to: 'pdfplumber', type: 'compatible' },
  { from: 'pandas', to: 'opencv', type: 'compatible' },
  { from: 'textract', to: 'tesseract', type: 'neutral' },
  { from: 'spacy', to: 'postgres', type: 'compatible' },
  { from: 'llm', to: 'huggingface', type: 'compatible' },
  { from: 'opencv', to: 'textract', type: 'conflict' },
  { from: 'pdfplumber', to: 'spacy', type: 'neutral' },
  { from: 'postgres', to: 'pandas', type: 'compatible' },
  { from: 'huggingface', to: 'postgres', type: 'conflict' },
];

const edgeColors = {
  compatible: 'rgba(136,255,136,0.4)',
  conflict: 'rgba(255,80,80,0.5)',
  neutral: 'rgba(74,74,90,0.5)',
};

const conflictPairs = [
  { a: 'pdfplumber + Scans', issue: 'Missing OCR preprocessing layer', severity: 'MEDIUM' },
  { a: 'Tesseract + Tables', issue: 'Poor column boundary detection', severity: 'HIGH' },
];

const compatibleStacks = [
  { stack: 'Tesseract + Pandas + LLM', label: 'Standard Invoice Stack', installs: '8.2k' },
  { stack: 'pdfplumber + Pandas + Postgres', label: 'High-Speed Text Stack', installs: '5.7k' },
  { stack: 'OpenCV + Tesseract + Spacy', label: 'Legacy Scan Stack', installs: '4.1k' },
];

export default function CompatibilitySection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setVisible(true);
          entries[0].target.querySelectorAll('.reveal').forEach((el, i) => {
            setTimeout(() => el.classList.add('visible'), i * 100);
          });
        }
      },
      { threshold: 0.2 }
    );
    if (sectionRef.current) observer.observe(sectionRef.current);
    return () => observer.disconnect();
  }, []);

  const getNodeEdges = (nodeId: string) =>
    edges.filter((e) => e.from === nodeId || e.to === nodeId);
  const isConnected = (nodeId: string) => {
    if (!activeNode) return true;
    if (nodeId === activeNode) return true;
    return getNodeEdges(activeNode).some((e) => e.from === nodeId || e.to === nodeId);
  };

  return (
    <section
      id="compatibility"
      ref={sectionRef}
      className="py-20 px-6"
      style={{ background: 'var(--carbon)' }}
    >
      <div className="max-w-7xl mx-auto">
        <div className="mb-10">
          <span
            className="mono text-xs uppercase tracking-widest"
            style={{ color: 'var(--orange)' }}
          >
            // 03 — Pipeline Integrations
          </span>
          <h2
            className="mono font-black text-3xl md:text-4xl mt-2"
            style={{ color: 'var(--aluminum)' }}
          >
            Pipeline Compatibility Matrix.
          </h2>
          <p className="mt-2 text-sm" style={{ color: 'var(--aluminum-dim)' }}>
            Hover an extraction node to see compatible models. Bottlenecks flagged before you build
            your pipeline.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          {/* Node graph — spans 2 cols */}
          <div
            className="bento-card reveal lg:col-span-2"
            style={{ background: 'var(--graphite)', minHeight: '360px', position: 'relative' }}
          >
            <div
              className="p-4 border-b flex items-center justify-between"
              style={{ borderColor: 'rgba(74,74,90,0.4)' }}
            >
              <span className="mono font-bold text-sm" style={{ color: 'var(--aluminum)' }}>
                Model Pipeline Graph
              </span>
              <div className="flex items-center gap-4 text-xs mono">
                <span className="flex items-center gap-1.5">
                  <span
                    className="inline-block w-3 h-0.5 rounded"
                    style={{ background: 'rgba(136,255,136,0.7)' }}
                  />
                  Compatible
                </span>
                <span
                  className="flex items-center gap-1.5"
                  style={{ color: 'var(--aluminum-dim)' }}
                >
                  <span
                    className="inline-block w-3 h-0.5 rounded"
                    style={{ background: 'rgba(255,80,80,0.7)' }}
                  />
                  Conflict
                </span>
                <span
                  className="flex items-center gap-1.5"
                  style={{ color: 'var(--titanium-light)' }}
                >
                  <span
                    className="inline-block w-3 h-0.5 rounded"
                    style={{ background: 'rgba(74,74,90,0.7)' }}
                  />
                  Neutral
                </span>
              </div>
            </div>
            <div className="p-4" style={{ height: '320px' }}>
              <svg
                width="100%"
                height="100%"
                viewBox="0 0 460 300"
                preserveAspectRatio="xMidYMid meet"
              >
                {/* Edges */}
                {edges.map((edge, i) => {
                  const fromNode = nodes.find((n) => n.id === edge.from);
                  const toNode = nodes.find((n) => n.id === edge.to);
                  if (!fromNode || !toNode) return null;
                  const isActive = activeNode
                    ? edge.from === activeNode || edge.to === activeNode
                    : true;
                  return (
                    <line
                      key={i}
                      x1={fromNode.x}
                      y1={fromNode.y}
                      x2={toNode.x}
                      y2={toNode.y}
                      stroke={edgeColors[edge.type]}
                      strokeWidth={isActive ? 1.5 : 0.5}
                      opacity={isActive ? 1 : 0.2}
                      strokeDasharray={edge.type === 'conflict' ? '4,3' : undefined}
                    />
                  );
                })}
                {/* Nodes */}
                {nodes.map((node) => {
                  const connected = isConnected(node.id);
                  return (
                    <g
                      key={node.id}
                      style={{ cursor: 'pointer' }}
                      onMouseEnter={() => setActiveNode(node.id)}
                      onMouseLeave={() => setActiveNode(null)}
                    >
                      <circle
                        cx={node.x}
                        cy={node.y}
                        r={activeNode === node.id ? 10 : 7}
                        fill={node.color}
                        opacity={connected ? (activeNode === node.id ? 1 : 0.85) : 0.2}
                        style={{ transition: 'r 0.2s ease, opacity 0.2s ease' }}
                      />
                      {/* Glow ring for active */}
                      {activeNode === node.id && (
                        <circle
                          cx={node.x}
                          cy={node.y}
                          r={16}
                          fill="none"
                          stroke={node.color}
                          strokeWidth={1}
                          opacity={0.3}
                        />
                      )}
                      <text
                        x={node.x}
                        y={node.y + 22}
                        textAnchor="middle"
                        fontSize="9"
                        fill={connected ? '#D0D0D8' : '#4A4A5A'}
                        fontFamily="JetBrains Mono, monospace"
                        fontWeight="600"
                        style={{ transition: 'fill 0.2s ease' }}
                      >
                        {node.label}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>
            {/* Pro lock overlay hint */}
            <div
              className="absolute bottom-0 left-0 right-0 p-4 flex items-center justify-between border-t"
              style={{
                borderColor: 'rgba(74,74,90,0.3)',
                background: 'rgba(13,13,13,0.6)',
                backdropFilter: 'blur(8px)',
              }}
            >
              <p className="mono text-xs" style={{ color: 'var(--aluminum-dim)' }}>
                <span style={{ color: 'var(--orange)' }}>Pro:</span> Full bottleneck reports + root
                cause analysis for 1487 datasets
              </p>
              <button className="btn-primary py-2 px-4 text-xs">Unlock Pro</button>
            </div>
          </div>

          {/* Right column: conflicts + stacks */}
          <div className="flex flex-col gap-3">
            {/* Known conflicts */}
            <div className="bento-card reveal flex-1 p-5" style={{ background: 'var(--graphite)' }}>
              <p className="mono font-bold text-sm mb-4" style={{ color: 'var(--aluminum)' }}>
                Known Conflicts
              </p>
              <div className="space-y-3">
                {conflictPairs.map((c, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg"
                    style={{
                      background: 'rgba(255,80,80,0.05)',
                      border: '1px solid rgba(255,80,80,0.15)',
                    }}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <span className="mono font-bold text-xs" style={{ color: 'var(--aluminum)' }}>
                        {c.a}
                      </span>
                      <span
                        className="mono text-xs px-1.5 py-0.5 rounded shrink-0"
                        style={{
                          background:
                            c.severity === 'HIGH' ? 'rgba(255,60,60,0.15)' : 'rgba(255,150,0,0.15)',
                          border: `1px solid ${c.severity === 'HIGH' ? 'rgba(255,60,60,0.4)' : 'rgba(255,150,0,0.4)'}`,
                          color: c.severity === 'HIGH' ? '#FF6060' : '#FFB020',
                          fontSize: '0.6rem',
                        }}
                      >
                        {c.severity}
                      </span>
                    </div>
                    <p className="mono text-xs" style={{ color: 'var(--aluminum-dim)' }}>
                      {c.issue}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Proven stacks */}
            <div className="bento-card reveal p-5" style={{ background: 'var(--graphite)' }}>
              <p className="mono font-bold text-sm mb-4" style={{ color: 'var(--aluminum)' }}>
                Proven Stacks ✓
              </p>
              <div className="space-y-3">
                {compatibleStacks.map((s, i) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg"
                    style={{
                      background: 'rgba(136,255,136,0.04)',
                      border: '1px solid rgba(136,255,136,0.12)',
                    }}
                  >
                    <p className="mono font-bold text-xs" style={{ color: 'var(--aluminum)' }}>
                      {s.label}
                    </p>
                    <p className="mono text-xs mt-0.5" style={{ color: 'var(--aluminum-dim)' }}>
                      {s.stack}
                    </p>
                    <p className="mono text-xs mt-1" style={{ color: '#88FF88', opacity: 0.7 }}>
                      {s.installs} teams using this
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
