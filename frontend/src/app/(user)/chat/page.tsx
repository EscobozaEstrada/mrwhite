"use client";

import { useState, useRef, useEffect } from "react";
import ChatSidebar from "./components/ChatSidebar";
import ChatHeader from "./components/ChatHeader";
import MessageList from "./components/MessageList";
import MessageInput from "./components/MessageInput";
import { streamMessage, clearChat as apiClearChat, getChatStatus, getConversationHistory } from "@/services/intelligentChatApi";
import { textToSpeech } from "@/services/ttsService";
import { SystemMessageApi } from "@/services/systemMessageApi";
import toast from "@/components/ui/sound-toast";
import { useAuth } from "@/context/AuthContext";

interface Document {
  id: number;
  filename: string;
  file_type: string;
  s3_url: string;
  created_at: string;
}

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  documents?: Document[];
}

export default function ChatPage() {
  // Auth context for credit management
  const { triggerCreditRefresh } = useAuth();
  
  // State for messages
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [dateScrollTrigger, setDateScrollTrigger] = useState<{ date: string; timestamp: number } | null>(null);

  // State for toggle buttons
  const [activeMode, setActiveMode] = useState<"reminders" | "health" | "wayofdog" | null>(null);

  // State for streaming
  const [isStreaming, setIsStreaming] = useState(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [selectedDogId, setSelectedDogId] = useState<number | null>(null);

  // State for voice conversation mode
  const [voiceMode, setVoiceMode] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const shouldAutoPlayRef = useRef(false);
  const lastSpokenLengthRef = useRef(0);
  const isSpeakingRef = useRef(false);

  // Ref to track current streaming message
  const currentStreamingMessageRef = useRef<string>("");
  const streamingMessageIdRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Load chat status and history on mount
  useEffect(() => {
    loadChatData();
  }, []);

  const loadChatData = async () => {
    try {
      // Load conversation status
      const status = await getChatStatus();
      if (status.has_conversation) {
        setConversationId(status.conversation_id);
        
        // Load conversation history
        await loadConversationHistory();
      }
    } catch (error) {
      console.error("Failed to load chat data:", error);
    }
  };

  const loadConversationHistory = async () => {
    try {
      const history = await getConversationHistory({ limit: 50 });
      if (history.messages && history.messages.length > 0) {
        // Convert API messages to ChatMessage format
        const chatMessages: ChatMessage[] = history.messages.map((msg: any) => ({
          id: msg.id.toString(),
          role: msg.role,
          content: msg.content,
          timestamp: new Date(msg.created_at),
          documents: msg.documents || [] 
        }));
        setMessages(chatMessages);
      }
    } catch (error) {
      console.error("Failed to load conversation history:", error);
    }
  };

  const handleSendMessage = async (content: string, attachments?: File[], documentIds?: number[], documents?: Document[], isVoiceMessage?: boolean) => {
    if (isStreaming) return;
    if (!content.trim() && (!documentIds || documentIds.length === 0)) return;

    // Enable auto-play if this is a voice message or if voice mode is on
    shouldAutoPlayRef.current = isVoiceMessage || voiceMode;

    // Add user message with documents
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content,
      timestamp: new Date(),
      documents: documents || [],
    };
    setMessages((prev) => [...prev, userMessage]);

    // Start streaming
    setIsStreaming(true);
    setIsWaitingForResponse(true); // Show loader while waiting
    currentStreamingMessageRef.current = "";
    streamingMessageIdRef.current = (Date.now() + 1).toString();
    lastSpokenLengthRef.current = 0; // Reset spoken length for new message
    isSpeakingRef.current = false; // Reset speaking state

    // Create abort controller for stopping stream
    abortControllerRef.current = new AbortController();

    try {
      // Call streaming API with abort signal
      console.log("🚀 Starting stream with signal:", abortControllerRef.current.signal);
      const stream = streamMessage({
        message: content,
        active_mode: activeMode,
        dog_profile_id: selectedDogId,
        document_ids: documentIds || [],
      }, abortControllerRef.current.signal);

      for await (const chunk of stream) {
        // Check if aborted - exit immediately
        if (abortControllerRef.current?.signal.aborted) {
          console.log("🚫 Abort detected in loop, breaking immediately");
          break;
        }

        if (chunk.type === "token" && chunk.content) {
          // Hide loader as soon as first token arrives
          setIsWaitingForResponse(false);
          
          // Append token to streaming message
          currentStreamingMessageRef.current += chunk.content;
          
          // Update or create assistant message with immediate UI update
          setMessages((prev) => {
            const lastMessage = prev[prev.length - 1];
            
            if (lastMessage?.id === streamingMessageIdRef.current) {
              // Update existing streaming message
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMessage,
                  content: currentStreamingMessageRef.current,
                },
              ];
            } else {
              // Create new assistant message
              return [
                ...prev,
                {
                  id: streamingMessageIdRef.current!,
                  role: "assistant" as const,
                  content: currentStreamingMessageRef.current,
                  timestamp: new Date(),
                },
              ];
            }
          });
          
          // Voice Mode: Speak chunks as they arrive (for faster response)
          // ONLY if not currently speaking (prevent overlap)
          if (shouldAutoPlayRef.current && !isSpeakingRef.current) {
            const currentText = currentStreamingMessageRef.current;
            const unspokenText = currentText.substring(lastSpokenLengthRef.current);
            
            // Check if we have enough text to speak (at least 1 complete sentence)
            // Look for sentence endings: . ! ? followed by space, newline, or end of string
            const sentenceEndMatch = unspokenText.match(/[.!?](?=[\s\n]|$)/g);
            
            if (sentenceEndMatch && sentenceEndMatch.length >= 1) {
              // Find the position after the first sentence ending
              const firstSentenceEnd = unspokenText.indexOf(sentenceEndMatch[0]) + 1;
              // Look for the next space/newline after the punctuation
              const nextWhitespace = unspokenText.substring(firstSentenceEnd).search(/[\s\n]/);
              const endPosition = nextWhitespace === -1 ? firstSentenceEnd : firstSentenceEnd + nextWhitespace + 1;
              
              const textToSpeak = unspokenText.substring(0, endPosition).trim();
              
              if (textToSpeak.length > 20) { // Minimum 20 chars to avoid tiny fragments
                console.log(`🔊 Speaking chunk (${textToSpeak.length} chars):`, textToSpeak.substring(0, 50) + "...");
                console.log(`📊 lastSpokenLengthRef: ${lastSpokenLengthRef.current}, endPosition: ${endPosition}`);
                
                // Mark as speaking
                isSpeakingRef.current = true;
                setIsSpeaking(true);
                
                // Speak this chunk and wait for it to finish
                textToSpeech(textToSpeak)
                  .then(() => {
                    // Mark as done speaking
                    isSpeakingRef.current = false;
                    setIsSpeaking(false);
                    // Update how much we've spoken ONLY when audio actually finishes
                    lastSpokenLengthRef.current += endPosition;
                  })
                  .catch(err => {
                    console.error("❌ TTS chunk failed:", err);
                    isSpeakingRef.current = false;
                    setIsSpeaking(false);
                  });
              }
            }
          }
          
          // Small delay to create typing effect and prevent React batching
          await new Promise(resolve => setTimeout(resolve, 30));
          
          // Check abort again after delay
          if (abortControllerRef.current?.signal.aborted) {
            console.log("🚫 Abort detected after delay, breaking");
            break;
          }
        } else if (chunk.type === "done") {
          // Stream complete
          if (chunk.metadata?.conversation_id) {
            setConversationId(chunk.metadata.conversation_id);
          }
          
          // Speak any remaining unspoken text (wait for current chunk to finish first)
          if (shouldAutoPlayRef.current && currentStreamingMessageRef.current) {
            // Wait for any ongoing TTS to finish
            while (isSpeakingRef.current) {
              await new Promise(resolve => setTimeout(resolve, 100));
            }
            
            const remainingText = currentStreamingMessageRef.current.substring(lastSpokenLengthRef.current).trim();
            
            if (remainingText.length > 10) {
              try {
                console.log(`🔊 Speaking remaining text (${remainingText.length} chars):`, remainingText.substring(0, 50) + "...");
                console.log(`📊 Final chunk - lastSpokenLengthRef: ${lastSpokenLengthRef.current}, total length: ${currentStreamingMessageRef.current.length}`);
                isSpeakingRef.current = true;
                setIsSpeaking(true);
                await textToSpeech(remainingText);
                // Update lastSpokenLengthRef to mark all text as spoken
                lastSpokenLengthRef.current = currentStreamingMessageRef.current.length;
                isSpeakingRef.current = false;
                setIsSpeaking(false);
              } catch (error) {
                console.error("❌ Final TTS chunk failed:", error);
                isSpeakingRef.current = false;
                setIsSpeaking(false);
              }
            }
          }
        } else if (chunk.type === "metadata") {
          // Initial metadata (conversation_id, etc.)
          if (chunk.metadata?.conversation_id) {
            setConversationId(chunk.metadata.conversation_id);
          }
        } else if (chunk.type === "error") {
          console.error("Streaming error:", chunk.error);
          // Show error message
          setMessages((prev) => [
            ...prev,
            {
              id: (Date.now() + 2).toString(),
              role: "assistant" as const,
              content: `❌ Error: ${chunk.error || "Failed to generate response"}`,
              timestamp: new Date(),
            },
          ]);
        }
      }
    } catch (error: any) {
      // Don't show error if user intentionally stopped the stream
      if (error.name === 'AbortError') {
        console.log("Stream stopped by user");
        return; // Exit gracefully
      }
      
      console.error("Failed to send message:", error);
      setIsWaitingForResponse(false); // Hide loader on error
      
      // Show error message only for real errors
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 2).toString(),
          role: "assistant" as const,
          content: `❌ Failed to send message. Please try again.`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsStreaming(false);
      setIsWaitingForResponse(false);
      setIsSpeaking(false);
      currentStreamingMessageRef.current = "";
      streamingMessageIdRef.current = null;
      abortControllerRef.current = null;
      
      // Update credits after message completion - trigger global credit refresh
      triggerCreditRefresh();
    }
  };

  const handleStopStreaming = () => {
    console.log("🛑 STOP BUTTON CLICKED");
    if (abortControllerRef.current) {
      console.log("✅ AbortController exists, calling abort()");
      abortControllerRef.current.abort();
      setIsStreaming(false);
      setIsSpeaking(false);
    } else {
      console.log("❌ AbortController is null!");
    }
  };

  // Dog profile event handlers
  const handleDogAdded = async (dogName: string, dogId: number) => {
    try {
      console.log(`🐕 Dog added: ${dogName} (ID: ${dogId})`);
      const response = await SystemMessageApi.createDogAddedMessage(dogName, dogId);
      
      // Add the system message to the chat
      const systemMessage: ChatMessage = {
        id: `system-${response.message_id}`,
        role: "assistant",
        content: `🐕 Thank you for adding ${dogName} to your family! I'm excited to learn more about ${dogName} and help you with their care. I'll remember ${dogName}'s information and can provide personalized advice based on their profile. Feel free to ask me anything about ${dogName}'s health, training, or daily care!`,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, systemMessage]);
      
    } catch (error) {
      console.error("Failed to create dog added message:", error);
      toast.error("Failed to notify chatbot about new dog. Please try again.");
    }
  };

  const handleDogEdited = async (dogName: string, dogId: number, changes: string[]) => {
    try {
      console.log(`✏️ Dog edited: ${dogName} (ID: ${dogId}), changes: ${changes.join(', ')}`);
      const response = await SystemMessageApi.createDogEditedMessage(dogName, dogId, changes);
      
      // Add the system message to the chat
      const changesText = changes.length > 0 ? ` I've noted the updates to: ${changes.join(', ')}.` : '';
      const systemMessage: ChatMessage = {
        id: `system-${response.message_id}`,
        role: "assistant",
        content: `✅ I've updated ${dogName}'s profile information!${changesText} This will help me provide more accurate and personalized advice for ${dogName}. Is there anything specific about ${dogName} you'd like to discuss?`,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, systemMessage]);
      
    } catch (error) {
      console.error("Failed to create dog edited message:", error);
      toast.error("Failed to notify chatbot about dog updates. Please try again.");
    }
  };

  const handleDogDeleted = async (dogName: string) => {
    try {
      console.log(`🗑️ Dog deleted: ${dogName}`);
      const response = await SystemMessageApi.createDogDeletedMessage(dogName);
      
      // Add the system message to the chat
      const systemMessage: ChatMessage = {
        id: `system-${response.message_id}`,
        role: "assistant",
        content: `🗑️ I've removed ${dogName} from your profile. I'll no longer reference ${dogName} in our conversations. If you have other dogs in your family, I'm still here to help with their care!`,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, systemMessage]);
      
    } catch (error) {
      console.error("Failed to create dog deleted message:", error);
      toast.error("Failed to notify chatbot about dog deletion. Please try again.");
    }
  };

  const handleClearChat = async (clearMemory: boolean) => {
    if (!conversationId) {
      setMessages([]);
      return;
    }

    try {
      await apiClearChat(conversationId, clearMemory);
      setMessages([]);
      
      // Show success message
      if (clearMemory) {
        console.log("✅ Chat and memories cleared successfully");
      } else {
        console.log("✅ Chat cleared successfully (memories preserved)");
      }
      
      // Reload conversation data
      await loadConversationHistory();
    } catch (error) {
      console.error("Failed to clear chat:", error);
      toast.error("Failed to clear chat. Please try again.");
      throw error; // Re-throw so dialog can handle it
    }
  };

  return (
    <div className="flex bg-[#0f0f0f] text-white h-screen pt-[70px] sm:pt-[80px] md:pt-[95px]">
      {/* Left Sidebar */}
      <ChatSidebar 
        onDogAdded={handleDogAdded}
        onDogEdited={handleDogEdited}
        onDogDeleted={handleDogDeleted}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Fixed Header */}
        <ChatHeader 
          onClearChat={handleClearChat}
          onSearchQueryChange={setSearchQuery}
          onDateSelect={(date) => setDateScrollTrigger({ date, timestamp: Date.now() })}
          voiceMode={voiceMode}
          onVoiceModeToggle={() => setVoiceMode(!voiceMode)}
        />

        {/* Scrollable Messages */}
        <MessageList 
          messages={messages} 
          isWaitingForResponse={isWaitingForResponse}
          searchQuery={searchQuery}
          dateScrollTrigger={dateScrollTrigger}
        />

        {/* Fixed Input Area */}
        <MessageInput
          activeMode={activeMode}
          onModeChange={setActiveMode}
          onSendMessage={handleSendMessage}
          isStreaming={isStreaming || isSpeaking}
          onStopStreaming={handleStopStreaming}
          conversationId={conversationId}
        />
      </div>
    </div>
  );
}

