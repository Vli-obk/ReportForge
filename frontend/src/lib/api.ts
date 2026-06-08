import axios from 'axios';
import type {
  AIAnalytics,
  AISummary,
  ApiRootInfo,
  DataRow,
  Dataset,
  GeminiExtractRequest,
  GeminiExtractResponse,
  GeminiHealth,
  PDFDocument,
  PipelineHealth,
  ProcessingJob,
  Statistics,
} from './api-types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
const addAuthToken = (config: any) => {
  const token = localStorage.getItem('reportforge_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

api.interceptors.request.use(addAuthToken);

// Handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || '';
    const isAuthRoute = url.includes('/auth/login') || url.includes('/auth/register');
    const hasStoredToken = typeof window !== 'undefined' && !!localStorage.getItem('reportforge_token');

    if (status === 401 && hasStoredToken && !isAuthRoute) {
      localStorage.removeItem('reportforge_token');
      localStorage.removeItem('reportforge_user');
      window.location.href = '/home/login';
    }
    return Promise.reject(error);
  }
);
export const systemAPI = {
  getOverview: (signal?: AbortSignal) => api.get<ApiRootInfo>('/overview', { signal }),

  getHealth: (signal?: AbortSignal) => api.get<PipelineHealth>('/pipeline/health', { signal }),
};

export const authAPI = {
  register: (data: { email: string; full_name: string; password: string }) =>
    api.post('/auth/register', data),

  login: (email: string, password: string) => {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);
    return api.post('/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },

  getMe: () => api.get('/auth/me'),

  updateSettings: (data: { ocr_enabled: boolean; max_upload_size: number; auto_process: boolean }) =>
    api.put('/auth/settings', data),
};

export const pdfAPI = {
  upload: (file: File, useOcr: boolean = false) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('use_ocr', useOcr.toString());
    return api.post('/pdfs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  scrape: (url: string, useOcr: boolean = false) => {
    const formData = new FormData();
    formData.append('url', url);
    formData.append('use_ocr', useOcr.toString());
    return api.post('/pdfs/scrape', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  getAll: (skip: number = 0, limit: number = 100, signal?: AbortSignal) =>
    api.get<PDFDocument[]>(`/pdfs?skip=${skip}&limit=${limit}`, { signal }),

  getById: (id: number, signal?: AbortSignal) => api.get<PDFDocument>(`/pdfs/${id}`, { signal }),

  delete: (id: number) => api.delete(`/pdfs/${id}`),

  getStatistics: (signal?: AbortSignal) => api.get<Statistics>('/dashboard/statistics', { signal }),

  geminiExtract: (docId: number) =>
    api.post<GeminiExtractResponse>(`/pdfs/${docId}/gemini-extract`),
};

export const datasetAPI = {
  getAll: (skip: number = 0, limit: number = 100, signal?: AbortSignal) =>
    api.get<Dataset[]>(`/datasets?skip=${skip}&limit=${limit}`, { signal }),

  getById: (id: number, signal?: AbortSignal) => api.get<Dataset>(`/datasets/${id}`, { signal }),

  getRows: (id: number, skip: number = 0, limit: number = 100, signal?: AbortSignal) =>
    api.get<DataRow[]>(`/datasets/${id}/rows?skip=${skip}&limit=${limit}`, { signal }),

  delete: (id: number) => api.delete(`/datasets/${id}`),
};

export const pipelineAPI = {
  getJobs: (skip: number = 0, limit: number = 100, signal?: AbortSignal) =>
    api.get<ProcessingJob[]>(`/pipeline/jobs?skip=${skip}&limit=${limit}`, { signal }),

  getJob: (id: number, signal?: AbortSignal) =>
    api.get<ProcessingJob>(`/pipeline/jobs/${id}`, { signal }),

  getHealth: (signal?: AbortSignal) => api.get<PipelineHealth>('/pipeline/health', { signal }),
};

export const aiAPI = {
  getSummary: (docId: number, signal?: AbortSignal) =>
    api.get<AISummary>(`/pdfs/${docId}/ai-summary`, { signal }),

  getAnalytics: (docId: number, signal?: AbortSignal) =>
    api.get<AIAnalytics>(`/pdfs/${docId}/analytics`, { signal }),

  triggerAI: (docId: number) => api.post<AISummary>(`/pdfs/${docId}/trigger-ai`),
};

export const financialReportsAPI = {
  getAll: (signal?: AbortSignal) =>
    api.get<import('./api-types').FinancialReport[]>('/financial-reports/?limit=200', { signal }),
};

export const geminiAPI = {
  getHealth: (signal?: AbortSignal) => api.get<GeminiHealth>('/gemini/health', { signal }),

  extract: (data: GeminiExtractRequest, signal?: AbortSignal) =>
    api.post<GeminiExtractResponse>('/gemini/extract', data, { signal }),
};

export default api;
