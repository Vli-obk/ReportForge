'use client';

import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  Activity,
  AlertCircle,
  Brain,
  CheckCircle,
  Clock,
  Cpu,
  RefreshCw,
  Server,
  Sparkles,
  X,
} from 'lucide-react';
import { aiAPI, datasetAPI, geminiAPI, pdfAPI, pipelineAPI, systemAPI } from '@/lib/api';
import type {
  DataRow,
  Dataset,
  GeminiExtractResponse,
  PDFDocument,
  ProcessingJob,
} from '@/lib/api-types';
import { formatBytes, formatDate, formatDateTime } from '@/lib/utils';
import { useApiQuery } from '@/hooks/useApiQuery';

const panelStyle = {
  background: 'rgba(26, 26, 46, 0.5)',
  border: '1px solid rgba(74, 74, 90, 0.4)',
};

const textMono = { color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' };

const badgeColor = (ok: boolean) => (ok ? '#4CAF50' : '#FF6B6B');

export function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-xs" style={{ ...textMono, color: badgeColor(ok) }}>
      <span className="h-2 w-2 rounded-full" style={{ background: badgeColor(ok) }} />
      {label}
    </span>
  );
}

export function SystemOverviewCard() {
  const { data, error, loading } = useApiQuery('system-overview', systemAPI.getOverview);
  const ok = !error && !!data;

  return (
    <div className="rounded-lg p-6" style={panelStyle}>
      <div className="flex items-center gap-2 mb-4">
        <Server size={22} style={{ color: 'var(--orange)' }} />
        <h2 className="text-xl font-bold" style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}>
          Vue d'Ensemble du Système
        </h2>
      </div>
      {loading ? (
        <p style={textMono}>Chargement des métadonnées système...</p>
      ) : error ? (
        <p style={{ ...textMono, color: '#FF6B6B' }}>{error}</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 text-sm">
          <p style={textMono}>Nom API</p>
          <p style={{ color: 'var(--aluminum)' }}>{data?.message}</p>
          <p style={textMono}>Version</p>
          <p style={{ color: 'var(--aluminum)' }}>{data?.version}</p>
          <p style={textMono}>Environnement</p>
          <p style={{ color: 'var(--aluminum)' }}>{data?.environment || 'Défaut backend'}</p>
          <p style={textMono}>Statut Serveur</p>
          <StatusBadge ok={ok} label={data?.status || 'online'} />
        </div>
      )}
    </div>
  );
}

export function HealthMonitoringWidget() {
  const { data, error, loading, responseTime, updatedAt } = useApiQuery(
    'system-health',
    systemAPI.getHealth,
    { retries: 0 }
  );
  const healthy = data?.status === 'healthy' && !error;
  const databaseStatus = data?.services?.database;

  return (
    <div className="rounded-lg p-6" style={panelStyle}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity size={22} style={{ color: 'var(--orange)' }} />
          <h2 className="text-xl font-bold" style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}>
            Surveillance de Santé
          </h2>
        </div>
        <StatusBadge ok={healthy} label={healthy ? 'en bonne santé' : 'indisponible'} />
      </div>
      {loading ? (
        <p style={textMono}>Vérification de la santé du backend...</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 text-sm">
          <p style={textMono}>Statut Backend</p>
          <StatusBadge ok={healthy} label={data?.status || error || 'hors ligne'} />
          <p style={textMono}>Statut Base de Données</p>
          <StatusBadge ok={databaseStatus === 'operational'} label={databaseStatus || (healthy ? 'opérationnel' : 'inconnu')} />
          <p style={textMono}>Disponibilité API</p>
          <StatusBadge ok={healthy} label={healthy ? 'disponible' : 'indisponible'} />
          <p style={textMono}>Temps de Réponse</p>
          <p style={{ color: 'var(--aluminum)' }}>{responseTime ?? '-'} ms</p>
          <p style={textMono}>Dernière Vérification</p>
          <p style={{ color: 'var(--aluminum)' }}>{updatedAt ? updatedAt.toLocaleTimeString() : '-'}</p>
        </div>
      )}
    </div>
  );
}

