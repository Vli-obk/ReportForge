'use client';

import { useState, useEffect } from 'react';
import { pdfAPI, datasetAPI, aiAPI } from '@/lib/api';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { TrendingUp, Database, FileText, Activity, Brain, Tag } from 'lucide-react';

interface Statistics {
  total_pdfs: number;
  total_rows: number;
  ocr_processed: number;
  failed_jobs: number;
  storage_used: number;
}

export default function AnalyticsPage() {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // AI Insights States
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [aiAnalytics, setAiAnalytics] = useState<any | null>(null);
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsResponse, datasetsResponse, documentsResponse] = await Promise.all([
          pdfAPI.getStatistics(),
          datasetAPI.getAll(),
          pdfAPI.getAll(),
        ]);
        setStats(statsResponse.data);
        setDatasets(datasetsResponse.data);
        setDocuments(documentsResponse.data);
      } catch (error) {
        console.error('Failed to fetch analytics data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleDocSelect = async (docId: number) => {
    setSelectedDocId(docId);
    setAiLoading(true);
    setAiAnalytics(null);
    try {
      const res = await aiAPI.getAnalytics(docId);
      setAiAnalytics(res.data);
    } catch (error) {
      console.error('Failed to fetch AI report analytics:', error);
    } finally {
      setAiLoading(false);
    }
  };

  const COLORS = ['#FF6B2B', '#4A4A5A', '#D0D0D8', '#8A8A9A', '#1A1A2E'];

  const pieData = [
    { name: 'Completed', value: stats?.total_pdfs || 0 },
    { name: 'OCR Processed', value: stats?.ocr_processed || 0 },
    { name: 'Failed', value: stats?.failed_jobs || 0 },
  ];

  const barData = datasets.slice(0, 10).map((dataset) => ({
    name: dataset.name.substring(0, 15),
    rows: dataset.row_count,
  }));

  const lineData = datasets.slice(0, 5).map((dataset, idx) => ({
    name: `Doc ${idx + 1}`,
    pdfs: Math.max(0, Math.round((dataset.row_count || 0) / 50)),
    rows: dataset.row_count || 0,
  }));

  return (
    <div>
      <div className="mb-8">
        <h1
          className="text-4xl font-bold"
          style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
        >
          Analytics
        </h1>
        <p
          className="text-sm mt-2"
          style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
        >
          Visualize your PDF extraction data
        </p>
      </div>

      {loading ? (
        <div
          className="rounded-lg p-8"
          style={{
            background: 'rgba(26, 26, 46, 0.5)',
            border: '1px solid rgba(74, 74, 90, 0.4)',
          }}
        >
          <p style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
            Loading analytics...
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Processing Status Pie Chart */}
          <div
            className="rounded-lg p-6"
            style={{
              background: 'rgba(26, 26, 46, 0.5)',
              border: '1px solid rgba(74, 74, 90, 0.4)',
            }}
          >
            <div className="flex items-center gap-2 mb-6">
              <Activity size={24} style={{ color: 'var(--orange)' }} />
              <h2
                className="text-xl font-bold"
                style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
              >
                Processing Status
              </h2>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: 'rgba(26, 26, 46, 0.9)',
                    border: '1px solid rgba(74, 74, 90, 0.4)',
                    borderRadius: '8px',
                    color: 'var(--aluminum)',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Dataset Row Counts Bar Chart */}
          <div
            className="rounded-lg p-6"
            style={{
              background: 'rgba(26, 26, 46, 0.5)',
              border: '1px solid rgba(74, 74, 90, 0.4)',
            }}
          >
            <div className="flex items-center gap-2 mb-6">
              <Database size={24} style={{ color: 'var(--orange)' }} />
              <h2
                className="text-xl font-bold"
                style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
              >
                Dataset Row Counts
              </h2>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(74, 74, 90, 0.4)" />
                <XAxis
                  dataKey="name"
                  stroke="var(--aluminum-dim)"
                  style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}
                />
                <YAxis
                  stroke="var(--aluminum-dim)"
                  style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}
                />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(26, 26, 46, 0.9)',
                    border: '1px solid rgba(74, 74, 90, 0.4)',
                    borderRadius: '8px',
                    color: 'var(--aluminum)',
                  }}
                />
                <Bar dataKey="rows" fill="#FF6B2B" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Extraction Trends Line Chart */}
          <div
            className="rounded-lg p-6 lg:col-span-2"
            style={{
              background: 'rgba(26, 26, 46, 0.5)',
              border: '1px solid rgba(74, 74, 90, 0.4)',
            }}
          >
            <div className="flex items-center gap-2 mb-6">
              <TrendingUp size={24} style={{ color: 'var(--orange)' }} />
              <h2
                className="text-xl font-bold"
                style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
              >
                Extraction Trends
              </h2>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={lineData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(74, 74, 90, 0.4)" />
                <XAxis
                  dataKey="name"
                  stroke="var(--aluminum-dim)"
                  style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}
                />
                <YAxis
                  stroke="var(--aluminum-dim)"
                  style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}
                />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(26, 26, 46, 0.9)',
                    border: '1px solid rgba(74, 74, 90, 0.4)',
                    borderRadius: '8px',
                    color: 'var(--aluminum)',
                  }}
                />
                <Legend
                  wrapperStyle={{
                    color: 'var(--aluminum)',
                    fontFamily: 'JetBrains Mono, monospace',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="pdfs"
                  stroke="#FF6B2B"
                  strokeWidth={2}
                  dot={{ fill: '#FF6B2B', strokeWidth: 2, r: 4 }}
                  name="PDFs Processed"
                />
                <Line
                  type="monotone"
                  dataKey="rows"
                  stroke="#4A4A5A"
                  strokeWidth={2}
                  dot={{ fill: '#4A4A5A', strokeWidth: 2, r: 4 }}
                  name="Rows Extracted"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Summary Stats */}
          <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div
              className="rounded-lg p-4 text-center"
              style={{
                background: 'rgba(26, 26, 46, 0.5)',
                border: '1px solid rgba(74, 74, 90, 0.4)',
              }}
            >
              <div className="flex items-center justify-center gap-2 mb-2">
                <FileText size={20} style={{ color: 'var(--orange)' }} />
                <span
                  className="text-2xl font-bold"
                  style={{ color: 'var(--aluminum)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  {stats?.total_pdfs || 0}
                </span>
              </div>
              <p
                className="text-xs uppercase tracking-wider"
                style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
              >
                Total PDFs
              </p>
            </div>

            <div
              className="rounded-lg p-4 text-center"
              style={{
                background: 'rgba(26, 26, 46, 0.5)',
                border: '1px solid rgba(74, 74, 90, 0.4)',
              }}
            >
              <div className="flex items-center justify-center gap-2 mb-2">
                <Database size={20} style={{ color: 'var(--orange)' }} />
                <span
                  className="text-2xl font-bold"
                  style={{ color: 'var(--aluminum)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  {stats?.total_rows || 0}
                </span>
              </div>
              <p
                className="text-xs uppercase tracking-wider"
                style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
              >
                Total Rows
              </p>
            </div>

            <div
              className="rounded-lg p-4 text-center"
              style={{
                background: 'rgba(26, 26, 46, 0.5)',
                border: '1px solid rgba(74, 74, 90, 0.4)',
              }}
            >
              <div className="flex items-center justify-center gap-2 mb-2">
                <Activity size={20} style={{ color: 'var(--orange)' }} />
                <span
                  className="text-2xl font-bold"
                  style={{ color: 'var(--aluminum)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  {stats?.ocr_processed || 0}
                </span>
              </div>
              <p
                className="text-xs uppercase tracking-wider"
                style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
              >
                OCR Processed
              </p>
            </div>

            <div
              className="rounded-lg p-4 text-center"
              style={{
                background: 'rgba(26, 26, 46, 0.5)',
                border: '1px solid rgba(74, 74, 90, 0.4)',
              }}
            >
              <div className="flex items-center justify-center gap-2 mb-2">
                <TrendingUp size={20} style={{ color: 'var(--orange)' }} />
                <span
                  className="text-2xl font-bold"
                  style={{ color: 'var(--aluminum)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  {datasets.length}
                </span>
              </div>
              <p
                className="text-xs uppercase tracking-wider"
                style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
              >
                Datasets
              </p>
            </div>
          </div>

          {/* AI Insights Section */}
          <div
            className="rounded-lg p-6 lg:col-span-2 mt-2"
            style={{
              background: 'rgba(26, 26, 46, 0.5)',
              border: '1px solid rgba(74, 74, 90, 0.4)',
              fontFamily: 'Manrope, sans-serif',
            }}
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
              <div className="flex items-center gap-2">
                <Brain size={24} style={{ color: 'var(--orange)' }} />
                <h2 className="text-xl font-bold" style={{ color: 'var(--aluminum)' }}>
                  AI Report Analytics & Insights
                </h2>
              </div>

              {/* Dropdown Selector */}
              <div className="relative min-w-[260px]">
                <select
                  value={selectedDocId || ''}
                  onChange={(e) => handleDocSelect(Number(e.target.value))}
                  className="input-field w-full appearance-none pr-10 cursor-pointer rounded-lg px-4 py-2"
                  style={{
                    background: 'rgba(255, 255, 255, 0.04)',
                    border: '1px solid rgba(74, 74, 90, 0.3)',
                    color: 'var(--aluminum)',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '13px',
                  }}
                >
                  <option value="" disabled style={{ background: '#0F0F1B' }}>
                    Select Report to analyze...
                  </option>
                  {documents
                    .filter((doc: any) => doc.status === 'completed')
                    .map((doc) => (
                      <option key={doc.id} value={doc.id} style={{ background: '#0F0F1B' }}>
                        {doc.original_filename}
                      </option>
                    ))}
                </select>
              </div>
            </div>

            {aiLoading ? (
              <div className="flex flex-col items-center justify-center py-16 space-y-4">
                <div
                  className="animate-spin rounded-full h-8 w-8 border-b-2"
                  style={{ borderColor: 'var(--orange)' }}
                />
                <p
                  className="text-xs uppercase tracking-widest"
                  style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  retrieving business insights...
                </p>
              </div>
            ) : aiAnalytics ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* KPIs List */}
                <div className="md:col-span-1 space-y-4">
                  <h3
                    className="text-xs uppercase font-bold tracking-widest"
                    style={{
                      color: 'var(--aluminum-dim)',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    Extracted KPIs
                  </h3>
                  <div className="space-y-3">
                    {Object.entries(aiAnalytics.kpis || {}).map(([key, val]: any, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-lg flex flex-col justify-center transition-all"
                        style={{
                          background: 'rgba(255, 107, 43, 0.04)',
                          border: '1px solid rgba(255, 107, 43, 0.12)',
                        }}
                      >
                        <span
                          className="text-[10px] uppercase tracking-wider font-bold"
                          style={{
                            fontFamily: 'JetBrains Mono, monospace',
                            color: 'var(--orange)',
                          }}
                        >
                          {key}
                        </span>
                        <span
                          className="text-lg font-bold mt-1"
                          style={{ color: 'var(--aluminum)' }}
                        >
                          {val}
                        </span>
                      </div>
                    ))}
                    {Object.keys(aiAnalytics.kpis || {}).length === 0 && (
                      <p
                        className="text-sm"
                        style={{
                          color: 'var(--aluminum-dim)',
                          fontFamily: 'JetBrains Mono, monospace',
                        }}
                      >
                        No structured KPIs extracted.
                      </p>
                    )}
                  </div>
                </div>

                {/* Strategic Insights */}
                <div className="md:col-span-2 space-y-4">
                  <h3
                    className="text-xs uppercase font-bold tracking-widest"
                    style={{
                      color: 'var(--aluminum-dim)',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    Strategic Recommendations
                  </h3>
                  <div className="space-y-3">
                    {(aiAnalytics.insights || []).map((insight: string, idx: number) => (
                      <div
                        key={idx}
                        className="p-4 rounded-lg flex items-start gap-3 transition-all"
                        style={{
                          background: 'rgba(255, 255, 255, 0.015)',
                          border: '1px solid rgba(74, 74, 90, 0.15)',
                        }}
                      >
                        <div
                          className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5"
                          style={{ background: 'rgba(255, 107, 43, 0.15)', color: 'var(--orange)' }}
                        >
                          {idx + 1}
                        </div>
                        <p className="text-sm leading-relaxed" style={{ color: 'var(--aluminum)' }}>
                          {insight}
                        </p>
                      </div>
                    ))}
                    {(aiAnalytics.insights || []).length === 0 && (
                      <p
                        className="text-sm"
                        style={{
                          color: 'var(--aluminum-dim)',
                          fontFamily: 'JetBrains Mono, monospace',
                        }}
                      >
                        No insights generated for this report.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div
                className="rounded-lg p-12 text-center"
                style={{
                  background: 'rgba(255, 255, 255, 0.01)',
                  border: '1px solid rgba(74, 74, 90, 0.15)',
                }}
              >
                <Brain
                  size={48}
                  className="mx-auto mb-4 opacity-30"
                  style={{ color: 'var(--orange)' }}
                />
                <h3
                  className="text-lg font-bold mb-2"
                  style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
                >
                  Select a Report to View AI Insights
                </h3>
                <p
                  className="text-sm max-w-md mx-auto"
                  style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  Choose one of your completed reports from the dropdown selector to load fully
                  automated strategic business analytics and key performance metrics.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
