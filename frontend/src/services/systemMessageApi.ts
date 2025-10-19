const API_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL || 'http://localhost:8000';

export interface SystemMessageRequest {
  content: string;
  dog_profile_id?: number;
  active_mode?: string;
  action_type: 'dog_added' | 'dog_edited' | 'dog_deleted';
}

export interface SystemMessageResponse {
  success: boolean;
  message_id: number;
  conversation_id: number;
  message: string;
}

// Helper function to get auth token (matches intelligentChatApi.ts)
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

export class SystemMessageApi {

  static async createSystemMessage(request: SystemMessageRequest): Promise<SystemMessageResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v2/system-message`, {
        method: 'POST',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      return response.json();
    } catch (error) {
      console.error('Failed to create system message:', error);
      throw error;
    }
  }

  static async createDogAddedMessage(dogName: string, dogProfileId: number): Promise<SystemMessageResponse> {
    const content = `🐕 Thank you for adding ${dogName} to your family! I'm excited to learn more about ${dogName} and help you with their care. I'll remember ${dogName}'s information and can provide personalized advice based on their profile. Feel free to ask me anything about ${dogName}'s health, training, or daily care!`;
    
    return this.createSystemMessage({
      content,
      dog_profile_id: dogProfileId,
      action_type: 'dog_added'
    });
  }

  static async createDogEditedMessage(dogName: string, dogProfileId: number, changes: string[]): Promise<SystemMessageResponse> {
    const changesText = changes.length > 0 ? ` I've noted the updates to: ${changes.join(', ')}.` : '';
    const content = `✅ I've updated ${dogName}'s profile information!${changesText} This will help me provide more accurate and personalized advice for ${dogName}. Is there anything specific about ${dogName} you'd like to discuss?`;
    
    return this.createSystemMessage({
      content,
      dog_profile_id: dogProfileId,
      action_type: 'dog_edited'
    });
  }

  static async createDogDeletedMessage(dogName: string): Promise<SystemMessageResponse> {
    const content = `🗑️ I've removed ${dogName} from your profile. I'll no longer reference ${dogName} in our conversations. If you have other dogs in your family, I'm still here to help with their care!`;
    
    return this.createSystemMessage({
      content,
      action_type: 'dog_deleted'
    });
  }
}