export function AIEngineStatusCard() {
  const { data, error, loading, updatedAt, refetch } = useApiQuery('gemini-health', geminiAPI.getHealth, {
    retries: 1,
  });
  const online = data?.available === true || data?.success === true || data?.status === 'online';

  return (
    <div className="rounded-lg p-6" style={panelStyle}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Cpu size={22} style={{ color: 'var(--orange)' }} />
          <h2 className="text-xl font-bold" style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}>
            Moteur IA
          </h2>
        </div>
        <button onClick={refetch} className="btn-secondary py-1 px-3 text-xs flex items-center gap-2">
          <RefreshCw size={14} />
          Reconnecter
        </button>
      </div>
      {loading ? (
        <p style={textMono}>Vérification Gemini...</p>
      ) : (
        <div className="grid grid-cols-2 gap-3 text-sm">
          <p style={textMono}>Gemini</p>
          <StatusBadge ok={online} label={online ? 'en ligne' : 'hors ligne'} />
          <p style={textMono}>Modèle Actuel</p>
          <p style={{ color: 'var(--aluminum)' }}>{data?.model || '-'}</p>
          <p style={textMono}>Statut Réponse</p>
          <p style={{ color: online ? '#4CAF50' : '#FF6B6B' }}>{data?.error || error || 'prêt'}</p>
          <p style={textMono}>Dernière Vérification</p>
          <p style={{ color: 'var(--aluminum)' }}>{updatedAt ? updatedAt.toLocaleTimeString() : '-'}</p>
        </div>
      )}
    </div>
  );
}

export function PDFDetailsDrawer({ documentId, onClose }: { documentId: number | null; onClose: () => void }) {
  const enabled = documentId !== null;
  const { data: doc, loading, error } = useApiQuery(
    `pdf-${documentId}`,
    (signal) => pdfAPI.getById(documentId as number, signal),
    { enabled }
  );
  const { data: datasets } = useApiQuery('datasets-for-pdf-detail', (signal) => datasetAPI.getAll(0, 100, signal), { enabled });
  const { data: jobs } = useApiQuery('jobs-for-pdf-detail', (signal) => pipelineAPI.getJobs(0, 100, signal), { enabled, pollMs: 30000 });

  if (!enabled) return null;

  const linkedDatasets = (datasets || []).filter((dataset) => dataset.pdf_document_id === documentId);
  const history = (jobs || []).filter((job) => job.pdf_document_id === documentId);
  const metadata = parseMetadata(doc?.extraction_metadata);

  return (
    <div className="fixed inset-0 z-50 flex justify-end" style={{ background: 'rgba(0, 0, 0, 0.55)' }}>
      <div className="absolute inset-0" onClick={onClose} />
      <div className="relative w-full max-w-2xl h-full overflow-y-auto p-6" style={{ background: 'rgba(15, 15, 27, 0.96)', borderLeft: '1px solid rgba(74, 74, 90, 0.5)' }}>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-bold" style={{ color: 'var(--aluminum)' }}>Détails PDF</h2>
          <button onClick={onClose} className="p-2 rounded hover:bg-white/10"><X size={20} style={{ color: 'var(--aluminum)' }} /></button>
        </div>
        {loading ? <p style={textMono}>Chargement des détails PDF...</p> : error ? <p style={{ ...textMono, color: '#FF6B6B' }}>{error}</p> : doc && (
          <div className="space-y-6">
            <DetailGrid items={[
              ['Nom du Document', doc.original_filename],
              ['Date de Téléchargement', formatDateTime(doc.created_at)],
              ['Taille du Fichier', formatBytes(doc.file_size)],
              ['Nombre de Pages', String(doc.page_count)],
              ['Statut de Traitement', doc.status],
              ['Source', doc.source_url || doc.source_type],
            ]} />
            <Section title="Métadonnées Extraites"><JsonBlock value={metadata} /></Section>
            <Section title="Datasets Liés">
              {linkedDatasets.length ? linkedDatasets.map((dataset) => (
                <p key={dataset.id} style={{ color: 'var(--aluminum)' }}>{dataset.name} — {dataset.row_count} lignes</p>
              )) : <p style={textMono}>Aucun dataset lié. Allez dans l'onglet Datasets pour lancer l'extraction IA.</p>}
            </Section>
            <Section title="Historique de Traitement">
              {history.length ? history.map((job) => <JobTimelineItem key={job.id} job={job} />) : <p style={textMono}>Aucun historique de traitement trouvé.</p>}
            </Section>
          </div>
        )}
      </div>
    </div>
  );
}

