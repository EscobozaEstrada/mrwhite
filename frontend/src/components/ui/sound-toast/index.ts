import originalToast from 'react-hot-toast';
import { playNotificationSound } from '@/utils/soundUtils';

// Enhanced toast functions with sound
const toast = {
  success: (message: string, options?: any) => {
    playNotificationSound('success');
    return originalToast.success(message, options);
  },
  
  error: (message: string, options?: any) => {
    playNotificationSound('error');
    return originalToast.error(message, options);
  },

  loading: (message: string, options?: any) => {
    playNotificationSound('loading');
    return originalToast.loading(message, options);
  },
  
  // Pass through other toast methods
  ...Object.entries(originalToast)
    .filter(([key]) => !['success', 'error', 'loading'].includes(key))
    .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {})
};

// Export as both default and named export
export { toast };
export default toast; 