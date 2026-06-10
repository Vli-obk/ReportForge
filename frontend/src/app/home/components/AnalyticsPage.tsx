'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { pdfAPI, datasetAPI, aiAPI, financialReportsAPI } from '@/lib/api';
import {
  BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  TrendingUp, Database, FileText, Activity, Brain,
  CheckCircle, XCircle, DollarSign, Target, BarChart2, Layers, RefreshCw,
} from 'lucide-react';
import type { FinancialReport, PDFDocument, Dataset, Statistics } from '@/lib/api-types';

// ─── helpers ────────────────────────────────────────────────────────────────

const fmt = (n: number | null | undefined): string => {
  if (n == null) return 'N/A';
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${(n / 1e12).toFixed(1)}T`;
  if (abs >= 1e9)  return `${(n / 1e9).toFixed(1)}B`;
  if (abs >= 1e6)  return `${(n / 1e6).toFixed(1)}M`;
  if (abs >= 1e3)  return `${(n / 1e3).toFixed(1)}K`;
  return n.toFixed(0);
};

const CARD_BG   = 'rgba(26, 26, 46, 0.6)';
const CARD_BR   = '1px solid rgba(74, 74, 90, 0.4)';
const GRID_CLR  = 'rgba(74, 74, 90, 0.25)';
const TIP_STYLE = {
  background: 'rgba(15, 15, 27, 0.95)',
  border: '1px solid rgba(74, 74, 90, 0.5)',
  borderRadius: '8px',
  color: '#D0D0D8',
  fontFamily: 'JetBrains Mono, monospace',
  fontSize: '12px',
};
const AXIS_STYLE = { fontFamily: 'JetBrains Mono, monospace', fontSize: '11px' };
const ORANGE = '#FF6B2B';
const STEEL  = '#4A4A5A';
const TEAL   = '#2BB5A0';
const RED    = '#E05C5C';
const PIE_COLORS = [ORANGE, RED, '#8A8A9A', TEAL];

// ─── sub-components ─────────────────────────────────────────────────────────

function KpiCard({
  icon: Icon, label, value, sub, color = ORANGE,
}: {
  icon: React.ElementType; label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <div className="rounded-xl p-5 flex flex-col gap-3" style={{ background: CARD_BG, border: CARD_BR }}>
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-widest" style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace' }}>
          {label}
        </span>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: `${color}18` }}>
          <Icon size={16} style={{ color }} />
        </div>
      </div>
      <div>
        <div className="text-3xl font-bold" style={{ color: '#D0D0D8', fontFamily: 'Manrope, sans-serif' }}>
          {value}
        </div>
        {sub && (
          <div className="text-xs mt-1" style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace' }}>
            {sub}
          </div>
        )}
      </div>
    </div>
  );
}

function SectionHeader({ icon: Icon, title, sub }: { icon: React.ElementType; title: string; sub?: string }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${ORANGE}18` }}>
        <Icon size={18} style={{ color: ORANGE }} />
      </div>
      <div>
        <h2 className="text-base font-bold" style={{ color: '#D0D0D8', fontFamily: 'Manrope, sans-serif' }}>
          {title}
        </h2>
        {sub && <p className="text-xs" style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace' }}>{sub}</p>}
      </div>
    </div>
  );
}

function EmptyChart({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center h-48" style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
      {message}
    </div>
  );
}

