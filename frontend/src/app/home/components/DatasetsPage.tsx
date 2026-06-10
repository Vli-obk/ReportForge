'use client';

import { useMemo, useState } from 'react';
import { Database, Search, Download, Trash2, RefreshCw, CheckCircle, Tags } from 'lucide-react';
import { datasetAPI, pdfAPI, nlpAPI } from '@/lib/api';
import type { DataRow, Dataset, GeminiExtractResponse } from '@/lib/api-types';
import { useApiQuery } from '@/hooks/useApiQuery';
import { formatDate } from '@/lib/utils';
import { DatasetDetailView } from './EndpointWidgets';

export default function DatasetsPage() {
  const { data: datasetsData, loading, error, refetch } = useApiQuery(
    'datasets-list',
    (signal) => datasetAPI.getAll(0, 100, signal),
    { pollMs: 6000 }
  );
  const datasets = datasetsData ?? [];
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [aiResult, setAiResult] = useState<GeminiExtractResponse | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [nlpEntities, setNlpEntities] = useState<Record<string, string[]> | null>(null);
  const [nlpBusy, setNlpBusy] = useState(false);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };
  const selectedSummary = datasets.find((dataset) => dataset.id === selectedDatasetId) || null;
  const { data: selectedDataset } = useApiQuery(
    `dataset-detail-${selectedDatasetId}`,
    (signal) => datasetAPI.getById(selectedDatasetId as number, signal),
    { enabled: selectedDatasetId !== null }
  );
  const { data: dataRowsData } = useApiQuery(
    `dataset-rows-${selectedDatasetId}`,
    (signal) => datasetAPI.getRows(selectedDatasetId as number, 0, 100, signal),
    { enabled: selectedDatasetId !== null }
  );
  const dataRows = dataRowsData ?? [];
  const { data: sourceDocument } = useApiQuery(
    `dataset-source-${selectedDataset?.pdf_document_id}`,
    (signal) => pdfAPI.getById(selectedDataset?.pdf_document_id as number, signal),
    { enabled: !!selectedDataset?.pdf_document_id }
  );

  const filteredDatasets = useMemo(
    () => datasets.filter((dataset) =>
      dataset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (dataset.description || '').toLowerCase().includes(searchTerm.toLowerCase())
    ),
    [datasets, searchTerm]
  );

  const exportData = (type: 'csv' | 'json') => {
    const dataset = selectedDataset || selectedSummary;
    if (!dataset || dataRows.length === 0) return;
    const rows = dataRows.map((row) => row.row_data);
    const content = type === 'json' ? JSON.stringify(rows, null, 2) : toCsv(rows);
    const blob = new Blob([type === 'csv' ? '\uFEFF' + content : content], {
      type: type === 'json' ? 'application/json;charset=utf-8' : 'text/csv;charset=utf-8',
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${dataset.name}.${type}`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this dataset?')) return;
    try {
      await datasetAPI.delete(id);
      if (selectedDatasetId === id) setSelectedDatasetId(null);
      await refetch();
      showToast('Dataset deleted.');
    } catch {
      alert('Échec de la suppression. Veuillez réessayer.');
    }
  };

  const runNLPExtract = async () => {
    if (!sourceDocument) {
      alert('Document source introuvable.');
      return;
    }
    setNlpBusy(true);
    setNlpEntities(null);
    try {
      const res = await nlpAPI.getEntities(sourceDocument.id);
      setNlpEntities(res.data.entities);
      showToast(`${res.data.total} entités détectées.`);
    } catch {
      alert('Échec de la détection d\'entités NLP.');
    } finally {
      setNlpBusy(false);
    }
  };

  const runAIExtract = async () => {
    if (!sourceDocument) {
      alert('Document source introuvable. Impossible de lancer l\'extraction IA.');
      return;
    }
    setAiBusy(true);
    setAiResult(null);
    try {
      const response = await pdfAPI.geminiExtract(sourceDocument.id);
      setAiResult(response.data);
      await refetch();
      if (response.data.dataset_id) {
        showToast(`New dataset created: ${response.data.row_count} rows.`);
      } else {
        showToast(response.data.message || 'Extraction terminée.');
      }
    } catch (err: any) {
      const message = err?.response?.data?.detail || err?.message || 'Vérifiez le statut du moteur IA.';
      alert(`Échec de l'extraction IA : ${message}`);
    } finally {
      setAiBusy(false);
    }
  };

  return (
    <div>
      {toast && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-2 rounded-lg px-4 py-3 shadow-lg"
          style={{ background: 'rgba(26,26,46,0.97)', border: '1px solid #4CAF50', color: '#4CAF50', fontFamily: 'JetBrains Mono, monospace', fontSize: '13px' }}>
          <CheckCircle size={16} />
          {toast}
        </div>
      )}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-4xl font-bold" style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}>Datasets</h1>
          <p className="text-sm mt-2" style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>Explorez et exportez vos datasets extraits</p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary py-2 px-3 text-sm flex items-center gap-2 mt-1" title="Actualiser">
          <RefreshCw size={15} />
          Actualiser
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="rounded-lg p-4 mb-4" style={panelStyle}>
            <div className="relative">
              <Search size={18} style={{ color: 'var(--aluminum-dim)', position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
              <input type="text" placeholder="Search datasets..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="input-field w-full pl-10" style={{ paddingLeft: '2.5rem' }} />
            </div>
          </div>
          <div className="rounded-lg" style={panelStyle}>
            <div className="p-4 border-b" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
              <h2 className="text-sm font-bold uppercase tracking-wider" style={mono}>Datasets ({filteredDatasets.length})</h2>
            </div>
            {loading ? <Empty text="Loading datasets..." /> : error ? <Empty text={error} error /> : filteredDatasets.length === 0 ? <Empty text="No datasets found" /> : (
              <div className="divide-y max-h-96 overflow-y-auto" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
                {filteredDatasets.map((dataset) => (
                  <div key={dataset.id} className={`p-4 cursor-pointer transition-colors ${selectedDatasetId === dataset.id ? 'bg-orange/10' : 'hover:bg-white/5'}`} onClick={() => { setSelectedDatasetId(dataset.id); setAiResult(null); }}>
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Database size={16} style={{ color: 'var(--orange)' }} />
                        <h3 className="font-semibold text-sm" style={{ color: 'var(--aluminum)' }}>{dataset.name}</h3>
                      </div>
                      <button onClick={(e) => { e.stopPropagation(); handleDelete(dataset.id); }} className="p-1 rounded hover:bg-red-500/10 transition-colors">
                        <Trash2 size={14} style={{ color: '#FF6B6B' }} />
                      </button>
                    </div>
                    <div className="flex items-center gap-3 text-xs" style={mono}>
                      <span>{dataset.row_count} rows</span>
                      <span>{formatDate(dataset.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="lg:col-span-2">
          {selectedSummary ? (
            <div className="rounded-lg" style={panelStyle}>
              <div className="p-6 flex justify-end gap-2 flex-wrap">
                <button onClick={runNLPExtract} disabled={nlpBusy || !sourceDocument} className="btn-secondary py-2 px-4 text-sm flex items-center gap-2" style={{ borderColor: 'rgba(255,107,43,0.4)', opacity: (!sourceDocument || nlpBusy) ? 0.5 : 1 }}>
                  <Tags size={16} />{nlpBusy ? 'Analyse...' : 'Entités NLP'}
                </button>
                <button onClick={() => exportData('csv')} className="btn-secondary py-2 px-4 text-sm flex items-center gap-2"><Download size={16} />CSV</button>
                <button onClick={() => exportData('json')} className="btn-secondary py-2 px-4 text-sm flex items-center gap-2"><Download size={16} />JSON</button>
              </div>
              <DatasetDetailView dataset={(selectedDataset || selectedSummary) as Dataset} rows={dataRows} sourceDocument={sourceDocument} onAIExtract={runAIExtract} aiBusy={aiBusy} />
              {aiResult && <pre className="m-6 rounded-lg p-4 whitespace-pre-wrap text-sm" style={{ ...panelStyle, color: 'var(--aluminum)' }}>{aiResult.response}</pre>}
              {nlpEntities && <NLPEntitiesPanel entities={nlpEntities} onClose={() => setNlpEntities(null)} />}
              <DataPreview rows={dataRows} />
            </div>
          ) : (
            <div className="rounded-lg p-12 text-center" style={panelStyle}>
              <Database size={48} style={{ color: 'var(--orange)', margin: '0 auto 1rem' }} />
              <h3 className="text-lg font-bold mb-2" style={{ color: 'var(--aluminum)' }}>Select a Dataset</h3>
              <p className="text-sm" style={mono}>Choose a dataset from the list to view details, statistics and a preview.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const panelStyle = { background: 'rgba(26, 26, 46, 0.5)', border: '1px solid rgba(74, 74, 90, 0.4)' };
const mono = { color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' };

function Empty({ text, error = false }: { text: string; error?: boolean }) {
  return <div className="p-8 text-center"><p style={{ ...mono, color: error ? '#FF6B6B' : mono.color }}>{text}</p></div>;
}

function DataPreview({ rows }: { rows: DataRow[] }) {
  const columns = getMeaningfulColumns(rows);
  const previewRows = rows
    .map((row) => ({
      row,
      filled: columns.reduce((count, key) => count + (isPresent(row.row_data[key]) ? 1 : 0), 0),
    }))
    .filter((item) => item.filled > 0)
    .sort((a, b) => b.filled - a.filled)
    .slice(0, 50)
    .map((item) => item.row);
  if (!rows.length) return <Empty text="No rows in this dataset" />;
  if (!columns.length || !previewRows.length) return <Empty text="Des lignes existent, mais les champs extraits sont vides pour cet aperçu." />;
  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead><tr className="border-b text-left text-xs uppercase tracking-wider" style={{ borderColor: 'rgba(74, 74, 90, 0.4)', ...mono }}>{columns.map((key) => <th key={key} className="p-4 font-semibold">{key}</th>)}</tr></thead>
        <tbody className="divide-y" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>{previewRows.map((row) => <tr key={row.id} className="hover:bg-white/5 transition-colors">{columns.map((key) => <td key={key} className="p-4 text-sm max-w-[260px] truncate" title={String(row.row_data[key] ?? '')} style={{ color: 'var(--aluminum)', fontFamily: 'JetBrains Mono, monospace' }}>{formatCell(row.row_data[key])}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function toCsv(rows: Record<string, unknown>[]) {
  if (!rows.length) return '';
  const headers = getMeaningfulColumns(rows.map((row, index) => ({
    id: index,
    dataset_id: 0,
    row_data: row,
    page_number: null,
    extraction_method: 'export',
    confidence_score: null,
    created_at: '',
  })));
  const escapeCell = (value: unknown) => {
    const text = value === null || value === undefined ? '' : String(value).replace(/\r?\n/g, ' ').trim();
    return `"${text.replace(/"/g, '""')}"`;
  };
  return [headers.map(escapeCell).join(','), ...rows.map((row) => headers.map((key) => escapeCell(row[key])).join(','))].join('\n');
}

function getMeaningfulColumns(rows: DataRow[]) {
  const counts = new Map<string, number>();
  rows.forEach((row) => {
    Object.entries(row.row_data).forEach(([key, value]) => {
      if (isPresent(value)) counts.set(key, (counts.get(key) || 0) + 1);
    });
  });
  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 16)
    .map(([key]) => key);
}

function isPresent(value: unknown) {
  return value !== null && value !== undefined && String(value).trim() !== '';
}

function formatCell(value: unknown) {
  return isPresent(value) ? String(value) : '-';
}

const LABEL_COLORS: Record<string, string> = {
  PER: '#FF6B6B', ORG: '#4FC3F7', LOC: '#81C784', DATE: '#FFB74D',
  MISC: '#CE93D8', MONTANT: '#80CBC4', EMAIL: '#F48FB1', TELEPHONE: '#AED581', IBAN: '#FFD54F',
};

function NLPEntitiesPanel({ entities, onClose }: { entities: Record<string, string[]>; onClose: () => void }) {
  const entries = Object.entries(entities).filter(([, vals]) => vals.length > 0);
  if (!entries.length) return (
    <div className="mx-6 mb-4 rounded-lg p-4 text-center" style={panelStyle}>
      <p style={mono}>Aucune entité détectée.</p>
    </div>
  );
  return (
    <div className="mx-6 mb-4 rounded-lg p-5" style={{ ...panelStyle, borderColor: 'rgba(255,107,43,0.35)' }}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Tags size={16} style={{ color: 'var(--orange)' }} />
          <span className="text-sm font-bold uppercase tracking-wider" style={{ color: 'var(--aluminum)', fontFamily: 'JetBrains Mono, monospace' }}>
            Entités Détectées (NLP)
          </span>
        </div>
        <button onClick={onClose} className="text-xs px-2 py-1 rounded" style={{ color: 'var(--aluminum-dim)', background: 'rgba(74,74,90,0.3)' }}>✕</button>
      </div>
      <div className="flex flex-col gap-4">
        {entries.map(([label, values]) => (
          <div key={label}>
            <span className="text-xs font-bold uppercase tracking-widest mb-2 inline-block px-2 py-0.5 rounded"
              style={{ background: `${LABEL_COLORS[label] || '#90A4AE'}22`, color: LABEL_COLORS[label] || '#90A4AE', fontFamily: 'JetBrains Mono, monospace' }}>
              {label}
            </span>
            <div className="flex flex-wrap gap-2 mt-1">
              {values.map((v, i) => (
                <span key={i} className="text-xs px-2 py-1 rounded"
                  style={{ background: 'rgba(74,74,90,0.25)', color: 'var(--aluminum)', fontFamily: 'JetBrains Mono, monospace', border: '1px solid rgba(74,74,90,0.4)' }}>
                  {v}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
