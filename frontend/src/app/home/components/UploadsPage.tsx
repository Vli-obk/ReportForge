'use client';

import { useCallback, useState } from 'react';
import type { DragEvent } from 'react';
import { Link as LinkIcon, FileText, Trash2, CheckCircle, XCircle, Clock, Upload, RefreshCw } from 'lucide-react';
import { pdfAPI } from '@/lib/api';
import type { PDFDocument } from '@/lib/api-types';
import { useApiQuery } from '@/hooks/useApiQuery';
import { formatBytes, formatDate } from '@/lib/utils';
import { PDFDetailsDrawer } from './EndpointWidgets';

export default function UploadsPage() {
  const { data: documentsData, loading, error, refetch } = useApiQuery(
    'uploads-documents',
    (signal) => pdfAPI.getAll(0, 100, signal),
    { pollMs: 5000 }
  );
  const documents = documentsData ?? [];
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [useOcr, setUseOcr] = useState(false);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  const handleDrag = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  }, []);

  const handleDrop = useCallback(async (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) await handleFileUpload(e.dataTransfer.files[0]);
  }, [useOcr]);

  const handleFileUpload = async (file: File) => {
    if (!file.name.endsWith('.pdf')) {
      alert('Veuillez télécharger un fichier PDF');
      return;
    }
    setUploading(true);
    try {
      await pdfAPI.upload(file, useOcr);
      await refetch();
      showToast(`"${file.name}" téléchargé — traitement en cours...`);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Téléchargement échoué. Veuillez réessayer.';
      alert(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleUrlScrape = async () => {
    if (!urlInput) {
      alert('Veuillez entrer une URL');
      return;
    }
    setUploading(true);
    try {
      await pdfAPI.scrape(urlInput, useOcr);
      setUrlInput('');
      await refetch();
      showToast('PDF récupéré — traitement en cours...');
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Échec de la récupération. Vérifiez l'URL.";
      alert(msg);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce PDF ?')) return;
    try {
      await pdfAPI.delete(id);
      if (selectedDocId === id) setSelectedDocId(null);
      await refetch();
    } catch {
      alert('Échec de la suppression du PDF. Veuillez réessayer.');
    }
  };

  const hasPending = documents.some(d => d.status === 'pending' || d.status === 'processing');

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
          <h1 className="text-4xl font-bold" style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}>Téléchargements</h1>
          <p className="text-sm mt-2" style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>Téléchargez des PDFs ou récupérez depuis des URLs</p>
        </div>
        <div className="flex items-center gap-2 mt-1">
          {hasPending && <span className="text-xs animate-pulse" style={{ color: 'var(--orange)', fontFamily: 'JetBrains Mono, monospace' }}>traitement en cours...</span>}
          <button onClick={() => refetch()} className="btn-secondary py-2 px-3 text-sm flex items-center gap-2" title="Actualiser">
            <RefreshCw size={15} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="rounded-lg p-8 border-2 border-dashed transition-all" style={{ background: 'rgba(26, 26, 46, 0.5)', borderColor: dragActive ? 'var(--orange)' : 'rgba(74, 74, 90, 0.4)' }} onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}>
          <div className="flex flex-col items-center justify-center text-center">
            <Upload size={48} style={{ color: 'var(--orange)', marginBottom: '1rem' }} />
            <h3 className="text-lg font-bold mb-2" style={{ color: 'var(--aluminum)' }}>Glisser & Déposer un PDF</h3>
            <p className="text-sm mb-4" style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>ou cliquez pour parcourir</p>
            <input type="file" accept=".pdf" onChange={(e) => e.target.files?.[0] && handleFileUpload(e.target.files[0])} className="hidden" id="file-upload" />
            <label htmlFor="file-upload" className="btn-primary py-2 px-6 cursor-pointer text-sm">{uploading ? 'En cours...' : 'Choisir un fichier'}</label>
          </div>
        </div>

        <div className="rounded-lg p-8" style={{ background: 'rgba(26, 26, 46, 0.5)', border: '1px solid rgba(74, 74, 90, 0.4)' }}>
          <div className="flex flex-col items-center justify-center text-center mb-6">
            <LinkIcon size={48} style={{ color: 'var(--orange)', marginBottom: '1rem' }} />
            <h3 className="text-lg font-bold mb-2" style={{ color: 'var(--aluminum)' }}>Récupérer depuis une URL</h3>
            <p className="text-sm" style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>Entrez l'URL du PDF à extraire</p>
          </div>
          <div className="space-y-4">
            <input type="url" placeholder="https://example.com/document.pdf" value={urlInput} onChange={(e) => setUrlInput(e.target.value)} className="input-field w-full" disabled={uploading} />
            <button onClick={handleUrlScrape} disabled={uploading || !urlInput} className="btn-primary w-full py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed">{uploading ? 'En cours...' : 'Récupérer le PDF'}</button>
          </div>
        </div>
      </div>

      <div className="rounded-lg p-4 mb-8 flex items-center justify-between" style={{ background: 'rgba(26, 26, 46, 0.5)', border: '1px solid rgba(74, 74, 90, 0.4)' }}>
        <div className="flex items-center gap-3">
          <FileText size={20} style={{ color: 'var(--orange)' }} />
          <span className="text-sm" style={{ color: 'var(--aluminum)', fontFamily: 'JetBrains Mono, monospace' }}>Activer l'OCR pour les PDFs scannés</span>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input type="checkbox" checked={useOcr} onChange={(e) => setUseOcr(e.target.checked)} className="sr-only peer" />
          <div className="w-11 h-6 bg-gray-600 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:w-5 after:transition-all peer-checked:bg-orange" />
        </label>
      </div>

      <div className="rounded-lg" style={{ background: 'rgba(26, 26, 46, 0.5)', border: '1px solid rgba(74, 74, 90, 0.4)' }}>
        <div className="p-6 border-b" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
          <h2 className="text-xl font-bold" style={{ color: 'var(--aluminum)' }}>Documents Téléchargés</h2>
        </div>
        {loading ? <EmptyText text="Chargement des documents..." /> : error ? <EmptyText text={error} error /> : documents.length === 0 ? <EmptyText text="Aucun document téléchargé" /> : (
          <div className="divide-y" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
            {documents.map((doc: PDFDocument) => (
              <div key={doc.id} onClick={() => setSelectedDocId(doc.id)} className="p-6 flex items-center justify-between transition-colors cursor-pointer hover:bg-white/5">
                <div className="flex items-center gap-4 flex-1">
                  <div className="p-3 rounded-lg" style={{ background: 'rgba(255, 107, 43, 0.1)' }}><FileText size={20} style={{ color: 'var(--orange)' }} /></div>
                  <div className="flex-1">
                    <h4 className="font-semibold mb-1" style={{ color: 'var(--aluminum)' }}>{doc.original_filename}</h4>
                    <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
                      <span>{formatBytes(doc.file_size)}</span>
                      <span>{doc.page_count} pages</span>
                      <span>{formatDate(doc.created_at)}</span>
                      <span className="flex items-center gap-1">{getStatusIcon(doc.status)}{doc.status}</span>
                      {doc.ocr_processed && <span>OCR</span>}
                    </div>
                  </div>
                </div>
                <button onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }} className="p-2 rounded hover:bg-red-500/10 transition-colors" title="Delete">
                  <Trash2 size={18} style={{ color: '#FF6B6B' }} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <PDFDetailsDrawer documentId={selectedDocId} onClose={() => setSelectedDocId(null)} />
    </div>
  );
}

function EmptyText({ text, error = false }: { text: string; error?: boolean }) {
  return <div className="p-8 text-center"><p style={{ color: error ? '#FF6B6B' : 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>{text}</p></div>;
}

function getStatusIcon(status: string) {
  if (status === 'completed') return <CheckCircle size={16} style={{ color: '#4CAF50' }} />;
  if (status === 'failed') return <XCircle size={16} style={{ color: '#FF6B6B' }} />;
  return <Clock size={16} style={{ color: 'var(--orange)' }} />;
}
