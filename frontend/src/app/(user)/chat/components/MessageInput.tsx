"use client";

import { useState, useRef } from "react";
import { FiSend, FiPaperclip, FiMic, FiSquare, FiX, FiLoader } from "react-icons/fi";
import { MdHealthAndSafety } from "react-icons/md";
import { IoMdAlarm } from "react-icons/io";
import { FaDog } from "react-icons/fa";
import { uploadDocument, validateFile } from "@/services/documentApi";
import VoiceChatModal from "./VoiceChatModal";
import toast from "@/components/ui/sound-toast";

type ModeType = "reminders" | "health" | "wayofdog" | null;

interface Document {
  id: number;
  filename: string;
  file_type: string;
  s3_url: string;
  created_at: string;
}

interface MessageInputProps {
  activeMode: ModeType;
  onModeChange: (mode: ModeType) => void;
  onSendMessage: (content: string, attachments?: File[], documentIds?: number[], documents?: Document[], isVoiceMessage?: boolean) => void;
  isStreaming: boolean;
  onStopStreaming?: () => void;
  conversationId: number | null;
}

export default function MessageInput({
  activeMode,
  onModeChange,
  onSendMessage,
  isStreaming,
  onStopStreaming,
  conversationId,
}: MessageInputProps) {
  const [message, setMessage] = useState("");
  const [attachments, setAttachments] = useState<File[]>([]);
  const [uploadedDocs, setUploadedDocs] = useState<Array<{ file: File; id: number; status: string; filename: string; file_type: string; s3_url: string }>>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState<string>("");
  const [isVoiceModalOpen, setIsVoiceModalOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((message.trim() || uploadedDocs.length > 0) && !isProcessing && !isStreaming) {
      // Send message with document IDs and document objects for UI
      const docIds = uploadedDocs.map(doc => doc.id);
      const documents: Document[] = uploadedDocs.map(doc => ({
        id: doc.id,
        filename: doc.filename,
        file_type: doc.file_type,
        s3_url: doc.s3_url,
        created_at: new Date().toISOString() 
      }));
      onSendMessage(message, [], docIds, documents);
      setMessage("");
      setUploadedDocs([]);
      
      // Reset textarea height after sending
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleStopStreaming = (e?: React.MouseEvent) => {
    // Prevent any form submission
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (onStopStreaming) {
      onStopStreaming();
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    
    // Check total limit (current + new)
    if (uploadedDocs.length + files.length > 5) {
      toast.error("Maximum 5 documents allowed per message");
      return;
    }
    
    // Process each file
    setIsProcessing(true);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      setProcessingStatus(`Uploading ${i + 1}/${files.length}: ${file.name}...`);
      
      try {
        // Validate file
        const validation = validateFile(file);
        if (!validation.valid) {
          toast.error(`${file.name}: ${validation.error}`);
          continue;
        }
        
        // Upload and process (backend will create conversation if needed)
        const result = await uploadDocument(file, conversationId || 0);
        
        if (result.success) {
          setUploadedDocs(prev => [...prev, {
            file,
            id: result.document.id,
            status: result.document.status,
            filename: result.document.filename,
            file_type: result.document.file_type,
            s3_url: result.document.s3_url
          }]);
        } else {
          toast.error(`Failed to upload ${file.name}`);
        }
      } catch (error: any) {
        console.error(`Upload failed for ${file.name}:`, error);
        toast.error(`Failed to upload ${file.name}: ${error.message}`);
      }
    }
    
    setIsProcessing(false);
    setProcessingStatus("");
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };
  
  const removeDocument = (index: number) => {
    setUploadedDocs(prev => prev.filter((_, i) => i !== index));
  };

  const handleVoiceTranscription = (transcription: string) => {
    // Send the transcribed text as a message with voice flag
    if (transcription.trim()) {
      onSendMessage(transcription, [], [], [], true);
    }
  };

  const handleToggleMode = (mode: ModeType) => {
    // Toggle off if clicking the same mode, otherwise switch to new mode
    onModeChange(activeMode === mode ? null : mode);
  };

  return (
    <div className="px-6 py-4 flex flex-col items-center">
      <div className="w-full max-w-4xl">
        {/* Mode Toggle Buttons Row */}
        <div className="flex items-center justify-end mb-3 px-2">
          {/* Mode Toggle Buttons */}
          <div className="flex items-center space-x-2">
            <span className="text-xs text-gray-500 font-medium mr-1">Mode:</span>
            
            {/* Reminders Toggle */}
            <button
              onClick={() => handleToggleMode("reminders")}
              disabled={isStreaming}
              className={`px-3 py-1.5 cursor-pointer rounded-md text-xs font-medium transition-all flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed ${
                activeMode === "reminders"
                  ? "bg-green-600 text-white"
                  : "bg-[#2a2a2a] text-gray-400 hover:bg-[#333333]"
              }`}
            >
              <IoMdAlarm size={14} />
              <span>Reminders</span>
            </button>

            {/* Health Toggle */}
            <button
              onClick={() => handleToggleMode("health")}
              disabled={isStreaming}
              className={`px-3 py-1.5 cursor-pointer rounded-md text-xs font-medium transition-all flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed ${
                activeMode === "health"
                  ? "bg-red-600 text-white"
                  : "bg-[#2a2a2a] text-gray-400 hover:bg-[#333333]"
              }`}
            >
              <MdHealthAndSafety size={14} />
              <span>Health</span>
            </button>

            {/* Way Of Dog Toggle */}
            <button
              onClick={() => handleToggleMode("wayofdog")}
              disabled={isStreaming}
              className={`px-3 py-1.5 cursor-pointer rounded-md text-xs font-medium transition-all flex items-center space-x-1.5 disabled:opacity-50 disabled:cursor-not-allowed ${
                activeMode === "wayofdog"
                  ? "bg-blue-600 text-white"
                  : "bg-[#2a2a2a] text-gray-400 hover:bg-[#333333]"
              }`}
            >
              <FaDog size={14} />
              <span>Way Of Dog</span>
            </button>
          </div>
        </div>

        {/* Processing Status */}
        {isProcessing && (
          <div className="mb-3 px-2">
            <div className="bg-blue-900/30 border border-blue-700/50 px-4 py-2 rounded-lg text-sm flex items-center space-x-3">
              <FiLoader className="animate-spin text-blue-400" size={16} />
              <span className="text-blue-300">{processingStatus}</span>
            </div>
          </div>
        )}


        {/* Input Form - Capsule Style */}
        <form onSubmit={handleSubmit}>
          <div className="flex items-end space-x-3 bg-[#1a1a1a] rounded-3xl border border-gray-800 px-5 py-3">
            {/* Text Input */}
            <div className="flex-1">
              {/* Uploaded Documents - inside input, above textarea */}
              {uploadedDocs.length > 0 && (
                <div className="mb-2 pb-2 border-b border-gray-800">
                  <div className="flex items-center flex-wrap gap-2">
                    {uploadedDocs.map((doc, index) => (
                      <div
                        key={index}
                        className="bg-[#2a2a2a] px-3 py-1.5 rounded-lg text-xs flex items-center space-x-2 group hover:bg-[#333333] transition-colors"
                      >
                        <span className="text-gray-400">📎</span>
                        <span className="text-gray-300 truncate max-w-[150px]">{doc.file.name}</span>
                        {doc.status === 'completed' && (
                          <span className="text-green-400 text-[10px]">✓</span>
                        )}
                        {doc.status === 'processing' && (
                          <FiLoader className="animate-spin text-blue-400" size={10} />
                        )}
                        <button
                          type="button"
                          onClick={() => removeDocument(index)}
                          className="text-gray-500 hover:text-red-400 transition-colors"
                          title="Remove"
                        >
                          <FiX size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              <textarea
                ref={textareaRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e);
                  }
                }}
                placeholder={isStreaming ? "AI is responding..." : "Ask anything..."}
                disabled={isStreaming}
                className={`w-full bg-transparent text-gray-300 placeholder-gray-500 resize-none focus:outline-none text-sm leading-6 scrollbar-hide ${
                  isStreaming ? "opacity-50 cursor-not-allowed" : ""
                }`}
                rows={1}
                style={{
                  maxHeight: "200px",
                  overflowY: "hidden",
                }}
                onInput={(e) => {
                  const target = e.target as HTMLTextAreaElement;
                  target.style.height = "auto";
                  const newHeight = Math.min(target.scrollHeight, 200);
                  target.style.height = newHeight + "px";
                  // Only show scroll when content exceeds max height
                  target.style.overflowY = target.scrollHeight > 200 ? "auto" : "hidden";
                }}
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center space-x-2 pb-1">
              {/* Attachment Button - Only show in General Mode and Health Mode */}
              {(activeMode === null || activeMode === "health") && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isProcessing || uploadedDocs.length >= 5 || isStreaming}
                  className="p-2 hover:bg-[#2a2a2a] cursor-pointer rounded-full transition-colors text-gray-400 disabled:opacity-50 disabled:cursor-not-allowed"
                  title={uploadedDocs.length >= 5 ? "Maximum 5 documents" : isStreaming ? "Wait for AI to finish" : "Attach file"}
                >
                  <FiPaperclip size={18} />
                </button>
              )}

              {/* Voice Button */}
              <button
                type="button"
                onClick={() => setIsVoiceModalOpen(true)}
                disabled={isStreaming}
                className="p-2 hover:bg-[#2a2a2a] cursor-pointer rounded-full transition-colors text-gray-400 hover:text-purple-500 disabled:opacity-50 disabled:cursor-not-allowed"
                title={isStreaming ? "Wait for AI to finish" : "Voice message"}
              >
                <FiMic size={18} />
              </button>

              {/* Send or Stop Button */}
              {isStreaming ? (
                <button
                  type="button"
                  onClick={handleStopStreaming}
                  className="p-2 bg-red-600 hover:bg-red-700 cursor-pointer rounded-full transition-colors text-white"
                  title="Stop streaming"
                >
                  <FiSquare size={18} />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isProcessing || (!message.trim() && uploadedDocs.length === 0)}
                  className="p-2 bg-purple-600 hover:bg-purple-700 cursor-pointer disabled:bg-[#2a2a2a] disabled:cursor-not-allowed rounded-full transition-colors text-white disabled:text-gray-600"
                  title={isProcessing ? "Processing documents..." : "Send message"}
                >
                  <FiSend size={18} />
                </button>
              )}
            </div>
          </div>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
            accept=".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png,.bmp,.gif,.tiff"
          />
        </form>
      </div>

      {/* Voice Chat Modal */}
      <VoiceChatModal
        isOpen={isVoiceModalOpen}
        onClose={() => setIsVoiceModalOpen(false)}
        onTranscriptionReady={handleVoiceTranscription}
      />
    </div>
  );
}

