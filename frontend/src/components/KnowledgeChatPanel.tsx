'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Loader2, Send, BookOpen, MessageSquare } from 'lucide-react';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';
import { Badge } from '@/components/ui/badge';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Message {
  id: string;
  content: string;
  type: 'user' | 'ai';
  timestamp: string;
  userKnowledgeUsed?: boolean;
}

interface KnowledgeChatPanelProps {
  bookId?: string;
  bookCopyId?: number;
}

const KnowledgeChatPanel: React.FC<KnowledgeChatPanelProps> = ({ bookId, bookCopyId }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputValue.trim()) return;
    
    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      type: 'user',
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    
    try {
      // Format conversation history for the API
      const conversationHistory = messages.map(msg => ({
        role: msg.type === 'user' ? 'user' : 'assistant',
        content: msg.content
      }));
      
      // Call the knowledge-aware chat endpoint
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/book/knowledge-chat`,
        {
          query: userMessage.content,
          conversation_history: conversationHistory,
          book_id: bookId,
          book_copy_id: bookCopyId
        },
        { withCredentials: true }
      );
      
      if (response.data.success) {
        const aiMessage: Message = {
          id: Date.now().toString(),
          content: response.data.response,
          type: 'ai',
          timestamp: new Date().toISOString(),
          userKnowledgeUsed: response.data.chat_info?.user_knowledge_used || false
        };
        
        setMessages(prev => [...prev, aiMessage]);
      } else {
        toast.error('Failed to get response');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      toast.error('Error sending message');
    } finally {
      setIsLoading(false);
      // Focus the input after sending
      setTimeout(() => {
        inputRef.current?.focus();
      }, 0);
    }
  };

  // Typing indicator component
  const TypingIndicator = () => (
    <div className="flex justify-start">
      <Card className="p-3 max-w-[80%] bg-muted">
        <div className="flex items-center space-x-2">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
          </div>
          <span className="text-sm text-muted-foreground">AI is thinking...</span>
        </div>
      </Card>
    </div>
  );

  return (
    <div className="flex flex-col h-full border rounded-lg bg-background">
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center">
          <BookOpen className="mr-2 h-5 w-5" />
          <h2 className="text-lg font-semibold">Knowledge Chat</h2>
        </div>
        <Badge variant="secondary" className="px-2">
          <MessageSquare className="h-3 w-3 mr-1" />
          Personal Knowledge
        </Badge>
      </div>
      
      <ScrollArea className="flex-grow p-4">
        <div className="space-y-4">
          {messages.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              <MessageSquare className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p>Ask questions about the book and your personal notes</p>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <Card
                  className={`p-3 max-w-[80%] ${
                    message.type === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  {message.type === 'ai' ? (
                    <div className="markdown-content">
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                          strong: ({node, ...props}) => <strong className="font-bold" {...props} />,
                          em: ({node, ...props}) => <em className="italic" {...props} />,
                          code: ({node, className, inline, ...props}: any) => 
                            inline 
                              ? <code className="bg-gray-200 px-1 py-0.5 rounded text-sm" {...props} />
                              : <code className="block bg-gray-200 p-2 rounded my-2 overflow-x-auto text-sm" {...props} />,
                          ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-2" {...props} />,
                          ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-2" {...props} />,
                          li: ({node, ...props}) => <li className="mb-1" {...props} />,
                          a: ({node, ...props}) => <a className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer" {...props} />,
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap">{message.content}</div>
                  )}
                  {message.userKnowledgeUsed && (
                    <Badge variant="outline" className="mt-2 text-xs">
                      Used your notes
                    </Badge>
                  )}
                </Card>
              </div>
            ))
          )}
          {isLoading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      
      <form onSubmit={handleSendMessage} className="p-4 border-t">
        <div className="flex gap-2">
          <Textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask about your notes and comments..."
            className="flex-grow resize-none"
            rows={1}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage(e);
              }
            }}
            disabled={isLoading}
          />
          <Button type="submit" disabled={isLoading || !inputValue.trim()}>
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </form>
    </div>
  );
};

export default KnowledgeChatPanel; 