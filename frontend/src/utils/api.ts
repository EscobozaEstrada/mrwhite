import axios from 'axios';

// FastAPI Chat Service Configuration (NEW)
const FASTAPI_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL;

// Flask Legacy API Configuration (EXISTING)
const FLASK_BASE_URL = process.env.NEXT_PUBLIC_FLASK_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL;

// Use FastAPI for all chat and health-related endpoints
const API_BASE_URL = FASTAPI_BASE_URL;

/**
 * Fetch conversation history for a user
 * @param userId User ID to fetch history for
 * @returns Formatted conversation history
 */
export const fetchConversationHistory = async (userId: string) => {
  try {
    // FastAPI endpoint: GET /api/conversations
    const response = await axios.get(`${FASTAPI_BASE_URL}/api/conversations`, {
      withCredentials: true,
      params: {
        limit: 50,
        offset: 0
      }
    });

    if (!response.data?.success || !Array.isArray(response.data.conversations)) {
      return [];
    }

    // Group conversations by date
    const groupedByDate = response.data.conversations.reduce((acc: any, conversation: any) => {
      // Convert the date string to a date object
      const date = new Date(conversation.created_at);
      // Format the date for grouping (YYYY-MM-DD)
      const dateStr = date.toISOString().split('T')[0];

      // Check if we already have this date in our accumulator
      if (!acc[dateStr]) {
        acc[dateStr] = [];
      }

      // Add the conversation to the accumulator with its ID
      acc[dateStr].push({
        id: conversation.id,
        title: conversation.title || `Conversation ${conversation.id}`
      });

      return acc;
    }, {});

    // Convert the grouped data to the format expected by our history state
    return Object.keys(groupedByDate).map(date => {
      // Format the date for display
      const displayDate = new Date(date).toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'short',
        day: 'numeric'
      });

      return {
        date: displayDate,
        conversations: groupedByDate[date]
      };
    });
  } catch (error) {
    console.error('Error fetching conversation history:', error);
    throw error;
  }
};

/**
 * Fetch bookmarked conversations
 * @returns Formatted bookmarks
 */
export const fetchBookmarks = async () => {
  try {
    // FastAPI endpoint: GET /api/bookmarked-conversations
    const response = await axios.get(`${FASTAPI_BASE_URL}/api/bookmarked-conversations`, {
      withCredentials: true
    });

    if (!response.data?.success || !Array.isArray(response.data.conversations)) {
      return [];
    }

    return response.data.conversations.map((conversation: any) => ({
      id: conversation.id.toString(),
      content: conversation.title || `Conversation ${conversation.id}`,
      type: 'ai' as 'user' | 'ai',
      timestamp: conversation.updated_at, // Store as ISO string
      bookmarkedAt: conversation.updated_at // Store as ISO string
    }));
  } catch (error) {
    console.error('Error fetching bookmarks:', error);
    throw error;
  }
};

/**
 * Toggle bookmark status for a conversation
 * @param conversationId ID of the conversation to toggle bookmark for
 * @returns Updated bookmark status
 */
export const toggleConversationBookmark = async (conversationId: string | number) => {
  try {
    // FastAPI endpoint: POST /api/conversations/{conversation_id}/bookmark
    const response = await axios.post(
      `${FASTAPI_BASE_URL}/api/conversations/${conversationId}/bookmark`,
      {},
      { withCredentials: true }
    );
    return response.data;
  } catch (error) {
    console.error('Error toggling conversation bookmark:', error);
    throw error;
  }
};

/**
 * Create a new conversation
 * @returns ID of the newly created conversation as string
 */
export const createNewConversation = async () => {
  try {
    // FastAPI endpoint: POST /api/conversations
    const response = await axios.post(
      `${FASTAPI_BASE_URL}/api/conversations`,
      { title: process.env.NEXT_PUBLIC_DEFAULT_CONVERSATION_TITLE || 'New Conversation' },
      { withCredentials: true }
    );

    if (response.data?.success && response.data.conversation?.id) {
      return response.data.conversation.id.toString();
    }
    throw new Error('Failed to create conversation');
  } catch (error) {
    console.error('Error creating new conversation:', error);
    throw error;
  }
};

/**
 * Load messages for a conversation
 * @param conversationId ID of the conversation to load
 * @returns Formatted messages
 */
