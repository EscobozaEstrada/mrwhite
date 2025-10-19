"use client"

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PiGlobeHemisphereWestBold } from "react-icons/pi";
import { RiVoiceprintFill } from "react-icons/ri";
import { FiPaperclip, FiSend } from "react-icons/fi";
import { Heart, Coins, Sparkles } from "lucide-react";
import { InputBox } from '@/components/InputBox';
import SelectedFiles from '@/components/SelectedFiles';
import { useRouter } from "next/navigation";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { useAuth } from '@/context/AuthContext';
import { HiCurrencyDollar } from "react-icons/hi";
import VoiceMessageModal from './VoiceMessageModal';
import EnhancedBookDropdown from './EnhancedBookDropdown';
import { GrUpgrade } from "react-icons/gr";

interface ChatControlsProps {
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSendMessage: () => void;
  selectedFiles: Array<{
    file: File;
    type: 'file' | 'image' | 'audio';
    previewUrl?: string;
    description?: string;
  }>;
  removeSelectedFile: (index: number) => void;
  openUploadModal: (type: 'file' | 'image' | 'book-generator' | 'enhanced-book-generator') => void;
  toggleConversationBookmark: () => void;
  isBookmarked: boolean;
  isHealthMode: boolean;
  toggleHealthMode: () => void;
  placeholder?: string;
  onVoiceMessageAdd?: (file: File, transcription: string) => void;
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
  placeholder,
  onVoiceMessageAdd
}: ChatControlsProps) => {
  const router = useRouter();
  const { user, creditStatus } = useAuth();
  const [isCreditModalOpen, setIsCreditModalOpen] = useState(false);
  const [isVoiceMessageModalOpen, setIsVoiceMessageModalOpen] = useState(false);

  const handlePlanButtonClick = () => {
    if (!user?.is_premium) {
      // Redirect to subscription page for free users
      // router.push('/subscription');
    } else {
      // Show credit modal for elite users
      setIsCreditModalOpen(true);
    }
  };

  const handleGoBack = () => {
    router.back();
  };

  // Format credits as USD
  const formatCreditsAsUSD = (credits: number) => {
    return `$${(credits / 100).toFixed(2)}`;
  };

  // Check if message can be sent (non-empty input or has files)
  const canSendMessage = inputValue.trim().length > 0 || selectedFiles.length > 0;

  // Check if user has an active subscription
  const hasActiveSubscription = user?.is_premium && 
    user?.subscription_status === 'active';

  // Get usage breakdown from creditStatus or use empty object if not available
  const usageBreakdown = creditStatus?.cost_breakdown || {
    chat_messages: 0,
    document_processing: 0,
    health_features: 0,
    book_generation: 0,
    voice_processing: 0
  };

  // Calculate total usage from breakdown - this is the accurate total
  const totalUsage = Object.values(usageBreakdown).reduce((sum: number, value: number) => sum + value, 0);

  // Handle voice message
  const handleVoiceMessageReady = (file: File, transcription: string) => {
    if (onVoiceMessageAdd) {
      onVoiceMessageAdd(file, transcription);
    } else {
      // Fallback: Add the transcription to the input field
      const newValue = inputValue.trim() 
        ? `${inputValue.trim()} ${transcription}` 
        : transcription;
      setInputValue(newValue);
    }
  };

  return (
    <div className="rounded-sm bg-neutral-900 p-4 md:p-8 flex flex-col gap-y-4 md:gap-y-8">
      <div className="flex items-center gap-x-4">
        <InputBox inputValue={inputValue} setInputValue={setInputValue} onSubmit={handleSendMessage} placeholder={placeholder} />
        <Button
          onClick={handleSendMessage}
          type="submit"
          disabled={!canSendMessage}
          className="text-black hidden max-[640px]:flex items-center justify-center p-2 rounded-lg h-[40px] w-[40px] mt-2 sm:mt-0 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer">
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
            onClick={handlePlanButtonClick}
            className="font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 text-white bg-white/5 p-1 md:p-2 lg:p-3 hover:bg-white/10"
          >
            {user?.is_premium ? <Coins className="w-4 h-4" /> : <PiGlobeHemisphereWestBold />}
            <span className="hidden sm:inline">{user?.is_premium ? 'Elite Plan' : 'Free Plan'}</span>
          </Button>

          {/* Health button - only show for users with active subscription */}
          {hasActiveSubscription && (
            <Button
              onClick={toggleHealthMode}
              className={`font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 p-1 md:p-2 lg:p-3 ${isHealthMode ? 'text-red-500 bg-red-500/10 hover:bg-red-500/20' : 'text-white'}`}
              variant="ghost"
            >
              <Heart className={`w-4 h-4 ${isHealthMode ? 'fill-current' : ''}`} />
              <span className="hidden sm:inline">Health</span>
            </Button>
          )}

          <Button
            onClick={() => openUploadModal('file')}
            className="font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 text-white p-1 md:p-2 lg:p-3"
            variant="ghost"
          >
            <FiPaperclip />
            <span className="hidden sm:inline">Attach File</span>
          </Button>

          {/* Enhanced Book Generator - only show for users with active subscription */}
          {hasActiveSubscription && (
            <EnhancedBookDropdown openUploadModal={openUploadModal} />
          )}

          {/* Voice Message - only show for users with active subscription */}
          {hasActiveSubscription && (
            <Button 
              onClick={() => setIsVoiceMessageModalOpen(true)}
              className="font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 text-white p-1 md:p-2 lg:p-3" 
              variant="ghost"
            >
              <RiVoiceprintFill />
              <span className="hidden sm:inline">Voice Message</span>
            </Button>
          )}

          {/* Upgrade prompt for free users */}
          {!hasActiveSubscription && (
            <Button
              onClick={() => router.push('/subscription')}
              className="font-public-sans font-light text-[14px] lg:text-[20px] flex items-center gap-1 lg:gap-2 text-[var(--mrwhite-primary-color)] border border-[var(--mrwhite-primary-color)]/30 hover:bg-[var(--mrwhite-primary-color)]/10 p-1 md:p-2 lg:p-3"
              variant="outline"
            >
              <Sparkles className="w-4 h-4" />
              <span className="hidden sm:inline">Upgrade for More</span>
            </Button>
          )}
        </div>
        <Button
          onClick={handleSendMessage}
          type="submit"
          disabled={!canSendMessage}
          className="text-black max-[640px]:hidden p-2 rounded-lg h-[40px] w-[40px] mt-2 sm:mt-0 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer">
          <FiSend className="!w-6 !h-6" />
        </Button>
      </div>

      {/* Credit Information Modal */}
      <Dialog open={isCreditModalOpen} onOpenChange={setIsCreditModalOpen}>
        <DialogContent className="sm:max-w-[450px] bg-neutral-900 text-white border-neutral-700 font-public-sans">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-white flex items-center gap-2">
              <Coins className="w-5 h-5 font-work-sans text-[var(--mrwhite-primary-color)]" />
              Mini Credits Dashboard
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-6 py-4 overflow-y-auto custom-scrollbar h-[400px] pr-2">
            {/* Credit Balance Card */}
            <div className="bg-gradient-to-r from-neutral-800 to-neutral-900 rounded-md p-4 border border-[var(--mrwhite-primary-color)]/20">
              <div className="flex justify-between items-center mb-2">
                <span className="text-neutral-300">Available Credits</span>
                <span className="text-2xl font-bold text-[var(--mrwhite-primary-color)]">{creditStatus?.available_credits || 0}</span>
              </div>

              {/* Credit Status Bar */}
              <div className="w-full bg-neutral-700 rounded-full h-2 mb-1">
                <div
                  className="bg-[var(--mrwhite-primary-color)] h-2 rounded-full"
                  style={{ width: `${Math.min(((creditStatus?.available_credits || 0) / 100) * 100, 100)}%` }}
                ></div>
              </div>
              <div className="text-xs text-neutral-400 text-right">
                {(creditStatus?.available_credits || 0) < 20 ? 'Low balance' : 'Healthy balance'}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-2 gap-3">
              <Button
                onClick={() => {
                  setIsCreditModalOpen(false);
                  router.push('/account/credits');
                }}
                className="bg-[var(--mrwhite-primary-color)] font-public-sans font-medium hover:bg-[var(--mrwhite-primary-color)]/80 text-black"
              >
                <HiCurrencyDollar className="!w-5 !h-5 mr-2 max-[400px]:hidden" />
                <span className="max-[350px]:text-xs">Buy Credits</span>
              </Button>

              <Button
                onClick={() => {
                  setIsCreditModalOpen(false);
                  router.push('/subscription');
                }}
                variant="outline"
                className="border-[var(--mrwhite-primary-color)]/50 font-public-sans font-medium text-[var(--mrwhite-primary-color)]"
              >
                <GrUpgrade className="w-4 h-4 mr-2 max-[400px]:hidden" />
                <span className="max-[350px]:text-xs">Upgrade Plan</span>
              </Button>
            </div>

            {/* Usage Tracking Summary */}
            <div className="bg-neutral-800 rounded-md p-4">
              <h4 className="text-sm font-medium mb-3 text-neutral-200">Today's Usage Breakdown</h4>
              <div className="space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <span className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-blue-500"></div>
                    Basic Chat
                  </span>
                  <span className="text-neutral-300">{usageBreakdown.chat_messages || 0} credits</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-green-500"></div>
                    File Analysis
                  </span>
                  <span className="text-neutral-300">{usageBreakdown.document_processing || 0} credits</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-red-500"></div>
                    Health Mode
                  </span>
                  <span className="text-neutral-300">{usageBreakdown.health_features || 0} credits</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                    Book Generation
                  </span>
                  <span className="text-neutral-300">{(usageBreakdown as any).book_generation || 0} credits</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="flex items-center gap-1">
                    <div className="w-2 h-2 rounded-full bg-orange-500"></div>
                    Voice Message
                  </span>
                  <span className="text-neutral-300">{(usageBreakdown as any).voice_processing || 0} credits</span>
                </div>

              </div>
              <div className="mt-3 pt-3 border-t border-neutral-700">
                <div className="flex justify-between items-center text-xs mb-2">
                  <span className="text-neutral-400">Total Today</span>
                  <span className="font-medium text-[var(--mrwhite-primary-color)]">{totalUsage} credits</span>
                </div>
                {totalUsage === 0 && (
                  <p className="text-xs text-neutral-500 italic">No usage yet today. Start chatting to see tracking!</p>
                )}
              </div>
            </div>

            {/* Credit Renewal Info */}
            <div className="text-center text-sm text-neutral-400 mt-2">
              {creditStatus?.is_elite ? (
                <>
                  <p>Your Elite plan includes {creditStatus?.plan_info?.monthly_credit_allowance || 3000} monthly credits</p>
                  <p className="text-[var(--mrwhite-primary-color)]">
                    Next renewal: {user?.subscription_end_date ?
                      new Date(user.subscription_end_date).toLocaleDateString('en-US', { 
                        year: 'numeric', 
                        month: 'long', 
                        day: 'numeric' 
                      }) :
                      'Date unavailable'}
                  </p>
                </>
              ) : (
                <p>Upgrade to Elite for 3,000 monthly credits</p>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Voice Message Modal */}
      <VoiceMessageModal
        isOpen={isVoiceMessageModalOpen}
        onClose={() => setIsVoiceMessageModalOpen(false)}
        onVoiceMessageReady={handleVoiceMessageReady}
      />
    </div>
  );
};

export default ChatControls; 