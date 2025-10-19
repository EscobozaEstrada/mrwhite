'use client';

import React, { useEffect, useState } from 'react';
import { Globe, Clock, Check } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';

interface TimezoneDetectorProps {
  onTimezoneDetected?: (timezone: string) => void;
  showNotification?: boolean;
}

/**
 * 🌍 GLOBAL TIMEZONE DETECTOR
 * Automatically detects user's timezone and optionally updates it in the backend
 */
export const TimezoneDetector: React.FC<TimezoneDetectorProps> = ({
  onTimezoneDetected,
  showNotification = true
}) => {
  const { user } = useAuth(); // Get user authentication state
  const [currentTimezone, setCurrentTimezone] = useState<string>('');
  const [detectedTimezone, setDetectedTimezone] = useState<string>('');
  const [isUpdating, setIsUpdating] = useState(false);
  const [showUpdatePrompt, setShowUpdatePrompt] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);

  useEffect(() => {
    // Only run timezone detection if user is authenticated
    if (user) {
      detectTimezone();
    }
  }, [user]);

  const detectTimezone = () => {
    try {
      // Get user's current timezone using Intl API
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      setDetectedTimezone(timezone);
      
      // Get user's current timezone from backend/context if available
      // This would typically come from user context or API call
      getCurrentUserTimezone().then(userTimezone => {
        setCurrentTimezone(userTimezone || 'UTC');
        
        // If detected timezone differs from stored timezone, show update prompt
        if (timezone !== userTimezone && userTimezone && showNotification) {
          setShowUpdatePrompt(true);
        }
      });

      if (onTimezoneDetected) {
        onTimezoneDetected(timezone);
      }
    } catch (error) {
      console.error('Error detecting timezone:', error);
    }
  };

  const getCurrentUserTimezone = async (): Promise<string | null> => {
    try {
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/me`,
        { withCredentials: true }
      );
      return response.data?.timezone || null;
    } catch (error) {
      // Silently handle 401/404 errors for non-authenticated users
      if (axios.isAxiosError(error) && (error.response?.status === 401 || error.response?.status === 404)) {
        return null; // User not authenticated, no need to log error
      }
      console.error('Error fetching user timezone:', error);
      return null;
    }
  };

  const updateTimezone = async () => {
    setIsUpdating(true);
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/update-timezone`,
        { timezone: detectedTimezone },
        { withCredentials: true }
      );
      
      setCurrentTimezone(detectedTimezone);
      setShowUpdatePrompt(false);
      setUpdateSuccess(true);
      
      // Hide success message after 3 seconds
      setTimeout(() => setUpdateSuccess(false), 3000);
      
    } catch (error) {
      console.error('Error updating timezone:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  const formatTimezone = (timezone: string) => {
    // Convert timezone to readable format
    const now = new Date();
    const formatter = new Intl.DateTimeFormat('en-US', {
      timeZone: timezone,
      timeZoneName: 'short'
    });
    
    const parts = formatter.formatToParts(now);
    const timeZoneName = parts.find(part => part.type === 'timeZoneName')?.value || '';
    
    return `${timezone.replace('_', ' ')} (${timeZoneName})`;
  };

  // Don't render anything if user is not authenticated
  if (!user) {
    return null;
  }

  if (updateSuccess) {
    return (
      <div className="fixed top-20 sm:top-24 md:top-28 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-[60] flex items-center space-x-2">
        <Check className="w-4 h-4" />
        <span>Timezone updated successfully!</span>
      </div>
    );
  }

  if (!showUpdatePrompt) {
    return null;
  }

  return (
    <div className="fixed top-20 sm:top-24 md:top-28 right-4 bg-blue-500 text-white p-4 rounded-lg shadow-lg z-[60] max-w-sm">
      <div className="flex items-start space-x-3">
        <Globe className="w-6 h-6 mt-1 flex-shrink-0" />
        <div className="flex-1">
          <h3 className="font-semibold text-sm mb-2">Timezone Update Available</h3>
          <p className="text-xs mb-3 opacity-90">
            We detected your timezone as <strong>{formatTimezone(detectedTimezone)}</strong>.
            Your current setting is <strong>{formatTimezone(currentTimezone)}</strong>.
          </p>
          <div className="flex space-x-2">
            <button
              onClick={updateTimezone}
              disabled={isUpdating}
              className="bg-white text-blue-500 px-3 py-1 rounded text-xs font-medium hover:bg-gray-100 disabled:opacity-50"
            >
              {isUpdating ? 'Updating...' : 'Update'}
            </button>
            <button
              onClick={() => setShowUpdatePrompt(false)}
              className="text-white px-3 py-1 rounded text-xs border border-white/30 hover:bg-white/10"
            >
              Later
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

/**
 * 🌍 TIMEZONE UTILS
 * Utility functions for timezone handling
 */
export const TimezoneUtils = {
  /**
   * Get user's current timezone
   */
  getCurrentTimezone: (): string => {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  },

  /**
   * Convert a date to user's timezone
   */
  toUserTimezone: (date: Date, timezone?: string): Date => {
    const userTimezone = timezone || TimezoneUtils.getCurrentTimezone();
    return new Date(date.toLocaleString('en-US', { timeZone: userTimezone }));
  },

  /**
   * Format date in user's timezone
   */
  formatInTimezone: (date: Date, timezone?: string, options?: Intl.DateTimeFormatOptions): string => {
    const userTimezone = timezone || TimezoneUtils.getCurrentTimezone();
    return date.toLocaleString('en-US', {
      timeZone: userTimezone,
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...options
    });
  },

  /**
   * Get timezone offset in hours
   */
  getTimezoneOffset: (timezone?: string): number => {
    const userTimezone = timezone || TimezoneUtils.getCurrentTimezone();
    const now = new Date();
    const utc = new Date(now.getTime() + (now.getTimezoneOffset() * 60000));
    const local = new Date(utc.toLocaleString('en-US', { timeZone: userTimezone }));
    return (local.getTime() - utc.getTime()) / (1000 * 60 * 60);
  },

  /**
   * List of common timezones with friendly names
   */
  commonTimezones: [
    { value: 'America/New_York', label: 'Eastern Time (US)' },
    { value: 'America/Chicago', label: 'Central Time (US)' },
    { value: 'America/Denver', label: 'Mountain Time (US)' },
    { value: 'America/Los_Angeles', label: 'Pacific Time (US)' },
    { value: 'Europe/London', label: 'London, UK' },
    { value: 'Europe/Paris', label: 'Paris, France' },
    { value: 'Europe/Berlin', label: 'Berlin, Germany' },
    { value: 'Asia/Tokyo', label: 'Tokyo, Japan' },
    { value: 'Asia/Shanghai', label: 'Shanghai, China' },
    { value: 'Asia/Kolkata', label: 'Mumbai, India' },
    { value: 'Asia/Dubai', label: 'Dubai, UAE' },
    { value: 'Australia/Sydney', label: 'Sydney, Australia' },
    { value: 'UTC', label: 'UTC (Coordinated Universal Time)' }
  ]
};

export default TimezoneDetector;
