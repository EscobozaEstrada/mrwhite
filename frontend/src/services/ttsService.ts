/**
 * Text-to-Speech Service using ElevenLabs API
 */

const ELEVENLABS_API_KEY = process.env.NEXT_PUBLIC_ELEVEN_LABS_API_KEY;
const ELEVENLABS_VOICE_ID = process.env.NEXT_PUBLIC_MR_WHITE_VOICE_ID;
const ELEVENLABS_API_URL = 'https://api.elevenlabs.io/v1/text-to-speech';

// Debug: Log environment variables (remove in production)
console.log('🔊 TTS Config:', {
  hasApiKey: !!ELEVENLABS_API_KEY,
  hasVoiceId: !!ELEVENLABS_VOICE_ID,
  apiKey: ELEVENLABS_API_KEY ? `${ELEVENLABS_API_KEY.substring(0, 10)}...` : 'NOT SET',
  voiceId: ELEVENLABS_VOICE_ID || 'NOT SET'
});

// Audio player instance
let currentAudio: HTMLAudioElement | null = null;

/**
 * Convert text to speech using ElevenLabs and play it
 * @param text - The text to convert to speech
 * @returns Promise that resolves when audio finishes playing
 */
export async function textToSpeech(text: string): Promise<void> {
  if (!ELEVENLABS_API_KEY || !ELEVENLABS_VOICE_ID) {
    console.error('❌ TTS Config missing:', {
      apiKey: ELEVENLABS_API_KEY,
      voiceId: ELEVENLABS_VOICE_ID,
      allEnvVars: Object.keys(process.env).filter(k => k.includes('ELEVEN') || k.includes('VOICE'))
    });
    throw new Error('ElevenLabs API key or Voice ID not configured');
  }

  // Stop any currently playing audio
  stopAudio();

  try {
    // Clean markdown from text
    const cleanText = cleanMarkdown(text);

    // Call ElevenLabs API
    const response = await fetch(`${ELEVENLABS_API_URL}/${ELEVENLABS_VOICE_ID}`, {
      method: 'POST',
      headers: {
        'Accept': 'audio/mpeg',
        'Content-Type': 'application/json',
        'xi-api-key': ELEVENLABS_API_KEY,
      },
      body: JSON.stringify({
        text: cleanText,
        model_id: 'eleven_monolingual_v1',
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.5,
        },
      }),
    });

    if (!response.ok) {
      throw new Error(`ElevenLabs API error: ${response.statusText}`);
    }

    // Convert response to audio blob
    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);

    // Create and play audio
    currentAudio = new Audio(audioUrl);
    
    return new Promise((resolve, reject) => {
      if (currentAudio) {
        // Resolve when audio ENDS playing (not when it starts)
        currentAudio.onended = () => {
          URL.revokeObjectURL(audioUrl);
          currentAudio = null;
          resolve(); // Resolve when audio actually finishes
        };
        
        currentAudio.onerror = () => {
          URL.revokeObjectURL(audioUrl);
          currentAudio = null;
          reject(new Error('Audio playback failed'));
        };
        
        currentAudio.play().catch(reject);
      } else {
        reject(new Error('Audio creation failed'));
      }
    });
  } catch (error) {
    console.error('TTS Error:', error);
    throw error;
  }
}

/**
 * Stop currently playing audio
 */
export function stopAudio(): void {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }
}

/**
 * Check if audio is currently playing
 */
export function isPlaying(): boolean {
  return currentAudio !== null && !currentAudio.paused;
}

/**
 * Clean markdown and special characters from text for TTS
 */
function cleanMarkdown(text: string): string {
  return text
    // Remove markdown links [text](url)
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove markdown images ![alt](url)
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '')
    // Remove markdown bold/italic
    .replace(/(\*\*|__)(.*?)\1/g, '$2')
    .replace(/(\*|_)(.*?)\1/g, '$2')
    // Remove markdown headers
    .replace(/^#+\s+/gm, '')
    // Remove markdown code blocks
    .replace(/```[\s\S]*?```/g, '')
    // Remove inline code
    .replace(/`([^`]+)`/g, '$1')
    // Remove bullet points
    .replace(/^[\*\-]\s+/gm, '')
    // Remove numbered lists
    .replace(/^\d+\.\s+/gm, '')
    // Remove multiple newlines
    .replace(/\n{3,}/g, '\n\n')
    // Remove emojis (optional - comment out if you want to keep them)
    .replace(/[\u{1F600}-\u{1F64F}]/gu, '')
    .replace(/[\u{1F300}-\u{1F5FF}]/gu, '')
    .replace(/[\u{1F680}-\u{1F6FF}]/gu, '')
    .replace(/[\u{1F1E0}-\u{1F1FF}]/gu, '')
    .replace(/[\u{2600}-\u{26FF}]/gu, '')
    .replace(/[\u{2700}-\u{27BF}]/gu, '')
    // Trim whitespace
    .trim();
}

