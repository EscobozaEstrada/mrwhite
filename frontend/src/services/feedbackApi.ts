/**
 * Feedback API Service
 * Handles message feedback (like/dislike) operations
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

export interface FeedbackRequest {
  message_id: number;
  feedback_type: 'like' | 'dislike';
  feedback_reason?: string;
}

export interface FeedbackResponse {
  success: boolean;
  message: string;
  feedback_id?: number;
}

/**
 * Submit or update feedback for a message
 */
export async function submitFeedback(request: FeedbackRequest): Promise<FeedbackResponse> {
  const response = await fetch(`${API_BASE_URL}/feedback`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Failed to submit feedback: ${error.detail || response.statusText}`);
  }

  return response.json();
}

/**
 * Get existing feedback for a message
 */
export async function getFeedback(messageId: number): Promise<{ feedback: any | null }> {
  const response = await fetch(`${API_BASE_URL}/feedback/${messageId}`, {
    method: 'GET',
    headers: getAuthHeaders(),
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(`Failed to get feedback: ${error.detail || response.statusText}`);
  }

  return response.json();
}

