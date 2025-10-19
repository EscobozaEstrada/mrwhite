/**
 * API Service for Intelligent Chat Backend
 * Connects to the new intelligent_chat FastAPI backend on port 8001
 */

const API_BASE_URL = `${process.env.NEXT_PUBLIC_FASTAPI_BASE_URL}/api/v2`;

// Helper function to get auth token
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  
  // Check cookies first (primary auth method)
  const cookieToken = document.cookie.split('; ').find(row => row.startsWith('token='))?.split('=')[1];
  if (cookieToken) return cookieToken;
  
  // Fallback to localStorage
  return localStorage.getItem('token') || null;
}

// Helper function to get auth headers
function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
}

export interface Message {
  id: number;
  conversation_id: number;
  role: 'user' | 'assistant';
  content: string;
  tokens_used: number;
  credits_used: number;
  has_documents: boolean;
  document_ids: number[];
  active_mode: string | null;
  created_at: string;
  date_group: string | null;
}

export interface ChatRequest {
  message: string;
  active_mode?: 'reminders' | 'health' | 'wayofdog' | null;
  dog_profile_id?: number | null;
  document_ids?: number[];
}

export interface ChatResponse {
  message: Message;
  streaming: boolean;
  conversation_id: number;
  credits_remaining: number;
}

export interface StreamChunk {
  type: 'token' | 'metadata' | 'done' | 'error';
  content?: string;
  metadata?: any;
  error?: string;
}

/**
 * Send a message and get non-streaming response
 */
export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/send`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Send a message and get streaming response (SSE)
 */
export async function* streamMessage(
  request: ChatRequest,
  signal?: AbortSignal
): AsyncGenerator<StreamChunk> {
  console.log("📡 streamMessage called with signal:", signal);
  const response = await fetch(`${API_BASE_URL}/stream`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
    signal, // Add abort signal support
  });
  console.log("✅ Fetch initiated with abort support");

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('Response body is null');
  }

  let buffer = ''; // Buffer to accumulate incomplete chunks

  try {
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;

      // Decode and add to buffer
      buffer += decoder.decode(value, { stream: true });
      
      // Split by double newline (SSE message separator)
      const messages = buffer.split('\n\n');
      
      // Keep last incomplete message in buffer
      buffer = messages.pop() || '';

      for (const message of messages) {
        const lines = message.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6); // Remove 'data: ' prefix
            
            if (data.trim()) {
              try {
                const parsed: StreamChunk = JSON.parse(data);
                yield parsed;
              } catch (e) {
                // Silently skip malformed chunks (will be in next buffer)
                console.debug('Skipping incomplete chunk');
              }
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

/**
 * Get conversation history
 */
export async function getConversationHistory(params?: {
  limit?: number;
  offset?: number;
  search_query?: string;
  date_filter?: string;
}) {
  const queryParams = new URLSearchParams();
  
  if (params?.limit) queryParams.append('limit', params.limit.toString());
  if (params?.offset) queryParams.append('offset', params.offset.toString());
  if (params?.search_query) queryParams.append('search_query', params.search_query);
  if (params?.date_filter) queryParams.append('date_filter', params.date_filter);

  const response = await fetch(`${API_BASE_URL}/history?${queryParams}`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Clear chat messages
 */
export async function clearChat(conversationId: number, clearMemory: boolean = false) {
  const response = await fetch(`${API_BASE_URL}/clear`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify({
      conversation_id: conversationId,
      clear_memory: clearMemory,
    }),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get chat status
 */
export async function getChatStatus() {
  const response = await fetch(`${API_BASE_URL}/status`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Upload documents
 */
export async function uploadDocuments(files: File[], conversationId: number) {
  const formData = new FormData();
  
  files.forEach((file) => {
    formData.append('files', file);
  });
  
  formData.append('conversation_id', conversationId.toString());

  const token = getAuthToken();
  const headers: HeadersInit = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  // Note: Don't set Content-Type for FormData, browser will set it with boundary
  
  const response = await fetch(`${API_BASE_URL}/documents/upload`, {
    method: 'POST',
    headers: headers,
    credentials: 'include',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Upload failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get user's current credit status
 */
export async function getCredits() {
  const response = await fetch(`${API_BASE_URL}/credits`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

