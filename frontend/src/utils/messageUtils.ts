import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL;

// Track the speaking state globally
let isSpeaking = false;

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

// Audio player instance for Eleven Labs TTS
let audioPlayer: HTMLAudioElement | null = null;

/**
 * Stop any currently playing audio
 */
export const stopSpeaking = () => {
  if (audioPlayer) {
    audioPlayer.pause();
    audioPlayer = null;
  }

  // Also stop any native speech synthesis
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }

  isSpeaking = false;
};

/**
 * Use Eleven Labs text-to-speech to speak a message
 * @param text Text to speak
 * @param onStateChange Callback to update UI state (loading/speaking/stopped)
 * @returns Function to check if speaking is active
 */
export const speakText = async (text: string, onStateChange?: (state: 'loading' | 'speaking' | 'stopped') => void) => {
  // If already speaking, stop it
  if (isSpeaking) {
    stopSpeaking();
    if (onStateChange) onStateChange('stopped');
    return;
  }

  // Set speaking state to true
  isSpeaking = true;

  // Notify that we're loading the audio
  if (onStateChange) onStateChange('loading');

  try {
    // Strip markdown formatting before speaking
    const plainText = stripMarkdown(text);

    // Stop any currently playing audio
    stopSpeaking();

    // Call our backend API to proxy the Eleven Labs request
    // This avoids exposing API keys in the frontend
    const response = await axios.post(
      `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/text-to-speech`,
      {
        text: plainText
      },
      {
        responseType: 'blob',
        withCredentials: true
      }
    );

    // Create a blob URL from the audio data
    const audioBlob = new Blob([response.data], { type: 'audio/mpeg' });
    const audioUrl = URL.createObjectURL(audioBlob);

    // Create and play audio
    audioPlayer = new Audio(audioUrl);

    // Update state to speaking when audio starts playing
    if (onStateChange) onStateChange('speaking');

    audioPlayer.addEventListener('ended', () => {
      // Clean up the blob URL when audio playback is complete
      URL.revokeObjectURL(audioUrl);
      audioPlayer = null;
      isSpeaking = false;

      // Update state to stopped when audio finishes
      if (onStateChange) onStateChange('stopped');
    });

    // Play the audio
    await audioPlayer.play();

  } catch (error) {
    console.error('Error using Eleven Labs TTS:', error);

    // Reset speaking state
    isSpeaking = false;

    // Fallback to browser's native TTS if Eleven Labs fails
    const fallbackText = stripMarkdown(text);
    const utterance = new SpeechSynthesisUtterance(fallbackText);

    // Set up event handlers for native speech synthesis
    utterance.onstart = () => {
      if (onStateChange) onStateChange('speaking');
    };

    utterance.onend = () => {
      isSpeaking = false;
      if (onStateChange) onStateChange('stopped');
    };

    utterance.onerror = () => {
      isSpeaking = false;
      if (onStateChange) onStateChange('stopped');
    };

    speechSynthesis.speak(utterance);

    // Update state to speaking (in case onstart doesn't fire)
    if (onStateChange) onStateChange('speaking');
  }
};

/**
 * Handle like/dislike for a message
 * @param messageId ID of the message to like/dislike
 * @param isLike Whether this is a like (true) or dislike (false)
 * @returns Updated message data from the server
 */
export const handleMessageReaction = async (messageId: string, isLike: boolean) => {
  try {
    // Save reaction to database
    const response = await axios.post(`${API_BASE_URL}/api/messages/${messageId}/reaction`, {
      type: isLike ? 'like' : 'dislike'
    }, {
      withCredentials: true
    });

    // Return the updated message data from the server
    return response.data;
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
  attachments?: Array<{ type: string, url: string, name: string }>
) => {
  try {
    // Convert conversation ID to number if it's a string
    const numericConversationId = conversationId && conversationId !== 'new-chat' 
      ? parseInt(conversationId, 10) 
      : undefined;

    // Use the dedicated retry endpoint to regenerate response
    // This tells the backend to generate a different response to the same query
    const response = await axios.post(`${API_BASE_URL}/api/messages/${messageId}/retry`, {
      message: userMessageContent, // EXACT original message
      context: 'chat',
      conversation_id: numericConversationId,
      files: []
    }, {
      withCredentials: true
    });

    // Return the content from the response (FastAPI returns content, not response)
    return response.data.content || response.data.response;
  } catch (error) {
    console.error('Error retrying message:', error);
    throw error;
  }
}; 