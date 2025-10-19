'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
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
    Bot,
    StickyNote,
    Highlighter,
    Bookmark,
    Play,
    Pause,
    Clock,
    Target,
    TrendingUp,
    Save,
    Trash2,
    Search,
    Filter,
    Download,
    Settings,
    Eye,
    EyeOff,
    Plus,
    FileText,
    Palette,
    ChevronLeft,
    ChevronRight,
    ZoomIn,
    ZoomOut
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { motion, AnimatePresence } from 'motion/react';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';
import HighlightOverlay from './HighlightOverlay';
import SemanticSearchInterface from './SemanticSearchInterface';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Configure PDF.js worker - Use CDN to ensure version matching
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface BookCopy {
    id: number;
    user_id: number;
    book_title: string;
    book_type: string;
    original_pdf_url: string;
    font_size: string;
    theme: string;
    reading_speed: number;
    created_at: string;
    last_accessed_at: string;
    total_notes: number;
    total_highlights: number;
}

interface ReadingProgress {
    id: number;
    user_book_copy_id: number;
    current_page: number;
    total_pages: number;
    progress_percentage: number;
    reading_time_minutes: number;
    session_count: number;
    pdf_scroll_position: number;
    pdf_zoom_level: number;
    pdf_page_mode: string;
    current_chapter: string;
    last_read_at: string;
    reading_started_at: string;
}

interface BookNote {
    id: number;
    book_copy_id: number;
    note_text: string;
    note_type: string;
    color: string;
    page_number: number;
    chapter_name?: string;
    pdf_coordinates?: {
        x: number;
        y: number;
    };
    selected_text?: string;
    tags: string[];
    created_at: string;
    updated_at?: string;
}

interface BookHighlight {
    id: number;
    book_copy_id: number;
    highlighted_text: string;
    color: string;
    highlight_type?: string;
    page_number: number;
    chapter_name?: string;
    pdf_coordinates?: {
        x: number;
        y: number;
        width: number;
        height: number;
    };
    tags?: string[];
    created_at: string;
}

interface ChatMessage {
    type: 'user' | 'ai';
    content: string;
    timestamp: string;
}

interface ReadingSession {
    id: number;
    user_book_copy_id: number;
    start_time: string;
    end_time?: string;
    duration_minutes?: number;
    start_page?: number;
    end_page?: number;
}

interface EnhancedBookReaderProps {
    className?: string;
    bookTitle?: string;
    bookType?: string;
    bookReferenceId?: number;
}

