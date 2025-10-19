'use client';

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, BookOpen, MessageSquare, Highlighter, Bookmark, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';

// Configure PDF.js worker - Using recommended CDN approach for react-pdf 10.x
if (typeof window !== 'undefined') {
    pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
}

interface UserBookCopy {
    id: number;
    user_id: number;
    book_title: string;
    original_pdf_url: string;
    font_size: string;
    theme: string;
    total_notes: number;
    total_highlights: number;
}

interface ReadingProgress {
    id: number;
    current_page: number;
    total_pages: number;
    progress_percentage: number;
    pdf_scroll_position: number;
    pdf_zoom_level: number;
    reading_time_minutes: number;
    last_read_at: string;
}

interface BookNote {
    id: number;
    note_text: string;
    note_type: string;
    color: string;
    page_number: number;
    pdf_coordinates: { x: number; y: number; page: number };
    selected_text?: string;
    text_bounds?: DOMRect;
    created_at: string;
}

interface BookHighlight {
    id: number;
    highlighted_text: string;
    color: string;
    page_number: number;
    pdf_coordinates: { startX: number; startY: number; endX: number; endY: number; page: number };
    text_bounds?: DOMRect;
    created_at: string;
}

interface TextSelection {
    text: string;
    bounds: DOMRect;
    range: Range;
    page: number;
}

const HIGHLIGHT_COLORS = {
    yellow: '#FFD93D',
    blue: '#6FCFFF',
    green: '#6BCF7F',
    pink: '#FF6B9D',
    purple: '#C77DFF'
} as const;

type HighlightColor = keyof typeof HIGHLIGHT_COLORS;

