'use client';

import { useMemo, useState } from 'react';
import { Database, Search, Download, Trash2 } from 'lucide-react';
import { datasetAPI, geminiAPI, pdfAPI } from '@/lib/api';
import type { DataRow, Dataset, GeminiExtractResponse } from '@/lib/api-types';
import { useApiQuery } from '@/hooks/useApiQuery';
import { formatDate } from '@/lib/utils';
import { DatasetDetailView } from './EndpointWidgets';

export default function DatasetsPage() {
  const { data: datasetsData, loading, error, refetch } = useApiQuery('datasets-list', (signal) => datasetAPI.getAll(0, 100, signal));
  const datasets = datasetsData ?? [];
  const [selectedDatasetId, setSelectedDatasetId] = useState<number | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [aiResult, setAiResult] = useState<GeminiExtractResponse | null>(null);
  const [aiBusy, setAiBusy] = useState(false);
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
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce jeu de données ?')) return;
    try {
      await datasetAPI.delete(id);
      if (selectedDatasetId === id) setSelectedDatasetId(null);
      await refetch();
    } catch {
      alert('Échec de la suppression. Veuillez réessayer.');
    }
  };

  const runAIExtract = async () => {
    const dataset = selectedDataset || selectedSummary;
    if (!dataset) return;
    setAiBusy(true);
    try {
      const response = await geminiAPI.extract({
        text: JSON.stringify({
          dataset,
          source_document: sourceDocument,
          sample_rows: dataRows.slice(0, 20).map((row) => row.row_data),
        }),
      });
      setAiResult(response.data);
    } catch (err: any) {
      const message = err?.response?.data?.error || err?.response?.data?.detail || err?.message || "Vérifiez le statut du moteur IA sur le tableau de bord.";
      alert(`AI extraction failed. ${message}`);
    } finally {
      setAiBusy(false);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-4xl font-bold" style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}>Jeux de Données</h1>
        <p className="text-sm mt-2" style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>Explorez et exportez vos jeux de données extraits</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="rounded-lg p-4 mb-4" style={panelStyle}>
            <div className="relative">
              <Search size={18} style={{ color: 'var(--aluminum-dim)', position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
              <input type="text" placeholder="Rechercher des jeux de données..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="input-field w-full pl-10" style={{ paddingLeft: '2.5rem' }} />
            </div>
          </div>
          <div className="rounded-lg" style={panelStyle}>
            <div className="p-4 border-b" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
              <h2 className="text-sm font-bold uppercase tracking-wider" style={mono}>Datasets ({filteredDatasets.length})</h2>
            </div>
            {loading ? <Empty text="Chargement des jeux de données..." /> : error ? <Empty text={error} error /> : filteredDatasets.length === 0 ? <Empty text="Aucun jeu de données trouvé" /> : (
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
              <div className="p-6 flex justify-end gap-2">
                <button onClick={() => exportData('csv')} className="btn-secondary py-2 px-4 text-sm flex items-center gap-2"><Download size={16} />CSV</button>
                <button onClick={() => exportData('json')} className="btn-secondary py-2 px-4 text-sm flex items-center gap-2"><Download size={16} />JSON</button>
              </div>
              <DatasetDetailView dataset={(selectedDataset || selectedSummary) as Dataset} rows={dataRows} sourceDocument={sourceDocument} onAIExtract={runAIExtract} aiBusy={aiBusy} />
              {aiResult && <pre className="m-6 rounded-lg p-4 whitespace-pre-wrap text-sm" style={{ ...panelStyle, color: 'var(--aluminum)' }}>{aiResult.response}</pre>}
              <DataPreview rows={dataRows} />
            </div>
          ) : (
            <div className="rounded-lg p-12 text-center" style={panelStyle}>
              <Database size={48} style={{ color: 'var(--orange)', margin: '0 auto 1rem' }} />
              <h3 className="text-lg font-bold mb-2" style={{ color: 'var(--aluminum)' }}>Sélectionner un Jeu de Données</h3>
              <p className="text-sm" style={mono}>Choisissez un jeu de données dans la liste pour voir les détails, les statistiques et un aperçu.</p>
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
  if (!rows.length) return <Empty text="Aucune ligne dans ce jeu de données" />;
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
