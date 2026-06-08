export interface ApiRootInfo {
  message: string;
  version: string;
  docs: string;
  environment?: string;
  status?: string;
}

export interface HealthCheck {
  status: string;
  database?: string;
}

export interface Statistics {
  total_pdfs: number;
  total_rows: number;
  ocr_processed: number;
  failed_jobs: number;
  storage_used: number;
}

export interface PDFDocument {
  id: number;
  user_id: number;
  filename: string;
  original_filename: string;
  file_path: string;
  file_size: number;
  page_count: number;
  status: string;
  source_type: string;
  source_url: string | null;
  ocr_processed: boolean;
  extraction_metadata: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface Dataset {
  id: number;
  user_id: number;
  pdf_document_id: number;
  name: string;
  description: string | null;
  schema_definition: Record<string, unknown> | null;
  row_count: number;
  status: string;
  data_preview: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface DataRow {
  id: number;
  dataset_id: number;
  row_data: Record<string, unknown>;
  page_number: number | null;
  extraction_method: string;
  confidence_score: number | null;
  created_at: string;
}

export interface ProcessingJob {
  id: number;
  user_id: number;
  pdf_document_id: number | null;
  job_type: string;
  status: string;
  progress: number;
  result: string | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface PipelineHealth {
  status: string;
  services: Record<string, string>;
}

export interface GeminiHealth {
  success?: boolean;
  status?: string;
  model: string;
  available: boolean;
  model_available?: boolean;
  error?: string | null;
}

export interface GeminiExtractRequest {
  text: string;
  temperature?: number;
  max_tokens?: number;
}

export interface GeminiExtractResponse {
  success: boolean;
  model: string;
  response: string;
  processing_time: number;
  dataset_id?: number | null;
  dataset_name?: string | null;
  row_count?: number;
  message?: string | null;
  error?: string;
}

export interface AISummary {
  id?: number;
  pdf_document_id?: number;
  summary: string;
  classification?: string | null;
  entities?: Array<Record<string, unknown>>;
}

export interface AIAnalytics {
  id?: number;
  pdf_document_id?: number;
  insights?: string[];
  kpis?: Record<string, unknown>;
}

export interface FinancialReport {
  id: number;
  pdf_document_id: number | null;
  user_id: number;
  report_type: string | null;
  company_name: string | null;
  fiscal_year: string | null;
  currency: string | null;
  revenue: number | null;
  gross_profit: number | null;
  operating_income: number | null;
  net_income: number | null;
  ebitda: number | null;
  total_assets: number | null;
  total_liabilities: number | null;
  shareholders_equity: number | null;
  operating_cash_flow: number | null;
  investing_cash_flow: number | null;
  financing_cash_flow: number | null;
  source_pages: number[];
  confidence_score: number;
  processing_status: string;
  error_message: string | null;
  extraction_timestamp: string | null;
  created_at: string;
  updated_at: string | null;
}