const EnhancedPDFReader: React.FC = () => {
    const { user } = useAuth();
    const [userBookCopy, setUserBookCopy] = useState<UserBookCopy | null>(null);
    const [progress, setProgress] = useState<ReadingProgress | null>(null);
    const [notes, setNotes] = useState<BookNote[]>([]);
    const [highlights, setHighlights] = useState<BookHighlight[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // PDF state
    const [numPages, setNumPages] = useState<number>(0);
    const [currentPage, setCurrentPage] = useState(1);
    const [scale, setScale] = useState(1.2);
    const [rotation, setRotation] = useState(0);

    // Selection state
    const [selectedTool, setSelectedTool] = useState<'none' | 'highlight' | 'note'>('none');
    const [selectedColor, setSelectedColor] = useState<HighlightColor>('yellow');
    const [currentSelection, setCurrentSelection] = useState<TextSelection | null>(null);
    const [showNotes, setShowNotes] = useState(false);

    // Note modal state
    const [noteModalOpen, setNoteModalOpen] = useState(false);
    const [newNoteText, setNewNoteText] = useState('');

    // Progress tracking
    const [lastSavedPage, setLastSavedPage] = useState(1);
    const [readingStartTime, setReadingStartTime] = useState<Date | null>(null);
    const [progressSaving, setProgressSaving] = useState(false);

    // Refs
    const documentRef = useRef<HTMLDivElement>(null);
    const selectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const progressSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

    // Memoized PDF options to prevent unnecessary reloads
    const pdfOptions = useMemo(() => ({}), []);

    // Memoized values
    const liveProgressPercentage = useMemo(() =>
        numPages > 0 ? (currentPage / numPages) * 100 : 0
        , [currentPage, numPages]);

    const sessionReadingTime = useMemo(() =>
        readingStartTime ? Math.floor((new Date().getTime() - readingStartTime.getTime()) / 60000) : 0
        , [readingStartTime]);

    const totalReadingTime = useMemo(() =>
        (progress?.reading_time_minutes || 0) + sessionReadingTime
        , [progress, sessionReadingTime]);

    // Initialize PDF and load data
    useEffect(() => {
        initializeBook();
    }, []);

    // Handle text selection
    useEffect(() => {
        const handleSelectionChange = () => {
            if (selectionTimeoutRef.current) {
                clearTimeout(selectionTimeoutRef.current);
            }

            selectionTimeoutRef.current = setTimeout(() => {
                handleTextSelection();
            }, 150);
        };

        document.addEventListener('selectionchange', handleSelectionChange);
        return () => {
            document.removeEventListener('selectionchange', handleSelectionChange);
            if (selectionTimeoutRef.current) {
                clearTimeout(selectionTimeoutRef.current);
            }
        };
    }, [selectedTool]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (progressSaveTimeoutRef.current) {
                clearTimeout(progressSaveTimeoutRef.current);
            }
        };
    }, []);

    const initializeBook = async () => {
        try {
            setLoading(true);
            setError(null);
            setReadingStartTime(new Date());

            // Get book copy
            const bookCopyResponse = await axios.get(`${apiUrl}/api/user-books/test-copy?title=The Way of the Dog Anahata&type=public`);
            if (!bookCopyResponse.data.success) {
                throw new Error('Failed to get book copy');
            }

            const bookCopy = bookCopyResponse.data.book_copy;
            setUserBookCopy(bookCopy);

            // Load progress, notes, and highlights
            await Promise.all([
                loadProgress(bookCopy.id),
                loadNotes(bookCopy.id),
                loadHighlights(bookCopy.id)
            ]);

        } catch (err) {
            console.error('Error initializing book:', err);
            setError(err instanceof Error ? err.message : 'Failed to load book');
        } finally {
            setLoading(false);
        }
    };

    const loadProgress = async (bookCopyId: number) => {
        try {
            const response = await axios.get(`${apiUrl}/api/user-books/test-progress/${bookCopyId}`);
            if (response.data.success) {
                const savedProgress = response.data.progress;
                setProgress(savedProgress);

                if (savedProgress.current_page && savedProgress.current_page > 1) {
                    setCurrentPage(savedProgress.current_page);
                }
                if (savedProgress.pdf_zoom_level) {
                    setScale(savedProgress.pdf_zoom_level);
                }
                setLastSavedPage(savedProgress.current_page || 1);
            }
        } catch (err) {
            console.error('Error loading progress:', err);
        }
    };

    const loadNotes = async (bookCopyId: number) => {
        try {
            const response = await axios.get(`${apiUrl}/api/user-books/test-notes/${bookCopyId}`);
            if (response.data.success) {
                setNotes(response.data.notes);
            }
        } catch (err) {
            console.error('Error loading notes:', err);
        }
    };

    const loadHighlights = async (bookCopyId: number) => {
        try {
            const response = await axios.get(`${apiUrl}/api/user-books/test-highlights/${bookCopyId}`);
            if (response.data.success) {
                setHighlights(response.data.highlights);
            }
        } catch (err) {
            console.error('Error loading highlights:', err);
        }
    };

    const handleTextSelection = useCallback(() => {
        const selection = window.getSelection();

        if (!selection || selection.toString().trim() === '' || selectedTool === 'none') {
            setCurrentSelection(null);
            return;
        }

        const selectedText = selection.toString().trim();
        const range = selection.getRangeAt(0);
        const bounds = range.getBoundingClientRect();

        // Find which page the selection is on
        const pageElement = range.startContainer.parentElement?.closest('[data-page-number]');
        const pageNumber = pageElement ? parseInt(pageElement.getAttribute('data-page-number') || '1') : currentPage;

        const textSelection: TextSelection = {
            text: selectedText,
            bounds,
            range,
            page: pageNumber
        };

        setCurrentSelection(textSelection);

        // Auto-trigger action based on selected tool
        if (selectedTool === 'highlight') {
            createHighlight(textSelection);
        } else if (selectedTool === 'note') {
            setNoteModalOpen(true);
        }
    }, [selectedTool, currentPage]);

    const createHighlight = async (selection: TextSelection) => {
        if (!userBookCopy || !selection) return;

        try {
            const response = await axios.post(`${apiUrl}/api/user-books/test-highlights`, {
                book_copy_id: userBookCopy.id,
                highlighted_text: selection.text,
                color: selectedColor,
                page_number: selection.page,
                pdf_coordinates: {
                    startX: selection.bounds.left,
                    startY: selection.bounds.top,
                    endX: selection.bounds.right,
                    endY: selection.bounds.bottom,
                    page: selection.page
                }
            });

            if (response.data.success) {
                const newHighlight = response.data.highlight;
                newHighlight.text_bounds = selection.bounds;
                setHighlights(prev => [...prev, newHighlight]);

                // Visual feedback
                highlightSelectedText(selection, selectedColor);

                // Clear selection
                clearSelection();
                setSelectedTool('none');
            }
        } catch (err) {
            console.error('Error creating highlight:', err);
        }
    };

    const createNote = async () => {
        if (!userBookCopy || !currentSelection || !newNoteText.trim()) return;

        try {
            const response = await axios.post(`${apiUrl}/api/user-books/test-notes`, {
                book_copy_id: userBookCopy.id,
                note_text: newNoteText,
                note_type: 'text_note',
                color: selectedColor,
                page_number: currentSelection.page,
                selected_text: currentSelection.text,
                pdf_coordinates: {
                    x: currentSelection.bounds.left + currentSelection.bounds.width / 2,
                    y: currentSelection.bounds.top + currentSelection.bounds.height / 2,
                    page: currentSelection.page
                }
            });

            if (response.data.success) {
                const newNote = response.data.note;
                newNote.text_bounds = currentSelection.bounds;
                setNotes(prev => [...prev, newNote]);

                // Visual feedback
                highlightSelectedText(currentSelection, selectedColor);

                // Reset modal
                setNoteModalOpen(false);
                setNewNoteText('');
                clearSelection();
                setSelectedTool('none');
            }
        } catch (err) {
            console.error('Error creating note:', err);
        }
    };

    const highlightSelectedText = (selection: TextSelection, color: HighlightColor) => {
        const span = document.createElement('span');
        span.style.backgroundColor = HIGHLIGHT_COLORS[color];
        span.style.opacity = '0.4';
        span.style.transition = 'opacity 0.3s ease';

        try {
            selection.range.surroundContents(span);

            // Animate highlight
            setTimeout(() => {
                span.style.opacity = '0.6';
            }, 100);
        } catch (err) {
            // Fallback for complex selections
            span.appendChild(selection.range.extractContents());
            selection.range.insertNode(span);
        }
    };

    const clearSelection = () => {
        window.getSelection()?.removeAllRanges();
        setCurrentSelection(null);
    };

    const debouncedSaveProgress = useCallback((page: number, zoom: number) => {
        if (progressSaveTimeoutRef.current) {
            clearTimeout(progressSaveTimeoutRef.current);
        }

        progressSaveTimeoutRef.current = setTimeout(async () => {
            if (!userBookCopy || page === lastSavedPage) return;

            setProgressSaving(true);
            try {
                const progressPercentage = numPages > 0 ? (page / numPages) * 100 : 0;
                const totalTime = (progress?.reading_time_minutes || 0) + sessionReadingTime;

                await axios.put(`${apiUrl}/api/user-books/test-progress/${userBookCopy.id}`, {
                    current_page: page,
                    total_pages: numPages,
                    progress_percentage: progressPercentage,
                    pdf_zoom_level: zoom,
                    reading_time_minutes: totalTime,
                    last_read_at: new Date().toISOString()
                });

                setLastSavedPage(page);
            } catch (err) {
                console.error('Error saving progress:', err);
            } finally {
                setProgressSaving(false);
            }
        }, 1000);
    }, [userBookCopy, numPages, lastSavedPage, sessionReadingTime, progress, apiUrl]);

    const goToPage = (page: number) => {
        if (page < 1 || page > numPages) return;
        setCurrentPage(page);
        debouncedSaveProgress(page, scale);
    };

    const handleZoom = (delta: number) => {
        const newScale = Math.max(0.5, Math.min(3.0, scale + delta));
        setScale(newScale);
        debouncedSaveProgress(currentPage, newScale);
    };

    const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
        setNumPages(numPages);
        setLoading(false);
        setError(null);
    };

    const onDocumentLoadError = (error: Error) => {
        console.error('PDF Load Error:', error);
        setError(`Failed to load PDF: ${error.message}`);
        setLoading(false);
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
                <motion.div
                    className="text-center space-y-4"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    <div className="text-blue-500 text-6xl">📚</div>
                    <h2 className="text-2xl font-bold">Loading your book...</h2>
                    <motion.div
                        className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    />
                    <p className="text-gray-400">Preparing enhanced reading experience...</p>
                </motion.div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
                <motion.div
                    className="text-center space-y-4"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5 }}
                >
                    <div className="text-red-500 text-6xl">❌</div>
                    <h2 className="text-2xl font-bold text-red-400">Error Loading Book</h2>
                    <p className="text-gray-400 max-w-md">{error}</p>
                    <motion.button
                        onClick={() => window.location.reload()}
                        className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                    >
                        Retry
                    </motion.button>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-900 text-white">
            {/* Header */}
            <motion.header
                className="border-b border-gray-700 p-4 bg-gray-800/50 backdrop-blur-sm sticky top-0 z-50"
                initial={{ y: -100 }}
                animate={{ y: 0 }}
                transition={{ type: "spring", stiffness: 100 }}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <BookOpen className="w-6 h-6 text-blue-400" />
                        <h1 className="text-xl font-bold">{userBookCopy?.book_title || 'Loading...'}</h1>
                        <div className="flex items-center space-x-4 text-sm text-gray-400">
                            <span>Page {currentPage} of {numPages}</span>
                            <span>•</span>
                            <span>{Math.round(liveProgressPercentage)}% complete</span>
                            {totalReadingTime > 0 && (
                                <>
                                    <span>•</span>
                                    <span className="text-blue-400">📖 {totalReadingTime} min read</span>
                                </>
                            )}
                        </div>
                        {progressSaving && (
                            <motion.div
                                className="flex items-center space-x-2 text-blue-400"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                            >
                                <motion.div
                                    className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full"
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                                />
                                <span className="text-xs">Saving...</span>
                            </motion.div>
                        )}
                    </div>

                    <div className="flex items-center space-x-2">
                        {/* Tool Selection */}
                        <div className="flex items-center space-x-1 bg-gray-700/50 rounded-lg p-1">
                            <motion.button
                                onClick={() => setSelectedTool(selectedTool === 'highlight' ? 'none' : 'highlight')}
                                className={`p-2 rounded ${selectedTool === 'highlight' ? 'bg-yellow-500 text-black' : 'bg-transparent hover:bg-gray-600'} transition-colors`}
                                title="Highlight Text"
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <Highlighter className="w-4 h-4" />
                            </motion.button>

                            <motion.button
                                onClick={() => setSelectedTool(selectedTool === 'note' ? 'none' : 'note')}
                                className={`p-2 rounded ${selectedTool === 'note' ? 'bg-blue-500' : 'bg-transparent hover:bg-gray-600'} transition-colors`}
                                title="Add Note"
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <MessageSquare className="w-4 h-4" />
                            </motion.button>

                            <motion.button
                                onClick={() => setShowNotes(!showNotes)}
                                className="p-2 rounded bg-transparent hover:bg-gray-600 transition-colors"
                                title="Toggle Notes Panel"
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <Bookmark className="w-4 h-4" />
                            </motion.button>
                        </div>

                        {/* Color Selection */}
                        {(selectedTool === 'highlight' || selectedTool === 'note') && (
                            <motion.div
                                className="flex items-center space-x-1 bg-gray-700/50 rounded-lg p-1"
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 20 }}
                            >
                                {Object.entries(HIGHLIGHT_COLORS).map(([color, value]) => (
                                    <motion.button
                                        key={color}
                                        onClick={() => setSelectedColor(color as HighlightColor)}
                                        className={`w-6 h-6 rounded-full border-2 ${selectedColor === color ? 'border-white scale-110' : 'border-gray-500'
                                            } transition-all`}
                                        style={{ backgroundColor: value }}
                                        title={color}
                                        whileHover={{ scale: 1.1 }}
                                        whileTap={{ scale: 0.9 }}
                                    />
                                ))}
                            </motion.div>
                        )}

                        {/* Zoom Controls */}
                        <div className="flex items-center space-x-1 bg-gray-700/50 rounded-lg p-1">
                            <motion.button
                                onClick={() => handleZoom(-0.2)}
                                className="p-2 rounded hover:bg-gray-600 transition-colors"
                                title="Zoom Out"
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <ZoomOut className="w-4 h-4" />
                            </motion.button>
                            <span className="text-sm text-gray-400 min-w-[4rem] text-center">
                                {Math.round(scale * 100)}%
                            </span>
                            <motion.button
                                onClick={() => handleZoom(0.2)}
                                className="p-2 rounded hover:bg-gray-600 transition-colors"
                                title="Zoom In"
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                            >
                                <ZoomIn className="w-4 h-4" />
                            </motion.button>
                        </div>

                        {/* Reset Button */}
                        <motion.button
                            onClick={() => {
                                setCurrentPage(1);
                                debouncedSaveProgress(1, scale);
                            }}
                            className="p-2 rounded bg-gray-700/50 hover:bg-gray-600 transition-colors"
                            title="Go to First Page"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                        >
                            <RotateCcw className="w-4 h-4" />
                        </motion.button>
                    </div>
                </div>

                {/* Tool Instructions */}
                <AnimatePresence>
                    {selectedTool !== 'none' && (
                        <motion.div
                            className="mt-3 flex items-center justify-center space-x-2 text-sm"
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                        >
                            <motion.span
                                className="text-blue-400"
                                animate={{ x: [0, 5, 0] }}
                                transition={{ duration: 1.5, repeat: Infinity }}
                            >
                                →
                            </motion.span>
                            <span className="text-gray-300">
                                {selectedTool === 'highlight'
                                    ? 'Select text to highlight with ' + selectedColor
                                    : 'Select text to add a note'
                                }
                            </span>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Current Selection Indicator */}
                <AnimatePresence>
                    {currentSelection && (
                        <motion.div
                            className="mt-2 flex items-center justify-center space-x-2 text-sm text-blue-400"
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                        >
                            <span>📝</span>
                            <span>Selected: "{currentSelection.text.substring(0, 50)}..."</span>
                            <motion.button
                                onClick={clearSelection}
                                className="text-gray-400 hover:text-white ml-2"
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.9 }}
                            >
                                ✕
                            </motion.button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.header>

            <div className="flex h-[calc(100vh-120px)]">
                {/* Main PDF Viewer */}
                <motion.div
                    className="flex-1 flex flex-col"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.5 }}
                >
                    {/* PDF Document */}
                    <div
                        ref={documentRef}
                        className="flex-1 overflow-auto bg-gray-800 flex items-center justify-center p-4"
                        style={{ userSelect: 'text' }}
                    >
                        <motion.div
                            initial={{ scale: 0.8 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", stiffness: 100 }}
                        >
                            <Document
                                file="/books/the-way-of-the-dog-anahata.pdf"
                                onLoadSuccess={onDocumentLoadSuccess}
                                onLoadError={onDocumentLoadError}
                                className="shadow-2xl"
                                options={pdfOptions}
                            >
                                <Page
                                    pageNumber={currentPage}
                                    scale={scale}
                                    rotate={rotation}
                                    renderTextLayer={true}
                                    renderAnnotationLayer={false}
                                    className="border border-gray-600 bg-white"
                                    data-page-number={currentPage}
                                />
                            </Document>
                        </motion.div>
                    </div>

                    {/* Navigation Controls */}
                    <motion.div
                        className="border-t border-gray-700 p-4 flex items-center justify-between bg-gray-800/50 backdrop-blur-sm"
                        initial={{ y: 100 }}
                        animate={{ y: 0 }}
                        transition={{ type: "spring", stiffness: 100 }}
                    >
                        <motion.button
                            onClick={() => goToPage(currentPage - 1)}
                            disabled={currentPage <= 1}
                            className="flex items-center space-x-2 px-4 py-2 bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
                            whileHover={currentPage > 1 ? { scale: 1.05 } : {}}
                            whileTap={currentPage > 1 ? { scale: 0.95 } : {}}
                        >
                            <ChevronLeft className="w-4 h-4" />
                            <span>Previous</span>
                        </motion.button>

                        <div className="flex items-center space-x-4">
                            <span className="text-sm text-gray-400">Go to page:</span>
                            <input
                                type="number"
                                min="1"
                                max={numPages}
                                value={currentPage}
                                onChange={(e) => {
                                    const page = parseInt(e.target.value);
                                    if (page >= 1 && page <= numPages) {
                                        goToPage(page);
                                    }
                                }}
                                className="w-20 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-center focus:border-blue-500 focus:outline-none transition-colors"
                            />
                            <span className="text-sm text-gray-400">of {numPages}</span>
                        </div>

                        <motion.button
                            onClick={() => goToPage(currentPage + 1)}
                            disabled={currentPage >= numPages}
                            className="flex items-center space-x-2 px-4 py-2 bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
                            whileHover={currentPage < numPages ? { scale: 1.05 } : {}}
                            whileTap={currentPage < numPages ? { scale: 0.95 } : {}}
                        >
                            <span>Next</span>
                            <ChevronRight className="w-4 h-4" />
                        </motion.button>
                    </motion.div>
                </motion.div>

                {/* Notes Panel */}
                <AnimatePresence>
                    {showNotes && (
                        <motion.div
                            className="w-80 border-l border-gray-700 bg-gray-800 flex flex-col"
                            initial={{ x: 320 }}
                            animate={{ x: 0 }}
                            exit={{ x: 320 }}
                            transition={{ type: "spring", stiffness: 100, damping: 20 }}
                        >
                            <div className="p-4 border-b border-gray-700">
                                <h3 className="text-lg font-semibold">Notes & Highlights</h3>
                                <p className="text-sm text-gray-400 mt-1">
                                    {notes.length} notes • {highlights.length} highlights
                                </p>
                            </div>

                            <div className="flex-1 overflow-y-auto p-4 space-y-4 notes-panel-scroll">
                                {/* Recent Notes */}
                                {notes.slice().reverse().slice(0, 10).map((note) => (
                                    <motion.div
                                        key={note.id}
                                        className="bg-gray-700 rounded p-3 hover:bg-gray-600 transition-colors cursor-pointer"
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        whileHover={{ scale: 1.02 }}
                                        onClick={() => goToPage(note.page_number)}
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-xs text-gray-400">Page {note.page_number}</span>
                                            <div
                                                className="w-3 h-3 rounded-full"
                                                style={{ backgroundColor: HIGHLIGHT_COLORS[note.color as HighlightColor] || HIGHLIGHT_COLORS.yellow }}
                                            />
                                        </div>
                                        <p className="text-sm">{note.note_text}</p>
                                        {note.selected_text && (
                                            <p className="text-xs text-gray-400 mt-2 italic">
                                                "{note.selected_text.substring(0, 100)}..."
                                            </p>
                                        )}
                                    </motion.div>
                                ))}

                                {/* Recent Highlights */}
                                {highlights.slice().reverse().slice(0, 5).map((highlight) => (
                                    <motion.div
                                        key={highlight.id}
                                        className="bg-gray-700 rounded p-3 hover:bg-gray-600 transition-colors cursor-pointer"
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        whileHover={{ scale: 1.02 }}
                                        onClick={() => goToPage(highlight.page_number)}
                                    >
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-xs text-gray-400">Page {highlight.page_number}</span>
                                            <div
                                                className="w-3 h-3 rounded-full"
                                                style={{ backgroundColor: HIGHLIGHT_COLORS[highlight.color as HighlightColor] || HIGHLIGHT_COLORS.yellow }}
                                            />
                                        </div>
                                        <p className="text-sm italic">"{highlight.highlighted_text.substring(0, 100)}..."</p>
                                    </motion.div>
                                ))}

                                {notes.length === 0 && highlights.length === 0 && (
                                    <div className="text-center text-gray-500 mt-8">
                                        <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
                                        <p className="text-sm">No notes or highlights yet</p>
                                        <p className="text-xs mt-1">Select text and choose a tool to get started</p>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Note Creation Modal */}
            <AnimatePresence>
                {noteModalOpen && (
                    <motion.div
                        className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <motion.div
                            className="bg-gray-800 rounded-lg p-6 w-96 max-w-md border border-gray-600"
                            initial={{ scale: 0.8, y: 50 }}
                            animate={{ scale: 1, y: 0 }}
                            exit={{ scale: 0.8, y: 50 }}
                            transition={{ type: "spring", stiffness: 200, damping: 20 }}
                        >
                            <h3 className="text-lg font-semibold mb-4">
                                Add Note to Selected Text
                            </h3>

                            {currentSelection && (
                                <div className="mb-4 p-3 bg-gray-700 rounded border-l-4 border-blue-500">
                                    <p className="text-xs text-gray-400 mb-1">Selected text:</p>
                                    <p className="text-sm italic text-gray-300">
                                        "{currentSelection.text.substring(0, 150)}..."
                                    </p>
                                </div>
                            )}

                            <textarea
                                value={newNoteText}
                                onChange={(e) => setNewNoteText(e.target.value)}
                                placeholder="Add your note about this text..."
                                className="w-full h-32 p-3 bg-gray-700 border border-gray-600 rounded resize-none focus:border-blue-500 focus:outline-none transition-colors"
                                autoFocus
                            />

                            <div className="flex justify-end space-x-3 mt-4">
                                <motion.button
                                    onClick={() => {
                                        setNoteModalOpen(false);
                                        setNewNoteText('');
                                        clearSelection();
                                        setSelectedTool('none');
                                    }}
                                    className="px-4 py-2 bg-gray-600 rounded hover:bg-gray-500 transition-colors"
                                    whileHover={{ scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                >
                                    Cancel
                                </motion.button>
                                <motion.button
                                    onClick={createNote}
                                    disabled={!newNoteText.trim()}
                                    className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    whileHover={newNoteText.trim() ? { scale: 1.05 } : {}}
                                    whileTap={newNoteText.trim() ? { scale: 0.95 } : {}}
                                >
                                    Add Note
                                </motion.button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default EnhancedPDFReader; 