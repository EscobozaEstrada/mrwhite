import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

/**
 * Copy text to clipboard
 * @param text Text to copy to clipboard
 * @param stripFormatting Whether to strip markdown formatting (default: false)
 */
export const copyToClipboard = (text: string, stripFormatting: boolean = false) => {
  // If stripFormatting is true, remove markdown formatting
  const textToCopy = stripFormatting ? stripMarkdown(text) : text;
  
  if (navigator.clipboard && window.isSecureContext) {
    // Modern API available in secure contexts
    navigator.clipboard.writeText(textToCopy)
      .catch(err => {
        console.error('Failed to copy text:', err);
      });
  } else {
    // Fallback for older browsers or non-secure contexts
    const textArea = document.createElement('textarea');
    textArea.value = textToCopy;
    textArea.style.position = 'fixed';  // Avoid scrolling to bottom
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
      document.execCommand('copy');
    } catch (err) {
      console.error('Failed to copy text:', err);
    }

    document.body.removeChild(textArea);
  }
};

/**
 * Strip markdown formatting from text
 * @param text Text with markdown formatting
 * @returns Plain text without markdown formatting
 */
const stripMarkdown = (text: string): string => {
  // Remove headers
  let plainText = text.replace(/#{1,6}\s+/g, '');
  
  // Remove bold and italic
  plainText = plainText.replace(/(\*\*|__)(.*?)\1/g, '$2'); // Bold
  plainText = plainText.replace(/(\*|_)(.*?)\1/g, '$2');    // Italic
  
  // Remove links
  plainText = plainText.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
  
  // Remove code blocks
  plainText = plainText.replace(/```[\s\S]*?```/g, '');
  plainText = plainText.replace(/`([^`]+)`/g, '$1');
  
  // Remove blockquotes
  plainText = plainText.replace(/^\s*>\s+/gm, '');
  
  // Remove list markers
  plainText = plainText.replace(/^\s*[\*\-+]\s+/gm, '');
  plainText = plainText.replace(/^\s*\d+\.\s+/gm, '');
  
  // Remove horizontal rules
  plainText = plainText.replace(/^\s*[-*_]{3,}\s*$/gm, '');
  
  // Remove images
  plainText = plainText.replace(/!\[([^\]]+)\]\([^)]+\)/g, '');
  
  // Remove HTML tags
  plainText = plainText.replace(/<[^>]*>/g, '');
  
  // Remove extra whitespace
  plainText = plainText.replace(/\n{3,}/g, '\n\n');
  
  return plainText.trim();
};

/**
 * Use text-to-speech to speak a message
 * @param text Text to speak
 */
export const speakText = (text: string) => {
  // Strip markdown formatting before speaking
  const plainText = stripMarkdown(text);
  
  const utterance = new SpeechSynthesisUtterance(plainText);
  speechSynthesis.speak(utterance);
};

/**
 * Handle like/dislike for a message
 * @param messageId ID of the message to like/dislike
 * @param isLike Whether this is a like (true) or dislike (false)
 */
export const handleMessageReaction = async (messageId: string, isLike: boolean) => {
  try {
    // Save reaction to database
    await axios.post(`${API_BASE_URL}/api/messages/${messageId}/reaction`, {
      type: isLike ? 'like' : 'dislike'
    }, {
      withCredentials: true
    });
    return true;
  } catch (error) {
    console.error('Error saving reaction:', error);
    throw error;
  }
};

/**
 * Bookmark a message
 * @param messageId ID of the message to bookmark
 */
export const bookmarkMessage = async (messageId: string) => {
  try {
    // Toggle bookmark status on the backend
    await axios.post(`${API_BASE_URL}/api/messages/${messageId}/bookmark`, {}, {
      withCredentials: true
    });
    return true;
  } catch (error) {
    console.error('Error bookmarking message:', error);
    throw error;
  }
};

/**
 * Retry an AI message generation
 * @param messageId ID of the AI message to retry
 * @param userMessageContent Content of the user message that prompted this AI response
 * @param conversationId ID of the conversation
 * @param attachments Any attachments from the original user message
 * @returns New AI response
 */
export const retryAiMessage = async (
  messageId: string,
  userMessageContent: string,
  conversationId: string,
  attachments?: Array<{type: string, url: string, name: string}>
) => {
  try {
    // Re-send the user message to get a new AI response
    const response = await axios.post(`${API_BASE_URL}/api/chat`, {
      message: userMessageContent,
      context: attachments?.length ? 'file_upload' : 'chat',
      conversationId: conversationId,
      attachments: attachments || []
    }, {
      withCredentials: true
    });

    return response.data.response;
  } catch (error) {
    console.error('Error retrying message:', error);
    throw error;
  }
}; 