export type DocumentItem = {
  doc_id: string;
  filename: string;
  file_type: string;
  status: string;
  total_chunks: number;
  processed_chunks: number;
  failed_chunks: number;
  qa_count: number;
  imported_to_chroma: boolean;
  created_at: string;
  updated_at: string;
};

export type Paged<T> = {
  total: number;
  items: T[];
};

const API_BASE = '/api';
const SEARCH_API_BASE = (import.meta as any).env?.VITE_SEARCH_API_BASE || API_BASE;

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || response.statusText);
  }
  return response.json() as Promise<T>;
}

export const api = {
  upload(file: File) {
    const form = new FormData();
    form.append('file', file);
    return request<{ doc_id: string; filename: string; status: string }>(`${API_BASE}/files/upload`, {
      method: 'POST',
      body: form
    });
  },
  listDocuments() {
    return request<DocumentItem[]>(`${API_BASE}/files`);
  },
  getState(docId: string) {
    return request<Record<string, any>>(`${API_BASE}/files/${docId}/state`);
  },
  getLogs(docId: string) {
    return request<{ doc_id: string; log: string }>(`${API_BASE}/files/${docId}/logs`);
  },
  chunk(docId: string) {
    return request<Record<string, any>>(`${API_BASE}/files/${docId}/chunk`, { method: 'POST' });
  },
  generateQA(docId: string) {
    return request<Record<string, any>>(`${API_BASE}/files/${docId}/generate-qa`, { method: 'POST' });
  },
  importChroma(docId: string) {
    return request<Record<string, any>>(`${API_BASE}/files/${docId}/import-chroma`, { method: 'POST' });
  },
  compactQARecords(docId: string) {
    return request<Record<string, any>>(`${API_BASE}/files/${docId}/compact-qa-records`, { method: 'POST' });
  },
  chromaInfo() {
    return request<Record<string, any>>(`${API_BASE}/files/-/chroma-info`);
  },
  retryFailed(docId: string) {
    return request<Record<string, any>>(`${API_BASE}/files/${docId}/retry-failed`, { method: 'POST' });
  },
  deleteDocument(docId: string) {
    return request<Record<string, any>>(`${API_BASE}/files/${docId}`, { method: 'DELETE' });
  },
  chunks(docId: string, page: number, pageSize: number) {
    return request<Paged<any>>(`${API_BASE}/files/${docId}/chunks?page=${page}&page_size=${pageSize}`);
  },
  qaRecords(docId: string, page: number, pageSize: number, q?: string) {
    const query = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (q) query.set('q', q);
    return request<Paged<any>>(`${API_BASE}/files/${docId}/qa-records?${query.toString()}`);
  },
  failedChunks(docId: string) {
    return request<Paged<any>>(`${API_BASE}/files/${docId}/failed-chunks?page=1&page_size=200`);
  },
  reviewQueue(docId: string, page: number, pageSize: number) {
    return request<Paged<any> & { summary: Record<string, number> }>(
      `${API_BASE}/files/${docId}/review-queue?page=${page}&page_size=${pageSize}`
    );
  },
  batch(docIds: string[], steps: string[]) {
    return request<Record<string, any>>(`${API_BASE}/batch/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_ids: docIds, steps })
    });
  },
  search(query: string, topK: number) {
    return request<any[]>(`${SEARCH_API_BASE}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, top_k: topK })
    });
  }
};
