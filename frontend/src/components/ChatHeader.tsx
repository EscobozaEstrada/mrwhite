"use client"

import { Button } from "@/components/ui/button";
import { PiInfo } from "react-icons/pi";
import { FiBookmark, FiClock } from "react-icons/fi";
import { FaPlus } from "react-icons/fa6";
import { useRouter } from "next/navigation";
import { createNewConversation } from "@/utils/api";

interface ChatHeaderProps {
  fetchBookmarks: () => void;
  toggleHistory: () => void;
  user: any;
  clearChat?: () => void;
}

const ChatHeader = ({ fetchBookmarks, toggleHistory, user, clearChat }: ChatHeaderProps) => {
  const router = useRouter();

  const handleNewChat = async () => {
    if (clearChat) {
      clearChat();
    }
    
    // First navigate to new-chat to clear the UI
    router.push('/talk/conversation/new-chat');
    
    // If user is logged in, create a new conversation and update URL
    if (user) {
      try {
        const newConversationId = await createNewConversation();
        if (newConversationId) {
          // Use replaceState to update URL without adding to history stack
          window.history.replaceState(
            {},
            '',
            `/talk/conversation/${newConversationId}`
          );
        }
      } catch (error) {
        console.error('Error creating new conversation:', error);
      }
    }
  };

  return (
    <div className="flex w-full max-w-7xl justify-between items-center mb-4 md:mb-8 px-2 md:px-4">
      <Button
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
          variant="ghost"
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
          variant="ghost"
        >
          <FiClock />
          <p className="hidden sm:inline">History</p>
        </Button>
        <Button
          className="flex items-center gap-1 text-[16px] md:text-[20px] font-public-sans font-medium bg-neutral-900 hover:bg-white/30 text-white p-2"
          variant="ghost"
          onClick={handleNewChat}
        >
          <FaPlus />
        </Button>
      </div>
    </div>
  );
};

export default ChatHeader; 