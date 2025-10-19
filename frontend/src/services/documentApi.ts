/**
 * Document API Service
 * Handles document uploads and processing
 */

const API_BASE_URL = `${process.env.NEXT_PUBLIC_FASTAPI_BASE_URL}/api/v2/documents`;

// Helper to get auth token (same as intelligentChatApi)
function getAuthToken(): string | null {
  // Check cookie first (Flask sets this)
  const cookies = document.cookie.split(';');
  
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'token') {
      return decodeURIComponent(value);
    }
  }
  
  // Fallback to localStorage (for cross-port access)
  const token = localStorage.getItem('token');
  if (token) {
    return token;
  }
  
  // Check for auth_token in localStorage (alternative)
  return localStorage.getItem('auth_token');
}

export interface DocumentUploadResult {
  success: boolean;
  document: {
    id: number;
    filename: string;
    file_type: string;
    file_size: number;
    s3_url: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    chunk_count?: number;
    error?: string;
  };
}

export interface BatchUploadResult {
  success: boolean;
  documents: DocumentUploadResult['document'][];
  errors?: Array<{
    filename: string;
    error: string;
  }>;
  total: number;
  successful: number;
  failed: number;
}

export interface DocumentStatus {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  s3_url: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error?: string;
  chunk_count: number;
  vectors_stored: boolean;
  created_at: string;
}

/**
 * Upload a single document
 */
export async function uploadDocument(
  file: File,
  conversationId: number
): Promise<DocumentUploadResult> {
  const token = getAuthToken();

  const formData = new FormData();
  formData.append('file', file);
  formData.append('conversation_id', conversationId.toString());

  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    headers,
    credentials: 'include', // Send cookies for Flask fallback
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

/**
 * Upload multiple documents at once (max 5)
 */
export async function batchUploadDocuments(
  files: File[],
  conversationId: number,
  onProgress?: (index: number, total: number) => void
): Promise<BatchUploadResult> {
  const token = getAuthToken();

  if (files.length > 5) {
    throw new Error('Maximum 5 documents allowed per message');
  }

  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  formData.append('conversation_id', conversationId.toString());

  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/batch-upload`, {
    method: 'POST',
    headers,
    credentials: 'include', // Send cookies for Flask fallback
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Batch upload failed');
  }

  return response.json();
}

/**
 * Get document processing status
 */
export async function getDocumentStatus(documentId: number): Promise<DocumentStatus> {
  const token = getAuthToken();

  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/status/${documentId}`, {
    method: 'GET',
    headers,
    credentials: 'include', // Send cookies for Flask fallback
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to get status');
  }

  return response.json();
}

/**
 * Delete a document
 */
export async function deleteDocument(documentId: number): Promise<void> {
  const token = getAuthToken();

  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/${documentId}`, {
    method: 'DELETE',
    headers,
    credentials: 'include', // Send cookies for Flask fallback
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to delete document');
  }
}

/**
 * Validate file before upload
 */
export function validateFile(file: File): { valid: boolean; error?: string } {
  const MAX_SIZE = 10 * 1024 * 1024; // 10MB
  const ALLOWED_TYPES = [
    'pdf', 'docx', 'doc', 'txt',
    'jpg', 'jpeg', 'png', 'bmp', 'gif', 'tiff'
  ];

  // Check size
  if (file.size > MAX_SIZE) {
    return { valid: false, error: `File too large (max 10MB)` };
  }

  if (file.size === 0) {
    return { valid: false, error: 'File is empty' };
  }

  // Check extension
  const ext = file.name.split('.').pop()?.toLowerCase();
  if (!ext || !ALLOWED_TYPES.includes(ext)) {
    return {
      valid: false,
      error: `File type not allowed. Allowed: ${ALLOWED_TYPES.join(', ')}`
    };
  }

  return { valid: true };
}