const EnhancedBookReader: React.FC<EnhancedBookReaderProps> = ({
    className = '',
    bookTitle,
    bookType = 'public',
    bookReferenceId
}) => {
    const { user } = useAuth();
    const iframeRef = useRef<HTMLIFrameElement>(null);
    const progressUpdateRef = useRef<NodeJS.Timeout>();

    // Core state
    const [bookCopy, setBookCopy] = useState<BookCopy | null>(null);
    const [progress, setProgress] = useState<ReadingProgress | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // PDF state
    const [numPages, setNumPages] = useState<number>(0);
    const [pageNumber, setPageNumber] = useState<number>(1);
    const [scale, setScale] = useState<number>(1.2);
    const [selectedText, setSelectedText] = useState<string>('');

    // UI state
    const [activeTab, setActiveTab] = useState<'read' | 'notes' | 'chat' | 'progress' | 'settings'>('read');
    const [showControls, setShowControls] = useState(true);
    const [isReading, setIsReading] = useState(false);

    // Notes and highlights
    const [notes, setNotes] = useState<BookNote[]>([]);
    const [highlights, setHighlights] = useState<BookHighlight[]>([]);
    const [newNoteText, setNewNoteText] = useState('');
    const [newNoteColor, setNewNoteColor] = useState('yellow');
    const [noteFilter, setNoteFilter] = useState('all');
    const [highlightColor, setHighlightColor] = useState('yellow');

    // Chat state
    const [chatQuery, setChatQuery] = useState('');
    const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
    const [chatLoading, setChatLoading] = useState(false);

    // Reading session
    const [currentSession, setCurrentSession] = useState<ReadingSession | null>(null);
    const [sessionStats, setSessionStats] = useState({
        notes_created: 0,
        highlights_created: 0,
        pdf_interactions: 0
    });

    // Settings
    const [settings, setSettings] = useState({
        auto_save_progress: true,
        progress_update_interval: 30, // seconds
        show_reading_analytics: true,
        enable_text_selection: true
    });

    // Enhanced UI state
    const [showAnnotations, setShowAnnotations] = useState(true);
    const [showSemanticSearch, setShowSemanticSearch] = useState(false);

    // Using FASTAPI_BASE_URL for FastAPI service
    const apiUrl = process.env.NEXT_PUBLIC_FASTAPI_BASE_URL;

    // PDF event handlers
    const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
        setNumPages(numPages);
        console.log('📖 PDF loaded successfully:', numPages, 'pages');
    };

    const onDocumentLoadError = (error: Error) => {
        console.error('❌ Error loading PDF:', error);
        setError('Failed to load PDF document');
    };

    const onTextSelect = () => {
        const selection = window.getSelection();
        if (selection && selection.toString().trim()) {
            setSelectedText(selection.toString().trim());
            console.log('📝 Text selected:', selection.toString().trim());
        }
    };

    const createHighlightFromSelection = async () => {
        if (!selectedText || !bookCopy) return;

        try {
            const response = await axios.post(`${apiUrl}/api/user-books/highlights`, {
                book_copy_id: bookCopy.id,
                page_number: pageNumber,
                highlighted_text: selectedText,
                color: highlightColor,
                pdf_coordinates: { page: pageNumber, text: selectedText }
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                setHighlights(prev => [...prev, response.data.highlight]);
                setSessionStats(prev => ({ ...prev, highlights_created: prev.highlights_created + 1 }));
                toast.success('Highlight created!');
                setSelectedText('');
            }
        } catch (err) {
            console.error('Error creating highlight:', err);
            toast.error('Failed to create highlight');
        }
    };

    // Navigate to specific page
    const navigateToPage = (page: number) => {
        setPageNumber(page);
        updateProgressFromPDF();
    };

    // Handle highlight and note interactions
    const handleHighlightClick = (highlight: any) => {
        console.log('📍 Highlight clicked:', highlight);
    };

    const handleNoteClick = (note: any) => {
        console.log('📍 Note clicked:', note);
    };

    const deleteHighlight = async (highlightId: number) => {
        try {
            const response = await axios.delete(`${apiUrl}/api/user-books/highlights/${highlightId}`, {
                withCredentials: true
            });

            if (response.data.success) {
                setHighlights(prev => prev.filter(h => h.id !== highlightId));
                toast.success('Highlight deleted');
            }
        } catch (err) {
            console.error('Error deleting highlight:', err);
            toast.error('Failed to delete highlight');
        }
    };

    const deleteNote = async (noteId: number) => {
        try {
            const response = await axios.delete(`${apiUrl}/api/user-books/notes/${noteId}`, {
                withCredentials: true
            });

            if (response.data.success) {
                setNotes(prev => prev.filter(n => n.id !== noteId));
                toast.success('Note deleted');
            }
        } catch (err) {
            console.error('Error deleting note:', err);
            toast.error('Failed to delete note');
        }
    };

    const updateProgressFromPDF = useCallback(async () => {
        if (!bookCopy || !iframeRef.current) return;

        try {
            // Get current scroll position and page from PDF viewer
            // This would require communication with the PDF iframe
            const progressData = {
                current_page: progress?.current_page || 1,
                pdf_scroll_position: 0.5, // Placeholder - would get from PDF
                reading_time_minutes: 1 // Placeholder - would calculate actual time
            };

            const response = await axios.put(`${apiUrl}/api/user-books/progress/${bookCopy.id}`, progressData, {
                withCredentials: true
            });

            if (response.data.success) {
                setProgress(response.data.progress);
            }
        } catch (err) {
            console.error('Error updating progress:', err);
        }
    }, [bookCopy, progress?.current_page, progress?.current_chapter, apiUrl]);

    useEffect(() => {
        if (user) {
            initializeBookReader();
        }
    }, [user, bookTitle, bookType, bookReferenceId]);

    useEffect(() => {
        // Set up auto-save progress if enabled
        if (settings.auto_save_progress && bookCopy && isReading) {
            progressUpdateRef.current = setInterval(() => {
                updateProgressFromPDF();
            }, settings.progress_update_interval * 1000);
        }

        return () => {
            if (progressUpdateRef.current) {
                clearInterval(progressUpdateRef.current);
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [settings.auto_save_progress, settings.progress_update_interval, bookCopy, isReading]);

    const initializeBookReader = async () => {
        try {
            setLoading(true);
            setError(null);

            // Get or create user book copy
            const params = new URLSearchParams();
            if (bookTitle) params.append('title', bookTitle);
            if (bookType) params.append('type', bookType);
            if (bookReferenceId) params.append('reference_id', bookReferenceId.toString());

            const response = await axios.get(`${apiUrl}/api/user-books/my-copy?${params.toString()}`, {
                withCredentials: true
            });

            if (response.data.success) {
                setBookCopy(response.data.book_copy);
                await loadBookData(response.data.book_copy.id);
            } else {
                setError(response.data.message || 'Failed to get book copy');
            }
        } catch (err: any) {
            console.error('Error initializing book reader:', err);
            setError(err.response?.data?.message || 'Error loading book');
        } finally {
            setLoading(false);
        }
    };

    const loadBookData = async (bookCopyId: number) => {
        try {
            // Load annotations (notes and highlights)
            const annotationsResponse = await axios.get(`${apiUrl}/api/user-books/annotations/${bookCopyId}`, {
                withCredentials: true
            });

            if (annotationsResponse.data.success) {
                setNotes(annotationsResponse.data.notes);
                setHighlights(annotationsResponse.data.highlights);
            }

            // Additional data loading can be added here
        } catch (err) {
            console.error('Error loading book data:', err);
        }
    };

    const startReadingSession = async () => {
        if (!bookCopy || currentSession) return;

        try {
            const response = await axios.post(`${apiUrl}/api/user-books/sessions/start`, {
                book_copy_id: bookCopy.id
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                setCurrentSession(response.data.session);
                setIsReading(true);
                setSessionStats({ notes_created: 0, highlights_created: 0, pdf_interactions: 0 });
                toast.success('Reading session started');
            }
        } catch (err) {
            console.error('Error starting reading session:', err);
            toast.error('Failed to start reading session');
        }
    };

    const endReadingSession = async () => {
        if (!currentSession) return;

        try {
            const endData = {
                end_page: progress?.current_page,
                notes_created: sessionStats.notes_created,
                highlights_created: sessionStats.highlights_created,
                pdf_interactions: sessionStats.pdf_interactions
            };

            const response = await axios.put(`${apiUrl}/api/user-books/sessions/${currentSession.id}/end`, endData, {
                withCredentials: true
            });

            if (response.data.success) {
                setCurrentSession(null);
                setIsReading(false);
                toast.success(`Reading session ended: ${response.data.session.duration_minutes} minutes`);
            }
        } catch (err) {
            console.error('Error ending reading session:', err);
            toast.error('Failed to end reading session');
        }
    };



    const createNote = async () => {
        if (!bookCopy || !newNoteText.trim()) return;

        try {
            const noteData = {
                book_copy_id: bookCopy.id,
                note_text: newNoteText,
                color: newNoteColor,
                page_number: progress?.current_page,
                chapter_name: progress?.current_chapter
            };

            const response = await axios.post(`${apiUrl}/api/user-books/notes`, noteData, {
                withCredentials: true
            });

            if (response.data.success) {
                setNotes([response.data.note, ...notes]);
                setNewNoteText('');
                setSessionStats(prev => ({ ...prev, notes_created: prev.notes_created + 1 }));
                toast.success('Note created successfully');
            }
        } catch (err) {
            console.error('Error creating note:', err);
            toast.error('Failed to create note');
        }
    };

    const createHighlight = async (selectedText: string, coordinates: any) => {
        if (!bookCopy) return;

        try {
            const highlightData = {
                book_copy_id: bookCopy.id,
                highlighted_text: selectedText,
                color: highlightColor,
                page_number: progress?.current_page,
                chapter_name: progress?.current_chapter,
                pdf_coordinates: coordinates
            };

            const response = await axios.post(`${apiUrl}/api/user-books/highlights`, highlightData, {
                withCredentials: true
            });

            if (response.data.success) {
                setHighlights([response.data.highlight, ...highlights]);
                setSessionStats(prev => ({ ...prev, highlights_created: prev.highlights_created + 1 }));
                toast.success('Text highlighted');
            }
        } catch (err) {
            console.error('Error creating highlight:', err);
            toast.error('Failed to create highlight');
        }
    };

    const handleChatSubmit = async () => {
        if (!chatQuery.trim() || chatLoading || !bookCopy) return;

        const userMessage: ChatMessage = {
            type: 'user',
            content: chatQuery,
            timestamp: new Date().toISOString()
        };

        setChatHistory(prev => [...prev, userMessage]);
        setChatLoading(true);

        try {
            const response = await axios.post(`${apiUrl}/api/book/chat`, {
                query: chatQuery,
                conversation_history: chatHistory
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                const aiMessage: ChatMessage = {
                    type: 'ai',
                    content: response.data.response,
                    timestamp: new Date().toISOString()
                };
                setChatHistory(prev => [...prev, aiMessage]);
            }
        } catch (err) {
            console.error('Error in chat:', err);
            toast.error('Chat failed');
        } finally {
            setChatLoading(false);
            setChatQuery('');
        }
    };

    const filteredNotes = notes.filter(note => {
        if (noteFilter === 'all') return true;
        if (noteFilter === 'bookmarks') return note.note_type === 'bookmark';
        if (noteFilter === 'notes') return note.note_type === 'note';
        return note.color === noteFilter;
    });

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <Loader2 className="h-8 w-8 animate-spin" />
                <span className="ml-2">Loading your personal book...</span>
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
            {/* Enhanced Header */}
            <div className={`bg-background border-b transition-all duration-300 ${showControls ? 'h-auto' : 'h-16'} overflow-hidden`}>
                <div className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-3">
                        <BookOpen className="h-6 w-6" />
                        <div>
                            <h1 className="text-lg font-semibold">{bookCopy?.book_title}</h1>
                            {showControls && progress && (
                                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                    <span>Page {progress.current_page} of {progress.total_pages}</span>
                                    <Progress value={progress.progress_percentage} className="w-32" />
                                    <span>{Math.round(progress.progress_percentage)}%</span>
                                </div>
                            )}
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Badge variant="secondary">
                            {bookCopy?.book_type === 'public' ? 'Public' : 'Personal'}
                        </Badge>
                        <Badge variant="outline">
                            {bookCopy?.total_notes} notes
                        </Badge>
                        <Badge variant="outline">
                            {bookCopy?.total_highlights} highlights
                        </Badge>
                        {isReading ? (
                            <Button onClick={endReadingSession} variant="destructive" size="sm">
                                <Pause className="h-4 w-4 mr-1" />
                                End Session
                            </Button>
                        ) : (
                            <Button onClick={startReadingSession} size="sm">
                                <Play className="h-4 w-4 mr-1" />
                                Start Reading
                            </Button>
                        )}
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

            {/* Main Content Area */}
            <div className="flex-1 flex">
                {/* PDF Viewer */}
                <div className="flex-1 flex flex-col relative">
                    {/* PDF Controls */}
                    <div className="bg-background border-b p-2 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Button
                                onClick={() => setPageNumber(Math.max(1, pageNumber - 1))}
                                disabled={pageNumber <= 1}
                                variant="outline"
                                size="sm"
                            >
                                <ChevronLeft className="h-4 w-4" />
                            </Button>
                            <span className="text-sm font-medium">
                                Page {pageNumber} of {numPages}
                            </span>
                            <Button
                                onClick={() => setPageNumber(Math.min(numPages, pageNumber + 1))}
                                disabled={pageNumber >= numPages}
                                variant="outline"
                                size="sm"
                            >
                                <ChevronRight className="h-4 w-4" />
                            </Button>
                        </div>

                        <div className="flex items-center gap-2">
                            <Button
                                onClick={() => setScale(Math.max(0.5, scale - 0.1))}
                                variant="outline"
                                size="sm"
                            >
                                <ZoomOut className="h-4 w-4" />
                            </Button>
                            <span className="text-xs px-2">{Math.round(scale * 100)}%</span>
                            <Button
                                onClick={() => setScale(Math.min(3, scale + 0.1))}
                                variant="outline"
                                size="sm"
                            >
                                <ZoomIn className="h-4 w-4" />
                            </Button>
                        </div>

                        <div className="flex items-center gap-2">
                            <Button
                                onClick={() => setShowSemanticSearch(true)}
                                variant="outline"
                                size="sm"
                            >
                                <Search className="h-4 w-4 mr-1" />
                                Search
                            </Button>
                        </div>

                        {selectedText && (
                            <div className="flex items-center gap-2">
                                <Select value={highlightColor} onValueChange={setHighlightColor}>
                                    <SelectTrigger className="w-32 h-8">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="yellow">Yellow</SelectItem>
                                        <SelectItem value="blue">Blue</SelectItem>
                                        <SelectItem value="green">Green</SelectItem>
                                        <SelectItem value="pink">Pink</SelectItem>
                                    </SelectContent>
                                </Select>
                                <Button
                                    onClick={createHighlightFromSelection}
                                    size="sm"
                                    variant="outline"
                                >
                                    <Highlighter className="h-3 w-3 mr-1" />
                                    Highlight
                                </Button>
                            </div>
                        )}
                    </div>

                    {/* PDF Content */}
                    <div className="flex-1 overflow-auto bg-gray-100 flex justify-center p-4">
                        {bookCopy?.original_pdf_url ? (
                            <Document
                                file={bookCopy.original_pdf_url}
                                onLoadSuccess={onDocumentLoadSuccess}
                                onLoadError={onDocumentLoadError}
                                loading={
                                    <div className="flex items-center justify-center p-8">
                                        <Loader2 className="h-8 w-8 animate-spin mr-2" />
                                        <span>Loading PDF...</span>
                                    </div>
                                }
                                error={
                                    <div className="flex items-center justify-center p-8 text-red-600">
                                        <p>Failed to load PDF document</p>
                                    </div>
                                }
                            >
                                <Page
                                    pageNumber={pageNumber}
                                    scale={scale}
                                    renderTextLayer={true}
                                    renderAnnotationLayer={true}
                                    className="shadow-lg"
                                    onRenderSuccess={() => {
                                        // Set up text selection listener
                                        setTimeout(() => {
                                            document.addEventListener('mouseup', onTextSelect);
                                        }, 100);
                                    }}
                                />

                                {/* Highlight Overlay */}
                                <HighlightOverlay
                                    currentPage={pageNumber}
                                    highlights={highlights}
                                    notes={notes}
                                    pdfScale={scale}
                                    onHighlightClick={handleHighlightClick}
                                    onNoteClick={handleNoteClick}
                                    onDeleteHighlight={deleteHighlight}
                                    onDeleteNote={deleteNote}
                                    showOverlay={showAnnotations}
                                    onToggleOverlay={setShowAnnotations}
                                />
                            </Document>
                        ) : (
                            <div className="flex items-center justify-center h-full text-muted-foreground">
                                <p>PDF viewer not available</p>
                            </div>
                        )}
                    </div>
                </div>

                {/* Side Panel with Enhanced Features */}
                {showControls && (
                    <motion.div
                        initial={{ width: 0, opacity: 0 }}
                        animate={{ width: 400, opacity: 1 }}
                        exit={{ width: 0, opacity: 0 }}
                        className="w-96 bg-card border-l"
                    >
                        <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)} className="h-full flex flex-col">
                            <TabsList className="grid w-full grid-cols-5">
                                <TabsTrigger value="read" className="flex items-center gap-1 text-xs">
                                    <BookOpen className="h-3 w-3" />
                                    Read
                                </TabsTrigger>
                                <TabsTrigger value="notes" className="flex items-center gap-1 text-xs">
                                    <StickyNote className="h-3 w-3" />
                                    Notes
                                </TabsTrigger>
                                <TabsTrigger value="chat" className="flex items-center gap-1 text-xs">
                                    <MessageCircle className="h-3 w-3" />
                                    Chat
                                </TabsTrigger>
                                <TabsTrigger value="progress" className="flex items-center gap-1 text-xs">
                                    <TrendingUp className="h-3 w-3" />
                                    Stats
                                </TabsTrigger>
                                <TabsTrigger value="settings" className="flex items-center gap-1 text-xs">
                                    <Settings className="h-3 w-3" />
                                    Settings
                                </TabsTrigger>
                            </TabsList>

                            <div className="flex-1 overflow-hidden">
                                {/* Reading Tab */}
                                <TabsContent value="read" className="h-full p-4 space-y-4">
                                    <div>
                                        <h3 className="font-semibold mb-2">Quick Actions</h3>
                                        <div className="space-y-2">
                                            <Button
                                                onClick={() => window.open(bookCopy?.original_pdf_url, '_blank')}
                                                variant="outline"
                                                className="w-full justify-start"
                                            >
                                                <ExternalLink className="h-4 w-4 mr-2" />
                                                Open in New Tab
                                            </Button>
                                            <Button
                                                onClick={() => {/* TODO: Implement download */ }}
                                                variant="outline"
                                                className="w-full justify-start"
                                            >
                                                <Download className="h-4 w-4 mr-2" />
                                                Download PDF
                                            </Button>
                                        </div>
                                    </div>

                                    {progress && (
                                        <div>
                                            <h3 className="font-semibold mb-2">Reading Progress</h3>
                                            <div className="space-y-2">
                                                <div className="flex justify-between text-sm">
                                                    <span>Progress</span>
                                                    <span>{Math.round(progress.progress_percentage)}%</span>
                                                </div>
                                                <Progress value={progress.progress_percentage} />
                                                <div className="text-xs text-muted-foreground">
                                                    <p>Page {progress.current_page} of {progress.total_pages}</p>
                                                    <p>Reading time: {progress.reading_time_minutes} minutes</p>
                                                    <p>Sessions: {progress.session_count}</p>
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {isReading && currentSession && (
                                        <div>
                                            <h3 className="font-semibold mb-2">Current Session</h3>
                                            <div className="bg-muted p-3 rounded-lg text-sm space-y-1">
                                                <div className="flex items-center gap-2">
                                                    <Clock className="h-3 w-3" />
                                                    <span>Started: {new Date(currentSession.start_time).toLocaleTimeString()}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span>Notes created:</span>
                                                    <span>{sessionStats.notes_created}</span>
                                                </div>
                                                <div className="flex justify-between">
                                                    <span>Highlights:</span>
                                                    <span>{sessionStats.highlights_created}</span>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </TabsContent>

                                {/* Notes Tab */}
                                <TabsContent value="notes" className="h-full p-4 space-y-4">
                                    <div>
                                        <h3 className="font-semibold mb-2">Create Note</h3>
                                        <div className="space-y-2">
                                            <Textarea
                                                placeholder="Write your note..."
                                                value={newNoteText}
                                                onChange={(e) => setNewNoteText(e.target.value)}
                                                className="min-h-[80px]"
                                            />
                                            <div className="flex gap-2">
                                                <Select value={newNoteColor} onValueChange={setNewNoteColor}>
                                                    <SelectTrigger className="w-24">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        <SelectItem value="yellow">🟡 Yellow</SelectItem>
                                                        <SelectItem value="blue">🔵 Blue</SelectItem>
                                                        <SelectItem value="green">🟢 Green</SelectItem>
                                                        <SelectItem value="red">🔴 Red</SelectItem>
                                                        <SelectItem value="purple">🟣 Purple</SelectItem>
                                                    </SelectContent>
                                                </Select>
                                                <Button onClick={createNote} disabled={!newNoteText.trim()} className="flex-1">
                                                    <Plus className="h-4 w-4 mr-1" />
                                                    Add Note
                                                </Button>
                                            </div>
                                        </div>
                                    </div>

                                    <div>
                                        <div className="flex items-center justify-between mb-2">
                                            <h3 className="font-semibold">My Notes ({filteredNotes.length})</h3>
                                            <Select value={noteFilter} onValueChange={setNoteFilter}>
                                                <SelectTrigger className="w-20">
                                                    <Filter className="h-3 w-3" />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="all">All</SelectItem>
                                                    <SelectItem value="notes">Notes</SelectItem>
                                                    <SelectItem value="bookmarks">Bookmarks</SelectItem>
                                                    <SelectItem value="yellow">Yellow</SelectItem>
                                                    <SelectItem value="blue">Blue</SelectItem>
                                                    <SelectItem value="green">Green</SelectItem>
                                                    <SelectItem value="red">Red</SelectItem>
                                                    <SelectItem value="purple">Purple</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </div>

                                        <ScrollArea className="h-64">
                                            <div className="space-y-2">
                                                {filteredNotes.map((note) => (
                                                    <motion.div
                                                        key={note.id}
                                                        initial={{ opacity: 0, y: 10 }}
                                                        animate={{ opacity: 1, y: 0 }}
                                                        className="p-3 border rounded-lg bg-card"
                                                    >
                                                        <div className="flex items-start justify-between mb-2">
                                                            <div className="flex items-center gap-2">
                                                                <div
                                                                    className="w-3 h-3 rounded-full"
                                                                    style={{ backgroundColor: note.color === 'yellow' ? '#fbbf24' : note.color }}
                                                                />
                                                                <span className="text-xs text-muted-foreground">
                                                                    Page {note.page_number}
                                                                </span>
                                                            </div>
                                                            <Button
                                                                onClick={() => deleteNote(note.id)}
                                                                variant="ghost"
                                                                size="sm"
                                                                className="h-6 w-6 p-0"
                                                            >
                                                                <Trash2 className="h-3 w-3" />
                                                            </Button>
                                                        </div>
                                                        <p className="text-sm">{note.note_text}</p>
                                                        <div className="text-xs text-muted-foreground mt-2">
                                                            {new Date(note.created_at).toLocaleDateString()}
                                                        </div>
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </ScrollArea>
                                    </div>
                                </TabsContent>

                                {/* Chat Tab */}
                                <TabsContent value="chat" className="h-full p-4 space-y-4">
                                    <ScrollArea className="h-64 border rounded-lg p-3">
                                        {chatHistory.length === 0 ? (
                                            <div className="text-center text-muted-foreground py-8">
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
                                            onChange={(e) => setChatQuery(e.target.value)}
                                            className="min-h-[40px] resize-none"
                                            rows={2}
                                        />
                                        <Button
                                            onClick={handleChatSubmit}
                                            disabled={!chatQuery.trim() || chatLoading}
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

                                {/* Progress Tab */}
                                <TabsContent value="progress" className="h-full p-4 space-y-4">
                                    <div>
                                        <h3 className="font-semibold mb-2">Reading Analytics</h3>
                                        {progress && (
                                            <div className="space-y-3">
                                                <div className="grid grid-cols-2 gap-2 text-sm">
                                                    <div className="bg-muted p-2 rounded">
                                                        <div className="font-medium">{progress.reading_time_minutes}</div>
                                                        <div className="text-muted-foreground">Total Minutes</div>
                                                    </div>
                                                    <div className="bg-muted p-2 rounded">
                                                        <div className="font-medium">{progress.session_count}</div>
                                                        <div className="text-muted-foreground">Sessions</div>
                                                    </div>
                                                    <div className="bg-muted p-2 rounded">
                                                        <div className="font-medium">{notes.length}</div>
                                                        <div className="text-muted-foreground">Notes</div>
                                                    </div>
                                                    <div className="bg-muted p-2 rounded">
                                                        <div className="font-medium">{highlights.length}</div>
                                                        <div className="text-muted-foreground">Highlights</div>
                                                    </div>
                                                </div>

                                                <div>
                                                    <div className="text-sm font-medium mb-2">Reading Progress</div>
                                                    <Progress value={progress.progress_percentage} className="mb-1" />
                                                    <div className="text-xs text-muted-foreground">
                                                        {Math.round(progress.progress_percentage)}% complete
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </TabsContent>

                                {/* Settings Tab */}
                                <TabsContent value="settings" className="h-full p-4 space-y-4">
                                    <div>
                                        <h3 className="font-semibold mb-2">Reading Settings</h3>
                                        <div className="space-y-3">
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm">Auto-save progress</span>
                                                <Switch
                                                    checked={settings.auto_save_progress}
                                                    onCheckedChange={(checked) =>
                                                        setSettings(prev => ({ ...prev, auto_save_progress: checked }))
                                                    }
                                                />
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm">Show analytics</span>
                                                <Switch
                                                    checked={settings.show_reading_analytics}
                                                    onCheckedChange={(checked) =>
                                                        setSettings(prev => ({ ...prev, show_reading_analytics: checked }))
                                                    }
                                                />
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm">Enable text selection</span>
                                                <Switch
                                                    checked={settings.enable_text_selection}
                                                    onCheckedChange={(checked) =>
                                                        setSettings(prev => ({ ...prev, enable_text_selection: checked }))
                                                    }
                                                />
                                            </div>
                                        </div>
                                    </div>

                                    <div>
                                        <h3 className="font-semibold mb-2">Highlight Color</h3>
                                        <Select value={highlightColor} onValueChange={setHighlightColor}>
                                            <SelectTrigger>
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="yellow">🟡 Yellow</SelectItem>
                                                <SelectItem value="blue">🔵 Blue</SelectItem>
                                                <SelectItem value="green">🟢 Green</SelectItem>
                                                <SelectItem value="red">🔴 Red</SelectItem>
                                                <SelectItem value="purple">🟣 Purple</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                </TabsContent>
                            </div>
                        </Tabs>
                    </motion.div>
                )}
            </div>

            {/* Semantic Search Interface */}
            <SemanticSearchInterface
                isOpen={showSemanticSearch}
                onClose={() => setShowSemanticSearch(false)}
                onNavigateToPage={navigateToPage}
                currentBookCopyId={bookCopy?.id}
            />
        </div>
    );
};

export default EnhancedBookReader; 