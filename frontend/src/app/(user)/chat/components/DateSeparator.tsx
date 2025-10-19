"use client";

interface DateSeparatorProps {
  label: string;
  dateKey?: string; // Used for scrolling to specific dates
}

export default function DateSeparator({ label, dateKey }: DateSeparatorProps) {
  return (
    <div 
      className="flex items-center justify-center my-8 rounded-lg py-2 transition-colors duration-500"
      data-date={dateKey} // For date-based scrolling
    >
      <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-700 to-gray-700"></div>
      
      <div className="px-4">
        <div className="bg-[#1a1a1a] border border-gray-800 rounded-full px-6 py-2">
          <span className="text-sm font-medium text-gray-400">
            {label}
          </span>
        </div>
      </div>
      
      <div className="flex-1 h-px bg-gradient-to-l from-transparent via-gray-700 to-gray-700"></div>
    </div>
  );
}

