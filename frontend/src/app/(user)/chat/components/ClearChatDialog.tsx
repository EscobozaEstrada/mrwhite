"use client";

import { useState } from "react";
import { FiX, FiTrash2, FiDatabase } from "react-icons/fi";

interface ClearChatDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (clearMemory: boolean) => Promise<void>;
}

export default function ClearChatDialog({ isOpen, onClose, onConfirm }: ClearChatDialogProps) {
  const [isClearing, setIsClearing] = useState(false);

  if (!isOpen) return null;

  const handleClearChatOnly = async () => {
    setIsClearing(true);
    try {
      await onConfirm(false); // clearMemory = false
      onClose();
    } catch (error) {
      console.error("Clear chat failed:", error);
    } finally {
      setIsClearing(false);
    }
  };

  const handleClearChatAndMemory = async () => {
    setIsClearing(true);
    try {
      await onConfirm(true); // clearMemory = true
      onClose();
    } catch (error) {
      console.error("Clear chat and memory failed:", error);
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[#1a1a1a] border border-gray-800 rounded-xl shadow-2xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-xl font-semibold text-white">Clear Chat</h2>
          <button
            onClick={onClose}
            disabled={isClearing}
            className="text-gray-400 cursor-pointer hover:text-white transition-colors disabled:opacity-50"
          >
            <FiX size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6 space-y-6">
          <p className="text-gray-300 text-sm">
            Choose how you want to clear your chat:
          </p>

          {/* Option 1: Clear Chat Only */}
          <div className="space-y-3">
            <button
              onClick={handleClearChatOnly}
              disabled={isClearing}
              className="w-full flex cursor-pointer items-start space-x-4 p-4 bg-[#252525] hover:bg-[#2d2d2d] border border-gray-700 hover:border-purple-600 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
            >
              <div className="flex-shrink-0 w-12 h-12 flex items-center justify-center bg-purple-600/10 group-hover:bg-purple-600/20 rounded-lg transition-colors">
                <FiTrash2 className="text-purple-500" size={24} />
              </div>
              <div className="flex-1 text-left">
                <h3 className="text-white font-semibold mb-1">Clear Chat Only</h3>
                <p className="text-gray-400 text-sm">
                  Delete all messages from the chat. AI will remember past context for personalized responses.
                </p>
                <div className="mt-2 flex items-center space-x-2">
                  <span className="text-xs text-gray-500">✓ Messages cleared</span>
                  <span className="text-xs text-gray-500">✓ AI memory preserved</span>
                </div>
              </div>
            </button>

            {/* Option 2: Clear Chat + Memory */}
            <button
              onClick={handleClearChatAndMemory}
              disabled={isClearing}
              className="w-full flex cursor-pointer items-start space-x-4 p-4 bg-[#252525] hover:bg-[#2d2d2d] border border-gray-700 hover:border-red-600 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
            >
              <div className="flex-shrink-0 w-12 h-12 flex items-center justify-center bg-red-600/10 group-hover:bg-red-600/20 rounded-lg transition-colors">
                <FiDatabase className="text-red-500" size={24} />
              </div>
              <div className="flex-1 text-left">
                <h3 className="text-white font-semibold mb-1">Clear Chat + Memory</h3>
                <p className="text-gray-400 text-sm">
                  Complete reset. Delete all messages and AI's learned context. Fresh start from scratch.
                </p>
                <div className="mt-2 flex items-center space-x-2">
                  <span className="text-xs text-gray-500">✓ Messages cleared</span>
                  <span className="text-xs text-red-400">✓ AI memory erased</span>
                </div>
              </div>
            </button>
          </div>

          {/* Info Box */}
          <div className="bg-blue-600/10 border border-blue-600/30 rounded-lg p-3">
            <p className="text-blue-400 text-xs">
              <strong>Note:</strong> Your dog profiles, documents, and vet reports will remain safe. Only chat history and AI memory are affected.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-800">
          <button
            onClick={onClose}
            disabled={isClearing}
            className="w-full px-4 py-2 bg-gray-700 cursor-pointer hover:bg-gray-600 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}


