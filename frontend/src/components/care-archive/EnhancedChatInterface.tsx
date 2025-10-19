"use client"

import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
    Send,
    FileText,
    Heart,
    Bell,
    Search,
    Brain,
    Loader2,
    MessageSquare,
    Lightbulb
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import axios from 'axios';
import { toast } from 'react-toastify';
import { useAuth } from '@/context/AuthContext';
import {
    EnhancedChatResponse,
    ChatMessage,
    ContextSource,
    IntentAnalysis
} from '@/types/care-archive';

interface EnhancedChatInterfaceProps {
    conversationId?: number;
    threadId?: string;
    onNewConversation?: (conversationId: number, threadId: string) => void;
}

const EnhancedChatInterface: React.FC<EnhancedChatInterfaceProps> = ({
    conversationId,
    threadId: initialThreadId,
    onNewConversation
}) => {
    const { user, triggerCreditRefresh } = useAuth();
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [contextSources, setContextSources] = useState<ContextSource[]>([]);
    const [showSources, setShowSources] = useState(true);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [intentAnalysis, setIntentAnalysis] = useState<IntentAnalysis | null>(null);
    const [threadId, setThreadId] = useState<string>(initialThreadId || '');

    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        if (conversationId) {
            fetchConversationHistory();
            fetchSuggestions();
        }
    }, [conversationId]);

    const fetchConversationHistory = async () => {
        try {
            const response = await axios.get(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/care-archive/conversation/${conversationId}/context`,
                { withCredentials: true }
            );

            if (response.data.success) {
                const conversationData = response.data.conversation_data;
                setMessages(conversationData.messages || []);
                setContextSources(conversationData.context?.sources || []);
            }
        } catch (error) {
            console.error('Error fetching conversation history:', error);
        }
    };

    const fetchSuggestions = async () => {
        if (!conversationId) return;

        try {
            const response = await axios.get(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/care-archive/conversation/${conversationId}/suggestions`,
                { withCredentials: true }
            );

            if (response.data.success) {
                setSuggestions(response.data.suggestions);
            }
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
    };

    const analyzeIntent = async (message: string) => {
        try {
            const response = await axios.post(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/care-archive/analyze-intent`,
                { message },
                { withCredentials: true }
            );

            if (response.data.success) {
                setIntentAnalysis(response.data.intent_analysis);
            }
        } catch (error) {
            console.error('Error analyzing intent:', error);
        }
    };

    const sendMessage = async () => {
        if (!inputMessage.trim() || isLoading) return;

        const userMessage = inputMessage.trim();
        setInputMessage('');
        setIsLoading(true);

        // Add user message to chat immediately
        const newUserMessage: ChatMessage = {
            type: 'user',
            content: userMessage,
            timestamp: new Date().toISOString()
        };
        setMessages(prev => [...prev, newUserMessage]);

        // Analyze intent
        await analyzeIntent(userMessage);

        try {
            const response = await axios.post<EnhancedChatResponse>(
                `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/care-archive/enhanced-chat`,
                {
                    message: userMessage,
                    conversation_id: conversationId,
                    thread_id: threadId
                },
                { withCredentials: true }
            );

            if (response.data.success) {
                const aiMessage: ChatMessage = {
                    type: 'ai',
                    content: response.data.response,
                    timestamp: new Date().toISOString()
                };

                setMessages(prev => [...prev, aiMessage]);
                setContextSources(response.data.context_info.sources || []);

                // If this was a new conversation, update the conversation ID and thread ID
                if (!conversationId && response.data.context_info.conversation_id) {
                    const newThreadId = response.data.context_info.thread_id || threadId;
                    setThreadId(newThreadId);
                    onNewConversation?.(response.data.context_info.conversation_id, newThreadId);
                }

                // Fetch new suggestions
                setTimeout(fetchSuggestions, 1000);

                // Trigger credit refresh
                triggerCreditRefresh();
            } else {
                toast.error('Failed to get AI response');
            }
        } catch (error: any) {
            console.error('Error sending message:', error);

            let errorMessage = 'I apologize, but I encountered an error. Please try again.';

            // Handle specific error types
            if (axios.isAxiosError(error) && error.response?.status === 402) {
                // Credit-related error (Payment Required)
                const errorData = error.response.data;
                if (errorData && errorData.message) {
                    errorMessage = errorData.message;
                } else {
                    errorMessage = 'Insufficient credits to continue using this feature.';
                }

                // Trigger credit refresh to update displays
                triggerCreditRefresh();

                // Show toast for immediate feedback
                toast.error('Credits required for this feature');
            } else if (axios.isAxiosError(error) && error.response?.status === 403) {
                // Elite subscription required error
                const errorData = error.response.data;
                if (errorData && errorData.message) {
                    errorMessage = errorData.message;
                } else {
                    errorMessage = 'This feature requires an Elite subscription. Upgrade to access all premium features and get 3,000 monthly credits.';
                }

                // Show toast for immediate feedback
                toast.error('Elite subscription required');
            } else {
                // Generic error handling
                toast.error('Failed to send message');
            }

            // Add error message to chat
            const errorChatMessage: ChatMessage = {
                type: 'ai',
                content: errorMessage,
                timestamp: new Date().toISOString()
            };
            setMessages(prev => [...prev, errorChatMessage]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const useSuggestion = (suggestion: string) => {
        setInputMessage(suggestion);
        inputRef.current?.focus();
    };

    const getSourceIcon = (type: string) => {
        switch (type) {
            case 'document':
                return <FileText className="h-4 w-4" />;
            case 'care_record':
                return <Heart className="h-4 w-4" />;
            case 'reminder':
                return <Bell className="h-4 w-4" />;
            default:
                return <MessageSquare className="h-4 w-4" />;
        }
    };

    const getSourceColor = (type: string) => {
        switch (type) {
            case 'document':
                return 'text-blue-600 bg-blue-50';
            case 'care_record':
                return 'text-red-600 bg-red-50';
            case 'reminder':
                return 'text-yellow-600 bg-yellow-50';
            default:
                return 'text-gray-600 bg-gray-50';
        }
    };

    return (
        <div className="flex flex-col h-full bg-background">
            {/* Header */}
            <div className="border-b border-border p-4 bg-card">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Brain className="h-6 w-6 text-primary" />
                        <h2 className="text-xl font-semibold">Enhanced AI Assistant</h2>
                    </div>

                    {intentAnalysis && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <span>Intent: {intentAnalysis.primary_intent.replace('_', ' ')}</span>
                            {intentAnalysis.requires_context && (
                                <div className="flex items-center gap-1">
                                    <Search className="h-3 w-3" />
                                    <span>Using context</span>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            <div className="flex flex-1 overflow-hidden">
                {/* Chat Area */}
                <div className="flex-1 flex flex-col">
                    {/* Messages */}
                    <ScrollArea className="flex-1 p-4">
                        <div className="space-y-4">
                            <AnimatePresence>
                                {messages.map((message, index) => (
                                    <motion.div
                                        key={index}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ duration: 0.3 }}
                                        className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'
                                            }`}
                                    >
                                        <div
                                            className={`max-w-[80%] rounded-lg p-3 ${message.type === 'user'
                                                ? 'bg-primary text-primary-foreground'
                                                : 'bg-muted text-foreground border'
                                                }`}
                                        >
                                            <p className="whitespace-pre-wrap">{message.content}</p>
                                            <p className="text-xs opacity-70 mt-1">
                                                {new Date(message.timestamp).toLocaleTimeString()}
                                            </p>
                                        </div>
                                    </motion.div>
                                ))}
                            </AnimatePresence>

                            {isLoading && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    className="flex justify-start"
                                >
                                    <div className="bg-muted rounded-lg p-3 border">
                                        <div className="flex items-center gap-2">
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                            <span>Thinking...</span>
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </div>
                        <div ref={messagesEndRef} />
                    </ScrollArea>

                    {/* Suggestions */}
                    {suggestions.length > 0 && (
                        <div className="p-4 border-t">
                            <div className="flex items-center gap-2 mb-2">
                                <Lightbulb className="h-4 w-4 text-yellow-500" />
                                <span className="text-sm font-medium">Suggested questions:</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                {suggestions.slice(0, 3).map((suggestion, index) => (
                                    <Button
                                        key={index}
                                        variant="outline"
                                        size="sm"
                                        className="text-xs h-8"
                                        onClick={() => useSuggestion(suggestion)}
                                    >
                                        {suggestion}
                                    </Button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Input Area */}
                    <div className="border-t border-border p-4 bg-card">
                        <div className="flex gap-2">
                            <input
                                ref={inputRef}
                                type="text"
                                value={inputMessage}
                                onChange={(e) => setInputMessage(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder="Ask me about your pet's care history, documents, or health..."
                                className="flex-1 px-3 py-2 border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                                disabled={isLoading}
                            />
                            <Button
                                onClick={sendMessage}
                                disabled={!inputMessage.trim() || isLoading}
                                size="sm"
                            >
                                <Send className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>
                </div>

                {/* Context Sources Sidebar */}
                {showSources && contextSources.length > 0 && (
                    <motion.div
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 320, opacity: 1 }}
                        transition={{ duration: 0.3 }}
                        className="border-l border-border bg-card overflow-hidden"
                    >
                        <div className="p-4">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="font-semibold text-sm">Context Sources</h3>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setShowSources(false)}
                                >
                                    ×
                                </Button>
                            </div>

                            <div className="space-y-2">
                                {contextSources.map((source, index) => (
                                    <div
                                        key={index}
                                        className={`p-3 rounded-lg text-xs ${getSourceColor(source.type)}`}
                                    >
                                        <div className="flex items-center gap-2 mb-1">
                                            {getSourceIcon(source.type)}
                                            <span className="font-medium">{source.title}</span>
                                        </div>

                                        {source.content_preview && (
                                            <p className="text-xs opacity-80 line-clamp-2">
                                                {source.content_preview}
                                            </p>
                                        )}

                                        {source.date && (
                                            <p className="text-xs opacity-70 mt-1">
                                                {new Date(source.date).toLocaleDateString()}
                                            </p>
                                        )}

                                        {source.relevance_score && (
                                            <div className="mt-1">
                                                <div className="h-1 bg-black/20 rounded">
                                                    <div
                                                        className="h-1 bg-current rounded"
                                                        style={{ width: `${source.relevance_score * 100}%` }}
                                                    />
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </motion.div>
                )}

                {/* Show Sources Button (when sidebar is hidden) */}
                {!showSources && contextSources.length > 0 && (
                    <div className="p-2">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setShowSources(true)}
                            className="writing-mode-vertical-rl text-xs h-20"
                        >
                            Sources ({contextSources.length})
                        </Button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default EnhancedChatInterface; 