export const loadConversationMessages = async (conversationId: string | number) => {
  try {
    // FastAPI endpoint: GET /api/conversations/{conversation_id}
    const response = await axios.get(`${FASTAPI_BASE_URL}/api/conversations/${conversationId}`, {
      withCredentials: true
    });

    if (!response.data?.success || !response.data.data) {
      return { messages: [], isBookmarked: false };
    }

    const conversationData = response.data.data;
    console.log('FastAPI Response conversation data:', conversationData);
    console.log('FastAPI Response structure:', {
      hasConversation: !!conversationData.conversation,
      hasMessages: !!conversationData.messages,
      messagesType: conversationData.messages ? typeof conversationData.messages : 'undefined',
      isArray: Array.isArray(conversationData.messages),
      messageCount: Array.isArray(conversationData.messages) ? conversationData.messages.length : 0,
      firstMessage: Array.isArray(conversationData.messages) && conversationData.messages.length > 0 ? conversationData.messages[0] : null
    });

    // Check if the data structure has conversation and messages directly
    const messagesArray = conversationData.messages || [];
    const isBookmarked = conversationData.conversation?.is_bookmarked || conversationData.is_bookmarked || false;

    // Format the messages according to our Message interface
    const formattedMessages = messagesArray.map((msg: any, index: number) => {
      console.log('Original message data:', msg);

      // Deduplicate attachments by URL to prevent duplicates
      let uniqueAttachments = [];
      if (Array.isArray(msg.attachments) && msg.attachments.length > 0) {
        const seenUrls = new Set();
        uniqueAttachments = msg.attachments.filter((attachment: { file_path: string }) => {
          // If we've seen this URL before, filter it out
          if (seenUrls.has(attachment.file_path)) {
            return false;
          }
          // Otherwise, add it to our set and keep it
          seenUrls.add(attachment.file_path);
          return true;
        }).map((attachment: { id: number; file_type: string; file_path: string; file_name: string }) => ({
          id: attachment.id,
          type: attachment.file_type || 'file',
          url: attachment.file_path || '',
          name: attachment.file_name || 'Unknown File'
        }));
      }

      // Generate a truly unique ID for messages without an ID or with potential duplicates
      const generateUniqueId = () => {
        const timestamp = Date.now();
        const randomPart = Math.floor(Math.random() * 1000000).toString().padStart(6, '0');
        const indexPart = index.toString().padStart(3, '0');
        return `api-msg-${timestamp}-${randomPart}-${indexPart}`;
      };

      // Use the actual database ID if available, otherwise generate a unique ID
      const messageId = msg.id ? msg.id.toString() : generateUniqueId();

      // Determine the correct message type
      let messageType = msg.message_type || msg.type;
      
      // Handle different possible values from backend
      if (messageType === 'user') {
        messageType = 'user';
      } else if (messageType === 'ai' || messageType === 'assistant') {
        messageType = 'ai';
      } else {
        // For any other type ('text', null, undefined, etc.), try to infer from sender
        if (msg.sender === 'user') {
          messageType = 'user';
        } else {
          // Default to 'ai' for assistant messages or unclear cases
          messageType = 'ai';
        }
      }

      return {
        id: messageId,
        content: msg.content || '',
        type: messageType as 'user' | 'ai',
        timestamp: msg.timestamp || new Date().toISOString(), // Fallback to current time if timestamp is missing
        liked: Boolean(msg.liked),
        disliked: Boolean(msg.disliked),
        attachments: uniqueAttachments.length > 0 ? uniqueAttachments : undefined
      };
    });

    console.log('Formatted messages:', formattedMessages);

    return {
      messages: formattedMessages,
      isBookmarked: isBookmarked
    };
  } catch (error) {
    console.error('Error loading conversation messages:', error);
    throw error;
  }
};

// Add a timestamp reference for rate limiting
let lastSubscriptionCheckTime = 0;
const SUBSCRIPTION_CHECK_COOLDOWN = 5000; // 5 seconds between checks

/**
 * Check user's subscription status
 * @returns User subscription information
 */
export const checkSubscriptionStatus = async () => {
  try {
    // Add rate limiting
    const now = Date.now();
    if (now - lastSubscriptionCheckTime < SUBSCRIPTION_CHECK_COOLDOWN) {
      console.log(`🔄 API utility subscription check rate limited - Last check ${now - lastSubscriptionCheckTime}ms ago`);
      throw new Error('Rate limited');
    }

    lastSubscriptionCheckTime = now;

    // Use Flask API for subscription status (not migrated to FastAPI yet)
    const response = await axios.get(`${FLASK_BASE_URL}/api/subscription/status`, {
      withCredentials: true
    });
    return response.data;
  } catch (error) {
    console.error('Error checking subscription status:', error);
    throw error;
  }
};

/**
 * Create a Stripe checkout session for subscription
 * @param userId User ID
 * @param email User email
 * @returns Checkout session URL
 */
export const createCheckoutSession = async (userId?: string, email?: string) => {
  try {
    // Use Flask API for payment processing (not migrated to FastAPI yet)
    const response = await axios.post(`${FLASK_BASE_URL}/api/payment/create-checkout-session`, {
      success_url: `${window.location.origin}/payment-success`,
      cancel_url: `${window.location.origin}/subscription`,
      user_id: userId,
      email: email
    }, {
      withCredentials: true
    });
    return response.data;
  } catch (error) {
    console.error('Error creating checkout session:', error);
    throw error;
  }
};

// ==================== FASTAPI CHAT SERVICE UTILITIES ====================

/**
 * Send a chat message to FastAPI talk service (with full AWS integration)
 * @param message The message content
 * @param conversationId Optional conversation ID
 * @param files Optional files to upload
 * @returns Chat response with full AWS stack (DynamoDB, OpenSearch, MemoryDB, Bedrock Knowledge, Bedrock Agents)
 */
