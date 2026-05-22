'use client';

import { useState, useEffect } from 'react';
import { pipelineAPI } from '@/lib/api';
import { usePipelineStream } from '@/hooks/usePipelineStream';
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  Server,
  Database as DBIcon,
} from 'lucide-react';
import { formatDateTime } from '@/lib/utils';

interface ProcessingJob {
  id: number;
  job_type: string;
  status: string;
  progress: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

interface PipelineHealth {
  status: string;
  services: {
    pdf_scraper: string;
    ocr: string;
    database: string;
    transformer: string;
  };
}

export default function PipelinePage() {
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [health, setHealth] = useState<PipelineHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { jobs: streamedJobs, connected } = usePipelineStream();

  const fetchData = async () => {
    try {
      const [jobsResponse, healthResponse] = await Promise.all([
        pipelineAPI.getJobs(),
        pipelineAPI.getHealth(),
      ]);
      setJobs(jobsResponse.data);
      setHealth(healthResponse.data);
    } catch (error) {
      console.error('Failed to fetch pipeline data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const getStatusIcon = (status: string, justCompleted: boolean = false) => {
    switch (status) {
      case 'completed':
      case 'done':
        return <CheckCircle size={16} style={{ color: justCompleted ? '#69F0AE' : '#4CAF50' }} />;
      case 'failed':
        return <XCircle size={16} style={{ color: '#FF6B6B' }} />;
      case 'running':
      case 'processing':
        return <RefreshCw size={16} className="animate-spin" style={{ color: 'var(--orange)' }} />;
      default:
        return <Clock size={16} style={{ color: 'var(--aluminum-dim)' }} />;
    }
  };

  const getStatusColor = (status: string, justCompleted: boolean = false) => {
    switch (status) {
      case 'completed':
      case 'done':
        return justCompleted ? '#69F0AE' : '#4CAF50';
      case 'failed':
        return '#FF6B6B';
      case 'running':
      case 'processing':
        return 'var(--orange)';
      default:
        return 'var(--aluminum-dim)';
    }
  };

  const getServiceIcon = (service: string) => {
    switch (service) {
      case 'pdf_scraper':
        return <Activity size={20} />;
      case 'ocr':
        return <RefreshCw size={20} />;
      case 'database':
        return <DBIcon size={20} />;
      case 'transformer':
        return <Server size={20} />;
      default:
        return <Activity size={20} />;
    }
  };

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1
            className="text-4xl font-bold"
            style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
          >
            Pipeline
          </h1>
          <p
            className="text-sm mt-2"
            style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
          >
            Monitor processing jobs and pipeline health
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn-secondary py-2 px-4 flex items-center gap-2 disabled:opacity-50"
        >
          <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{
              backgroundColor: connected ? '#4CAF50' : '#FF6B6B',
              animation: connected ? 'pulse 2s infinite' : 'none',
            }}
          />
          <span
            className="text-xs"
            style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
          >
            {connected ? 'Live' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Pipeline Health */}
      {health && (
        <div
          className="rounded-lg p-6 mb-6"
          style={{
            background: 'rgba(26, 26, 46, 0.5)',
            border: '1px solid rgba(74, 74, 90, 0.4)',
          }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Activity size={24} style={{ color: 'var(--orange)' }} />
            <h2
              className="text-xl font-bold"
              style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
            >
              Pipeline Health
            </h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(health.services).map(([service, status]) => (
              <div
                key={service}
                className="rounded-lg p-4 flex items-center gap-3"
                style={{
                  background:
                    status === 'operational'
                      ? 'rgba(76, 175, 80, 0.1)'
                      : 'rgba(255, 107, 107, 0.1)',
                  border: `1px solid ${status === 'operational' ? 'rgba(76, 175, 80, 0.3)' : 'rgba(255, 107, 107, 0.3)'}`,
                }}
              >
                <div style={{ color: status === 'operational' ? '#4CAF50' : '#FF6B6B' }}>
                  {getServiceIcon(service)}
                </div>
                <div>
                  <p
                    className="text-xs uppercase tracking-wider mb-1"
                    style={{
                      color: 'var(--aluminum-dim)',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    {service.replace('_', ' ')}
                  </p>
                  <p
                    className="text-sm font-semibold"
                    style={{
                      color: status === 'operational' ? '#4CAF50' : '#FF6B6B',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    {status}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Processing Jobs */}
      <div
        className="rounded-lg"
        style={{
          background: 'rgba(26, 26, 46, 0.5)',
          border: '1px solid rgba(74, 74, 90, 0.4)',
        }}
      >
        <div className="p-6 border-b" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
          <h2
            className="text-xl font-bold"
            style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
          >
            Processing Jobs
          </h2>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <p style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
              Loading jobs...
            </p>
          </div>
        ) : streamedJobs.size === 0 ? (
          <div className="p-8 text-center">
            <p style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
              No processing jobs found
            </p>
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
            {Array.from(streamedJobs.entries()).map(([jobId, job]) => (
              <div 
                key={jobId} 
                className={`p-6 hover:bg-white/5 transition-colors ${job.justCompleted ? 'animate-flash-green' : ''}`}
                style={{
                  animation: job.justCompleted ? 'flashGreen 2s ease-out' : 'none',
                }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div
                      className="p-2 rounded-lg"
                      style={{ background: `${getStatusColor(job.status, job.justCompleted)}15` }}
                    >
                      {getStatusIcon(job.status, job.justCompleted)}
                    </div>
                    <div>
                      <h3
                        className="font-semibold mb-1"
                        style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
                      >
                        {job.filename}
                      </h3>
                      <p
                        className="text-xs"
                        style={{
                          color: 'var(--aluminum-dim)',
                          fontFamily: 'JetBrains Mono, monospace',
                        }}
                      >
                        Job ID: {jobId}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p
                      className="text-sm font-semibold mb-1"
                      style={{
                        color: getStatusColor(job.status, job.justCompleted),
                        fontFamily: 'JetBrains Mono, monospace',
                      }}
                    >
                      {job.status.toUpperCase()}
                    </p>
                  </div>
                </div>

                {/* Progress Bar */}
                {(job.status === 'running' || job.status === 'processing') && (
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <span
                        className="text-xs"
                        style={{
                          color: 'var(--aluminum-dim)',
                          fontFamily: 'JetBrains Mono, monospace',
                        }}
                      >
                        Progress
                      </span>
                      <span
                        className="text-xs font-semibold"
                        style={{ color: 'var(--orange)', fontFamily: 'JetBrains Mono, monospace' }}
                      >
                        {job.progress}%
                      </span>
                    </div>
                    <div
                      className="w-full h-2 rounded-full overflow-hidden"
                      style={{ background: 'rgba(74, 74, 90, 0.4)' }}
                    >
                      <div
                        className="h-full transition-all duration-300"
                        style={{
                          width: `${job.progress}%`,
                          background: 'var(--orange)',
                        }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