// ─── main component ──────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [stats,            setStats]            = useState<Statistics | null>(null);
  const [datasets,         setDatasets]         = useState<Dataset[]>([]);
  const [documents,        setDocuments]        = useState<PDFDocument[]>([]);
  const [financialReports, setFinancialReports] = useState<FinancialReport[]>([]);
  // Each section has its own loading flag so the page renders immediately
  const [statsLoading,  setStatsLoading]  = useState(true);
  const [docsLoading,   setDocsLoading]   = useState(true);
  const [frLoading,     setFrLoading]     = useState(true);
  const [refreshing,    setRefreshing]    = useState(false);

  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [aiAnalytics,   setAiAnalytics]   = useState<any | null>(null);
  const [aiLoading,     setAiLoading]     = useState(false);

  const load = useCallback((silent = false) => {
    if (silent) setRefreshing(true);

    // Fire all requests independently — each section shows as soon as its data arrives
    pdfAPI.getStatistics()
      .then(r => setStats(r.data))
      .catch(err => console.error('stats error:', err))
      .finally(() => setStatsLoading(false));

    Promise.all([pdfAPI.getAll(), datasetAPI.getAll()])
      .then(([docs, ds]) => { setDocuments(docs.data); setDatasets(ds.data); })
      .catch(err => console.error('docs/datasets error:', err))
      .finally(() => setDocsLoading(false));

    financialReportsAPI.getAll()
      .then(r => setFinancialReports(r.data))
      .catch(err => console.error('financial reports error:', err))
      .finally(() => { setFrLoading(false); if (silent) setRefreshing(false); });
  }, []);

  useEffect(() => { load(); }, [load]);

  // Auto-refresh every 30s so stats stay current after background processing
  useEffect(() => {
    const id = setInterval(() => load(true), 30000);
    return () => clearInterval(id);
  }, [load]);

  const handleDocSelect = async (docId: number) => {
    setSelectedDocId(docId);
    setAiLoading(true);
    setAiAnalytics(null);
    try {
      const res = await aiAPI.getAnalytics(docId);
      setAiAnalytics(res.data);
    } catch { /* ignored */ }
    finally { setAiLoading(false); }
  };

  // ── computed chart data ───────────────────────────────────────────────────

  const statusData = useMemo(() => {
    const completed  = documents.filter(d => d.status === 'completed').length;
    const failed     = documents.filter(d => d.status === 'failed').length;
    const processing = documents.filter(d => d.status === 'processing' || d.status === 'pending').length;
    return [
      { name: 'Completed',  value: completed  },
      { name: 'Failed',     value: failed     },
      { name: 'Processing', value: processing },
    ].filter(d => d.value > 0);
  }, [documents]);

  const activityData = useMemo(() => {
    const byDate: Record<string, number> = {};
    documents.forEach(doc => {
      const date = doc.created_at?.split('T')[0];
      if (date) byDate[date] = (byDate[date] || 0) + 1;
    });
    return Object.entries(byDate)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-20)
      .map(([date, count]) => ({ date: date.slice(5), uploads: count }));
  }, [documents]);

  const revenueData = useMemo(() => {
    const byCompany: Record<string, number> = {};
    financialReports.forEach(r => {
      if (r.company_name && r.revenue != null) {
        if (!byCompany[r.company_name] || r.revenue > byCompany[r.company_name])
          byCompany[r.company_name] = r.revenue;
      }
    });
    return Object.entries(byCompany)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 8)
      .map(([name, revenue]) => ({
        name: name.length > 22 ? name.slice(0, 20) + '…' : name,
        revenue: +(revenue / 1e9).toFixed(2),
      }));
  }, [financialReports]);

  const coverageData = useMemo(() => {
    if (!financialReports.length) return [];
    const total = financialReports.length;
    const fields: { key: keyof FinancialReport; label: string }[] = [
      { key: 'revenue',            label: 'Revenue'       },
      { key: 'net_income',         label: 'Net Income'    },
      { key: 'total_assets',       label: 'Total Assets'  },
      { key: 'total_liabilities',  label: 'Liabilities'   },
      { key: 'gross_profit',       label: 'Gross Profit'  },
      { key: 'ebitda',             label: 'EBITDA'        },
      { key: 'operating_cash_flow',label: 'Op. Cash Flow' },
      { key: 'shareholders_equity',label: 'Equity'        },
    ];
    return fields
      .map(({ key, label }) => ({
        name: label,
        pct: Math.round(financialReports.filter(r => r[key] != null).length / total * 100),
      }))
      .sort((a, b) => b.pct - a.pct);
  }, [financialReports]);

  const datasetData = useMemo(() =>
    datasets
      .filter(d => (d.row_count || 0) > 0)
      .sort((a, b) => (b.row_count || 0) - (a.row_count || 0))
      .slice(0, 10)
      .map(d => ({
        name: d.name.length > 18 ? d.name.slice(0, 16) + '…' : d.name,
        rows: d.row_count || 0,
      })),
  [datasets]);

  const completedFR      = financialReports.filter(r => r.processing_status === 'completed');
  const avgConfidence    = completedFR.length
    ? Math.round(completedFR.reduce((s, r) => s + r.confidence_score, 0) / completedFR.length * 100)
    : null;
  const successRate = documents.length
    ? Math.round(documents.filter(d => d.status === 'completed').length / documents.length * 100)
    : null;

  const initialLoading = statsLoading && docsLoading;

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-8">

      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold" style={{ color: '#D0D0D8', fontFamily: 'Manrope, sans-serif' }}>
            Analyses
          </h1>
          <p className="text-sm mt-1" style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace' }}>
            Performance de traitement et aperçu des données financières extraites
          </p>
        </div>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="btn-secondary py-2 px-3 text-sm flex items-center gap-2 mt-1 disabled:opacity-50"
          title="Actualiser les statistiques"
        >
          <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
          Actualiser
        </button>
      </div>

      {/* ── KPI cards ── */}
      {initialLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-xl h-28 animate-pulse" style={{ background: 'rgba(74,74,90,0.2)' }} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard icon={FileText}    label="Documents"          value={stats?.total_pdfs ?? 0} sub="total téléchargé" />
          <KpiCard icon={Database}    label="Datasets"           value={datasets.length} sub={`${fmt(stats?.total_rows ?? 0)} lignes extraites`} color={TEAL} />
          <KpiCard icon={CheckCircle} label="Taux de Réussite"   value={successRate != null ? `${successRate}%` : '—'} sub="terminés / total" color="#8A8A9A" />
          <KpiCard icon={Target}      label="Rapports Financiers" value={frLoading ? '…' : financialReports.length}
            sub={avgConfidence != null ? `confiance moy. ${avgConfidence}%` : 'traités'} color={ORANGE} />
        </div>
      )}

      {/* ── Processing Status + Upload Activity ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Donut — processing status */}
        <div className="rounded-xl p-6" style={{ background: CARD_BG, border: CARD_BR }}>
          <SectionHeader icon={Activity} title="Statut de Traitement" sub="répartition de tous les documents" />
          {statusData.length === 0 ? (
            <EmptyChart message="Aucun document pour l'instant" />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={statusData} cx="50%" cy="50%" innerRadius={60} outerRadius={95}
                  paddingAngle={3} dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  labelLine={false}
                >
                  {statusData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={TIP_STYLE} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Area — upload activity */}
        <div className="rounded-xl p-6" style={{ background: CARD_BG, border: CARD_BR }}>
          <SectionHeader icon={TrendingUp} title="Activité de Téléchargement" sub="documents au fil du temps" />
          {activityData.length === 0 ? (
            <EmptyChart message="Aucun historique de téléchargement" />
          ) : (
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={activityData} margin={{ top: 4, right: 4, bottom: 0, left: -10 }}>
                <defs>
                  <linearGradient id="uploadGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor={ORANGE} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={ORANGE} stopOpacity={0}   />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID_CLR} />
                <XAxis dataKey="date" tick={{ ...AXIS_STYLE, fill: '#8A8A9A' }} />
                <YAxis allowDecimals={false} tick={{ ...AXIS_STYLE, fill: '#8A8A9A' }} />
                <Tooltip contentStyle={TIP_STYLE} />
                <Area type="monotone" dataKey="uploads" stroke={ORANGE} strokeWidth={2}
                  fill="url(#uploadGrad)" dot={{ fill: ORANGE, r: 3 }} name="Uploads" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ── Financial Reports section ── */}
      {frLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="rounded-xl h-72 animate-pulse" style={{ background: 'rgba(74,74,90,0.2)' }} />
          ))}
        </div>
      ) : financialReports.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Bar — revenue by company */}
          <div className="rounded-xl p-6" style={{ background: CARD_BG, border: CARD_BR }}>
            <SectionHeader icon={DollarSign} title="Revenus par Entreprise" sub="valeur la plus élevée rapportée (en milliards)" />
            {revenueData.length === 0 ? (
              <EmptyChart message="Aucune donnée de revenus extraite" />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={revenueData} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_CLR} horizontal={false} />
                  <XAxis type="number" tick={{ ...AXIS_STYLE, fill: '#8A8A9A' }}
                    tickFormatter={v => `$${v}B`} />
                  <YAxis type="category" dataKey="name" width={110}
                    tick={{ ...AXIS_STYLE, fill: '#D0D0D8' }} />
                  <Tooltip contentStyle={TIP_STYLE}
                    formatter={(v: number) => [`$${v}B`, 'Revenue']} />
                  <Bar dataKey="revenue" fill={ORANGE} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Bar — metric coverage */}
          <div className="rounded-xl p-6" style={{ background: CARD_BG, border: CARD_BR }}>
            <SectionHeader icon={BarChart2} title="Couverture d'Extraction"
              sub={`% des ${financialReports.length} rapport${financialReports.length > 1 ? 's' : ''} avec chaque métrique`} />
            {coverageData.length === 0 ? (
              <EmptyChart message="Aucune donnée de couverture" />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={coverageData} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID_CLR} horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} tick={{ ...AXIS_STYLE, fill: '#8A8A9A' }}
                    tickFormatter={v => `${v}%`} />
                  <YAxis type="category" dataKey="name" width={90}
                    tick={{ ...AXIS_STYLE, fill: '#D0D0D8' }} />
                  <Tooltip contentStyle={TIP_STYLE}
                    formatter={(v: number) => [`${v}%`, 'Coverage']} />
                  <Bar dataKey="pct" radius={[0, 4, 4, 0]}
                    fill={TEAL}
                    background={{ fill: 'rgba(255,255,255,0.03)', radius: 4 }} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Financial reports stats row */}
          <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Terminés', value: completedFR.length, icon: CheckCircle, color: TEAL },
              { label: 'Échoués',    value: financialReports.filter(r => r.processing_status === 'failed').length, icon: XCircle, color: RED },
              { label: 'Avec Revenus', value: financialReports.filter(r => r.revenue != null).length, icon: DollarSign, color: ORANGE },
              { label: 'Confiance Moy.', value: avgConfidence != null ? `${avgConfidence}%` : '—', icon: Target, color: '#8A8A9A' },
            ].map(({ label, value, icon: Icon, color }) => (
              <div key={label} className="rounded-xl p-4 flex items-center gap-3" style={{ background: CARD_BG, border: CARD_BR }}>
                <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0" style={{ background: `${color}18` }}>
                  <Icon size={16} style={{ color }} />
                </div>
                <div>
                  <div className="text-xl font-bold" style={{ color: '#D0D0D8', fontFamily: 'Manrope, sans-serif' }}>{value}</div>
                  <div className="text-xs" style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace' }}>{label}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Dataset sizes ── */}
      <div className="rounded-xl p-6" style={{ background: CARD_BG, border: CARD_BR }}>
        <SectionHeader icon={Layers} title="Principaux Datasets par Taille" sub="nombre de lignes par dataset extrait" />
        {datasetData.length === 0 ? (
          <EmptyChart message="Aucun dataset généré" />
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={datasetData} margin={{ top: 4, right: 8, bottom: 40, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_CLR} />
              <XAxis dataKey="name" tick={{ ...AXIS_STYLE, fill: '#D0D0D8' }} angle={-30} textAnchor="end" interval={0} />
              <YAxis tick={{ ...AXIS_STYLE, fill: '#8A8A9A' }} />
              <Tooltip contentStyle={TIP_STYLE} formatter={(v: number) => [v.toLocaleString(), 'Rows']} />
              <Bar dataKey="rows" fill={ORANGE} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── AI Insights ── */}
      <div className="rounded-xl p-6" style={{ background: CARD_BG, border: CARD_BR }}>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <SectionHeader icon={Brain} title="Insights IA sur les Rapports" sub="sélectionnez un document terminé" />
          <select
            value={selectedDocId || ''}
            onChange={e => handleDocSelect(Number(e.target.value))}
            className="rounded-lg px-4 py-2 text-sm min-w-[240px] appearance-none cursor-pointer"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(74,74,90,0.4)',
              color: '#D0D0D8',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '13px',
            }}
          >
            <option value="" disabled style={{ background: '#0F0F1B' }}>
              Sélectionner un rapport...
            </option>
            {documents.filter(d => d.status === 'completed').map(doc => (
              <option key={doc.id} value={doc.id} style={{ background: '#0F0F1B' }}>
                {doc.original_filename}
              </option>
            ))}
          </select>
        </div>

        {aiLoading ? (
          <div className="flex flex-col items-center gap-3 py-14">
            <div className="w-7 h-7 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: `${ORANGE} transparent transparent transparent` }} />
            <p style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
              récupération des insights...
            </p>
          </div>
        ) : aiAnalytics ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-widest font-bold" style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace' }}>
                KPIs
              </p>
              {Object.entries(aiAnalytics.kpis || {}).length === 0 ? (
                <p style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>Aucun KPI trouvé.</p>
              ) : (
                Object.entries(aiAnalytics.kpis || {}).map(([key, val]: any, i) => (
                  <div key={i} className="rounded-lg p-3" style={{ background: `${ORANGE}08`, border: `1px solid ${ORANGE}20` }}>
                    <div className="text-[10px] uppercase tracking-wider font-bold mb-1" style={{ color: ORANGE, fontFamily: 'JetBrains Mono, monospace' }}>{key}</div>
                    <div className="text-base font-bold" style={{ color: '#D0D0D8' }}>{String(val)}</div>
                  </div>
                ))
              )}
            </div>
            <div className="md:col-span-2 space-y-3">
              <p className="text-xs uppercase tracking-widest font-bold" style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace' }}>
                Insights Stratégiques
              </p>
              {(aiAnalytics.insights || []).length === 0 ? (
                <p style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>Aucun insight généré.</p>
              ) : (
                (aiAnalytics.insights || []).map((insight: string, i: number) => (
                  <div key={i} className="flex items-start gap-3 rounded-lg p-4" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(74,74,90,0.2)' }}>
                    <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5"
                      style={{ background: `${ORANGE}20`, color: ORANGE }}>
                      {i + 1}
                    </div>
                    <p className="text-sm leading-relaxed" style={{ color: '#D0D0D8' }}>{insight}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-14 gap-3">
            <Brain size={40} style={{ color: '#4A4A5A' }} />
            <p style={{ color: '#8A8A9A', fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' }}>
              Sélectionnez un rapport terminé ci-dessus pour charger les insights IA
            </p>
          </div>
        )}
      </div>

    </div>
  );
}
