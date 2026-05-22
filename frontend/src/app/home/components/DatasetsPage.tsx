'use client';

import { useState, useEffect } from 'react';
import { datasetAPI } from '@/lib/api';
import { Database, Search, Download, Trash2, Eye } from 'lucide-react';
import { formatDate } from '@/lib/utils';

interface Dataset {
  id: number;
  name: string;
  description: string | null;
  row_count: number;
  status: string;
  created_at: string;
  pdf_document_id: number;
}

interface DataRow {
  id: number;
  row_data: Record<string, any>;
  created_at: string;
}

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<Dataset | null>(null);
  const [dataRows, setDataRows] = useState<DataRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchDatasets = async () => {
    try {
      const response = await datasetAPI.getAll();
      setDatasets(response.data);
    } catch (error) {
      console.error('Failed to fetch datasets:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDatasetRows = async (datasetId: number, pageNum: number = 1) => {
    try {
      const response = await datasetAPI.getRows(datasetId, (pageNum - 1) * 50, 50);
      setDataRows(response.data);
      setTotalPages(Math.ceil(response.data.length / 50) + 1);
    } catch (error) {
      console.error('Failed to fetch dataset rows:', error);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleSelectDataset = (dataset: Dataset) => {
    setSelectedDataset(dataset);
    setPage(1);
    fetchDatasetRows(dataset.id, 1);
  };

  const handleExportCSV = () => {
    if (!selectedDataset || dataRows.length === 0) return;

    const headers = Object.keys(dataRows[0].row_data);
    const escapeCell = (val: any) => {
      if (val === null || val === undefined) return '';
      const str = String(val).replace(/\r?\n/g, ' ').trim();
      if (str.includes(',') || str.includes('"') || str.includes('\n')) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    };

    const csvContent = [
      headers.map(escapeCell).join(','),
      ...dataRows.map((row) =>
        headers.map((h) => escapeCell(row.row_data[h])).join(',')
      ),
    ].join('\n');

    const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedDataset.name}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    if (!selectedDataset || dataRows.length === 0) return;

    const normalizedRows = dataRows.map((row) => {
      const normalized: Record<string, any> = {};
      for (const [k, v] of Object.entries(row.row_data)) {
        normalized[k] = typeof v === 'string' ? v.replace(/\r?\n/g, ' ').trim() : v;
      }
      return normalized;
    });

    const jsonContent = JSON.stringify(
      normalizedRows,
      null,
      2
    );
    const blob = new Blob(['\uFEFF' + jsonContent], { type: 'application/json;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedDataset.name}.json`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this dataset?')) {
      return;
    }

    try {
      await datasetAPI.delete(id);
      if (selectedDataset?.id === id) {
        setSelectedDataset(null);
        setDataRows([]);
      }
      await fetchDatasets();
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to delete dataset. Please try again.');
    }
  };

  const filteredDatasets = datasets.filter(
    (dataset) =>
      dataset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (dataset.description && dataset.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  return (
    <div>
      <div className="mb-8">
        <h1
          className="text-4xl font-bold"
          style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
        >
          Datasets
        </h1>
        <p
          className="text-sm mt-2"
          style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
        >
          Explore and export your extracted datasets
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Datasets List */}
        <div className="lg:col-span-1">
          <div
            className="rounded-lg p-4 mb-4"
            style={{
              background: 'rgba(26, 26, 46, 0.5)',
              border: '1px solid rgba(74, 74, 90, 0.4)',
            }}
          >
            <div className="relative">
              <Search
                size={18}
                style={{
                  color: 'var(--aluminum-dim)',
                  position: 'absolute',
                  left: '12px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                }}
              />
              <input
                type="text"
                placeholder="Search datasets..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="input-field w-full pl-10"
                style={{ paddingLeft: '2.5rem' }}
              />
            </div>
          </div>

          <div
            className="rounded-lg"
            style={{
              background: 'rgba(26, 26, 46, 0.5)',
              border: '1px solid rgba(74, 74, 90, 0.4)',
            }}
          >
            <div className="p-4 border-b" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
              <h2
                className="text-sm font-bold uppercase tracking-wider"
                style={{ color: 'var(--aluminum)', fontFamily: 'JetBrains Mono, monospace' }}
              >
                Datasets ({filteredDatasets.length})
              </h2>
            </div>

            {loading ? (
              <div className="p-8 text-center">
                <p
                  style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  Loading datasets...
                </p>
              </div>
            ) : filteredDatasets.length === 0 ? (
              <div className="p-8 text-center">
                <p
                  style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  No datasets found
                </p>
              </div>
            ) : (
              <div
                className="divide-y max-h-96 overflow-y-auto"
                style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}
              >
                {filteredDatasets.map((dataset) => (
                  <div
                    key={dataset.id}
                    className={`p-4 cursor-pointer transition-colors ${
                      selectedDataset?.id === dataset.id ? 'bg-orange/10' : 'hover:bg-white/5'
                    }`}
                    onClick={() => handleSelectDataset(dataset)}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Database size={16} style={{ color: 'var(--orange)' }} />
                        <h3
                          className="font-semibold text-sm"
                          style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
                        >
                          {dataset.name}
                        </h3>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(dataset.id);
                        }}
                        className="p-1 rounded hover:bg-red-500/10 transition-colors"
                      >
                        <Trash2 size={14} style={{ color: '#FF6B6B' }} />
                      </button>
                    </div>
                    <div
                      className="flex items-center gap-3 text-xs"
                      style={{
                        color: 'var(--aluminum-dim)',
                        fontFamily: 'JetBrains Mono, monospace',
                      }}
                    >
                      <span>{dataset.row_count} rows</span>
                      <span>•</span>
                      <span>{formatDate(dataset.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Dataset Details */}
        <div className="lg:col-span-2">
          {selectedDataset ? (
            <div
              className="rounded-lg"
              style={{
                background: 'rgba(26, 26, 46, 0.5)',
                border: '1px solid rgba(74, 74, 90, 0.4)',
              }}
            >
              <div
                className="p-6 border-b flex items-center justify-between"
                style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}
              >
                <div>
                  <h2
                    className="text-xl font-bold mb-1"
                    style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
                  >
                    {selectedDataset.name}
                  </h2>
                  {selectedDataset.description && (
                    <p
                      className="text-sm"
                      style={{
                        color: 'var(--aluminum-dim)',
                        fontFamily: 'JetBrains Mono, monospace',
                      }}
                    >
                      {selectedDataset.description}
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleExportCSV}
                    className="btn-secondary py-2 px-4 text-sm flex items-center gap-2"
                  >
                    <Download size={16} />
                    CSV
                  </button>
                  <button
                    onClick={handleExportJSON}
                    className="btn-secondary py-2 px-4 text-sm flex items-center gap-2"
                  >
                    <Download size={16} />
                    JSON
                  </button>
                </div>
              </div>

              {dataRows.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr
                        className="border-b text-left text-xs uppercase tracking-wider"
                        style={{
                          borderColor: 'rgba(74, 74, 90, 0.4)',
                          color: 'var(--aluminum-dim)',
                          fontFamily: 'JetBrains Mono, monospace',
                        }}
                      >
                        {Object.keys(dataRows[0].row_data).map((key) => (
                          <th key={key} className="p-4 font-semibold">
                            {key}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
                      {dataRows.map((row, index) => (
                        <tr key={row.id} className="hover:bg-white/5 transition-colors">
                          {Object.values(row.row_data).map((value: any, cellIndex) => (
                            <td
                              key={cellIndex}
                              className="p-4 text-sm"
                              style={{
                                color: 'var(--aluminum)',
                                fontFamily: 'JetBrains Mono, monospace',
                              }}
                            >
                              {value !== null && value !== undefined ? String(value) : '-'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="p-8 text-center">
                  <p
                    style={{
                      color: 'var(--aluminum-dim)',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    No data rows in this dataset
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div
              className="rounded-lg p-12 text-center"
              style={{
                background: 'rgba(26, 26, 46, 0.5)',
                border: '1px solid rgba(74, 74, 90, 0.4)',
              }}
            >
              <Database size={48} style={{ color: 'var(--orange)', marginBottom: '1rem' }} />
              <h3
                className="text-lg font-bold mb-2"
                style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
              >
                Select a Dataset
              </h3>
              <p
                className="text-sm"
                style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
              >
                Choose a dataset from the list to view and export its data
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
