'use client';

import { useEffect, useState } from 'react';
import { pdfAPI } from '@/lib/api';
import { formatBytes } from '@/lib/utils';
import { FileText, Database, ScanText, AlertCircle, HardDrive } from 'lucide-react';

interface Statistics {
  total_pdfs: number;
  total_rows: number;
  ocr_processed: number;
  failed_jobs: number;
  storage_used: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await pdfAPI.getStatistics();
        setStats(response.data);
      } catch (error) {
        console.error('Failed to fetch statistics:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  const statCards = [
    {
      title: 'Total PDFs',
      value: stats?.total_pdfs || 0,
      icon: FileText,
      color: 'var(--orange)',
    },
    {
      title: 'Extracted Rows',
      value: stats?.total_rows || 0,
      icon: Database,
      color: 'var(--orange)',
    },
    {
      title: 'OCR Processed',
      value: stats?.ocr_processed || 0,
      icon: ScanText,
      color: 'var(--orange)',
    },
    {
      title: 'Failed Jobs',
      value: stats?.failed_jobs || 0,
      icon: AlertCircle,
      color: '#FF6B6B',
    },
    {
      title: 'Storage Used',
      value: formatBytes(stats?.storage_used || 0),
      icon: HardDrive,
      color: 'var(--orange)',
    },
  ];

  return (
    <div>
      <div className="mb-8">
        <h1
          className="text-4xl font-bold"
          style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
        >
          Dashboard
        </h1>
        <p
          className="text-sm mt-2"
          style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
        >
          Welcome to your PDF Analytics dashboard
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
            Loading statistics...
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {statCards.map((card, index) => {
            const Icon = card.icon;
            return (
              <div
                key={index}
                className="rounded-lg p-6"
                style={{
                  background: 'rgba(26, 26, 46, 0.5)',
                  border: '1px solid rgba(74, 74, 90, 0.4)',
                  transition: 'all 0.3s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = card.color;
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(74, 74, 90, 0.4)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <div className="flex items-center justify-between mb-4">
                  <div
                    className="p-3 rounded-lg"
                    style={{
                      background: `${card.color}15`,
                    }}
                  >
                    <Icon size={24} style={{ color: card.color }} />
                  </div>
                  <span
                    className="text-3xl font-bold"
                    style={{
                      color: 'var(--aluminum)',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    {card.value}
                  </span>
                </div>
                <p
                  className="text-sm uppercase tracking-wider"
                  style={{
                    color: 'var(--aluminum-dim)',
                    fontFamily: 'JetBrains Mono, monospace',
                  }}
                >
                  {card.title}
                </p>
              </div>
            );
          })}
        </div>
      )}

      <div
        className="mt-8 rounded-lg p-8"
        style={{
          background: 'rgba(26, 26, 46, 0.5)',
          border: '1px solid rgba(74, 74, 90, 0.4)',
        }}
      >
        <h2
          className="text-xl font-bold mb-4"
          style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
        >
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            className="btn-primary py-3 px-6 text-sm"
            onClick={() => (window.location.href = '/home/uploads')}
          >
            Upload PDF
          </button>
          <button
            className="btn-secondary py-3 px-6 text-sm"
            onClick={() => (window.location.href = '/home/datasets')}
          >
            View Datasets
          </button>
          <button
            className="btn-secondary py-3 px-6 text-sm"
            onClick={() => (window.location.href = '/home/analytics')}
          >
            View Analytics
          </button>
        </div>
      </div>
    </div>
  );
}
