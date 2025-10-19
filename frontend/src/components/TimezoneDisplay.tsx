'use client';

import { useState, useEffect } from 'react';
import { Clock, Globe, MapPin } from 'lucide-react';

interface TimezoneDisplayProps {
  userTimezone?: string;
  className?: string;
  format?: 'compact' | 'detailed';
  showIcon?: boolean;
  showDate?: boolean;
  auto24Hour?: boolean;
}

export default function TimezoneDisplay({
  userTimezone,
  className = '',
  format = 'detailed',
  showIcon = true,
  showDate = false,
  auto24Hour = false
}: TimezoneDisplayProps) {
  const [currentTime, setCurrentTime] = useState<string>('');
  const [timezone, setTimezone] = useState<string>('');
  const [timezoneAbbr, setTimezoneAbbr] = useState<string>('');
  const [userTz, setUserTz] = useState<string>(userTimezone || 'UTC');

  // Auto-detect user timezone if not provided
  useEffect(() => {
    if (!userTimezone) {
      const detectedTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      setUserTz(detectedTz);
    }
  }, [userTimezone]);

  useEffect(() => {
    const updateTime = () => {
      try {
        const now = new Date();
        
        // Format time based on user preference
        const timeOptions: Intl.DateTimeFormatOptions = {
          timeZone: userTz,
          hour: '2-digit',
          minute: '2-digit',
          hour12: !auto24Hour,
          ...(showDate && {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
          })
        };

        const formattedTime = now.toLocaleString('en-US', timeOptions);
        setCurrentTime(formattedTime);
        
        // Get timezone abbreviation
        const shortFormat = now.toLocaleString('en-US', {
          timeZone: userTz,
          timeZoneName: 'short'
        });
        
        // Extract timezone abbreviation from the formatted string
        const tzMatch = shortFormat.match(/\b([A-Z]{3,4})\b$/);
        const abbreviation = tzMatch ? tzMatch[1] : 'UTC';
        
        setTimezoneAbbr(abbreviation);
        
        // Clean up timezone name for display
        const cleanTz = userTz.replace('_', ' ').split('/').pop() || userTz;
        setTimezone(cleanTz);
        
      } catch (error) {
        console.error('Error updating time:', error);
        setCurrentTime('Time unavailable');
        setTimezoneAbbr('UTC');
        setTimezone('UTC');
      }
    };

    // Initial update
    updateTime();
    
    // Update every second
    const interval = setInterval(updateTime, 1000);
    
    return () => clearInterval(interval);
  }, [userTz, showDate, auto24Hour]);

  if (format === 'compact') {
    return (
      <div className={`flex items-center gap-1 text-sm ${className}`}>
        {showIcon && <Clock className="w-4 h-4" />}
        <span className="font-medium">{currentTime}</span>
        <span className="text-gray-500">({timezoneAbbr})</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {showIcon && <Globe className="w-5 h-5 text-blue-500" />}
      <div className="flex flex-col">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Your Local Time</span>
        </div>
        <div className="flex items-center gap-2 text-lg font-bold">
          {currentTime}
        </div>
        <div className="flex items-center gap-1 text-sm text-gray-500">
          <MapPin className="w-3 h-3" />
          <span>{timezoneAbbr} ({timezone})</span>
        </div>
      </div>
    </div>
  );
}
