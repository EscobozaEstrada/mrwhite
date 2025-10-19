/**
 * Date utility functions for chat messages
 */

export interface Message {
  id: string;
  timestamp: Date;
  [key: string]: any;
}

export interface GroupedMessages {
  date: Date;
  dateLabel: string;
  messages: Message[];
}

/**
 * Format date as human-readable label
 */
export function formatDateLabel(date: Date): string {
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  // Reset time parts for comparison
  const dateOnly = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const todayOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const yesterdayOnly = new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate());

  if (dateOnly.getTime() === todayOnly.getTime()) {
    return 'Today';
  } else if (dateOnly.getTime() === yesterdayOnly.getTime()) {
    return 'Yesterday';
  } else {
    // Format as "Wednesday, October 8th"
    const options: Intl.DateTimeFormatOptions = {
      weekday: 'long',
      month: 'long',
      day: 'numeric'
    };
    
    const formatted = date.toLocaleDateString('en-US', options);
    
    // Add ordinal suffix (st, nd, rd, th)
    const day = date.getDate();
    const suffix = getOrdinalSuffix(day);
    
    // Replace the day number with day + suffix
    return formatted.replace(/\d+/, `${day}${suffix}`);
  }
}

/**
 * Get ordinal suffix for a number (1st, 2nd, 3rd, 4th, etc.)
 */
function getOrdinalSuffix(day: number): string {
  if (day > 3 && day < 21) return 'th';
  switch (day % 10) {
    case 1: return 'st';
    case 2: return 'nd';
    case 3: return 'rd';
    default: return 'th';
  }
}

/**
 * Group messages by date
 */
export function groupMessagesByDate(messages: Message[]): GroupedMessages[] {
  const groups: { [key: string]: Message[] } = {};

  messages.forEach((message) => {
    const date = new Date(message.timestamp);
    const dateKey = date.toDateString(); // Use date string as key

    if (!groups[dateKey]) {
      groups[dateKey] = [];
    }
    groups[dateKey].push(message);
  });

  // Convert to array and sort by date
  return Object.entries(groups)
    .map(([dateKey, messages]) => ({
      date: new Date(dateKey),
      dateLabel: formatDateLabel(new Date(dateKey)),
      messages: messages,
    }))
    .sort((a, b) => a.date.getTime() - b.date.getTime());
}

/**
 * Check if two dates are the same day
 */
export function isSameDay(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  );
}


