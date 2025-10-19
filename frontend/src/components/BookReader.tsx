'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  BookOpen,
  MessageCircle,
  Edit,
  Send,
  Loader2,
  ExternalLink,
  Maximize2,
  Minimize2,
  Type,
  Bot
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface BookInfo {
  title: string;
  s3_url: string;
  description: string;
  public_access: boolean;
}

interface ChatMessage {
  type: 'user' | 'ai';
  content: string;
  timestamp: string;
}

interface BookReaderProps {
  className?: string;
}

const BookReader: React.FC<BookReaderProps> = ({ className = '' }) => {
  const { user } = useAuth();

  // State
  const [bookInfo, setBookInfo] = useState<BookInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showControls, setShowControls] = useState(true);

  // Chat state
  const [chatQuery, setChatQuery] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  // AI Edit state
  const [aiEditInstruction, setAiEditInstruction] = useState('');
  const [aiEditType, setAiEditType] = useState<'content' | 'style' | 'structure'>('content');
  const [aiEditLoading, setAiEditLoading] = useState(false);
  const [aiEditResult, setAiEditResult] = useState<string>('');

  // Manual Edit state
  const [manualEditContent, setManualEditContent] = useState('');
  const [manualEditLoading, setManualEditLoading] = useState(false);

  useEffect(() => {
    initializeBookReader();
  }, []);

  const initializeBookReader = async () => {
    await fetchBookInfo();
  };

  // API calls using Context7 patterns
  const fetchBookInfo = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${apiUrl}/api/book/info`);
      const data = await response.json();

      if (data.success) {
        setBookInfo(data.book_info);
      } else {
        setError(data.message || 'Failed to fetch book information');
      }
    } catch (err) {
      setError('Error connecting to server');
    } finally {
      setLoading(false);
    }
  };

  const handleChatSubmit = async () => {
    if (!chatQuery.trim() || chatLoading) return;

    const userMessage: ChatMessage = {
      type: 'user',
      content: chatQuery,
      timestamp: new Date().toISOString()
    };

    setChatHistory(prev => [...prev, userMessage]);
    setChatLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${apiUrl}/api/book/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          query: chatQuery,
          conversation_history: chatHistory
        }),
      });

      const data = await response.json();

      if (data.success) {
        const aiMessage: ChatMessage = {
          type: 'ai',
          content: data.response,
          timestamp: new Date().toISOString()
        };
        setChatHistory(prev => [...prev, aiMessage]);
      } else {
        setError(data.message || 'Chat failed');
      }
    } catch (err) {
      setError('Chat request failed');
    } finally {
      setChatLoading(false);
      setChatQuery('');
    }
  };

  const handleAiEditSubmit = async () => {
    if (!aiEditInstruction.trim() || aiEditLoading) return;
    if (!user) {
      setError('Please login to edit the book');
      return;
    }

    setAiEditLoading(true);
    setAiEditResult('');

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${apiUrl}/api/book/edit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          edit_instruction: aiEditInstruction,
          edit_type: aiEditType
        }),
      });

      const data = await response.json();

      if (data.success) {
        setAiEditResult(data.response);
      } else {
        setError(data.message || 'AI edit failed');
      }
    } catch (err) {
      setError('AI edit request failed');
    } finally {
      setAiEditLoading(false);
    }
  };

  const handleManualEditSave = async () => {
    if (!manualEditContent.trim() || manualEditLoading) return;
    if (!user) {
      setError('Please login to edit the book');
      return;
    }

    setManualEditLoading(true);

    try {
      // For now, just simulate saving the manual edit
      // In a real implementation, you'd send this to your backend
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Show success message
      alert('Manual edits saved successfully! (This is a demo - implement actual save functionality)');
    } catch (err) {
      setError('Failed to save manual edits');
    } finally {
      setManualEditLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent, action: 'chat' | 'ai-edit') => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (action === 'chat') {
        handleChatSubmit();
      } else {
        handleAiEditSubmit();
      }
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading book...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Card className="max-w-md mx-auto">
          <CardContent className="pt-6">
            <div className="text-center text-red-600">
              <h3 className="text-lg font-semibold">Error</h3>
              <p>{error}</p>
              <Button onClick={() => window.location.reload()} className="mt-4">
                Try Again
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className={`h-screen flex flex-col ${className}`}>
      {/* Header - Collapsible */}
      <div className={`bg-background border-b transition-all duration-300 ${showControls ? 'h-auto' : 'h-12'} overflow-hidden`}>
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            <BookOpen className="h-6 w-6" />
            <div>
              <h1 className="text-lg font-semibold">{bookInfo?.title}</h1>
              {showControls && (
                <p className="text-sm text-muted-foreground">
                  {bookInfo?.description}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="secondary">
              {bookInfo?.public_access ? 'Public' : 'Private'}
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(bookInfo?.s3_url, '_blank')}
            >
              <ExternalLink className="h-4 w-4 mr-1" />
              Open
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowControls(!showControls)}
            >
              {showControls ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content - Full Screen PDF + Overlay Controls */}
      <div className="flex-1 relative">
        {/* PDF Viewer - Full Screen */}
        <div className="w-full h-full">
          {bookInfo?.s3_url ? (
            <iframe
              src={`${bookInfo.s3_url}#toolbar=1&navpanes=1&scrollbar=1&page=1&view=FitH`}
              className="w-full h-full border-0"
              title={bookInfo.title}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-muted-foreground">
              <p>PDF viewer not available</p>
            </div>
          )}
        </div>

        {/* Floating Controls Panel */}
        {/* {showControls && (
          <div className="absolute top-4 right-4 w-96 bg-black rounded-lg shadow-xl">
            <Tabs defaultValue="chat" className="w-full">
              <div className="border-b px-4 pt-4">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="chat" className="flex items-center gap-2 text-xs">
                    <MessageCircle className="h-3 w-3" />
                    Chat
                  </TabsTrigger>
                  <TabsTrigger value="ai-edit" className="flex items-center gap-2 text-xs">
                    <Bot className="h-3 w-3" />
                    AI Edit
                  </TabsTrigger>
                  <TabsTrigger value="manual-edit" className="flex items-center gap-2 text-xs">
                    <Type className="h-3 w-3" />
                    Manual
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="chat" className="p-4 space-y-3">
                <ScrollArea className="h-60 w-full border rounded-lg p-3">
                  {chatHistory.length === 0 ? (
                    <div className="text-center text-muted-foreground py-4">
                      <MessageCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">Ask Mr. White about the book!</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {chatHistory.map((message, index) => (
                        <div
                          key={index}
                          className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                          <div
                            className={`max-w-[85%] rounded-lg p-2 text-sm ${message.type === 'user'
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
                                        ? <code className="bg-gray-200 px-1 py-0.5 rounded text-xs" {...props} />
                                        : <code className="block bg-gray-200 p-2 rounded my-2 overflow-x-auto text-xs" {...props} />,
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
                              message.content
                            )}
                          </div>
                        </div>
                      ))}
                      {chatLoading && (
                        <div className="flex justify-start">
                          <div className="bg-muted rounded-lg p-2">
                            <Loader2 className="h-3 w-3 animate-spin" />
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </ScrollArea>

                <div className="flex gap-2">
                  <Textarea
                    placeholder="Ask about the book..."
                    value={chatQuery}
                    onChange={(e) => {
                      console.log('Chat input changed:', e.target.value);
                      setChatQuery(e.target.value);
                    }}
                    onKeyDown={(e) => handleKeyPress(e, 'chat')}
                    className="min-h-[40px] text-sm bg-background text-white font-light font-work-sans focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)] resize-none"
                    rows={2}
                    style={{ fontSize: '14px', lineHeight: '1.4' }}
                  />
                  <Button
                    onClick={handleChatSubmit}
                    disabled={!chatQuery.trim() || chatLoading}
                    // size="sm"
                    className="shrink-0"
                  >
                    {chatLoading ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <Send className="h-3 w-3" />
                    )}
                  </Button>
                </div>
              </TabsContent>

              <TabsContent value="ai-edit" className="p-4 space-y-3">
                {!user ? (
                  <div className="text-center py-6 text-muted-foreground">
                    <Edit className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Login to use AI editing</p>
                  </div>
                ) : (
                  <>
                    <div>
                      <label className="text-sm font-medium">Edit Type</label>
                      <div className="flex gap-1 mt-1">
                        {(['content', 'style', 'structure'] as const).map((type) => (
                          <Button
                            key={type}
                            variant={aiEditType === type ? 'default' : 'outline'}
                            size="sm"
                            onClick={() => setAiEditType(type)}
                            className="text-xs"
                          >
                            {type}
                          </Button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <Textarea
                        placeholder="Describe your editing request..."
                        value={aiEditInstruction}
                        onChange={(e) => {
                          console.log('AI edit input changed:', e.target.value);
                          setAiEditInstruction(e.target.value);
                        }}
                        onKeyDown={(e) => handleKeyPress(e, 'ai-edit')}
                        className="min-h-[80px] text-sm bg-background text-white font-light font-work-sans focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)] resize-none"
                        rows={3}
                        style={{ fontSize: '14px', lineHeight: '1.4' }}
                      />
                    </div>

                    <Button
                      onClick={handleAiEditSubmit}
                      disabled={!aiEditInstruction.trim() || aiEditLoading}
                      className="w-full"
                      size="sm"
                    >
                      {aiEditLoading ? (
                        <>
                          <Loader2 className="h-3 w-3 animate-spin mr-2" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <Bot className="h-3 w-3 mr-2" />
                          AI Edit
                        </>
                      )}
                    </Button>

                    {aiEditResult && (
                      <ScrollArea className="h-40 w-full border rounded-lg p-3 mt-3">
                        <div className="whitespace-pre-wrap text-xs">
                          {aiEditResult}
                        </div>
                      </ScrollArea>
                    )}
                  </>
                )}
              </TabsContent>

              <TabsContent value="manual-edit" className="p-4 space-y-3">
                {!user ? (
                  <div className="text-center py-6 text-muted-foreground">
                    <Type className="h-8 w-8 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">Login to edit manually</p>
                  </div>
                ) : (
                  <>
                    <div>
                      <label className="text-sm font-medium">Edit Book Text</label>
                      <Textarea
                        placeholder="Type or paste your book content here for manual editing..."
                        value={manualEditContent}
                        onChange={(e) => {
                          console.log('Manual edit input changed:', e.target.value);
                          setManualEditContent(e.target.value);
                        }}
                        className="min-h-[200px] text-sm mt-1 bg-background text-white font-light font-work-sans focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)] resize-vertical"
                        rows={8}
                        style={{ fontSize: '14px', lineHeight: '1.4' }}
                      />
                    </div>

                    <div className="flex gap-2">
                      <Button
                        onClick={handleManualEditSave}
                        disabled={!manualEditContent.trim() || manualEditLoading}
                        className="flex-1"
                        size="sm"
                      >
                        {manualEditLoading ? (
                          <>
                            <Loader2 className="h-3 w-3 animate-spin mr-2" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Type className="h-3 w-3 mr-2" />
                            Save Edit
                          </>
                        )}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setManualEditContent('')}
                      >
                        Clear
                      </Button>
                    </div>

                    <div className="text-xs text-muted-foreground bg-muted p-2 rounded">
                      <p><strong>Manual Editing:</strong> Type your content directly. Changes will be saved to your personal copy.</p>
                    </div>
                  </>
                )}
              </TabsContent>
            </Tabs>
          </div>
        )} */}
      </div>
    </div>
  );
};

export default BookReader; 