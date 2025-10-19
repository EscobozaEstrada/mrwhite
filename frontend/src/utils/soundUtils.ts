// Sound utility for playing notification sounds

// Local storage key for sound preferences
const SOUND_PREFS_KEY = 'mr_white_sound_preferences';

// Default sound preferences
const DEFAULT_SOUND_PREFS = {
  enabled: true,
  volume: 0.5,
};

// Sound file paths
const SOUNDS = {
  success: '/sounds/success.mp3',
  error: '/sounds/error.mp3',
  loading: '/sounds/loading.mp3',
};

// Cache for audio objects
const audioCache: Record<string, HTMLAudioElement> = {};

/**
 * Get user sound preferences from localStorage
 */
export const getSoundPreferences = (): typeof DEFAULT_SOUND_PREFS => {
  if (typeof window === 'undefined') return DEFAULT_SOUND_PREFS;
  
  try {
    const savedPrefs = localStorage.getItem(SOUND_PREFS_KEY);
    if (savedPrefs) {
      return { ...DEFAULT_SOUND_PREFS, ...JSON.parse(savedPrefs) };
    }
  } catch (error) {
    console.error('Error loading sound preferences:', error);
  }
  
  return DEFAULT_SOUND_PREFS;
};

/**
 * Save user sound preferences to localStorage
 */
export const saveSoundPreferences = (prefs: Partial<typeof DEFAULT_SOUND_PREFS>) => {
  if (typeof window === 'undefined') return;
  
  try {
    const currentPrefs = getSoundPreferences();
    const updatedPrefs = { ...currentPrefs, ...prefs };
    localStorage.setItem(SOUND_PREFS_KEY, JSON.stringify(updatedPrefs));
  } catch (error) {
    console.error('Error saving sound preferences:', error);
  }
};

/**
 * Toggle sound on/off
 */
export const toggleSound = (enabled: boolean) => {
  saveSoundPreferences({ enabled });
};

/**
 * Set sound volume
 */
export const setSoundVolume = (volume: number) => {
  saveSoundPreferences({ volume });
};

/**
 * Preload sound files for faster playback
 */
export const preloadSounds = () => {
  if (typeof window === 'undefined') return;
  
  Object.entries(SOUNDS).forEach(([key, path]) => {
    try {
      const audio = new Audio(path);
      audio.preload = 'auto';
      audioCache[key] = audio;
    } catch (error) {
      console.error(`Error preloading sound ${key}:`, error);
    }
  });
};

/**
 * Play a notification sound
 */
export const playNotificationSound = (type: 'success' | 'error' | 'loading') => {
  if (typeof window === 'undefined') return;
  
  const prefs = getSoundPreferences();
  if (!prefs.enabled) return;
  
  try {
    // Use cached audio if available, otherwise create new
    let audio = audioCache[type] || new Audio(SOUNDS[type]);
    
    // Set volume
    audio.volume = prefs.volume;
    
    // Play sound
    audio.currentTime = 0;
    audio.play().catch(err => {
      console.error(`Error playing ${type} sound:`, err);
    });
  } catch (error) {
    console.error(`Error playing ${type} sound:`, error);
  }
};

// Initialize by preloading sounds
if (typeof window !== 'undefined') {
  // Only preload in browser environment
  window.addEventListener('DOMContentLoaded', preloadSounds);
}
