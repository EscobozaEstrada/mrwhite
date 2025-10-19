"use client"

import { Button } from "@/components/ui/button";
import { PiGlobeHemisphereWestBold, PiBookmarkBold, PiBookmarkFill } from "react-icons/pi";
import { RiVoiceprintFill } from "react-icons/ri";
import { FiPaperclip, FiSend } from "react-icons/fi";
import { IoImageOutline } from "react-icons/io5";
import { Heart } from "lucide-react";
import { InputBox } from '@/components/InputBox';
import SelectedFiles from '@/components/SelectedFiles';
import { BiBookAlt } from "react-icons/bi";

interface ChatControlsProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSendMessage: () => void;
  selectedFiles: Array<{
    file: File;
    type: 'file' | 'image';
    previewUrl?: string;
  }>;
  removeSelectedFile: (index: number) => void;
  openUploadModal: (type: 'file' | 'image' | 'book-generator') => void;
  toggleConversationBookmark: () => void;
  isBookmarked: boolean;
  isHealthMode: boolean;
  toggleHealthMode: () => void;
  placeholder?: string;
}

const ChatControls = ({
  inputValue,
  setInputValue,
  handleSendMessage,
  selectedFiles,
  removeSelectedFile,
  openUploadModal,
  toggleConversationBookmark,
  isBookmarked,
  isHealthMode,
  toggleHealthMode,
  placeholder
}: ChatControlsProps) => {
  return (
    <div className="rounded-sm overflow-hidden bg-neutral-900 p-4 md:p-8 flex flex-col gap-y-4 md:gap-y-8">
      <div className="flex items-center gap-x-4">
        <InputBox inputValue={inputValue} setInputValue={setInputValue} onSubmit={handleSendMessage} placeholder={placeholder} />
        <Button
          onClick={handleSendMessage}
          type="submit"
          className="text-black hidden max-[640px]:flex items-center justify-center p-2 rounded-lg h-[40px] w-[40px] mt-2 sm:mt-0">
          <FiSend className="!w-6 !h-6" />
        </Button>
      </div>

      <div className="flex items-center gap-x-4 justify-between">
        {selectedFiles.length > 0 && (
          <SelectedFiles
            files={selectedFiles}
            onRemove={removeSelectedFile}
          />
        )}
      </div>
      <div className="border-1 bg-neutral-900"></div>
      <div className="flex flex-col sm:flex-row items-center justify-between gap-y-4">
        <div className="flex flex-wrap items-center gap-1 lg:gap-5 w-full sm:w-auto justify-center sm:justify-start">
          <Button
            onClick={toggleHealthMode}
            className={`font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 p-1 md:p-2 lg:p-3 ${isHealthMode ? 'text-red-500 bg-red-500/10' : 'text-white'}`}
            variant="ghost"
          >
            <Heart className={`w-4 h-4 ${isHealthMode ? 'fill-current' : ''}`} />
            <span className="hidden sm:inline">Health</span>
          </Button>
          <Button className="font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 text-white bg-white/5 p-1 md:p-2 lg:p-3">
            <PiGlobeHemisphereWestBold />
            <span className="hidden sm:inline">Free Plan</span>
          </Button>
          <Button
            onClick={() => openUploadModal('file')}
            className="font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 text-white p-1 md:p-2 lg:p-3"
            variant="ghost"
          >
            <FiPaperclip />
            <span className="hidden sm:inline">Attach File</span>
          </Button>
          {/* <Button
            onClick={() => openUploadModal('image')}
            className="font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 text-white p-1 md:p-2 lg:p-3"
            variant="ghost"
          >
            <IoImageOutline />
            <span className="hidden sm:inline">Upload Image</span>
          </Button> */}

          <Button
            onClick={() => openUploadModal('book-generator')}
            className="font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 text-white p-1 md:p-2 lg:p-3"
            variant="ghost"
          >
            <BiBookAlt />
            <span className="hidden sm:inline">Generate Book</span>
          </Button>
          
          {/* <Button
            onClick={toggleConversationBookmark}
            className={`font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 p-1 md:p-2 lg:p-3 ${isBookmarked ? 'text-yellow-500' : 'text-white'}`}
            variant="ghost"
          >
            {isBookmarked ? <PiBookmarkFill /> : <PiBookmarkBold />}
            <span className="hidden sm:inline">Bookmark</span>
          </Button> */}
          <Button className="font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 text-white p-1 md:p-2 lg:p-3" variant="ghost">
            <RiVoiceprintFill />
            <span className="hidden sm:inline">Voice Message</span>
          </Button>
        </div>
        <Button
          onClick={handleSendMessage}
          type="submit"
          className="text-black max-[640px]:hidden p-2 rounded-lg h-[40px] w-[40px] mt-2 sm:mt-0">
          <FiSend className="!w-6 !h-6" />
        </Button>
      </div>
    </div>
  );
};

export default ChatControls; 