"use client";

import { useEffect, useRef, useState } from "react";
import { FiCopy, FiThumbsUp, FiThumbsDown, FiVolume2, FiCheck, FiStopCircle, FiLoader } from "react-icons/fi";
import { IoChatbubbleEllipses } from "react-icons/io5";
import { FaUser, FaRobot } from "react-icons/fa";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { submitFeedback } from "@/services/feedbackApi";
import { textToSpeech, stopAudio, isPlaying } from "@/services/ttsService";
import DateSeparator from "./DateSeparator";
import toast from "@/components/ui/sound-toast";
import { groupMessagesByDate } from "@/utils/dateUtils";
import { PiDogFill } from "react-icons/pi";

interface Document {
  id: number;
  filename: string;
  file_type: string;
  s3_url: string;
  created_at: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  documents?: Document[];
}

interface MessageListProps {
  messages: Message[];
  isWaitingForResponse?: boolean;
  dateScrollTrigger?: { date: string; timestamp: number } | null; // Trigger object for scrolling to specific date
  searchQuery?: string; // Keyword search query
}

export default function MessageList({ messages, isWaitingForResponse, dateScrollTrigger, searchQuery }: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [feedbackStates, setFeedbackStates] = useState<Record<string, 'like' | 'dislike' | null>>({});
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null);
  const [loadingAudioId, setLoadingAudioId] = useState<string | null>(null);
  const previousMessageCountRef = useRef<number>(0);
  const isInitialLoadRef = useRef<boolean>(true);
  const lastMessageContentRef = useRef<string>("");

  // Auto-scroll to bottom when new messages arrive OR content changes (streaming)
  useEffect(() => {
    if (isInitialLoadRef.current) {
      // On initial load: jump to bottom instantly without any scroll animation
      if (messagesContainerRef.current) {
        messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
      }
      isInitialLoadRef.current = false;
    } else {
      const lastMessage = messages[messages.length - 1];
      const messageCountChanged = messages.length > previousMessageCountRef.current;
      const messageContentChanged = lastMessage && lastMessage.content !== lastMessageContentRef.current;
      
      if (messageCountChanged || messageContentChanged) {
        // Smooth scroll for new messages or streaming updates
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      }
      
      if (lastMessage) {
        lastMessageContentRef.current = lastMessage.content;
      }
    }
    
    previousMessageCountRef.current = messages.length;
  }, [messages]);

  // Scroll to selected date when date is picked (triggers on timestamp change)
  useEffect(() => {
    if (dateScrollTrigger && dateScrollTrigger.date) {
      const targetDate = new Date(dateScrollTrigger.date).toDateString();
      const dateElement = document.querySelector(`[data-date="${targetDate}"]`);
      
      if (dateElement) {
        dateElement.scrollIntoView({ behavior: "smooth", block: "center" });
        
        // Flash effect to highlight the date separator
        dateElement.classList.add('bg-purple-900/20');
        setTimeout(() => {
          dateElement.classList.remove('bg-purple-900/20');
        }, 2000);
      }
    }
  }, [dateScrollTrigger]);

  const handleCopyMessage = (messageId: string, content: string) => {
    // Try modern clipboard API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(content).then(() => {
        setCopiedMessageId(messageId);
        setTimeout(() => setCopiedMessageId(null), 1000);
      }).catch((err) => {
        console.error('Failed to copy:', err);
        fallbackCopy(content, messageId);
      });
    } else {
      // Fallback for non-HTTPS contexts
      fallbackCopy(content, messageId);
    }
  };

  // Fallback copy method for non-HTTPS contexts
  const fallbackCopy = (content: string, messageId: string) => {
    const textArea = document.createElement('textarea');
    textArea.value = content;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
      document.execCommand('copy');
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 1000);
    } catch (err) {
      console.error('Fallback copy failed:', err);
      toast.error('Copy failed. Please copy manually.');
    }
    
    document.body.removeChild(textArea);
  };

  const handleFeedback = async (messageId: string, type: "like" | "dislike") => {
    try {
      // Optimistically update UI
      setFeedbackStates(prev => ({
        ...prev,
        [messageId]: prev[messageId] === type ? null : type
      }));

      // Convert string message ID to number (remove 'msg_' prefix if present)
      const numericId = parseInt(messageId.replace('msg_', ''));
      
      await submitFeedback({
        message_id: numericId,
        feedback_type: type,
      });

      console.log(`✅ Feedback ${type} submitted for message ${messageId}`);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      // Revert UI on error
      setFeedbackStates(prev => ({
        ...prev,
        [messageId]: null
      }));
    }
  };

  const handleReadAloud = async (messageId: string, content: string) => {
    try {
      // If already playing this message, stop it
      if (playingMessageId === messageId && isPlaying()) {
        stopAudio();
        setPlayingMessageId(null);
        setLoadingAudioId(null);
        return;
      }

      // Stop any currently playing audio
      stopAudio();
      
      // Show loading state
      setLoadingAudioId(messageId);
      setPlayingMessageId(null);
      
      // Start playing new message (Promise resolves when audio STARTS playing)
      await textToSpeech(content);
      
      // Audio has started playing
      setLoadingAudioId(null);
      setPlayingMessageId(messageId);
      
      // Set up a listener to detect when audio finishes
      // We'll poll isPlaying() to detect when audio ends
      const checkAudioStatus = setInterval(() => {
        if (!isPlaying()) {
          setPlayingMessageId(null);
          clearInterval(checkAudioStatus);
        }
      }, 500); // Check every 500ms
      
    } catch (error) {
      console.error('TTS Error:', error);
      setLoadingAudioId(null);
      setPlayingMessageId(null);
      toast.error('Failed to play audio. Please check your API keys.');
    }
  };

  // Group messages by date
  const groupedMessages = groupMessagesByDate(messages);

  return (
    <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-6  scrollbar-hide">
      {messages.length === 0 ? (
        // Empty state
        <div className="flex flex-col items-center justify-center h-full text-gray-400">
          <IoChatbubbleEllipses className="text-6xl mb-4" />
          <h3 className="text-xl font-semibold mb-2">No messages yet</h3>
          <p className="text-sm">Start a conversation with Mr. White!</p>
        </div>
      ) : (
        // Grouped Messages with Date Separators
        groupedMessages.map((group) => (
          <div key={group.date.toISOString()}>
            {/* Date Separator */}
            <DateSeparator 
              label={group.dateLabel} 
              dateKey={group.date.toDateString()}
            />
            
            {/* Messages for this date */}
            {group.messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div className={`flex space-x-3 max-w-3xl ${message.role === "user" ? "flex-row-reverse space-x-reverse" : ""}`}>
              {/* Avatar */}
              <div className="flex-shrink-0">
                <div className="w-10 h-10 rounded-full bg-[#333333] flex items-center justify-center">
                  {message.role === "user" ? (
                    <FaUser className="text-gray-400" size={18} />
                  ) : (
                    <PiDogFill className="text-[#D3B86A]" size={25} />
                  )}
                </div>
              </div>

              {/* Message Content */}
              <div className="flex-1">
                {/* Documents attached to message (shown above message content) */}
                {message.documents && message.documents.length > 0 && (
                  <div className="mb-2">
                    <div className="flex flex-wrap gap-2">
                      {message.documents.map((doc: Document) => (
                        <a
                          key={doc.id}
                          href={doc.s3_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center space-x-2 px-3 py-2 bg-[#1a1a1a] border border-gray-700 rounded-lg text-xs hover:bg-[#2a2a2a] hover:border-gray-600 transition-colors"
                          title="Open document"
                        >
                          <span className="text-gray-400">📎</span>
                          <span className="text-gray-300 truncate max-w-[200px]">{doc.filename}</span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}
                
                <div
                  className={`rounded-lg p-4 ${
                    message.role === "user"
                      ? "bg-purple-600 text-white"
                      : "bg-[#2a2a2a] text-gray-200"
                  }`}
                >
                  {/* Render markdown with formatting support */}
                  <div className="prose prose-invert max-w-none whitespace-pre-wrap">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        // Custom styling for markdown elements
                        p: ({ children }) => <p className="mb-2 last:mb-0 whitespace-pre-wrap">{children}</p>,
                        strong: ({ children }) => <strong className="font-bold text-white">{children}</strong>,
                        em: ({ children }) => <em className="italic">{children}</em>,
                        ul: ({ children }) => <ul className="list-disc list-outside ml-6 mb-2 space-y-2">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal list-outside ml-6 mb-2 space-y-2">{children}</ol>,
                        li: ({ children }) => <li className="pl-1" style={{ display: 'list-item' }}>{children}</li>,
                        code: ({ children }) => (
                          <code className="bg-gray-900 px-1 py-0.5 rounded text-sm">{children}</code>
                        ),
                        h1: ({ children }) => <h1 className="text-2xl font-bold mb-2">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-xl font-bold mb-2">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-lg font-bold mb-2">{children}</h3>,
                        // Image rendering - display inline with border and rounded corners
                        img: ({ src, alt }) => (
                          <a href={typeof src === 'string' ? src : ''} target="_blank" rel="noopener noreferrer" className="block my-3">
                            <img
                              src={typeof src === 'string' ? src : ''}
                              alt={alt || "Image"}
                              className="max-w-full h-auto rounded-lg border-2 border-gray-700 hover:border-purple-500 transition-colors cursor-pointer shadow-lg"
                              style={{ maxHeight: "400px", objectFit: "contain" }}
                            />
                          </a>
                        ),
                        // Link rendering - styled as clickable chips/buttons
                        a: ({ href, children }) => {
                          const isDownloadLink = children?.toString().includes("Click to download") || children?.toString().includes("📎");
                          return (
                            <a
                              href={href}
                              target="_blank"
                              rel="noopener noreferrer"
                              className={`inline-flex items-center ${
                                isDownloadLink
                                  ? "px-3 py-1.5 bg-purple-600 hover:bg-purple-700 rounded-lg text-white font-medium transition-colors my-1 mr-2"
                                  : "text-purple-400 hover:text-purple-300 underline"
                              }`}
                            >
                              {children}
                            </a>
                          );
                        },
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center space-x-2 mt-2 ml-2">
                  {/* Copy button - available for all messages */}
                  <button
                    onClick={() => handleCopyMessage(message.id, message.content)}
                    className="p-2 cursor-pointer text-gray-500 hover:text-gray-300 hover:bg-[#333333] rounded-md transition-colors"
                    title={copiedMessageId === message.id ? "Copied!" : "Copy message"}
                  >
                    {copiedMessageId === message.id ? (
                      <FiCheck size={16} className="text-green-500" />
                    ) : (
                      <FiCopy size={16} />
                    )}
                  </button>
                  
                  {/* Feedback and read aloud - only for assistant messages */}
                  {message.role === "assistant" && (
                    <>
                      <button
                        onClick={() => handleFeedback(message.id, "like")}
                        className={`p-2 cursor-pointer hover:bg-[#333333] rounded-md transition-colors ${
                          feedbackStates[message.id] === 'like'
                            ? 'text-green-500'
                            : 'text-gray-500 hover:text-green-500'
                        }`}
                        title="Good response"
                      >
                        <FiThumbsUp size={16} />
                      </button>
                      <button
                        onClick={() => handleFeedback(message.id, "dislike")}
                        className={`p-2 cursor-pointer hover:bg-[#333333] rounded-md transition-colors ${
                          feedbackStates[message.id] === 'dislike'
                            ? 'text-red-500'
                            : 'text-gray-500 hover:text-red-500'
                        }`}
                        title="Bad response"
                      >
                        <FiThumbsDown size={16} />
                      </button>
                      <button
                        onClick={() => handleReadAloud(message.id, message.content)}
                        disabled={loadingAudioId === message.id}
                        className={`p-2 cursor-pointer hover:bg-[#333333] rounded-md transition-colors disabled:cursor-not-allowed ${
                          playingMessageId === message.id
                            ? 'text-purple-500'
                            : loadingAudioId === message.id
                            ? 'text-blue-500'
                            : 'text-gray-500 hover:text-purple-500'
                        }`}
                        title={
                          loadingAudioId === message.id
                            ? "Loading audio..."
                            : playingMessageId === message.id
                            ? "Stop audio"
                            : "Read aloud"
                        }
                      >
                        {loadingAudioId === message.id ? (
                          <FiLoader size={16} className="animate-spin" />
                        ) : playingMessageId === message.id ? (
                          <FiStopCircle size={16} />
                        ) : (
                          <FiVolume2 size={16} />
                        )}
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
            ))}
          </div>
        ))
      )}
      
      {/* Bouncing dots loader when waiting for AI response (before stream starts) */}
      {isWaitingForResponse && (
        <div className="flex items-start space-x-4 mb-6">
          <div className="flex space-x-1.5 ml-14">
            <div 
              className="w-1.5 h-1.5 bg-gray-400 rounded-full" 
              style={{ 
                animation: 'bounce 1s infinite',
                animationDelay: '0ms'
              }}
            ></div>
            <div 
              className="w-1.5 h-1.5 bg-gray-400 rounded-full" 
              style={{ 
                animation: 'bounce 1s infinite',
                animationDelay: '150ms'
              }}
            ></div>
            <div 
              className="w-1.5 h-1.5 bg-gray-400 rounded-full" 
              style={{ 
                animation: 'bounce 1s infinite',
                animationDelay: '300ms'
              }}
            ></div>
          </div>
        </div>
      )}
      
      <style jsx>{`
        @keyframes bounce {
          0%, 100% {
            transform: translateY(0);
          }
          50% {
            transform: translateY(-12px);
          }
        }
      `}</style>
      
      <div ref={messagesEndRef} />
    </div>
  );
}