export function DatasetDetailView({
  dataset,
  rows,
  sourceDocument,
  onAIExtract,
  aiBusy,
}: {
  dataset: Dataset;
  rows: DataRow[];
  sourceDocument?: PDFDocument | null;
  onAIExtract: () => void;
  aiBusy?: boolean;
}) {
  const columns = useMemo(() => {
    const populated = new Set<string>();
    rows.forEach((row) => {
      Object.entries(row.row_data).forEach(([key, value]) => {
        if (value !== null && value !== undefined && String(value).trim() !== '') {
          populated.add(key);
        }
      });
    });
    return Array.from(populated);
  }, [rows]);
  const averageConfidence = rows.length
    ? Math.round(rows.reduce((sum, row) => sum + (row.confidence_score || 0), 0) / rows.length)
    : null;

  return (
    <div className="space-y-6">
      <div className="p-6 border-b flex flex-col md:flex-row md:items-start justify-between gap-4" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
        <div>
          <h2 className="text-xl font-bold mb-1" style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}>{dataset.name}</h2>
          <p className="text-sm" style={textMono}>{dataset.description || 'Aucune description'}</p>
        </div>
        <button onClick={onAIExtract} disabled={aiBusy} className="btn-secondary py-2 px-4 text-sm flex items-center gap-2 disabled:opacity-50">
          <Brain size={16} />
          {aiBusy ? 'Extraction...' : 'Extraction IA'}
        </button>
      </div>
      <div className="px-6 grid grid-cols-2 md:grid-cols-4 gap-4">
        <MiniStat label="Enregistrements" value={dataset.row_count} />
        <MiniStat label="Colonnes" value={columns.length} />
        <MiniStat label="Confiance" value={averageConfidence === null ? '-' : `${averageConfidence}%`} />
        <MiniStat label="Statut" value={dataset.status} />
      </div>
      <div className="px-6">
        <Section title="Dataset Metadata">
          <DetailGrid items={[
            ['Créé', formatDateTime(dataset.created_at)],
            ['Document Source', sourceDocument?.original_filename || `PDF #${dataset.pdf_document_id}`],
            ['Pipeline', rows[0]?.extraction_method || 'pdfplumber'],
            ['Colonnes du Schéma', columns.join(', ') || '-'],
          ]} />
        </Section>
      </div>
    </div>
  );
}

export function JobMonitoringPanel({ selectedJobId }: { selectedJobId: number | null }) {
  const enabled = selectedJobId !== null;
  const { data: job, loading, error } = useApiQuery(
    `job-${selectedJobId}`,
    (signal) => pipelineAPI.getJob(selectedJobId as number, signal),
    { enabled, pollMs: 5000, retries: 1 }
  );

  if (!enabled) return null;

  return (
    <div className="rounded-lg p-6 mb-6" style={panelStyle}>
      <div className="flex items-center gap-2 mb-4">
        <Clock size={22} style={{ color: 'var(--orange)' }} />
        <h2 className="text-xl font-bold" style={{ color: 'var(--aluminum)' }}>Moniteur de Tâche de Traitement</h2>
      </div>
      {loading ? <p style={textMono}>Chargement de la tâche...</p> : error ? <p style={{ ...textMono, color: '#FF6B6B' }}>{error}</p> : job && (
        <div className="space-y-4">
          <DetailGrid items={[
            ['ID Tâche', String(job.id)],
            ['Statut Actuel', job.status],
            ['Progression', `${job.progress}%`],
            ['Heure de Début', job.started_at ? formatDateTime(job.started_at) : '-'],
            ['Heure de Fin', job.completed_at ? formatDateTime(job.completed_at) : '-'],
            ['Étape de Traitement', job.job_type],
            ["Messages d'Erreur", job.error_message || '-'],
          ]} />
          <ProgressBar value={job.progress} status={job.status} />
          <Section title="Chronologie"><JobTimelineItem job={job} /></Section>
        </div>
      )}
    </div>
  );
}

