"use client"

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PiInfo } from "react-icons/pi";
import { FiBookmark, FiClock } from "react-icons/fi";
import { FaPlus } from "react-icons/fa6";
import { useRouter } from "next/navigation";
import { createNewConversation } from "@/utils/api";
import HowItWorksModal from "@/components/HowItWorksModal";

interface ChatHeaderProps {
  fetchBookmarks: () => void;
  toggleHistory: () => void;
  user: any;
  clearChat?: () => void;
}

const ChatHeader = ({ fetchBookmarks, toggleHistory, user, clearChat }: ChatHeaderProps) => {
  const router = useRouter();
  const [isHowItWorksOpen, setIsHowItWorksOpen] = useState(false);

  const handleNewChat = async () => {
    if (clearChat) {
      clearChat();
    }
    
    // First navigate to new-chat to clear the UI
    router.push('/talk/conversation/new-chat');
    
    // We don't need to create a conversation here
    // The conversation will be created when the user sends their first message
    // This fixes both issues:
    // 1. Conversation will be titled with the first message
    // 2. No empty conversations will be created
  };

  return (
    <div className="flex w-full max-w-7xl justify-between items-center mb-4 md:mb-8 px-2 md:px-4">
      <Button
        onClick={() => setIsHowItWorksOpen(true)}
        className="flex items-center gap-1 text-[16px] md:text-[20px] font-public-sans font-medium bg-neutral-900 hover:bg-white/30 text-white p-2"
      >
        <PiInfo />
        <p className="hidden sm:inline">How does it work?</p>
      </Button>
      <div className="flex gap-2 md:gap-4">
        <Button
          onClick={() => {
            if (user) {
              fetchBookmarks();
            } else {
              router.push('/login');
            }
          }}
          className="flex items-center gap-1 text-[16px] md:text-[20px] font-public-sans font-medium bg-neutral-900 hover:bg-white/30 text-white p-2"
        >
          <FiBookmark />
          <p className="hidden sm:inline">Bookmarks</p>
        </Button>
        <Button
          onClick={() => {
            if (user) {
              toggleHistory();
            } else {
              router.push('/login');
            }
          }}
          className="flex items-center gap-1 text-[16px] md:text-[20px] font-public-sans font-medium bg-neutral-900 hover:bg-white/30 text-white p-2"
        >
          <FiClock />
          <p className="hidden sm:inline">History</p>
        </Button>
        <Button
          className="flex items-center gap-1 text-[16px] md:text-[20px] font-public-sans font-medium bg-neutral-900 hover:bg-white/30 text-white p-2"
          onClick={handleNewChat}
        >
          <FaPlus />
        </Button>
      </div>
      
      {/* How It Works Modal */}
      <HowItWorksModal 
        isOpen={isHowItWorksOpen} 
        onClose={() => setIsHowItWorksOpen(false)} 
      />
    </div>
  );
};

export default ChatHeader; 