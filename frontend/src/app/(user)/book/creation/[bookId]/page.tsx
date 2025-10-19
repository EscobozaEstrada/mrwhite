'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Download,
  RefreshCw,
  Settings,
  BookOpen,
  ArrowLeft,
  Loader2,
  Pencil,
  Trash2,
  Volume2,
  VolumeX,
  MessageSquare,
  HelpCircle,
  Info
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { enhancedBookService } from '@/services/enhancedBookService';
import { EnhancedBook, EnhancedBookChapter } from '@/types/enhanced-book';
import { stopSpeaking } from '@/utils/messageUtils';
import { FaWandMagicSparkles } from "react-icons/fa6";
import { AiFillEdit } from 'react-icons/ai';
import { MdContentPaste } from 'react-icons/md';
import { IoStatsChart, IoText } from 'react-icons/io5';
import { FaBookOpen } from 'react-icons/fa';
import { FaQuestionCircle } from 'react-icons/fa';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu';
import { FiLoader } from 'react-icons/fi';

// Define API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

// Audio cache to store audio by chapter ID
interface AudioCacheItem {
  blob: Blob;
  url: string;
  audio: HTMLAudioElement;
}

// Chat message interface
interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

// Voice settings interface
interface VoiceSettings {
  speed: number;
  stability: number;
  similarity_boost: number;
}

