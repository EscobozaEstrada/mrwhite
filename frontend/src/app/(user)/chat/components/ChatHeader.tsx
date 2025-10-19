"use client";

import { useState } from "react";
import { FiSearch, FiCalendar, FiX, FiVolume2, FiVolumeX } from "react-icons/fi";
import ClearChatDialog from "./ClearChatDialog";

interface ChatHeaderProps {
  onClearChat: (clearMemory: boolean) => Promise<void>;
  onSearchQueryChange?: (query: string) => void;
  onDateSelect?: (date: string) => void;
  voiceMode?: boolean;
  onVoiceModeToggle?: () => void;
}

export default function ChatHeader({ onClearChat, onSearchQueryChange, onDateSelect, voiceMode, onVoiceModeToggle }: ChatHeaderProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDate, setSelectedDate] = useState("");
  const [isClearDialogOpen, setIsClearDialogOpen] = useState(false);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearchQueryChange) {
      onSearchQueryChange(searchQuery);
    }
  };

  const handleDateChange = (date: string) => {
    setSelectedDate(date);
    if (onDateSelect) {
      onDateSelect(date);
    }
  };

  const handleTodayClick = () => {
    const today = new Date().toISOString().split('T')[0]; // Format: YYYY-MM-DD
    setSelectedDate(today);
    if (onDateSelect) {
      onDateSelect(today);
    }
  };

  return (
    <>
      <div className="px-4 py-2 flex items-center justify-center relative">
        {/* Centered Search Container (Capsule) */}
        <div className="flex items-center bg-[#1a1a1a] rounded-full px-4 py-2 border border-gray-800">
          {/* Search Bar */}
          {/* <form onSubmit={handleSearch} className="flex-1">
            <div className="relative">
              <FiSearch className="absolute left-0 top-1/2 transform -translate-y-1/2 text-gray-500" size={18} />
              <input
                type="text"
                placeholder="Search chats..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent text-gray-300 pl-7 pr-4 py-1 text-sm focus:outline-none placeholder-gray-500 w-64"
              />
            </div>
          </form> */}

          {/* Date Selector */}
          <div className="relative flex items-center">
            <FiCalendar className="absolute left-0 text-gray-500 pointer-events-none z-10" size={16} />
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => handleDateChange(e.target.value)}
              className="bg-transparent text-gray-300 text-sm pl-6 pr-2 py-1 focus:outline-none cursor-pointer [&::-webkit-calendar-picker-indicator]:opacity-0 [&::-webkit-calendar-picker-indicator]:absolute [&::-webkit-calendar-picker-indicator]:inset-0 [&::-webkit-calendar-picker-indicator]:w-full [&::-webkit-calendar-picker-indicator]:h-full [&::-webkit-calendar-picker-indicator]:cursor-pointer"
            />
          </div>

          {/* Today Badge */}
          <div 
            onClick={handleTodayClick}
            className="bg-purple-600 hover:bg-purple-700 px-3 py-1 rounded-full text-xs font-medium text-white cursor-pointer transition-colors"
          >
            today
          </div>
        </div>

        {/* Clear Chat Button - Absolute Right */}
        {/* Voice Mode Toggle */}
        {onVoiceModeToggle && (
          <button
            onClick={onVoiceModeToggle}
            className={`absolute right-28 flex items-center space-x-2 rounded-lg px-3 py-2 transition-colors text-sm font-medium ${
              voiceMode
                ? "bg-purple-600 hover:bg-purple-700 text-white"
                : "bg-gray-700 hover:bg-gray-600 text-gray-300"
            }`}
            title={voiceMode ? "Voice Mode ON - AI will speak responses" : "Voice Mode OFF"}
          >
            {voiceMode ? <FiVolume2 size={16} /> : <FiVolumeX size={16} />}
            <span className="hidden sm:inline">{voiceMode ? "Voice ON" : "Voice OFF"}</span>
          </button>
        )}

        {/* Clear Button */}
        <button
          onClick={() => setIsClearDialogOpen(true)}
          className="absolute right-6 flex items-center space-x-2 bg-red-600 hover:bg-red-700 text-white rounded-lg px-3 py-2 transition-colors text-sm font-medium"
        >
          <FiX size={16} />
          <span>Clear</span>
        </button>
      </div>

      {/* Clear Chat Dialog */}
      <ClearChatDialog
        isOpen={isClearDialogOpen}
        onClose={() => setIsClearDialogOpen(false)}
        onConfirm={onClearChat}
      />
    </>
  );
}