export const sendChatMessage = async (
  message: string,
  conversationId?: number,
  files?: File[]
) => {
  try {
    // Convert files to base64 if present (chunked processing for large files)
    const processedFiles = files ? await Promise.all(
      files.map(async (file) => {
        const arrayBuffer = await file.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);
        
        // Convert to string in small chunks to avoid stack overflow, then encode once
        const chunkSize = 8192; // 8KB chunks to safely avoid stack overflow
        let binaryString = '';
        
        for (let i = 0; i < uint8Array.length; i += chunkSize) {
          const chunk = uint8Array.slice(i, i + chunkSize);
          // Use Array.from to safely convert chunk to string
          binaryString += String.fromCharCode.apply(null, Array.from(chunk));
        }
        
        // Encode the complete binary string to base64 (this is fast)
        const base64Content = btoa(binaryString);
        
        return {
          filename: file.name,
          content_type: file.type,
          content: base64Content,
          size: file.size
        };
      })
    ) : [];

    // /api/talk supports both text and files in a single endpoint
    const requestData = {
      message,
      conversation_id: conversationId,
      context: 'chat',
      files: processedFiles
    };

    return await axios.post(`${FASTAPI_BASE_URL}/api/talk`, requestData, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  } catch (error) {
    // Don't log 402 errors (insufficient credits) as they're expected behavior
    if (axios.isAxiosError(error) && error.response?.status !== 402) {
      console.error('Error sending chat message to FastAPI talk service:', error);
    }
    throw error;
  }
};

/**
 * Send a health AI message to FastAPI service
 * @param message The message content
 * @param conversationId Optional conversation ID
 * @param healthContext Optional health context
 * @param files Optional files to upload
 * @returns Health chat response
 */
export const sendHealthMessage = async (
  message: string,
  conversationId?: number,
  healthContext?: any,
  files?: File[]
) => {
  try {
    // Convert files to base64 if present (chunked processing for large files)
    const processedFiles = files ? await Promise.all(
      files.map(async (file) => {
        const arrayBuffer = await file.arrayBuffer();
        const uint8Array = new Uint8Array(arrayBuffer);
        
        // Convert to string in small chunks to avoid stack overflow, then encode once
        const chunkSize = 8192; // 8KB chunks to safely avoid stack overflow
        let binaryString = '';
        
        for (let i = 0; i < uint8Array.length; i += chunkSize) {
          const chunk = uint8Array.slice(i, i + chunkSize);
          // Use Array.from to safely convert chunk to string
          binaryString += String.fromCharCode.apply(null, Array.from(chunk));
        }
        
        // Encode the complete binary string to base64 (this is fast)
        const base64Content = btoa(binaryString);
        
        return {
          filename: file.name,
          content_type: file.type,
          content: base64Content,
          size: file.size
        };
      })
    ) : [];

    return await axios.post(`${FASTAPI_BASE_URL}/api/talk`, {
      message,
      conversation_id: conversationId,
      context: 'health',
      files: processedFiles
    }, {
      withCredentials: true,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  } catch (error) {
    // Don't log 402 errors (insufficient credits) as they're expected behavior
    if (axios.isAxiosError(error) && error.response?.status !== 402) {
      console.error('Error sending health message to FastAPI:', error);
    }
    throw error;
  }
};

/**
 * Get health dashboard data from FastAPI
 * @returns Health dashboard data
 */
export const getHealthDashboard = async () => {
  try {
    const response = await axios.get(`${FASTAPI_BASE_URL}/api/health-intelligence/dashboard`, {
      withCredentials: true
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching health dashboard from FastAPI:', error);
    throw error;
  }
};

/**
 * Get health records from FastAPI
 * @returns Health records
 */
export const getHealthRecords = async () => {
  try {
    const response = await axios.get(`${FASTAPI_BASE_URL}/api/health/records`, {
      withCredentials: true
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching health records from FastAPI:', error);
    throw error;
  }
};

/**
 * Get health summary from FastAPI
 * @returns Health summary
 */
export const getHealthSummary = async () => {
  try {
    const response = await axios.get(`${FASTAPI_BASE_URL}/api/health/summary`, {
      withCredentials: true
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching health summary from FastAPI:', error);
    throw error;
  }
};

/**
 * Send health chat message to FastAPI
 * @param message The message to send
 * @returns Health chat response
 */
export const sendHealthChat = async (message: string) => {
  try {
    const response = await axios.post(`${FASTAPI_BASE_URL}/api/health/chat`, {
      message
    }, {
      withCredentials: true
    });
    return response.data;
  } catch (error) {
    console.error('Error sending health chat to FastAPI:', error);
    throw error;
  }
};

// Export API base URLs for components that need direct access
export {
  API_BASE_URL,           // Points to FastAPI for chat/health features
  FASTAPI_BASE_URL,       // Explicit FastAPI URL
  FLASK_BASE_URL          // Explicit Flask URL for legacy features
}; 