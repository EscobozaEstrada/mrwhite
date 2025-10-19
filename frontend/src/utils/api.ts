import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

/**
 * Fetch conversation history for a user
 * @param userId User ID to fetch history for
 * @returns Formatted conversation history
 */
export const fetchConversationHistory = async (userId: string) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/user/${userId}/conversations`, {
      withCredentials: true
    });

    if (!response.data || !Array.isArray(response.data)) {
      return [];
    }

    // Group conversations by date
    const groupedByDate = response.data.reduce((acc: any, conversation: any) => {
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
    const response = await axios.get(`${API_BASE_URL}/api/bookmarked-conversations`, {
      withCredentials: true
    });

    if (!response.data || !Array.isArray(response.data)) {
      return [];
    }

    return response.data.map((conversation: any) => ({
      id: conversation.id.toString(),
      content: conversation.title || `Conversation ${conversation.id}`,
      type: 'ai' as 'user' | 'ai',
      timestamp: new Date(conversation.updated_at),
      bookmarkedAt: new Date(conversation.updated_at)
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
    const response = await axios.post(
      `${API_BASE_URL}/api/conversations/${conversationId}/bookmark`,
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
    const response = await axios.post(
      `${API_BASE_URL}/api/conversations`,
      { title: process.env.NEXT_PUBLIC_DEFAULT_CONVERSATION_TITLE || 'New Conversation' },
      { withCredentials: true }
    );
    return response.data.conversation.id.toString();
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
    const response = await axios.get(`${API_BASE_URL}/api/conversations/${conversationId}`, {
      withCredentials: true
    });

    if (!response.data || !response.data.messages) {
      return { messages: [], isBookmarked: false };
    }

    // Format the messages according to our Message interface
    const formattedMessages = response.data.messages.map((msg: any) => ({
      id: msg.id.toString(),
      content: msg.content,
      type: msg.type,
      timestamp: new Date(msg.created_at),
      liked: msg.liked,
      disliked: msg.disliked,
      attachments: Array.isArray(msg.attachments) && msg.attachments.length > 0
        ? msg.attachments.map((attachment: any) => ({
          type: attachment.type,
          url: attachment.url,
          name: attachment.name
        }))
        : undefined
    }));

    return {
      messages: formattedMessages,
      isBookmarked: response.data.is_bookmarked || false
    };
  } catch (error) {
    console.error('Error loading conversation messages:', error);
    throw error;
  }
};

/**
 * Check user's subscription status
 * @returns User subscription information
 */
export const checkSubscriptionStatus = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/subscription/status`, {
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
    const response = await axios.post(`${API_BASE_URL}/api/payment/create-checkout-session`, {
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