import axios from 'axios';

const configuredBaseUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
const API_BASE_URL = configuredBaseUrl && configuredBaseUrl.length > 0 ? configuredBaseUrl : '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('pdf_analytics_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url = error.config?.url || '';
    const isAuthRoute = url.includes('/auth/login') || url.includes('/auth/register');
    const hasStoredToken = typeof window !== 'undefined' && !!localStorage.getItem('pdf_analytics_token');

    if (status === 401 && hasStoredToken && !isAuthRoute) {
      localStorage.removeItem('pdf_analytics_token');
      localStorage.removeItem('pdf_analytics_user');
      window.location.href = '/home/login';
    }
    return Promise.reject(error);
  }
);

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

  getAll: (skip: number = 0, limit: number = 100) => api.get(`/pdfs?skip=${skip}&limit=${limit}`),

  getById: (id: number) => api.get(`/pdfs/${id}`),

  delete: (id: number) => api.delete(`/pdfs/${id}`),

  getStatistics: () => api.get('/pdfs/statistics/overview'),
};

export const datasetAPI = {
  getAll: (skip: number = 0, limit: number = 100) =>
    api.get(`/datasets?skip=${skip}&limit=${limit}`),

  getById: (id: number) => api.get(`/datasets/${id}`),

  getRows: (id: number, skip: number = 0, limit: number = 100) =>
    api.get(`/datasets/${id}/rows?skip=${skip}&limit=${limit}`),

  delete: (id: number) => api.delete(`/datasets/${id}`),
};

export const pipelineAPI = {
  getJobs: (skip: number = 0, limit: number = 100) =>
    api.get(`/pipeline/jobs?skip=${skip}&limit=${limit}`),

  getJob: (id: number) => api.get(`/pipeline/jobs/${id}`),

  getHealth: () => api.get('/pipeline/health'),
};

export const aiAPI = {
  getSummary: (docId: number) => api.get(`/pdfs/${docId}/ai-summary`),

  getAnalytics: (docId: number) => api.get(`/pdfs/${docId}/analytics`),

  triggerAI: (docId: number) => api.post(`/pdfs/${docId}/trigger-ai`),
};

export default api;
