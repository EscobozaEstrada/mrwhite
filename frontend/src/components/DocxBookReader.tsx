'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
    BookOpen,
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
    Eye,
    EyeOff,
    Plus,
    FileText,
    Palette,
    ChevronLeft,
    ChevronRight,
    Settings,
    Download
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { motion, AnimatePresence } from 'motion/react';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';

// Types
interface BookChapter {
    id: number;
    title: string;
    content: string;
    html_content: string;
    paragraphs: any[];
    word_count: number;
    page_number: number;
}

interface BookData {
    id: number;
    title: string;
    description: string;
    content_type: string;
    total_pages: number;
    total_chapters: number;
    chapters: BookChapter[];
    metadata: any;
    processing_info: any;
    created_at: string;
    updated_at: string;
    book_copy_id?: number;
    user_book_copy_id?: number;
}

interface BookNote {
    id: number;
    book_copy_id: number;
    note_text: string;
    note_type: string;
    color: string;
    page_number: number;
    chapter_name?: string;
    selected_text?: string;
    tags: string[];
    created_at: string;
}

interface BookHighlight {
    id: number;
    book_copy_id: number;
    highlighted_text: string;
    color: string;
    highlight_type?: string;
    page_number: number;
    chapter_name?: string;
    tags?: string[];
    created_at: string;
}

interface ReadingProgress {
    id: number;
    current_page: number;
    total_pages: number;
    progress_percentage: number;
    reading_time_minutes: number;
    session_count: number;
    last_read_at: string;
}

interface DocxBookReaderProps {
    className?: string;
    bookId?: number;
}