function DetailGrid({ items }: { items: Array<[string, string]> }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-lg p-3" style={{ background: 'rgba(255, 255, 255, 0.02)', border: '1px solid rgba(74, 74, 90, 0.2)' }}>
          <p className="text-xs uppercase mb-1" style={textMono}>{label}</p>
          <p style={{ color: 'var(--aluminum)' }}>{value}</p>
        </div>
      ))}
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <h3 className="text-xs uppercase font-bold tracking-widest mb-2" style={textMono}>{title}</h3>
      {children}
    </div>
  );
}

function JsonBlock({ value }: { value: unknown }) {
  return <pre className="rounded-lg p-4 overflow-x-auto text-xs" style={{ ...panelStyle, color: 'var(--aluminum)' }}>{JSON.stringify(value || {}, null, 2)}</pre>;
}

function parseMetadata(value?: string | null) {
  if (!value) return {};
  try {
    return JSON.parse(value);
  } catch {
    return { raw: value };
  }
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg p-4" style={panelStyle}>
      <p className="text-xs uppercase mb-2" style={textMono}>{label}</p>
      <p className="text-xl font-bold" style={{ color: 'var(--aluminum)' }}>{value}</p>
    </div>
  );
}

function ProgressBar({ value, status }: { value: number; status: string }) {
  return (
    <div>
      <div className="flex justify-between mb-2 text-xs" style={textMono}><span>{status}</span><span>{value}%</span></div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: 'rgba(74, 74, 90, 0.4)' }}>
        <div className="h-full" style={{ width: `${Math.max(0, Math.min(value, 100))}%`, background: 'var(--orange)' }} />
      </div>
    </div>
  );
}

function JobTimelineItem({ job }: { job: ProcessingJob }) {
  return (
    <div className="flex gap-3 text-sm">
      {job.status === 'failed' ? <AlertCircle size={18} style={{ color: '#FF6B6B' }} /> : job.status === 'completed' ? <CheckCircle size={18} style={{ color: '#4CAF50' }} /> : <Clock size={18} style={{ color: 'var(--orange)' }} />}
      <div>
        <p style={{ color: 'var(--aluminum)' }}>{job.job_type} - {job.status}</p>
        <p style={textMono}>{formatDate(job.created_at)}{job.completed_at ? ` -> ${formatDate(job.completed_at)}` : ''}</p>
      </div>
    </div>
  );
}

function AIExtractionResult({ result }: { result: GeminiExtractResponse }) {
  const created = !!result.dataset_id;
  return (
    <Section title="AI Extraction Results">
      <div className="rounded-lg p-4 space-y-3" style={panelStyle}>
        <DetailGrid items={[
          ['Modèle', result.model],
          ['Temps de Traitement', `${result.processing_time}s`],
          ['Status', created ? '✓ Dataset created' : 'No structured data found'],
          ...(created ? [
            ['Dataset', result.dataset_name ?? ''],
            ['Lignes', String(result.row_count ?? 0)],
          ] : []),
        ]} />
        {result.message && (
          <p className="text-sm" style={{ color: created ? '#4CAF50' : 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
            {result.message}
          </p>
        )}
        {created && (
          <p className="text-xs" style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
            Le dataset #{result.dataset_id} est maintenant visible dans la section Datasets et sous Datasets Liés ci-dessous.
          </p>
        )}
      </div>
    </Section>
  );
}
