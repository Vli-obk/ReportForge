'use client';

import { useState, useCallback, useEffect } from 'react';
import { pdfAPI, aiAPI } from '@/lib/api';
import {
  Upload,
  Link as LinkIcon,
  FileText,
  Trash2,
  CheckCircle,
  XCircle,
  Clock,
  Brain,
  Tag,
  Cpu,
  X,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import { formatBytes, formatDate } from '@/lib/utils';

interface PDFDocument {
  id: number;
  filename: string;
  original_filename: string;
  file_size: number;
  page_count: number;
  status: string;
  source_type: string;
  source_url: string | null;
  ocr_processed: boolean;
  created_at: string;
}

export default function UploadsPage() {
  const [documents, setDocuments] = useState<PDFDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [useOcr, setUseOcr] = useState(false);

  // AI Drawer states
  const [selectedDoc, setSelectedDoc] = useState<PDFDocument | null>(null);
  const [aiSummaryData, setAiSummaryData] = useState<any | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [triggeringAI, setTriggeringAI] = useState(false);

  const fetchDocuments = async () => {
    try {
      const response = await pdfAPI.getAll();
      setDocuments(response.data);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectDoc = async (doc: PDFDocument) => {
    if (doc.status !== 'completed') return;
    setSelectedDoc(doc);
    setAiLoading(true);
    setAiSummaryData(null);
    try {
      const res = await aiAPI.getSummary(doc.id);
      setAiSummaryData(res.data);
    } catch (error) {
      console.error('Failed to fetch AI summary:', error);
    } finally {
      setAiLoading(false);
    }
  };

  const handleTriggerAI = async () => {
    if (!selectedDoc) return;
    setTriggeringAI(true);
    try {
      const res = await aiAPI.triggerAI(selectedDoc.id);
      setAiSummaryData(res.data);
    } catch (error) {
      console.error('AI trigger failed:', error);
      alert('Failed to re-run AI processing. Ollama may be loading.');
    } finally {
      setTriggeringAI(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      await handleFileUpload(file);
    }
  }, []);

  const handleFileUpload = async (file: File) => {
    if (!file.name.endsWith('.pdf')) {
      alert('Please upload a PDF file');
      return;
    }

    setUploading(true);
    try {
      await pdfAPI.upload(file, useOcr);
      await fetchDocuments();
    } catch (error) {
      console.error('Upload failed:', error);
      alert('Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleUrlScrape = async () => {
    if (!urlInput) {
      alert('Please enter a URL');
      return;
    }

    setUploading(true);
    try {
      await pdfAPI.scrape(urlInput, useOcr);
      setUrlInput('');
      await fetchDocuments();
    } catch (error) {
      console.error('Scrape failed:', error);
      alert('Failed to scrape PDF from URL. Please check the URL and try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this PDF?')) {
      return;
    }

    try {
      await pdfAPI.delete(id);
      await fetchDocuments();
    } catch (error) {
      console.error('Delete failed:', error);
      alert('Failed to delete PDF. Please try again.');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={16} style={{ color: '#4CAF50' }} />;
      case 'failed':
        return <XCircle size={16} style={{ color: '#FF6B6B' }} />;
      default:
        return <Clock size={16} style={{ color: 'var(--orange)' }} />;
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1
          className="text-4xl font-bold"
          style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
        >
          Uploads
        </h1>
        <p
          className="text-sm mt-2"
          style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
        >
          Upload PDFs or scrape from URLs
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* File Upload */}
        <div
          className={`rounded-lg p-8 border-2 border-dashed transition-all ${
            dragActive ? 'border-orange' : ''
          }`}
          style={{
            background: 'rgba(26, 26, 46, 0.5)',
            borderColor: dragActive ? 'var(--orange)' : 'rgba(74, 74, 90, 0.4)',
          }}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="flex flex-col items-center justify-center text-center">
            <Upload size={48} style={{ color: 'var(--orange)', marginBottom: '1rem' }} />
            <h3
              className="text-lg font-bold mb-2"
              style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
            >
              Drag & Drop PDF
            </h3>
            <p
              className="text-sm mb-4"
              style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
            >
              or click to browse
            </p>
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  handleFileUpload(e.target.files[0]);
                }
              }}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="btn-primary py-2 px-6 cursor-pointer text-sm">
              Select File
            </label>
          </div>
        </div>

        {/* URL Scrape */}
        <div
          className="rounded-lg p-8"
          style={{
            background: 'rgba(26, 26, 46, 0.5)',
            border: '1px solid rgba(74, 74, 90, 0.4)',
          }}
        >
          <div className="flex flex-col items-center justify-center text-center mb-6">
            <LinkIcon size={48} style={{ color: 'var(--orange)', marginBottom: '1rem' }} />
            <h3
              className="text-lg font-bold mb-2"
              style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
            >
              Scrape from URL
            </h3>
            <p
              className="text-sm"
              style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
            >
              Enter PDF URL to extract
            </p>
          </div>
          <div className="space-y-4">
            <input
              type="url"
              placeholder="https://example.com/document.pdf"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="input-field w-full"
              disabled={uploading}
            />
            <button
              onClick={handleUrlScrape}
              disabled={uploading || !urlInput}
              className="btn-primary w-full py-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? 'Processing...' : 'Scrape PDF'}
            </button>
          </div>
        </div>
      </div>

      {/* OCR Toggle */}
      <div
        className="rounded-lg p-4 mb-8 flex items-center justify-between"
        style={{
          background: 'rgba(26, 26, 46, 0.5)',
          border: '1px solid rgba(74, 74, 90, 0.4)',
        }}
      >
        <div className="flex items-center gap-3">
          <FileText size={20} style={{ color: 'var(--orange)' }} />
          <span
            className="text-sm"
            style={{ color: 'var(--aluminum)', fontFamily: 'JetBrains Mono, monospace' }}
          >
            Enable OCR for scanned PDFs
          </span>
        </div>
        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={useOcr}
            onChange={(e) => setUseOcr(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-orange" />
        </label>
      </div>

      {/* Documents List */}
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
            Uploaded Documents
          </h2>
        </div>

        {loading ? (
          <div className="p-8 text-center">
            <p style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
              Loading documents...
            </p>
          </div>
        ) : documents.length === 0 ? (
          <div className="p-8 text-center">
            <p style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}>
              No documents uploaded yet
            </p>
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}>
            {documents.map((doc) => (
              <div
                key={doc.id}
                onClick={() => handleSelectDoc(doc)}
                className={`p-6 flex items-center justify-between transition-colors ${
                  doc.status === 'completed' ? 'cursor-pointer hover:bg-white/5' : ''
                }`}
              >
                <div className="flex items-center gap-4 flex-1">
                  <div className="p-3 rounded-lg" style={{ background: 'rgba(255, 107, 43, 0.1)' }}>
                    <FileText size={20} style={{ color: 'var(--orange)' }} />
                  </div>
                  <div className="flex-1">
                    <h4
                      className="font-semibold mb-1"
                      style={{ color: 'var(--aluminum)', fontFamily: 'Manrope, sans-serif' }}
                    >
                      {doc.original_filename}
                    </h4>
                    <div
                      className="flex items-center gap-4 text-xs"
                      style={{
                        color: 'var(--aluminum-dim)',
                        fontFamily: 'JetBrains Mono, monospace',
                      }}
                    >
                      <span>{formatBytes(doc.file_size)}</span>
                      <span>•</span>
                      <span>{doc.page_count} pages</span>
                      <span>•</span>
                      <span>{formatDate(doc.created_at)}</span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        {getStatusIcon(doc.status)}
                        {doc.status}
                      </span>
                      {doc.ocr_processed && <span>• OCR</span>}
                    </div>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(doc.id);
                  }}
                  className="p-2 rounded hover:bg-red-500/10 transition-colors"
                  title="Delete"
                >
                  <Trash2 size={18} style={{ color: '#FF6B6B' }} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Report Intelligence Drawer */}
      {selectedDoc && (
        <div
          className="fixed inset-0 z-50 flex justify-end animate-fade-in"
          style={{ background: 'rgba(0, 0, 0, 0.55)', backdropFilter: 'blur(6px)' }}
        >
          {/* Backdrop Click */}
          <div className="absolute inset-0 cursor-default" onClick={() => setSelectedDoc(null)} />

          {/* Drawer Content */}
          <div
            className="relative w-full max-w-lg h-full flex flex-col shadow-2xl overflow-y-auto"
            style={{
              background: 'rgba(15, 15, 27, 0.92)',
              backdropFilter: 'blur(24px)',
              borderLeft: '1px solid rgba(74, 74, 90, 0.5)',
              fontFamily: 'Manrope, sans-serif',
            }}
          >
            {/* Header */}
            <div
              className="p-6 border-b flex items-center justify-between"
              style={{ borderColor: 'rgba(74, 74, 90, 0.4)' }}
            >
              <div className="flex items-center gap-2">
                <Brain size={24} style={{ color: 'var(--orange)' }} />
                <h2 className="text-xl font-bold" style={{ color: 'var(--aluminum)' }}>
                  Report Intelligence
                </h2>
              </div>
              <button
                onClick={() => setSelectedDoc(null)}
                className="p-1.5 rounded-full hover:bg-white/10 transition-colors"
                style={{ color: 'var(--aluminum-dim)' }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Document Details & Actions */}
            <div className="p-6 flex-1 space-y-6">
              <div>
                <span
                  className="text-[10px] tracking-widest uppercase px-2 py-0.5 rounded text-gray-400 font-bold"
                  style={{
                    background: 'rgba(255, 255, 255, 0.08)',
                    fontFamily: 'JetBrains Mono, monospace',
                  }}
                >
                  active document
                </span>
                <h3 className="text-lg font-bold mt-2 mb-1" style={{ color: 'var(--aluminum)' }}>
                  {selectedDoc.original_filename}
                </h3>
                <p
                  className="text-xs"
                  style={{ color: 'var(--aluminum-dim)', fontFamily: 'JetBrains Mono, monospace' }}
                >
                  {formatBytes(selectedDoc.file_size)} • {selectedDoc.page_count} pages •{' '}
                  {formatDate(selectedDoc.created_at)}
                </p>
              </div>

              {/* AI Details */}
              {aiLoading ? (
                <div className="flex flex-col items-center justify-center py-20 space-y-4">
                  <div
                    className="animate-spin rounded-full h-8 w-8 border-b-2"
                    style={{ borderColor: 'var(--orange)' }}
                  />
                  <p
                    className="text-xs uppercase tracking-widest"
                    style={{
                      color: 'var(--aluminum-dim)',
                      fontFamily: 'JetBrains Mono, monospace',
                    }}
                  >
                    running AI analysis...
                  </p>
                </div>
              ) : aiSummaryData ? (
                <div className="space-y-6">
                  {/* Classification Badge */}
                  {aiSummaryData.classification && (
                    <div className="flex items-center gap-2">
                      <Tag size={16} style={{ color: 'var(--orange)' }} />
                      <span
                        className="text-[11px] font-bold uppercase tracking-widest px-3 py-1 rounded"
                        style={{
                          background: 'rgba(255, 107, 43, 0.15)',
                          color: 'var(--orange)',
                          fontFamily: 'JetBrains Mono, monospace',
                        }}
                      >
                        {aiSummaryData.classification}
                      </span>
                    </div>
                  )}

                  {/* Summary bullet points */}
                  <div>
                    <h4
                      className="text-xs uppercase font-bold tracking-widest mb-2"
                      style={{
                        color: 'var(--aluminum-dim)',
                        fontFamily: 'JetBrains Mono, monospace',
                      }}
                    >
                      AI Executive Summary
                    </h4>
                    <div
                      className="rounded-lg p-4 text-sm leading-relaxed space-y-2 whitespace-pre-line"
                      style={{
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid rgba(74, 74, 90, 0.25)',
                        color: 'var(--aluminum)',
                      }}
                    >
                      {aiSummaryData.summary}
                    </div>
                  </div>

                  {/* Entities Grid */}
                  {aiSummaryData.entities && aiSummaryData.entities.length > 0 && (
                    <div>
                      <h4
                        className="text-xs uppercase font-bold tracking-widest mb-2"
                        style={{
                          color: 'var(--aluminum-dim)',
                          fontFamily: 'JetBrains Mono, monospace',
                        }}
                      >
                        Extracted Knowledge & Entities
                      </h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {aiSummaryData.entities.map((ent: any, idx: number) => (
                          <div
                            key={idx}
                            className="p-3 rounded-lg flex flex-col justify-center transition-all"
                            style={{
                              background: 'rgba(255, 255, 255, 0.015)',
                              border: '1px solid rgba(74, 74, 90, 0.15)',
                            }}
                          >
                            <span
                              className="text-[9px] uppercase tracking-wider mb-1"
                              style={{
                                color: 'var(--aluminum-dim)',
                                fontFamily: 'JetBrains Mono, monospace',
                              }}
                            >
                              {ent.key}
                            </span>
                            <span
                              className="text-sm font-semibold truncate"
                              style={{ color: 'var(--aluminum)' }}
                            >
                              {ent.value}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Manual AI Trigger */}
                  <div className="pt-4">
                    <button
                      onClick={handleTriggerAI}
                      disabled={triggeringAI}
                      className="w-full btn-secondary py-3 text-sm flex items-center justify-center gap-2 rounded-lg"
                      style={{ transition: 'all 0.2s ease' }}
                    >
                      <RefreshCw size={16} className={triggeringAI ? 'animate-spin' : ''} />
                      {triggeringAI ? 'Re-analyzing Report...' : 'Re-run AI Intelligence'}
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  className="rounded-lg p-6 text-center"
                  style={{
                    background: 'rgba(26, 26, 46, 0.5)',
                    border: '1px solid rgba(74, 74, 90, 0.4)',
                  }}
                >
                  <p style={{ color: '#FF6B6B', fontFamily: 'JetBrains Mono, monospace' }}>
                    Failed to fetch AI insights.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