const DocxBookReader: React.FC<DocxBookReaderProps> = ({ className = '', bookId }) => {
    const { user } = useAuth();

    // Debug logging
    console.log('🔍 DocxBookReader mounted, user:', user);

    // Core state
    const [bookData, setBookData] = useState<BookData | null>(null);
    const [progress, setProgress] = useState<ReadingProgress | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // UI state
    const [currentChapter, setCurrentChapter] = useState(1);
    const [fontSize, setFontSize] = useState(16);
    const [darkMode, setDarkMode] = useState(true);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [selectedText, setSelectedText] = useState('');

    // Notes and highlights
    const [notes, setNotes] = useState<BookNote[]>([]);
    const [highlights, setHighlights] = useState<BookHighlight[]>([]);
    const [showNoteModal, setShowNoteModal] = useState(false);
    const [showHighlightModal, setShowHighlightModal] = useState(false);
    const [newNote, setNewNote] = useState({ content: '', page_number: 1 });

    // Progress tracking
    const [currentSession, setCurrentSession] = useState<any>(null);
    const [readingStartTime, setReadingStartTime] = useState<Date>(new Date());

    // Refs
    const contentRef = useRef<HTMLDivElement>(null);
    const progressUpdateRef = useRef<NodeJS.Timeout>();

    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

    // Simplified initialization - just load the book content
    useEffect(() => {
        const initializeReader = async () => {
            try {
                setLoading(true);
                setError(null);

                console.log('🚀 Initializing DocxBookReader...');

                // Load book ID 9 directly
                const targetBookId = bookId || 9;
                const response = await axios.get(`${apiUrl}/api/book-content/book-content/${targetBookId}`);

                if (response.data.success) {
                    console.log('✅ Book loaded:', response.data.book.title);
                    setBookData(response.data.book);
                } else {
                    throw new Error('Failed to load book content');
                }

            } catch (err: any) {
                console.error('❌ Error loading book:', err);
                setError(err.response?.data?.message || 'Failed to load book');
            } finally {
                setLoading(false);
            }
        };

        initializeReader();
    }, [bookId]);

    // Basic progress update without authentication
    useEffect(() => {
        if (bookData && currentChapter) {
            const progressData = {
                current_page: currentChapter,
                total_pages: bookData.total_chapters,
                progress_percentage: Math.round((currentChapter / bookData.total_chapters) * 100)
            };
            console.log('📊 Progress:', progressData);
        }
    }, [bookData, currentChapter]);

    const initializeDefaultBook = async () => {
        try {
            const response = await axios.post(`${apiUrl}/api/book-content/initialize-default-book`, {}, {
                withCredentials: true
            });

            if (response.data.success) {
                console.log('✅ Default book initialized:', response.data.book_id);
                return response.data.book_id;
            }
        } catch (err: any) {
            // Book might already exist, which is fine
            if (err.response?.status !== 200) {
                console.log('Default book may already exist or initialization failed');
            }
        }
    };

    const loadBookContent = async () => {
        try {
            // For now, directly load book ID 9 (The Way of the Dog Anahata)
            const targetBookId = bookId || 9;
            console.log('Loading book with ID:', targetBookId);

            // Load specific book content
            const bookResponse = await axios.get(`${apiUrl}/api/book-content/book-content/${targetBookId}`, {
                withCredentials: true
            });

            if (bookResponse.data.success) {
                const bookContent = bookResponse.data.book;
                console.log('✅ Book content loaded:', bookContent.title);

                // Try to get or create user book copy
                const userBookResponse = await axios.get(`${apiUrl}/api/user-books/my-copy?title=${encodeURIComponent(bookContent.title)}&type=generated&reference_id=${targetBookId}`, {
                    withCredentials: true
                });

                if (userBookResponse.data.success) {
                    const enrichedBookData = {
                        ...bookContent,
                        user_book_copy_id: userBookResponse.data.book_copy.id,
                        book_copy_id: userBookResponse.data.book_copy.id
                    };
                    setBookData(enrichedBookData);
                    await loadAnnotations(userBookResponse.data.book_copy.id);
                    await startReadingSession(userBookResponse.data.book_copy.id);
                } else {
                    // Set book data without user book copy
                    setBookData(bookContent);
                    console.warn('Could not create user book copy, some features may not work');
                }
            } else {
                throw new Error('Failed to load book content');
            }
        } catch (err) {
            console.error('Error loading book content:', err);
            throw err;
        }
    };

    const loadAnnotations = async (bookId: number) => {
        try {
            const response = await axios.get(`${apiUrl}/api/user-books/annotations/${bookId}`, {
                withCredentials: true
            });

            if (response.data.success) {
                setNotes(response.data.notes || []);
                setHighlights(response.data.highlights || []);
            }
        } catch (err) {
            console.error('Error loading annotations:', err);
        }
    };

    const startReadingSession = async (bookId: number) => {
        try {
            const response = await axios.post(`${apiUrl}/api/user-books/sessions/start`, {
                book_copy_id: bookId
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                setCurrentSession(response.data.session);
                setReadingStartTime(new Date());
            }
        } catch (err) {
            console.error('Error starting reading session:', err);
        }
    };

    const updateProgress = useCallback(async () => {
        if (!bookData) return;

        const progressData = {
            current_page: currentChapter,
            total_pages: bookData.total_chapters,
            progress_percentage: Math.round((currentChapter / bookData.total_chapters) * 100),
            reading_time_minutes: Math.round((Date.now() - readingStartTime.getTime()) / 60000)
        };

        try {
            const response = await axios.put(`${apiUrl}/api/user-books/progress/${bookData.book_copy_id}`, progressData, {
                withCredentials: true
            });

            if (response.data.success) {
                setProgress(response.data.progress);
            }
        } catch (err) {
            console.error('Error updating progress:', err);
        }
    }, [bookData, currentChapter, readingStartTime]);

    const createNote = async () => {
        if (!bookData || !newNoteText.trim()) return;

        try {
            const response = await axios.post(`${apiUrl}/api/user-books/notes`, {
                book_copy_id: bookData.id,
                note_text: newNoteText,
                note_type: 'user_note',
                color: '#ffeb3b',
                page_number: currentChapter,
                selected_text: selectedText,
                tags: []
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                setNotes(prev => [...prev, response.data.note]);
                setNewNoteText('');
                setSelectedText('');
                setShowNoteDialog(false);
                toast.success('Note created successfully');
            }
        } catch (err) {
            console.error('Error creating note:', err);
            toast.error('Failed to create note');
        }
    };

    const createHighlight = async (text: string, color: string = '#ffeb3b') => {
        if (!bookData || !text.trim()) return;

        try {
            const response = await axios.post(`${apiUrl}/api/user-books/highlights`, {
                book_copy_id: bookData.id,
                highlighted_text: text,
                color: color,
                highlight_type: 'user_highlight',
                page_number: currentChapter,
                tags: []
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                setHighlights(prev => [...prev, response.data.highlight]);
                toast.success('Text highlighted successfully');
            }
        } catch (err) {
            console.error('Error creating highlight:', err);
            toast.error('Failed to create highlight');
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

    const handleTextSelection = () => {
        const selection = window.getSelection();
        if (selection && selection.toString().trim()) {
            const text = selection.toString().trim();
            setSelectedText(text);

            // Show context menu or create highlight directly
            const confirmHighlight = window.confirm(`Highlight: "${text.substring(0, 50)}${text.length > 50 ? '...' : ''}"?`);
            if (confirmHighlight) {
                createHighlight(text);
            }

            selection.removeAllRanges();
        }
    };

    const getCurrentChapter = () => {
        if (!bookData || !bookData.chapters) return null;
        return bookData.chapters.find(ch => ch.id === currentChapter) || bookData.chapters[0];
    };

    const navigateChapter = (direction: 'prev' | 'next') => {
        if (!bookData) return;

        if (direction === 'prev' && currentChapter > 1) {
            setCurrentChapter(currentChapter - 1);
        } else if (direction === 'next' && currentChapter < bookData.total_chapters) {
            setCurrentChapter(currentChapter + 1);
        }

        // Scroll to top of content
        if (contentRef.current) {
            contentRef.current.scrollTop = 0;
        }
    };

    // Render highlight overlays
    const renderHighlightedContent = (htmlContent: string) => {
        let content = htmlContent;

        // Apply highlights to content
        highlights.filter(h => h.page_number === currentChapter).forEach(highlight => {
            const highlightClass = `highlight-${highlight.id}`;
            const highlightStyle = `background-color: ${highlight.color}; cursor: pointer;`;
            content = content.replace(
                highlight.highlighted_text,
                `<span class="${highlightClass}" style="${highlightStyle}" data-highlight-id="${highlight.id}">${highlight.highlighted_text}</span>`
            );
        });

        return content;
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center space-y-4">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="text-lg">Loading your book...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center space-y-4">
                    <div className="text-red-500 text-6xl">⚠️</div>
                    <h2 className="text-2xl font-bold">Error Loading Book</h2>
                    <p className="text-gray-600">{error}</p>
                    <Button onClick={() => window.location.reload()} className="mt-4">
                        Try Again
                    </Button>
                </div>
            </div>
        );
    }

    const chapter = getCurrentChapter();

    return (
        <div className={`min-h-screen bg-gray-50 ${className}`}>
            {/* Header */}
            <motion.div
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                className="bg-white shadow-sm border-b"
            >
                <div className="max-w-7xl mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                            <BookOpen className="h-8 w-8 text-blue-600" />
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900">
                                    {bookData?.title || 'The Way of the Dog Anahata'}
                                </h1>
                                <p className="text-gray-600">
                                    Chapter {currentChapter} of {bookData?.total_chapters || 1}
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center space-x-2">
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setShowControls(!showControls)}
                            >
                                <Settings className="h-4 w-4 mr-1" />
                                {showControls ? 'Hide' : 'Show'} Controls
                            </Button>
                        </div>
                    </div>

                    {/* Progress Bar */}
                    {progress && (
                        <div className="mt-4">
                            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
                                <span>Reading Progress</span>
                                <span>{progress.progress_percentage}% complete</span>
                            </div>
                            <Progress value={progress.progress_percentage} className="h-2" />
                        </div>
                    )}
                </div>
            </motion.div>

            <div className="max-w-7xl mx-auto px-4 py-6">
                <div className="grid grid-cols-12 gap-6">
                    {/* Controls Panel */}
                    <AnimatePresence>
                        {showControls && (
                            <motion.div
                                initial={{ x: -300, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                exit={{ x: -300, opacity: 0 }}
                                className="col-span-12 lg:col-span-3"
                            >
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center space-x-2">
                                            <Target className="h-5 w-5" />
                                            <span>Reading Controls</span>
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        {/* Chapter Navigation */}
                                        <div>
                                            <label className="text-sm font-medium mb-2 block">Chapter Navigation</label>
                                            <div className="flex space-x-2">
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => navigateChapter('prev')}
                                                    disabled={currentChapter <= 1}
                                                >
                                                    <ChevronLeft className="h-4 w-4" />
                                                </Button>
                                                <Select
                                                    value={currentChapter.toString()}
                                                    onValueChange={(value) => setCurrentChapter(parseInt(value))}
                                                >
                                                    <SelectTrigger className="flex-1">
                                                        <SelectValue />
                                                    </SelectTrigger>
                                                    <SelectContent>
                                                        {bookData?.chapters.map((ch) => (
                                                            <SelectItem key={ch.id} value={ch.id.toString()}>
                                                                {ch.title.substring(0, 30)}...
                                                            </SelectItem>
                                                        ))}
                                                    </SelectContent>
                                                </Select>
                                                <Button
                                                    variant="outline"
                                                    size="sm"
                                                    onClick={() => navigateChapter('next')}
                                                    disabled={currentChapter >= (bookData?.total_chapters || 1)}
                                                >
                                                    <ChevronRight className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>

                                        {/* Annotations Toggle */}
                                        <div>
                                            <label className="text-sm font-medium mb-2 block">Annotations</label>
                                            <Button
                                                variant={showAnnotations ? "default" : "outline"}
                                                size="sm"
                                                onClick={() => setShowAnnotations(!showAnnotations)}
                                                className="w-full"
                                            >
                                                {showAnnotations ? <Eye className="h-4 w-4 mr-2" /> : <EyeOff className="h-4 w-4 mr-2" />}
                                                {showAnnotations ? 'Hide' : 'Show'} Annotations
                                            </Button>
                                        </div>

                                        {/* Quick Note */}
                                        <div>
                                            <label className="text-sm font-medium mb-2 block">Quick Note</label>
                                            <Textarea
                                                value={newNoteText}
                                                onChange={(e) => setNewNoteText(e.target.value)}
                                                placeholder="Add a note about this chapter..."
                                                className="mb-2"
                                                rows={3}
                                            />
                                            <Button
                                                onClick={createNote}
                                                disabled={!newNoteText.trim()}
                                                size="sm"
                                                className="w-full"
                                            >
                                                <StickyNote className="h-4 w-4 mr-2" />
                                                Add Note
                                            </Button>
                                        </div>

                                        {/* Reading Stats */}
                                        {currentSession && (
                                            <div>
                                                <label className="text-sm font-medium mb-2 block">Current Session</label>
                                                <div className="text-sm text-gray-600 space-y-1">
                                                    <div className="flex items-center">
                                                        <Clock className="h-4 w-4 mr-2" />
                                                        Started: {new Date(currentSession.start_time).toLocaleTimeString()}
                                                    </div>
                                                    <div className="flex items-center">
                                                        <TrendingUp className="h-4 w-4 mr-2" />
                                                        Progress: {Math.round((currentChapter / (bookData?.total_chapters || 1)) * 100)}%
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>

                                {/* Annotations List */}
                                {showAnnotations && (notes.length > 0 || highlights.length > 0) && (
                                    <Card className="mt-4">
                                        <CardHeader>
                                            <CardTitle className="flex items-center space-x-2">
                                                <FileText className="h-5 w-5" />
                                                <span>Your Annotations</span>
                                            </CardTitle>
                                        </CardHeader>
                                        <CardContent>
                                            <ScrollArea className="h-64">
                                                {notes.filter(note => note.page_number === currentChapter).map((note) => (
                                                    <div key={note.id} className="mb-3 p-2 bg-yellow-50 rounded border">
                                                        <div className="flex items-start justify-between">
                                                            <div className="flex-1">
                                                                <p className="text-sm text-gray-800">{note.note_text}</p>
                                                                <p className="text-xs text-gray-500 mt-1">
                                                                    {new Date(note.created_at).toLocaleDateString()}
                                                                </p>
                                                            </div>
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => deleteNote(note.id)}
                                                            >
                                                                <Trash2 className="h-3 w-3" />
                                                            </Button>
                                                        </div>
                                                    </div>
                                                ))}
                                            </ScrollArea>
                                        </CardContent>
                                    </Card>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Main Content */}
                    <div className={showControls ? "col-span-12 lg:col-span-9" : "col-span-12"}>
                        <Card className="min-h-screen">
                            <CardContent className="p-0">
                                <ScrollArea className="h-screen">
                                    <div
                                        ref={contentRef}
                                        className="p-8 max-w-4xl mx-auto"
                                        onMouseUp={handleTextSelection}
                                    >
                                        {chapter ? (
                                            <div
                                                className="prose prose-lg max-w-none"
                                                style={{
                                                    fontSize: '18px',
                                                    lineHeight: '1.8',
                                                    color: '#374151'
                                                }}
                                                dangerouslySetInnerHTML={{
                                                    __html: showAnnotations
                                                        ? renderHighlightedContent(chapter.html_content)
                                                        : chapter.html_content
                                                }}
                                            />
                                        ) : (
                                            <div className="text-center py-12">
                                                <p className="text-gray-500">No content available for this chapter.</p>
                                            </div>
                                        )}
                                    </div>
                                </ScrollArea>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DocxBookReader; 