export default function EnhancedBookPage() {
  const { bookId } = useParams();
  const router = useRouter();
  const { user } = useAuth();

  // Audio cache ref to persist between renders
  const audioCache = useRef<Map<number, AudioCacheItem>>(new Map());
  const currentAudio = useRef<HTMLAudioElement | null>(null);

  const [book, setBook] = useState<EnhancedBook | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [generatingEpub, setGeneratingEpub] = useState(false);
  const [editChapterDialogOpen, setEditChapterDialogOpen] = useState(false);
  const [deleteChapterDialogOpen, setDeleteChapterDialogOpen] = useState(false);
  const [deleteBookDialogOpen, setDeleteBookDialogOpen] = useState(false);
  const [currentChapter, setCurrentChapter] = useState<EnhancedBookChapter | null>(null);
  const [editedTitle, setEditedTitle] = useState('');
  const [editedContent, setEditedContent] = useState('');
  const [speakingChapterId, setSpeakingChapterId] = useState<number | null>(null);
  const [speakingState, setSpeakingState] = useState<'loading' | 'speaking' | 'stopped'>('stopped');
  const [deletingChapter, setDeletingChapter] = useState(false);
  const [deletingBook, setDeletingBook] = useState(false);

  // AI chat state
  const [showAiChat, setShowAiChat] = useState(false);
  const [aiChatInput, setAiChatInput] = useState('');
  const [aiChatMessages, setAiChatMessages] = useState<ChatMessage[]>([]);
  const [aiChatLoading, setAiChatLoading] = useState(false);
  const [fetchingLatestChats, setFetchingLatestChats] = useState(false);
  const [updatingChapter, setUpdatingChapter] = useState(false);
  const [howItWorksDialogOpen, setHowItWorksDialogOpen] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [isChunkedProcessing, setIsChunkedProcessing] = useState(false);
  const [chunkStats, setChunkStats] = useState<{total: number, processed: number} | null>(null);

  // Initialize voice settings from localStorage or use defaults
  const [voiceSettings, setVoiceSettings] = useState<VoiceSettings>(() => {
    // Try to get voice settings from localStorage
    if (typeof window !== 'undefined') {
      const savedSettings = localStorage.getItem('voiceSettings');
      if (savedSettings) {
        try {
          return JSON.parse(savedSettings);
        } catch (e) {
          console.error('Error parsing saved voice settings:', e);
        }
      }
    }
    // Default settings if nothing in localStorage
    return {
      speed: 1.0,
      stability: 0.5,
      similarity_boost: 0.75
    };
  });

  useEffect(() => {
    if (!user) {
      router.push('/login');
      return;
    }

    fetchBookData();
  }, [bookId, user, router]);

  // Save voice settings to localStorage whenever they change
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('voiceSettings', JSON.stringify(voiceSettings));
    }
  }, [voiceSettings]);

  // Stop speaking and clean up audio cache when component unmounts
  useEffect(() => {
    return () => {
      // Stop any playing audio
      if (currentAudio.current) {
        currentAudio.current.pause();
        currentAudio.current.currentTime = 0;
        currentAudio.current = null;
      }

      // Clean up all cached audio URLs
      audioCache.current.forEach((item) => {
        URL.revokeObjectURL(item.url);
      });

      // Clear the cache
      audioCache.current.clear();

      // Also call the global stopSpeaking for backward compatibility
      stopSpeaking();
    };
  }, []);

  const fetchBookData = async () => {
    setLoading(true);
    try {
      const bookData = await enhancedBookService.getBook(Number(bookId));
      setBook(bookData);
    } catch (error) {
      console.error('Error fetching book data:', error);
      toast.error('Failed to load book data');
    } finally {
      setLoading(false);
    }
  };

  const handleGeneratePdf = async () => {
    setGeneratingPdf(true);
    try {
      const pdfUrl = await enhancedBookService.generatePdf(Number(bookId));

      if (pdfUrl) {
        // Update book with new PDF URL
        setBook(prev => prev ? { ...prev, pdf_url: pdfUrl } : null);
        toast.success('PDF generated successfully');
      }
    } catch (error) {
      console.error('Error generating PDF:', error);
      toast.error('Failed to generate PDF');
    } finally {
      setGeneratingPdf(false);
    }
  };

  const handleGoBack = () => {
    router.back();
  };

  const handleGenerateEpub = async () => {
    setGeneratingEpub(true);
    try {
      const epubUrl = await enhancedBookService.generateEpub(Number(bookId));

      if (epubUrl) {
        // Update book with new EPUB URL
        setBook(prev => prev ? { ...prev, epub_url: epubUrl } : null);
        toast.success('EPUB generated successfully');
      }
    } catch (error) {
      console.error('Error generating EPUB:', error);
      toast.error('Failed to generate EPUB');
    } finally {
      setGeneratingEpub(false);
    }
  };

  const openEditChapterDialog = (chapter: EnhancedBookChapter) => {
    setCurrentChapter(chapter);
    setEditedTitle(chapter.title);
    setEditedContent(chapter.content);
    setEditChapterDialogOpen(true);
    // Reset AI chat state when opening dialog
    setShowAiChat(false);
    setAiChatInput('');
    setAiChatMessages([]);
  };

  const openDeleteChapterDialog = (chapter: EnhancedBookChapter) => {
    setCurrentChapter(chapter);
    setDeleteChapterDialogOpen(true);
  };

  const handleUpdateChapter = async () => {
    if (!currentChapter) return;
    
    setUpdatingChapter(true);
    try {
      await enhancedBookService.updateChapter(
        Number(bookId),
        currentChapter.id,
        {
          title: editedTitle,
          content: editedContent
        }
      );
      
      // Update the book state with the edited chapter
      setBook(prev => {
        if (!prev) return null;
        
        const updatedChapters = prev.chapters.map(ch => 
          ch.id === currentChapter.id 
            ? { ...ch, title: editedTitle, content: editedContent }
            : ch
        );
        
        return { ...prev, chapters: updatedChapters };
      });
      
      // Clear audio cache for this chapter to ensure new audio is generated with current settings
      audioCache.current.delete(currentChapter.id);
      
      setEditChapterDialogOpen(false);
      toast.success('Chapter updated successfully');
      
      // Clear AI chat state
      setAiChatMessages([]);
      setAiChatInput('');
      setShowAiChat(false);
    } catch (error) {
      console.error('Error updating chapter:', error);
      toast.error('Failed to update chapter');
    } finally {
      setUpdatingChapter(false);
    }
  };

  // Toggle AI chat visibility
  const toggleAiChat = () => {
    setShowAiChat(prev => !prev);
  };

  // Handle AI chat submission
  const handleAiChatSubmit = async () => {
    if (!aiChatInput.trim() || aiChatLoading || !currentChapter || !book) return;

    // Add user message to chat
    const userMessage: ChatMessage = {
      role: 'user',
      content: aiChatInput
    };

    setAiChatMessages(prev => [...prev, userMessage]);
    setAiChatInput('');
    setAiChatLoading(true);
    setProcessingProgress(0);
    setIsChunkedProcessing(false);
    setChunkStats(null);

    try {
      // Prepare context for AI
      const bookContext = {
        bookTitle: book.title,
        chapterTitle: currentChapter.title,
        chapterContent: editedContent,
        tone: book.tone_type,
        textStyle: book.text_style
      };
      
      // Call API to get AI response with progress tracking
      const response = await enhancedBookService.aiChatEdit(
        Number(bookId),
        userMessage.content,
        bookContext,
        aiChatMessages,
        (progress) => {
          // Only show progress bar if we're making meaningful progress
          if (progress > 0) {
            setIsChunkedProcessing(true);
            setProcessingProgress(progress);
          }
        }
      );

      if (response.success) {
        // Add AI response to chat
        const aiMessage: ChatMessage = {
          role: 'assistant',
          content: response.message
        };

        setAiChatMessages(prev => [...prev, aiMessage]);

        // Only update the chapter content if the intent was to edit
        if (response.intent === 'edit' && response.editedContent) {
          setEditedContent(response.editedContent);
          
          // Show appropriate toast based on whether chunked processing was used
          if (response.is_chunked_processing) {
            const successRate = response.chunks_successful ? 
              Math.round((response.chunks_successful / (response.chunks_processed || 1)) * 100) : 100;
            
            setChunkStats({
              total: response.chunks_processed || 0,
              processed: response.chunks_successful || 0
            });
            
            if (successRate < 100) {
              toast.success(`Content processed in ${response.chunks_processed} chunks (${successRate}% successful). Some sections may not have been fully edited.`, { 
                id: 'ai-edit',
                duration: 5000
              });
            } else {
              toast.success(`AI has updated the chapter content (processed in ${response.chunks_processed} chunks)`, { id: 'ai-edit' });
            }
          } else {
            toast.success('AI has updated the chapter content', { id: 'ai-edit' });
          }

          // Scroll to the content textarea to show changes
          setTimeout(() => {
            const contentElement = document.getElementById('chapterContent');
            if (contentElement) {
              contentElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          }, 100);
        } else {
          // Just dismiss the loading toast for non-edit responses
          toast.success('AI responded to your question', { id: 'ai-edit' });
        }
      } else {
        toast.error('Failed to get AI response', { id: 'ai-edit' });
      }
    } catch (error) {
      console.error('Error with AI chat:', error);
      toast.error('Error communicating with AI service', { id: 'ai-edit' });
    } finally {
      setAiChatLoading(false);
      // Don't reset progress immediately to allow users to see the final state
      setTimeout(() => {
        setProcessingProgress(0);
        setIsChunkedProcessing(false);
      }, 2000);
    }
  };

  // Fetch latest chats and append to content
  const handleRefreshChats = async () => {
    if (fetchingLatestChats || !currentChapter || !book) return;
    
    setFetchingLatestChats(true);
    try {
      // Call API to get latest chats
      const response = await enhancedBookService.getLatestChats(
        Number(bookId),
        currentChapter.category, // Pass the chapter's category
        currentChapter.id // Pass the chapter ID to track last fetch time
      );
      
      if (response.success && response.formattedContent) {
        // Append the formatted content to the current chapter content
        const updatedContent = `${editedContent}\n\n${response.formattedContent}`;
        setEditedContent(updatedContent);
        toast.success(`Added content from ${response.messageCount} recent messages related to "${currentChapter.category}"`, {
          duration: 2000
        });
      } else {
        toast.error(`No recent chats found related to "${currentChapter.category}"`);
      }
    } catch (error) {
      console.error('Error fetching latest chats:', error);
      toast.error('Failed to fetch latest chats');
    } finally {
      setFetchingLatestChats(false);
    }
  };

  const handleDeleteChapter = async () => {
    if (!currentChapter) return;

    setDeletingChapter(true);
    try {
      await enhancedBookService.deleteChapter(
        Number(bookId),
        currentChapter.id
      );

      // Update the book state by removing the deleted chapter
      setBook(prev => {
        if (!prev) return null;

        return {
          ...prev,
          chapters: prev.chapters.filter(ch => ch.id !== currentChapter.id)
        };
      });

      setDeleteChapterDialogOpen(false);
      toast.success('Chapter deleted successfully');
    } catch (error) {
      console.error('Error deleting chapter:', error);
      toast.error('Failed to delete chapter');
    } finally {
      setDeletingChapter(false);
    }
  };

  const handleDeleteBook = async () => {
    setDeletingBook(true);
    try {
      await enhancedBookService.deleteBook(Number(bookId));
      toast.success('Book deleted successfully');
      setDeleteBookDialogOpen(false);
      // Redirect to talk page after deletion
      router.push('/talk/conversation/new-chat');
    } catch (error) {
      console.error('Error deleting book:', error);
      toast.error('Failed to delete book');
    } finally {
      setDeletingBook(false);
    }
  };

  const handleSpeakChapter = async (chapter: EnhancedBookChapter) => {
    if (speakingChapterId === chapter.id && speakingState !== 'stopped') {
      if (currentAudio.current) {
        currentAudio.current.pause();
        currentAudio.current.currentTime = 0;
        currentAudio.current = null;
      }
      setSpeakingState('stopped');
      setSpeakingChapterId(null);
      return;
    }
  
    if (speakingChapterId !== null && currentAudio.current) {
      currentAudio.current.pause();
      currentAudio.current.currentTime = 0;
    }
  
    setSpeakingChapterId(chapter.id);
  
    // Use cache if available
    if (audioCache.current.has(chapter.id)) {
      const cachedItem = audioCache.current.get(chapter.id)!;
      currentAudio.current = cachedItem.audio;
      currentAudio.current.currentTime = 0;
      setSpeakingState('speaking');
      toast.success(`Now narrating: ${chapter.title}`, {
        duration: 2000,
        icon: '🔊'
      });
  
      try {
        await cachedItem.audio.play();
        cachedItem.audio.onended = () => {
          setSpeakingState('stopped');
          setSpeakingChapterId(null);
          if (currentAudio.current) {
            currentAudio.current.currentTime = 0;
            currentAudio.current = null;
          }
        };
      } catch (error) {
        console.error('Error playing cached audio:', error);
        setSpeakingState('stopped');
        setSpeakingChapterId(null);
      }
  
      return;
    }
  
    setSpeakingState('loading');
    const enhancedContent = prepareContentForNarration(chapter);
    const plainText = enhancedContent;
    const maxChars = 10000;
  
    // Split long text
    const textChunks = [];
    for (let i = 0; i < plainText.length; i += maxChars) {
      textChunks.push(plainText.slice(i, i + maxChars));
    }
  
    try {
      const audioBlobs: Blob[] = [];
  
      for (const chunk of textChunks) {
        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/text-to-speech`,
          { 
            text: chunk,
            speed: voiceSettings.speed,
            stability: voiceSettings.stability,
            similarity_boost: voiceSettings.similarity_boost
          },
          { responseType: 'blob', withCredentials: true }
        );
  
        audioBlobs.push(new Blob([response.data], { type: 'audio/mpeg' }));
      }
  
      const audioUrls = audioBlobs.map(blob => URL.createObjectURL(blob));
      const audios = audioUrls.map(url => new Audio(url));
      audioCache.current.set(chapter.id, {
        blob: audioBlobs[0], // optional
        url: audioUrls[0],   // optional
        audio: audios[0]     // first one
      });
  
      let currentIndex = 0;
  
      const playNext = async () => {
        if (currentIndex >= audios.length) {
          setSpeakingState('stopped');
          setSpeakingChapterId(null);
          currentAudio.current = null;
          return;
        }
  
        const audio = audios[currentIndex];
        currentAudio.current = audio;
        setSpeakingState('speaking');
  
        audio.onended = () => {
          currentIndex++;
          playNext();
        };
  
        try {
          await audio.play();
        } catch (err) {
          console.error('Audio play error:', err);
          setSpeakingState('stopped');
          setSpeakingChapterId(null);
        }
      };
  
      toast.success(`Now narrating: ${chapter.title}`, {
        duration: 2000,
        icon: '🔊'
      });
  
      playNext();
  
    } catch (error) {
      console.error('Error loading audio:', error);
      setSpeakingState('stopped');
      setSpeakingChapterId(null);
      toast.error('Failed to load audio narration');
    }
  };

  // Process content to make narration more engaging
  const prepareContentForNarration = (chapter: EnhancedBookChapter): string => {
    // Start with an instruction for the AI voice
    let enhancedContent = "";

    // Add chapter title with pause
    enhancedContent += `${chapter.title}.\n\n`;

    // Process paragraphs to add better pacing
    const paragraphs = chapter.content.split('\n').filter(p => p.trim().length > 0);

    // Add paragraphs with proper spacing for pacing
    paragraphs.forEach((paragraph, index) => {
      // Clean up any markdown or special characters
      const cleanParagraph = paragraph
        .replace(/[*_~`#]/g, '') // Remove markdown symbols
        .replace(/^\s*[-*+]\s+/, '') // Remove list markers
        .replace(/^\s*\d+\.\s+/, '') // Remove numbered list markers
        .trim();

      if (cleanParagraph) {
        // Check if paragraph contains dialogue
        if (cleanParagraph.includes('"')) {
          // Add instruction for dialogue
          enhancedContent += `${cleanParagraph}`;
        } else {
          enhancedContent += cleanParagraph;
        }
      }
    });

    return enhancedContent;
  };

  // Add this function to handle voice settings changes
  const handleVoiceSettingChange = (setting: string, value: number) => {
    setVoiceSettings((prev: VoiceSettings) => ({
      ...prev,
      [setting]: value
    }));
    
    // Clear the entire audio cache when settings change to force regeneration with new settings
    audioCache.current.clear();
    
    // If there's currently audio playing, stop it
    if (speakingChapterId !== null && currentAudio.current) {
      currentAudio.current.pause();
      currentAudio.current.currentTime = 0;
      currentAudio.current = null;
      setSpeakingState('stopped');
      setSpeakingChapterId(null);
    }

    // Show feedback to the user
    toast.success(`Voice ${setting.replace('_', ' ')} updated`, {
      duration: 1000,
      icon: '🔊'
    });
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <p className="mt-4">Loading book...</p>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <p>Book not found or you do not have permission to view it.</p>
        <Button className="mt-4" onClick={() => router.push('/talk')}>
          Back to Conversations
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-6 px-12 max-[1024px]:px-4 max-[450px]:px-3 bg-background">
      <div className="flex items-center mb-6">
        <Button variant="ghost" onClick={handleGoBack} className="mr-2">
          <ArrowLeft className="h-4 w-4 max-[768px]:mr-0 mr-2" />
          <span className="max-[530px]:hidden block">Back</span>
        </Button>
        <h1 className="text-3xl font-bold">
          <FaBookOpen className="w-8 h-8 inline-block mr-2 text-[var(--mrwhite-primary-color)]" />
          {book.title}
        </h1>
        <div className="ml-auto flex items-center gap-2">
          <Button 
            variant="outline" 
            onClick={() => setDeleteBookDialogOpen(true)}
            className="text-red-500 border-red-500 hover:bg-red-500/10 "
          >
            <Trash2 className="h-4 w-4 max-[768px]:mr-0 mr-2" />
            <span className="max-[768px]:hidden block">Delete Book</span>
          </Button>
          <Button 
            variant="ghost" 
            onClick={() => setHowItWorksDialogOpen(true)} 
            title="How It Works"
          >
            <HelpCircle className="h-5 w-5 mr-1" />
            <span className="max-[768px]:hidden block">How It Works</span>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <BookOpen className="h-5 w-5 mr-2" />
              Book Details
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div>
                <span className="font-medium">Tone:</span> {book.tone_type.charAt(0).toUpperCase() + book.tone_type.slice(1)}
              </div>
              <div>
                <span className="font-medium">Text Style:</span> {book.text_style.charAt(0).toUpperCase() + book.text_style.slice(1)}
              </div>
              <div>
                <span className="font-medium">Status:</span> {book.status.charAt(0).toUpperCase() + book.status.slice(1)}
              </div>
              <div>
                <span className="font-medium">Created:</span> {new Date(book.created_at).toLocaleDateString()}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Download className="h-5 w-5 mr-2" />
              Download Book
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={handleGeneratePdf}
              disabled={generatingPdf}
              className="w-full"
            >
              {generatingPdf ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating PDF...
                </>
              ) : (
                <>
                  {book.pdf_url ? 'Regenerate PDF' : 'Generate PDF'}
                </>
              )}
            </Button>

            {book.pdf_url && (
              <Button
                variant="outline"
                className="w-full"
                onClick={() => book.pdf_url && window.open(book.pdf_url, '_blank')}
              >
                <Download className="h-4 w-4 mr-2" />
                Download PDF
              </Button>
            )}

            <Button
              onClick={handleGenerateEpub}
              disabled={generatingEpub}
              className="w-full"
            >
              {generatingEpub ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Generating EPUB...
                </>
              ) : (
                <>
                  {book.epub_url ? 'Regenerate EPUB' : 'Generate EPUB'}
                </>
              )}
            </Button>

            {book.epub_url && (
              <Button
                variant="outline"
                className="w-full"
                onClick={() => book.epub_url && window.open(book.epub_url, '_blank')}
              >
                <Download className="h-4 w-4 mr-2" />
                Download EPUB
              </Button>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <IoStatsChart className="h-5 w-5 mr-2" />
              Book Stats
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div>
                <span className="font-medium">Chapters:</span> {book.chapters.length}
              </div>
              <div>
                <span className="font-medium">Categories:</span> {new Set(book.chapters.map(ch => ch.category)).size}
              </div>
              <div>
                <span className="font-medium">Total Content:</span> {book.chapters.reduce((acc, ch) => acc + ch.content.length, 0).toLocaleString()} characters
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="chapters" className="w-full">
        <TabsList>
          <TabsTrigger value="chapters">Chapters</TabsTrigger>
        </TabsList>

        <TabsContent value="chapters" className="mt-6">
          {book.chapters.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No chapters found in this book.</p>
            </div>
          ) : (
            <div className="space-y-6">
              {book.chapters.sort((a, b) => a.order - b.order).map((chapter) => (
                <Card key={chapter.id}>
                  <CardHeader className="pb-2">
                    <div className="flex justify-between items-center">
                      <CardTitle className="text-xl">{chapter.title}</CardTitle>
                      <div className="flex space-x-2 items-center">
                        <span className="text-sm text-muted-foreground max-[440px]:hidden" title="Word count">
                          {chapter.content.split(/\s+/).length} words
                        </span>
                        
                        {/* Voice Settings Dropdown */}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="relative max-[500px]:hidden"
                              title="Voice Settings"
                            >
                              <Settings className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-64 p-4 space-y-4 bg-neutral-900">
                            <DropdownMenuLabel className="flex items-center">
                              <Volume2 className="h-4 w-4 mr-2 text-[var(--mrwhite-primary-color)]" />
                              Voice Tuning
                            </DropdownMenuLabel>
                            <DropdownMenuSeparator />
                            
                            {/* Speed Control */}
                            <div className="space-y-2">
                              <div className="flex justify-between items-center">
                                <Label className="text-xs">Speed: {voiceSettings.speed.toFixed(2)}</Label>
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  className="h-6 text-xs"
                                  onClick={() => handleVoiceSettingChange('speed', 1.0)}
                                >
                                  Reset
                                </Button>
                              </div>
                              <Slider
                                min={0.7}
                                max={1.2}
                                step={0.01}
                                value={[voiceSettings.speed]}
                                onValueChange={(values: number[]) => handleVoiceSettingChange('speed', values[0])}
                                className="w-full"
                              />
                              <div className="flex justify-between text-xs text-gray-400">
                                <span>Slower</span>
                                <span>Faster</span>
                              </div>
                            </div>
                            
                            {/* Stability Control */}
                            <div className="space-y-2">
                              <div className="flex justify-between items-center">
                                <Label className="text-xs">Stability: {voiceSettings.stability.toFixed(2)}</Label>
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  className="h-6 text-xs"
                                  onClick={() => handleVoiceSettingChange('stability', 0.5)}
                                >
                                  Reset
                                </Button>
                              </div>
                              <Slider
                                min={0.0}
                                max={1.0}
                                step={0.01}
                                value={[voiceSettings.stability]}
                                onValueChange={(values: number[]) => handleVoiceSettingChange('stability', values[0])}
                                className="w-full"
                              />
                              <div className="flex justify-between text-xs text-gray-400">
                                <span>More Expressive</span>
                                <span>More Consistent</span>
                              </div>
                            </div>
                            
                            {/* Similarity Boost Control */}
                            <div className="space-y-2">
                              <div className="flex justify-between items-center">
                                <Label className="text-xs">Clarity + Similarity: {voiceSettings.similarity_boost.toFixed(2)}</Label>
                                <Button 
                                  variant="ghost" 
                                  size="sm" 
                                  className="h-6 text-xs"
                                  onClick={() => handleVoiceSettingChange('similarity_boost', 0.75)}
                                >
                                  Reset
                                </Button>
                              </div>
                              <Slider
                                min={0.0}
                                max={1.0}
                                step={0.01}
                                value={[voiceSettings.similarity_boost]}
                                onValueChange={(values: number[]) => handleVoiceSettingChange('similarity_boost', values[0])}
                                className="w-full"
                              />
                              <div className="flex justify-between text-xs text-gray-400">
                                <span>Less Similar</span>
                                <span>More Similar</span>
                              </div>
                            </div>
                          </DropdownMenuContent>
                        </DropdownMenu>

                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleSpeakChapter(chapter)}
                          aria-label={speakingChapterId === chapter.id ? "Stop speaking" : "Speak chapter"}
                          className={speakingChapterId === chapter.id ? "text-blue-500" : ""}
                          title={speakingChapterId === chapter.id ? "Stop speaking" : "Speak chapter"}
                        >
                          {speakingChapterId === chapter.id ? (
                            speakingState === 'loading' ? (
                              <FiLoader className="h-4 w-4 animate-spin" />
                            ) : (
                              <VolumeX className="h-4 w-4" />
                            )
                          ) : (
                            <Volume2 className="h-4 w-4" />
                          )}
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openEditChapterDialog(chapter)}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openDeleteChapterDialog(chapter)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Category: {chapter.category}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="prose max-w-none">
                      {chapter.content.split('\n').map((paragraph, i) => (
                        <p key={i}>{paragraph}</p>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Enhanced Edit Chapter Dialog */}
      <Dialog open={editChapterDialogOpen} onOpenChange={setEditChapterDialogOpen} modal={true}>
        <DialogContent className="sm:max-w-[700px] max-h-[90vh] flex flex-col font-work-sans" onPointerDownOutside={(e) => e.preventDefault()}>
          <DialogHeader>
            <DialogTitle>
              <AiFillEdit className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)]" />
              Edit Chapter
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4 overflow-x-hidden overflow-y-auto flex-1 custom-scrollbar pr-2">
            {/* Chapter Title */}
            <div className="space-y-2">
              <Label htmlFor="chapterTitle"><IoText className="text-[var(--mrwhite-primary-color)]" />Chapter Title</Label>
              <input
                id="chapterTitle"
                value={editedTitle}
                onChange={(e) => setEditedTitle(e.target.value)}
                className="w-full bg-[#000000] font-light border border-gray-700 rounded-sm py-1 pl-2 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
              />
            </div>

            {/* Voice Tuning Controls */}
            <div className="space-y-4 bg-neutral-900 p-4 rounded-md hidden max-[500px]:block">
              <h3 className="text-sm font-medium flex items-center">
                <Volume2 className="h-4 w-4 mr-2 text-[var(--mrwhite-primary-color)]" />
                Voice Tuning
              </h3>
              
              {/* Speed Control */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label htmlFor="speed" className="text-xs">Speed: {voiceSettings.speed.toFixed(2)}</Label>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 text-xs"
                    onClick={() => handleVoiceSettingChange('speed', 1.0)}
                  >
                    Reset
                  </Button>
                </div>
                <Slider
                  id="speed"
                  min={0.7}
                  max={1.2}
                  step={0.01}
                  value={[voiceSettings.speed]}
                  onValueChange={(values: number[]) => handleVoiceSettingChange('speed', values[0])}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>Slower</span>
                  <span>Faster</span>
                </div>
              </div>
              
              {/* Stability Control */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label htmlFor="stability" className="text-xs">Stability: {voiceSettings.stability.toFixed(2)}</Label>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 text-xs"
                    onClick={() => handleVoiceSettingChange('stability', 0.5)}
                  >
                    Reset
                  </Button>
                </div>
                <Slider
                  id="stability"
                  min={0.0}
                  max={1.0}
                  step={0.01}
                  value={[voiceSettings.stability]}
                  onValueChange={(values: number[]) => handleVoiceSettingChange('stability', values[0])}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>More Expressive</span>
                  <span>More Consistent</span>
                </div>
              </div>
              
              {/* Similarity Boost Control */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <Label htmlFor="similarity" className="text-xs">Clarity + Similarity: {voiceSettings.similarity_boost.toFixed(2)}</Label>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    className="h-6 text-xs"
                    onClick={() => handleVoiceSettingChange('similarity_boost', 0.75)}
                  >
                    Reset
                  </Button>
                </div>
                <Slider
                  id="similarity"
                  min={0.0}
                  max={1.0}
                  step={0.01}
                  value={[voiceSettings.similarity_boost]}
                  onValueChange={(values: number[]) => handleVoiceSettingChange('similarity_boost', values[0])}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400">
                  <span>Less Similar</span>
                  <span>More Similar</span>
                </div>
              </div>
            </div>

            {/* AI Controls */}
            <div className="flex items-center space-x-2">
              <Button
                variant={showAiChat ? "secondary" : "outline"}
                size="sm"
                onClick={toggleAiChat}
                className="flex items-center"
              >
                <FaWandMagicSparkles className={`h-4 w-4 max-[400px]:mr-0 mr-2 ${showAiChat ? 'text-[var(--mrwhite-primary-color)]' : 'text-white'}`} />
                <span className="max-[400px]:hidden block">AI Edit</span>
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={handleRefreshChats}
                disabled={fetchingLatestChats}
                className="flex items-center"
              >
                {fetchingLatestChats ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <RefreshCw className="h-4 w-4 max-[400px]:mr-0 mr-2" />
                )}
                <span className="max-[400px]:hidden block">Fetch Latest Chats</span>
              </Button>
            </div>

            {/* AI Chat Interface (conditionally rendered) */}
            {showAiChat && (
              <div className="border rounded-md p-3 space-y-3 bg-neutral-900">


                {/* Chat Messages */}
                <div className="max-h-[200px] flex flex-col overflow-y-auto pr-2 custom-scrollbar space-y-2 mb-2">
                  {aiChatMessages.length > 0 ? (
                    aiChatMessages.map((msg, i) => (
                      <div
                        key={i}
                        className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`p-2 rounded-md max-w-[60%] ${msg.role === 'user'
                              ? 'bg-neutral-800 border-l-2 border-blue-500'
                              : 'bg-neutral-800 border-l-2 border-green-500'
                            }`}
                        >
                          <p className="text-sm">{msg.content}</p>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center text-sm text-gray-500 py-2">
                      Tell the AI what changes to make to your chapter
                    </div>
                  )}

                  {aiChatLoading && (
                    <div className="flex flex-col items-center justify-center p-2 space-y-2">
                      <div className="flex items-center">
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        <span className="text-sm">
                          {isChunkedProcessing 
                            ? "Processing long content in chunks..." 
                            : "AI is editing your content..."}
                        </span>
                      </div>
                      
                      {isChunkedProcessing && (
                        <div className="w-full space-y-1">
                          <Progress value={processingProgress} className="h-1 w-full" />
                          <div className="flex justify-between text-xs text-gray-500">
                            <span>{processingProgress}%</span>
                            {chunkStats && (
                              <span>{chunkStats.processed}/{chunkStats.total} chunks processed</span>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Chat Input */}
                <div className="flex items-center space-x-2">
                  <input
                    placeholder="Describe the changes you want to make..."
                    value={aiChatInput}
                    onChange={(e) => setAiChatInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleAiChatSubmit()}
                    disabled={aiChatLoading}
                    className="w-full bg-[#000000] border border-gray-700 rounded-sm py-1 pl-2 pr-4 text-white placeholder-gray-400 focus:outline-none focus:border-[var(--mrwhite-primary-color)] focus:ring-1 focus:ring-[var(--mrwhite-primary-color)]"
                  />
                  <Button
                    size="sm"
                    onClick={handleAiChatSubmit}
                    disabled={aiChatLoading || !aiChatInput.trim()}
                  >
                    Edit
                  </Button>
                </div>
              </div>
            )}

            {/* Chapter Content */}
            <div className="space-y-2">
              <Label htmlFor="chapterContent" className=""><MdContentPaste className="text-[var(--mrwhite-primary-color)]" />Chapter Content</Label>
              <Textarea
                id="chapterContent"
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                className="min-h-[170px] max-h-[100px] custom-scrollbar font-light"
              />
            </div>
          </div>

          <DialogFooter className="pt-2 border-t">
            <Button variant="outline" onClick={() => setEditChapterDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateChapter} disabled={updatingChapter}>
              {updatingChapter ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Chapter Dialog */}
      <Dialog open={deleteChapterDialogOpen} onOpenChange={setDeleteChapterDialogOpen}>
        <DialogContent className="sm:max-w-[500px] max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Delete Chapter</DialogTitle>
          </DialogHeader>
          <div className="py-4 flex-1 overflow-y-auto">
            <p>Are you sure you want to delete this chapter?</p>
            <p className="font-medium mt-2">{currentChapter?.title}</p>
            <p className="text-sm text-muted-foreground mt-1">This action cannot be undone.</p>
          </div>
          <DialogFooter className="pt-2 border-t">
            <Button variant="outline" onClick={() => setDeleteChapterDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              className="bg-red-500 hover:bg-red-600 text-white"
              onClick={handleDeleteChapter}
              disabled={deletingChapter}
            >
              {deletingChapter ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Book Dialog */}
      <Dialog open={deleteBookDialogOpen} onOpenChange={setDeleteBookDialogOpen}>
        <DialogContent className="sm:max-w-[500px] max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>Delete Book</DialogTitle>
          </DialogHeader>
          <div className="py-4 flex-1 overflow-y-auto">
            <p>Are you sure you want to delete this book?</p>
            <p className="font-medium mt-2">{book.title}</p>
            <p className="text-sm text-muted-foreground mt-1">This action cannot be undone. All chapters and content will be permanently deleted.</p>
          </div>
          <DialogFooter className="pt-2 border-t">
            <Button variant="outline" onClick={() => setDeleteBookDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              className="bg-red-500 hover:bg-red-600 text-white"
              onClick={handleDeleteBook}
              disabled={deletingBook}
            >
              {deletingBook ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                'Delete Book'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* How It Works Dialog */}
      <Dialog open={howItWorksDialogOpen} onOpenChange={setHowItWorksDialogOpen}>
        <DialogContent className="sm:max-w-[700px] max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="flex items-center text-xl">
              <FaQuestionCircle className="w-6 h-6 inline-block mr-2 text-[var(--mrwhite-primary-color)]" />
              How It Works: Book Creation Page
            </DialogTitle>
          </DialogHeader>
          <div className="py-4 flex-1 overflow-y-auto pr-2 custom-scrollbar">
            <div className="space-y-6">
              {/* Overview Section */}
              <div>
                <h3 className="text-lg font-medium mb-2 flex items-center">
                  <Info className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
                  Overview
                </h3>
                <p className="text-sm text-muted-foreground">
                  This page allows you to view, edit, and manage your AI-generated book. You can modify chapters, 
                  generate downloadable formats, and use AI assistance to improve your content.
                </p>
              </div>
              
              {/* Book Details Section */}
              <div>
                <h3 className="text-lg font-medium mb-2 flex items-center">
                  <BookOpen className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
                  Book Details
                </h3>
                <p className="text-sm text-muted-foreground mb-2">
                  The Book Details card shows important information about your book:
                </p>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  <li><span className="font-medium">Tone:</span> The emotional tone of your book (friendly, narrative, playful, etc.)</li>
                  <li><span className="font-medium">Text Style:</span> The writing style used throughout the book</li>
                  <li><span className="font-medium">Status:</span> Current state of the book (draft, completed, etc.)</li>
                  <li><span className="font-medium">Created:</span> The date when the book was initially created</li>
                </ul>
              </div>
              
              {/* Download Options Section */}
              <div>
                <h3 className="text-lg font-medium mb-2 flex items-center">
                  <Download className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
                  Download Options
                </h3>
                <p className="text-sm text-muted-foreground mb-2">
                  You can generate and download your book in different formats:
                </p>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  <li><span className="font-medium">Generate PDF:</span> Creates a PDF version of your book with proper formatting</li>
                  <li><span className="font-medium">Generate EPUB:</span> Creates an EPUB file for e-readers</li>
                  <li>Once generated, download buttons will appear to save the files to your device</li>
                  <li>You can regenerate files after making changes to update the content</li>
                </ul>
              </div>
              
              {/* Chapters Section */}
              <div>
                <h3 className="text-lg font-medium mb-2 flex items-center">
                  <AiFillEdit className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
                  Managing Chapters
                </h3>
                <p className="text-sm text-muted-foreground mb-2">
                  The Chapters tab displays all chapters in your book:
                </p>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  <li><span className="font-medium">Edit Chapter:</span> Click the pencil icon to modify a chapter's title and content</li>
                  <li><span className="font-medium">Delete Chapter:</span> Click the trash icon to remove a chapter (this cannot be undone)</li>
                  <li><span className="font-medium">Audio Narration:</span> Click the speaker icon to have the chapter narrated aloud</li>
                  <li>Chapters are organized by their original order in the book</li>
                </ul>
              </div>
              
              {/* AI Editing Section */}
              <div>
                <h3 className="text-lg font-medium mb-2 flex items-center">
                  <FaWandMagicSparkles className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
                  AI Editing Assistant
                </h3>
                <p className="text-sm text-muted-foreground mb-2">
                  When editing a chapter, you can use AI to help improve your content:
                </p>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  <li><span className="font-medium">AI Edit:</span> Click this button to open the AI chat interface</li>
                  <li><span className="font-medium">Ask for changes:</span> Type instructions like "Make this more dramatic" or "Fix grammar errors"</li>
                  <li><span className="font-medium">Ask questions:</span> You can also ask questions about the chapter without making changes</li>
                  <li><span className="font-medium">Smart editing:</span> The AI will only edit content when you explicitly ask for changes</li>
                  <li>The AI maintains your book's tone and style while making edits</li>
                  <li><span className="font-medium">Long Content Handling:</span> For very long chapters, the system automatically breaks content into manageable chunks, processes them in parallel, and seamlessly reassembles them</li>
                  <li>A progress bar appears when processing large content to keep you informed</li>
                </ul>
              </div>
              
              {/* Fetch Latest Chats Section */}
              <div>
                <h3 className="text-lg font-medium mb-2 flex items-center">
                  <RefreshCw className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
                  Fetch Latest Chats
                </h3>
                <p className="text-sm text-muted-foreground mb-2">
                  You can incorporate recent conversations into your book:
                </p>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  <li><span className="font-medium">Fetch Latest Chats:</span> Retrieves recent messages related to the chapter's category</li>
                  <li>The system formats these messages to match your book's style</li>
                  <li>New content is appended to the end of the current chapter</li>
                  <li>This is useful for adding new material from ongoing conversations</li>
                </ul>
              </div>
              
              {/* Audio Narration Section */}
              <div>
                <h3 className="text-lg font-medium mb-2 flex items-center">
                  <Volume2 className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
                  Audio Narration
                </h3>
                <p className="text-sm text-muted-foreground mb-2">
                  Listen to your chapters with text-to-speech narration:
                </p>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  <li>Click the speaker icon on any chapter to hear it read aloud</li>
                  <li>Click again to stop the narration</li>
                  <li>The system enhances the narration by adding proper pacing and emphasis</li>
                  <li>Audio is cached for faster playback if you listen again</li>
                </ul>
              </div>
              
              {/* Tips Section */}
              <div>
                <h3 className="text-lg font-medium mb-2 flex items-center">
                  <MessageSquare className="h-5 w-5 mr-2 text-[var(--mrwhite-primary-color)]" />
                  Tips for Best Results
                </h3>
                <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                  <li>Be specific when asking the AI to make edits</li>
                  <li>Review AI changes before saving</li>
                  <li>Generate new download files after making significant changes</li>
                  <li>Use "Fetch Latest Chats" periodically to incorporate new conversations</li>
                  <li>Save your changes frequently</li>
                </ul>
              </div>
            </div>
          </div>
          <DialogFooter className="pt-2 border-t">
            <Button onClick={() => setHowItWorksDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}