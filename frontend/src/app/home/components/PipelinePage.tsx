'use client';

import { useMemo, useState } from 'react';
import { Activity, CheckCircle, XCircle, Clock, RefreshCw, Server, Database as DBIcon } from 'lucide-react';
import { pipelineAPI } from '@/lib/api';
import { usePipelineStream } from '@/hooks/usePipelineStream';
import { useApiQuery } from '@/hooks/useApiQuery';
import type { ProcessingJob } from '@/lib/api-types';
import { formatDateTime } from '@/lib/utils';
import { JobMonitoringPanel } from './EndpointWidgets';

export default function PipelinePage() {
  const { data: jobsData, loading, error, refetch } = useApiQuery('pipeline-jobs', (signal) => pipelineAPI.getJobs(0, 100, signal), { pollMs: 30000, retries: 1 });
  const jobs = jobsData ?? [];
  const { data: health } = useApiQuery('pipeline-health', pipelineAPI.getHealth, { pollMs: 30000 });
  const { jobs: streamedJobs, connected } = usePipelineStream();
  const [refreshing, setRefreshing] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);

  const visibleJobs = useMemo(() => {
    const stream = Array.from(streamedJobs.entries()).map(([id, job]) => ({
      id: Number(id),
      user_id: 0,
      pdf_document_id: null,
      job_type: job.filename || 'streamed processing',
      status: job.status,
      progress: job.progress,
      result: null,
      error_message: null,
      started_at: null,
      completed_at: null,
      created_at: new Date().toISOString(),
    }));
    const ids = new Set(stream.map((job) => job.id));
    return [...stream, ...jobs.filter((job) => !ids.has(job.id))];
  }, [jobs, streamedJobs]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  };

  return (
    <div>
      <div className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold" style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}>Pipeline</h1>
          <p className="text-sm mt-2" style={mono}>Surveillez les tâches de traitement et la santé du pipeline</p>
        </div>
        <div className="flex items-center gap-4">
          <button onClick={handleRefresh} disabled={refreshing} className="btn-secondary py-2 px-4 flex items-center gap-2 disabled:opacity-50">
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
            Actualiser
          </button>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: connected ? '#4CAF50' : '#FF6B6B', animation: connected ? 'pulse 2s infinite' : 'none' }} />
            <span className="text-xs" style={mono}>{connected ? 'En Direct' : 'Déconnecté'}</span>
          </div>
        </div>
      </div>

      {health && (
        <div className="rounded-lg p-6 mb-6" style={panelStyle}>
          <div className="flex items-center gap-2 mb-4">
            <Activity size={24} style={{ color: 'var(--orange)' }} />
            <h2 className="text-xl font-bold" style={{ color: 'var(--aluminum)' }}>Santé du Pipeline</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(health.services).map(([service, status]) => <ServiceCard key={service} service={service} status={status} />)}
          </div>
        </div>
      )}

      <JobMonitoringPanel selectedJobId={selectedJobId} />

      <div className="rounded-lg" style={panelStyle}>
        <div className="p-6 border-b" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
          <h2 className="text-xl font-bold" style={{ color: 'var(--aluminum)' }}>Tâches de Traitement</h2>
        </div>
        {loading ? <Empty text="Chargement des tâches..." /> : error ? <Empty text={error} error /> : visibleJobs.length === 0 ? <Empty text="Aucune tâche de traitement trouvée" /> : (
          <div className="divide-y" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
            {visibleJobs.map((job) => <JobRow key={job.id} job={job} selected={selectedJobId === job.id} onClick={() => setSelectedJobId(job.id)} />)}
          </div>
        )}
      </div>
    </div>
  );
}

const panelStyle = { background: 'rgba(26, 26, 46, 0.5)', border: '1px solid rgba(74, 74, 90, 0.4)' };
const mono = { color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' };

function Empty({ text, error = false }: { text: string; error?: boolean }) {
  return <div className="p-8 text-center"><p style={{ ...mono, color: error ? '#FF6B6B' : mono.color }}>{text}</p></div>;
}

function ServiceCard({ service, status }: { service: string; status: string }) {
  const operational = status === 'operational';
  return (
    <div className="rounded-lg p-4 flex items-center gap-3" style={{ background: operational ? 'rgba(76, 175, 80, 0.1)' : 'rgba(255, 107, 107, 0.1)', border: `1px solid ${operational ? 'rgba(76, 175, 80, 0.3)' : 'rgba(255, 107, 107, 0.3)'}` }}>
      <div style={{ color: operational ? '#4CAF50' : '#FF6B6B' }}>{service === 'database' ? <DBIcon size={20} /> : service === 'transformer' ? <Server size={20} /> : <Activity size={20} />}</div>
      <div>
        <p className="text-xs uppercase tracking-wider mb-1" style={mono}>{service.replace('_', ' ')}</p>
        <p className="text-sm font-semibold" style={{ color: operational ? '#4CAF50' : '#FF6B6B', fontFamily: 'JetBrains Mono, monospace' }}>{status}</p>
      </div>
    </div>
  );
}

function JobRow({ job, selected, onClick }: { job: ProcessingJob; selected: boolean; onClick: () => void }) {
  return (
    <div onClick={onClick} className={`p-6 cursor-pointer hover:bg-white/5 transition-colors ${selected ? 'bg-orange/10' : ''}`}>
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg" style={{ background: `${statusColor(job.status)}15` }}>{statusIcon(job.status)}</div>
          <div>
            <h3 className="font-semibold mb-1" style={{ color: 'var(--aluminum)' }}>{job.job_type}</h3>
            <p className="text-xs" style={mono}>Job ID: {job.id} {job.pdf_document_id ? `| PDF #${job.pdf_document_id}` : ''}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-sm font-semibold mb-1" style={{ color: statusColor(job.status), fontFamily: 'JetBrains Mono, monospace' }}>{job.status.toUpperCase()}</p>
          <p className="text-xs" style={mono}>{formatDateTime(job.created_at)}</p>
        </div>
      </div>
      <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: 'rgba(74, 74, 90, 0.4)' }}>
        <div className="h-full transition-all duration-300" style={{ width: `${Math.max(0, Math.min(job.progress, 100))}%`, background: statusColor(job.status) }} />
      </div>
      {job.error_message && <p className="text-xs mt-3" style={{ color: '#FF6B6B', fontFamily: 'JetBrains Mono, monospace' }}>{job.error_message}</p>}
    </div>
  );
}

function statusColor(status: string) {
  if (status === 'completed' || status === 'done') return '#4CAF50';
  if (status === 'failed') return '#FF6B6B';
  if (status === 'running' || status === 'processing') return 'var(--orange)';
  return 'var(--aluminum-dim)';
}

function statusIcon(status: string) {
  if (status === 'completed' || status === 'done') return <CheckCircle size={16} style={{ color: '#4CAF50' }} />;
  if (status === 'failed') return <XCircle size={16} style={{ color: '#FF6B6B' }} />;
  if (status === 'running' || status === 'processing') return <RefreshCw size={16} className="animate-spin" style={{ color: 'var(--orange)' }} />;
  return <Clock size={16} style={{ color: 'var(--aluminum-dim)' }} />;
}
