import PageRouter from '../components/PageRouter';
import React from 'react';

export default function DatasetsPage() {
  // Assume selectedDataset and dataRows are available via context or props
  const handleExportCSV = () => {
    if (!selectedDataset || !dataRows || dataRows.length === 0) return;
    const headers = Object.keys(dataRows[0].row_data);
    const escapeCell = (val) => {
      if (val == null) return '';
      const str = String(val).replace(/\r?\n/g, ' ').trim();
      if (/[",\n]/.test(str)) return `"${str.replace(/"/g, '""')}"`;
      return str;
    };
    const csv = [
      headers.map(escapeCell).join(','),
      ...dataRows.map(r => headers.map(h => escapeCell(r.row_data[h])).join(','))
    ].join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedDataset.name}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJSON = () => {
    if (!selectedDataset || !dataRows) return;
    const json = JSON.stringify(dataRows.map(r => r.row_data), null, 2);
    const blob = new Blob([json], { type: 'application/json;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedDataset.name}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex space-x-2">
        <button onClick={handleExportCSV} className="px-4 py-2 bg-blue-600 text-white rounded">
          Export CSV
        </button>
        <button onClick={handleExportJSON} className="px-4 py-2 bg-gray-600 text-white rounded">
          Export JSON
        </button>
      </div>
      <PageRouter />
    </div>
  );
}
