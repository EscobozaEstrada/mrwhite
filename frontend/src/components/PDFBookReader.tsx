'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { ChevronLeft, ChevronRight, BookOpen, Settings, MessageSquare, Highlighter, Bookmark, RotateCcw } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';

// PDF.js types
declare global {
    interface Window {
        pdfjsLib: any;
    }
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
    text_coordinates?: {
        startX: number;
        startY: number;
        endX: number;
        endY: number;
        width: number;
        height: number;
    };
    created_at: string;
}

interface BookHighlight {
    id: number;
    highlighted_text: string;
    color: string;
    page_number: number;
    pdf_coordinates: { startX: number; startY: number; endX: number; endY: number; page: number };
    created_at: string;
}

interface TextSelection {
    text: string;
    startX: number;
    startY: number;
    endX: number;
    endY: number;
    width: number;
    height: number;
    page: number;
}

const PDFBookReader: React.FC = () => {
    const { user } = useAuth();
    const [userBookCopy, setUserBookCopy] = useState<UserBookCopy | null>(null);
    const [progress, setProgress] = useState<ReadingProgress | null>(null);
    const [notes, setNotes] = useState<BookNote[]>([]);
    const [highlights, setHighlights] = useState<BookHighlight[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // PDF viewer state
    const [pdfDoc, setPdfDoc] = useState<any>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [zoomLevel, setZoomLevel] = useState(1.0);
    const [isRendering, setIsRendering] = useState(false);

    // Progress tracking state
    const [lastSavedPage, setLastSavedPage] = useState(1);
    const [readingStartTime, setReadingStartTime] = useState<Date | null>(null);
    const [progressSaving, setProgressSaving] = useState(false);

    // UI state
    const [showNotes, setShowNotes] = useState(false);
    const [selectedTool, setSelectedTool] = useState<'none' | 'highlight' | 'note'>('none');
    const [selectedText, setSelectedText] = useState('');
    const [noteModalOpen, setNoteModalOpen] = useState(false);
    const [newNoteText, setNewNoteText] = useState('');

    // Text selection state
    const [isSelecting, setIsSelecting] = useState(false);
    const [selectionStart, setSelectionStart] = useState<{ x: number, y: number } | null>(null);
    const [selectionEnd, setSelectionEnd] = useState<{ x: number, y: number } | null>(null);
    const [currentSelection, setCurrentSelection] = useState<TextSelection | null>(null);
    const [textContent, setTextContent] = useState<any>(null);

    const canvasRef = useRef<HTMLCanvasElement>(null);
    const textLayerRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const progressSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

    // Storage keys for localStorage backup
    const STORAGE_KEYS = {
        lastPage: `book_progress_page_${userBookCopy?.id || 'default'}`,
        lastZoom: `book_progress_zoom_${userBookCopy?.id || 'default'}`,
        readingTime: `book_progress_time_${userBookCopy?.id || 'default'}`
    };

    // Initialize PDF.js
    useEffect(() => {
        const script = document.createElement('script');
        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        script.onload = () => {
            if (window.pdfjsLib) {
                window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                console.log('✅ PDF.js loaded');
                initializeBook();
            }
        };
        script.onerror = () => {
            setError('Failed to load PDF.js. Please check your internet connection.');
        };
        document.head.appendChild(script);

        return () => {
            if (document.head.contains(script)) {
                document.head.removeChild(script);
            }
        };
    }, []);

    // Save progress to localStorage (immediate backup)
    const saveProgressToLocalStorage = useCallback((page: number, zoom: number) => {
        try {
            localStorage.setItem(STORAGE_KEYS.lastPage, page.toString());
            localStorage.setItem(STORAGE_KEYS.lastZoom, zoom.toString());
            localStorage.setItem(STORAGE_KEYS.readingTime, new Date().toISOString());
            console.log(`💾 Progress saved to localStorage: page ${page}`);
        } catch (err) {
            console.warn('Failed to save progress to localStorage:', err);
        }
    }, [STORAGE_KEYS]);

    // Load progress from localStorage (backup)
    const loadProgressFromLocalStorage = useCallback((): { page: number; zoom: number } | null => {
        try {
            const savedPage = localStorage.getItem(STORAGE_KEYS.lastPage);
            const savedZoom = localStorage.getItem(STORAGE_KEYS.lastZoom);

            if (savedPage) {
                return {
                    page: parseInt(savedPage, 10),
                    zoom: savedZoom ? parseFloat(savedZoom) : 1.0
                };
            }
        } catch (err) {
            console.warn('Failed to load progress from localStorage:', err);
        }
        return null;
    }, [STORAGE_KEYS]);

    // Debounced progress saving to API
    const debouncedSaveProgress = useCallback((page: number, zoom: number) => {
        if (progressSaveTimeoutRef.current) {
            clearTimeout(progressSaveTimeoutRef.current);
        }

        // Save to localStorage immediately for instant backup
        saveProgressToLocalStorage(page, zoom);

        // Debounce API call to prevent excessive requests
        progressSaveTimeoutRef.current = setTimeout(async () => {
            if (!userBookCopy || page === lastSavedPage) return;

            setProgressSaving(true);
            try {
                const progressPercentage = totalPages > 0 ? (page / totalPages) * 100 : 0;
                const sessionTime = readingStartTime ?
                    Math.floor((new Date().getTime() - readingStartTime.getTime()) / 60000) : 0;
                const totalReadingTime = (progress?.reading_time_minutes || 0) + sessionTime;

                await axios.put(`${apiUrl}/api/user-books/test-progress/${userBookCopy.id}`, {
                    current_page: page,
                    total_pages: totalPages,
                    progress_percentage: progressPercentage,
                    pdf_zoom_level: zoom,
                    reading_time_minutes: totalReadingTime,
                    last_read_at: new Date().toISOString()
                });

                setLastSavedPage(page);
                console.log(`📊 Progress saved to API: page ${page}/${totalPages} (${progressPercentage.toFixed(1)}%) • ${totalReadingTime} min total`);
            } catch (err) {
                console.error('❌ Error saving progress to API:', err);
                // Progress is still saved in localStorage as backup
            } finally {
                setProgressSaving(false);
            }
        }, 1000); // 1 second debounce
    }, [userBookCopy, totalPages, lastSavedPage, readingStartTime, progress, apiUrl, saveProgressToLocalStorage]);

    const initializeBook = async () => {
        try {
            console.log('📚 Initializing book for demo mode');
            setReadingStartTime(new Date());

            // Get or create user book copy (using test route)
            const bookCopyResponse = await axios.get(`${apiUrl}/api/user-books/test-copy?title=The Way of the Dog Anahata&type=public`);

            if (!bookCopyResponse.data.success) {
                throw new Error('Failed to get book copy');
            }

            const bookCopy = bookCopyResponse.data.book_copy;
            setUserBookCopy(bookCopy);
            console.log('✅ Book copy loaded:', bookCopy.id);

            // Load PDF first and wait for it to complete
            const pdf = await loadPDF(bookCopy.original_pdf_url);

            // Now that PDF is loaded and totalPages is set, restore progress
            await loadAndRestoreProgress(bookCopy.id, pdf);

            // Load notes and highlights
            await Promise.all([
                loadNotes(bookCopy.id),
                loadHighlights(bookCopy.id)
            ]);

        } catch (err: any) {
            console.error('❌ Error initializing book:', err);
            setError('Failed to load book. Trying offline mode...');

            // Try to restore from localStorage as fallback
            const savedProgress = loadProgressFromLocalStorage();
            if (savedProgress) {
                console.log('📱 Restored from offline storage');
                setCurrentPage(savedProgress.page);
                setZoomLevel(savedProgress.zoom);
                // Try to render if we have a loaded PDF
                if (pdfDoc) {
                    await renderPage(savedProgress.page);
                }
            }
        } finally {
            setLoading(false);
        }
    };

    const loadPDF = async (pdfUrl: string) => {
        try {
            console.log('📄 Loading PDF from:', pdfUrl);
            const loadingTask = window.pdfjsLib.getDocument(pdfUrl);
            const pdf = await loadingTask.promise;

            setPdfDoc(pdf);
            setTotalPages(pdf.numPages);
            console.log(`✅ PDF loaded: ${pdf.numPages} pages`);

            return pdf;
        } catch (err) {
            console.error('❌ Error loading PDF:', err);
            throw new Error('Failed to load PDF');
        }
    };

    const loadAndRestoreProgress = async (bookCopyId: number, pdf?: any) => {
        try {
            console.log('📊 Loading saved progress...');
            const response = await axios.get(`${apiUrl}/api/user-books/test-progress/${bookCopyId}`);

            if (response.data.success) {
                const savedProgress = response.data.progress;
                setProgress(savedProgress);

                // Restore reading position
                const savedPage = savedProgress.current_page || 1;
                const savedZoom = savedProgress.pdf_zoom_level || 1.0;

                // Validate page number using current totalPages
                const currentTotalPages = pdf?.numPages || totalPages;
                const pageToRestore = Math.min(Math.max(savedPage, 1), currentTotalPages);

                setCurrentPage(pageToRestore);
                setZoomLevel(savedZoom);
                setLastSavedPage(pageToRestore);

                // Render the restored page only if PDF is loaded
                const pdfToUse = pdf || pdfDoc;
                if (pdfToUse) {
                    await renderPage(pageToRestore, pdfToUse);
                }

                console.log(`🔄 Restored reading position: page ${pageToRestore}/${currentTotalPages} (${((pageToRestore / currentTotalPages) * 100).toFixed(1)}%)`);

                // Show restoration notification
                if (pageToRestore > 1) {
                    setTimeout(() => {
                        const notification = document.createElement('div');
                        notification.className = 'fixed top-4 right-4 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-bounce';
                        notification.innerHTML = `📖 Resumed reading from page ${pageToRestore}`;
                        document.body.appendChild(notification);

                        setTimeout(() => {
                            if (document.body.contains(notification)) {
                                document.body.removeChild(notification);
                            }
                        }, 3000);
                    }, 1000);
                }
            } else {
                // No saved progress, start from page 1
                setCurrentPage(1);
                setZoomLevel(1.0);
                const pdfToUse = pdf || pdfDoc;
                if (pdfToUse) {
                    await renderPage(1, pdfToUse);
                }
            }
        } catch (err) {
            console.error('❌ Error loading progress:', err);

            // Fallback to localStorage
            const localProgress = loadProgressFromLocalStorage();
            if (localProgress) {
                const currentTotalPages = pdf?.numPages || totalPages;
                const pageToRestore = Math.min(Math.max(localProgress.page, 1), currentTotalPages);
                setCurrentPage(pageToRestore);
                setZoomLevel(localProgress.zoom);

                // Render page if PDF is available
                const pdfToUse = pdf || pdfDoc;
                if (pdfToUse) {
                    await renderPage(pageToRestore, pdfToUse);
                }
                console.log('📱 Restored from localStorage backup');
            } else {
                // Start from page 1 if no saved progress
                setCurrentPage(1);
                setZoomLevel(1.0);
                const pdfToUse = pdf || pdfDoc;
                if (pdfToUse) {
                    await renderPage(1, pdfToUse);
                }
            }
        }
    };

    const renderPage = async (pageNum: number, pdf?: any) => {
        const pdfToUse = pdf || pdfDoc;
        if (!pdfToUse || !canvasRef.current) return;

        // Cancel any existing rendering by clearing the canvas first
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        if (context) {
            context.clearRect(0, 0, canvas.width, canvas.height);
        }

        // Clear text layer
        if (textLayerRef.current) {
            textLayerRef.current.innerHTML = '';
        }

        setIsRendering(true);
        try {
            const page = await pdfToUse.getPage(pageNum);

            if (!context) return;

            const viewport = page.getViewport({ scale: zoomLevel });
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            // Render PDF page to canvas
            const renderContext = {
                canvasContext: context,
                viewport: viewport
            };

            await page.render(renderContext).promise;

            // Extract and render text layer for selection
            await renderTextLayer(page, viewport);

            console.log(`✅ Rendered page ${pageNum} with text layer`);

            // Render overlays (notes and highlights)
            renderOverlays(pageNum);

        } catch (err) {
            console.error('❌ Error rendering page:', err);
        } finally {
            setIsRendering(false);
        }
    };

    // Render text layer for text selection
    const renderTextLayer = async (page: any, viewport: any) => {
        try {
            const textContent = await page.getTextContent();
            setTextContent(textContent);

            if (!textLayerRef.current) return;

            // Clear existing text layer
            textLayerRef.current.innerHTML = '';
            textLayerRef.current.style.width = `${viewport.width}px`;
            textLayerRef.current.style.height = `${viewport.height}px`;

            // Create text layer div elements
            textContent.items.forEach((textItem: any, index: number) => {
                const textDiv = document.createElement('span');
                textDiv.textContent = textItem.str;
                textDiv.style.position = 'absolute';
                textDiv.style.left = `${textItem.transform[4]}px`;
                textDiv.style.top = `${viewport.height - textItem.transform[5]}px`;
                textDiv.style.fontSize = `${textItem.transform[0]}px`;
                textDiv.style.fontFamily = textItem.fontName || 'sans-serif';
                textDiv.style.color = 'transparent';
                textDiv.style.userSelect = 'text';
                textDiv.style.pointerEvents = 'auto';
                textDiv.dataset.textIndex = index.toString();

                if (textLayerRef.current) {
                    textLayerRef.current.appendChild(textDiv);
                }
            });

            console.log(`✅ Text layer rendered with ${textContent.items.length} text items`);
        } catch (err) {
            console.error('❌ Error rendering text layer:', err);
        }
    };

    const renderOverlays = (pageNum: number) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        // Render highlights for current page
        highlights
            .filter(h => h.page_number === pageNum)
            .forEach(highlight => {
                const coords = highlight.pdf_coordinates;
                if (coords) {
                    ctx.globalAlpha = 0.4;
                    ctx.fillStyle = highlight.color === 'yellow' ? '#FFFF00' :
                        highlight.color === 'blue' ? '#87CEEB' :
                            highlight.color === 'green' ? '#90EE90' : '#FFB6C1';

                    const width = coords.endX - coords.startX;
                    const height = coords.endY - coords.startY;
                    ctx.fillRect(coords.startX * zoomLevel, coords.startY * zoomLevel,
                        width * zoomLevel, height * zoomLevel);
                    ctx.globalAlpha = 1.0;
                }
            });

        // Render notes for current page
        notes
            .filter(n => n.page_number === pageNum)
            .forEach(note => {
                // If note has text coordinates, highlight the text area
                if (note.text_coordinates) {
                    const textCoords = note.text_coordinates;
                    ctx.globalAlpha = 0.2;
                    ctx.fillStyle = note.color === 'yellow' ? '#FFD700' :
                        note.color === 'blue' ? '#87CEEB' :
                            note.color === 'green' ? '#90EE90' : '#FFB6C1';

                    ctx.fillRect(
                        textCoords.startX * zoomLevel,
                        textCoords.startY * zoomLevel,
                        textCoords.width * zoomLevel,
                        textCoords.height * zoomLevel
                    );
                    ctx.globalAlpha = 1.0;

                    // Add border around highlighted text
                    ctx.strokeStyle = note.color === 'yellow' ? '#FFD700' :
                        note.color === 'blue' ? '#4169E1' :
                            note.color === 'green' ? '#32CD32' : '#DC143C';
                    ctx.lineWidth = 2;
                    ctx.strokeRect(
                        textCoords.startX * zoomLevel,
                        textCoords.startY * zoomLevel,
                        textCoords.width * zoomLevel,
                        textCoords.height * zoomLevel
                    );
                }

                // Draw note marker
                const coords = note.pdf_coordinates;
                if (coords) {
                    ctx.fillStyle = note.color === 'yellow' ? '#FFD700' :
                        note.color === 'blue' ? '#4169E1' :
                            note.color === 'green' ? '#32CD32' : '#DC143C';

                    // Draw note marker circle
                    ctx.beginPath();
                    ctx.arc(coords.x * zoomLevel, coords.y * zoomLevel, 10, 0, 2 * Math.PI);
                    ctx.fill();

                    // Add white border
                    ctx.strokeStyle = '#FFFFFF';
                    ctx.lineWidth = 2;
                    ctx.stroke();

                    // Add note icon
                    ctx.fillStyle = '#FFFFFF';
                    ctx.font = 'bold 12px Arial';
                    ctx.textAlign = 'center';
                    ctx.fillText('📝', coords.x * zoomLevel, coords.y * zoomLevel + 4);
                }
            });
    };

    const loadNotes = async (bookCopyId: number) => {
        try {
            const response = await axios.get(`${apiUrl}/api/user-books/test-notes/${bookCopyId}`);
            if (response.data.success) {
                setNotes(response.data.notes);
                console.log('✅ Notes loaded:', response.data.notes.length);
            }
        } catch (err) {
            console.error('❌ Error loading notes:', err);
        }
    };

    const loadHighlights = async (bookCopyId: number) => {
        try {
            const response = await axios.get(`${apiUrl}/api/user-books/test-highlights/${bookCopyId}`);
            if (response.data.success) {
                setHighlights(response.data.highlights);
                console.log('✅ Highlights loaded:', response.data.highlights.length);
            }
        } catch (err) {
            console.error('❌ Error loading highlights:', err);
        }
    };

    const goToPage = useCallback(async (page: number) => {
        if (page < 1 || page > totalPages || page === currentPage) return;

        console.log(`📖 Navigating to page ${page}`);
        setCurrentPage(page);

        // Render page immediately for responsive feel
        await renderPage(page);

        // Save progress with debouncing
        debouncedSaveProgress(page, zoomLevel);
    }, [currentPage, totalPages, pdfDoc, zoomLevel, debouncedSaveProgress]);

    const handleZoom = async (delta: number) => {
        const newZoom = Math.max(0.5, Math.min(3.0, zoomLevel + delta));
        setZoomLevel(newZoom);
        await renderPage(currentPage);

        // Save zoom level
        debouncedSaveProgress(currentPage, newZoom);
    };

    // Handle text selection for notes/highlights
    const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
        if (selectedTool === 'none') return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = (event.clientX - rect.left) / zoomLevel;
        const y = (event.clientY - rect.top) / zoomLevel;

        if (selectedTool === 'note') {
            setNoteModalOpen(true);
            // Store coordinates for note creation
            setSelectedText(JSON.stringify({ x, y, page: currentPage }));
        } else if (selectedTool === 'highlight') {
            // For highlights, we'd need more sophisticated text selection
            // This is a simplified version
            createHighlight(x, y, currentPage);
        }
    };

    const createNote = async () => {
        if (!userBookCopy || !newNoteText.trim()) return;

        // If we have a text selection, create note from selection
        if (currentSelection) {
            await createNoteFromSelection(newNoteText);
            return;
        }

        // Fallback to click-based note creation
        try {
            const coordinates = JSON.parse(selectedText);
            const response = await axios.post(`${apiUrl}/api/user-books/test-notes`, {
                book_copy_id: userBookCopy.id,
                note_text: newNoteText,
                note_type: 'note',
                color: 'yellow',
                page_number: coordinates.page,
                pdf_coordinates: coordinates
            });

            if (response.data.success) {
                setNotes(prev => [...prev, response.data.note]);
                setNoteModalOpen(false);
                setNewNoteText('');
                setSelectedTool('none');

                // Re-render page to show new note
                await renderPage(currentPage);

                console.log('✅ Note created successfully');
            }
        } catch (err) {
            console.error('❌ Error creating note:', err);
        }
    };

    const createHighlight = async (x: number, y: number, page: number) => {
        if (!userBookCopy) return;

        try {
            const response = await axios.post(`${apiUrl}/api/user-books/test-highlights`, {
                book_copy_id: userBookCopy.id,
                highlighted_text: 'Selected text',
                color: 'yellow',
                page_number: page,
                pdf_coordinates: {
                    startX: x - 50,
                    startY: y - 10,
                    endX: x + 50,
                    endY: y + 10,
                    page: page
                }
            });

            if (response.data.success) {
                setHighlights(prev => [...prev, response.data.highlight]);
                setSelectedTool('none');

                // Re-render page to show new highlight
                await renderPage(currentPage);

                console.log('✅ Highlight created successfully');
            }
        } catch (err) {
            console.error('❌ Error creating highlight:', err);
        }
    };

    // Restore to first page
    const restoreToFirstPage = () => {
        goToPage(1);
    };

    // Update reading time display periodically
    useEffect(() => {
        const interval = setInterval(() => {
            // Force re-render to update reading time display
            if (readingStartTime) {
                // This will trigger a re-render to update the session time
                setProgress(prev => prev ? { ...prev } : null);
            }
        }, 30000); // Update every 30 seconds

        return () => clearInterval(interval);
    }, [readingStartTime]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (progressSaveTimeoutRef.current) {
                clearTimeout(progressSaveTimeoutRef.current);
            }
        };
    }, []);

    // Text selection event handlers
    const handleTextSelection = () => {
        const selection = window.getSelection();
        if (!selection || selection.toString().trim() === '') {
            setCurrentSelection(null);
            return;
        }

        const selectedText = selection.toString().trim();
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        const containerRect = containerRef.current?.getBoundingClientRect();

        if (!containerRect) return;

        // Calculate relative coordinates
        const relativeX = (rect.left - containerRect.left) / zoomLevel;
        const relativeY = (rect.top - containerRect.top) / zoomLevel;
        const width = rect.width / zoomLevel;
        const height = rect.height / zoomLevel;

        const textSelection: TextSelection = {
            text: selectedText,
            startX: relativeX,
            startY: relativeY,
            endX: relativeX + width,
            endY: relativeY + height,
            width: width,
            height: height,
            page: currentPage
        };

        setCurrentSelection(textSelection);
        console.log('📝 Text selected:', selectedText, textSelection);
    };

    const handleTextSelectionEnd = () => {
        setTimeout(() => {
            handleTextSelection();
        }, 100); // Small delay to ensure selection is complete
    };

    const createNoteFromSelection = async (noteText: string, color: string = 'yellow') => {
        if (!userBookCopy || !currentSelection) return;

        try {
            const response = await axios.post(`${apiUrl}/api/user-books/test-notes`, {
                book_copy_id: userBookCopy.id,
                note_text: noteText,
                note_type: 'text_note',
                color: color,
                page_number: currentSelection.page,
                selected_text: currentSelection.text,
                pdf_coordinates: {
                    x: currentSelection.startX + (currentSelection.width / 2),
                    y: currentSelection.startY + (currentSelection.height / 2),
                    page: currentSelection.page
                },
                text_coordinates: {
                    startX: currentSelection.startX,
                    startY: currentSelection.startY,
                    endX: currentSelection.endX,
                    endY: currentSelection.endY,
                    width: currentSelection.width,
                    height: currentSelection.height
                }
            });

            if (response.data.success) {
                setNotes(prev => [...prev, response.data.note]);
                setNoteModalOpen(false);
                setNewNoteText('');
                setSelectedTool('none');
                setCurrentSelection(null);

                // Clear text selection
                window.getSelection()?.removeAllRanges();

                // Re-render page to show new note
                await renderPage(currentPage);

                console.log('✅ Note created from text selection');
            }
        } catch (err) {
            console.error('❌ Error creating note from selection:', err);
        }
    };

    const createHighlightFromSelection = async (color: string = 'yellow') => {
        if (!userBookCopy || !currentSelection) return;

        try {
            const response = await axios.post(`${apiUrl}/api/user-books/test-highlights`, {
                book_copy_id: userBookCopy.id,
                highlighted_text: currentSelection.text,
                color: color,
                page_number: currentSelection.page,
                pdf_coordinates: {
                    startX: currentSelection.startX,
                    startY: currentSelection.startY,
                    endX: currentSelection.endX,
                    endY: currentSelection.endY,
                    page: currentSelection.page
                }
            });

            if (response.data.success) {
                setHighlights(prev => [...prev, response.data.highlight]);
                setSelectedTool('none');
                setCurrentSelection(null);

                // Clear text selection
                window.getSelection()?.removeAllRanges();

                // Re-render page to show new highlight
                await renderPage(currentPage);

                console.log('✅ Highlight created from text selection');
            }
        } catch (err) {
            console.error('❌ Error creating highlight from selection:', err);
        }
    };

    // Handle tool selection with text
    const handleToolAction = () => {
        if (!currentSelection) return;

        if (selectedTool === 'note') {
            setNoteModalOpen(true);
        } else if (selectedTool === 'highlight') {
            createHighlightFromSelection();
        }
    };

    // Auto-trigger tool action when text is selected and tool is active
    useEffect(() => {
        if (currentSelection && selectedTool !== 'none') {
            handleToolAction();
        }
    }, [currentSelection, selectedTool]);

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center space-y-4">
                    <div className="text-blue-500 text-6xl">📚</div>
                    <h2 className="text-2xl font-bold">Loading your book...</h2>
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
                    <p className="text-gray-500">Restoring your reading progress...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center space-y-4">
                    <div className="text-red-500 text-6xl">❌</div>
                    <h2 className="text-2xl font-bold text-red-600">Error</h2>
                    <p className="text-gray-600">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    // Calculate live progress percentage
    const liveProgressPercentage = totalPages > 0 ? (currentPage / totalPages) * 100 : 0;

    // Calculate reading time from session start
    const sessionReadingTime = readingStartTime ?
        Math.floor((new Date().getTime() - readingStartTime.getTime()) / 60000) : 0;

    // Total reading time (from stored progress + current session)
    const totalReadingTime = (progress?.reading_time_minutes || 0) + sessionReadingTime;

    return (
        <div className="min-h-screen bg-gray-900 text-white">
            {/* Header */}
            <div className="border-b border-gray-700 p-4">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <BookOpen className="w-6 h-6 text-blue-400" />
                        <h1 className="text-xl font-bold">{userBookCopy?.book_title}</h1>
                        <div className="flex items-center space-x-4">
                            <span className="text-sm text-gray-400">
                                Page {currentPage} of {totalPages} • {Math.round(liveProgressPercentage)}% complete
                            </span>
                            {totalReadingTime > 0 && (
                                <span className="text-sm text-blue-400">
                                    📖 {totalReadingTime} min read
                                </span>
                            )}
                        </div>
                        {progressSaving && (
                            <div className="flex items-center space-x-2 text-blue-400">
                                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
                                <span className="text-xs">Saving...</span>
                            </div>
                        )}
                    </div>

                    <div className="flex items-center space-x-2">
                        {/* Restore to First Page */}
                        <button
                            onClick={restoreToFirstPage}
                            className="p-2 rounded bg-gray-700 hover:bg-gray-600 transition-colors"
                            title="Go to First Page"
                        >
                            <RotateCcw className="w-5 h-5" />
                        </button>

                        {/* Tool Selection */}
                        <button
                            onClick={() => setSelectedTool(selectedTool === 'highlight' ? 'none' : 'highlight')}
                            className={`p-2 rounded ${selectedTool === 'highlight' ? 'bg-yellow-500' : 'bg-gray-700'} hover:bg-yellow-600 transition-colors`}
                            title="Select text and highlight it"
                        >
                            <Highlighter className="w-5 h-5" />
                        </button>

                        <button
                            onClick={() => setSelectedTool(selectedTool === 'note' ? 'none' : 'note')}
                            className={`p-2 rounded ${selectedTool === 'note' ? 'bg-blue-500' : 'bg-gray-700'} hover:bg-blue-600 transition-colors`}
                            title="Select text and add a note"
                        >
                            <MessageSquare className="w-5 h-5" />
                        </button>

                        {/* Tool Instructions */}
                        {selectedTool !== 'none' && (
                            <div className="flex items-center space-x-2 text-sm text-gray-300">
                                <span className="animate-pulse">→</span>
                                <span>
                                    {selectedTool === 'highlight'
                                        ? 'Select text to highlight'
                                        : 'Select text to add note'
                                    }
                                </span>
                            </div>
                        )}

                        {/* Current Selection Indicator */}
                        {currentSelection && (
                            <div className="flex items-center space-x-2 text-sm text-blue-400">
                                <span>📝</span>
                                <span>Text selected: "{currentSelection.text.substring(0, 30)}..."</span>
                            </div>
                        )}

                        <button
                            onClick={() => setShowNotes(!showNotes)}
                            className="p-2 rounded bg-gray-700 hover:bg-gray-600 transition-colors"
                            title="Toggle Notes Panel"
                        >
                            <Bookmark className="w-5 h-5" />
                        </button>

                        {/* Zoom Controls */}
                        <button
                            onClick={() => handleZoom(-0.2)}
                            className="p-2 rounded bg-gray-700 hover:bg-gray-600 transition-colors"
                            title="Zoom Out"
                        >
                            -
                        </button>
                        <span className="text-sm text-gray-400 min-w-[4rem] text-center">
                            {Math.round(zoomLevel * 100)}%
                        </span>
                        <button
                            onClick={() => handleZoom(0.2)}
                            className="p-2 rounded bg-gray-700 hover:bg-gray-600 transition-colors"
                            title="Zoom In"
                        >
                            +
                        </button>
                    </div>
                </div>
            </div>

            <div className="flex h-[calc(100vh-80px)]">
                {/* Main PDF Viewer */}
                <div className="flex-1 flex flex-col">
                    {/* PDF Canvas with Text Layer */}
                    <div
                        ref={containerRef}
                        className="flex-1 overflow-auto bg-gray-800 flex items-center justify-center p-4 relative"
                        onMouseUp={handleTextSelectionEnd}
                        onTouchEnd={handleTextSelectionEnd}
                    >
                        <div className="relative">
                            <canvas
                                ref={canvasRef}
                                onClick={handleCanvasClick}
                                className="border border-gray-600 bg-white transition-opacity duration-200"
                                style={{
                                    cursor: selectedTool !== 'none' ? 'crosshair' : 'text',
                                    opacity: isRendering ? 0.7 : 1
                                }}
                            />

                            {/* Text Layer for Selection */}
                            <div
                                ref={textLayerRef}
                                className="absolute top-0 left-0 pointer-events-auto"
                                style={{
                                    zIndex: 1,
                                    mixBlendMode: 'multiply'
                                }}
                            />

                            {/* Current Selection Highlight */}
                            {currentSelection && (
                                <div
                                    className="absolute border-2 border-blue-500 bg-blue-200 bg-opacity-30 pointer-events-none"
                                    style={{
                                        left: `${currentSelection.startX * zoomLevel}px`,
                                        top: `${currentSelection.startY * zoomLevel}px`,
                                        width: `${currentSelection.width * zoomLevel}px`,
                                        height: `${currentSelection.height * zoomLevel}px`,
                                        zIndex: 2
                                    }}
                                />
                            )}
                        </div>

                        {isRendering && (
                            <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30">
                                <div className="bg-gray-800 rounded-lg p-3 flex items-center space-x-2">
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                                    <span className="text-sm text-gray-300">Loading page...</span>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Navigation Controls */}
                    <div className="border-t border-gray-700 p-4 flex items-center justify-between">
                        <button
                            onClick={() => goToPage(currentPage - 1)}
                            disabled={currentPage <= 1}
                            className="flex items-center space-x-2 px-4 py-2 bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
                        >
                            <ChevronLeft className="w-4 h-4" />
                            <span>Previous</span>
                        </button>

                        <div className="flex items-center space-x-4">
                            <span className="text-sm text-gray-400">Go to page:</span>
                            <input
                                type="number"
                                min="1"
                                max={totalPages}
                                value={currentPage}
                                onChange={(e) => {
                                    const page = parseInt(e.target.value);
                                    if (page >= 1 && page <= totalPages) {
                                        goToPage(page);
                                    }
                                }}
                                className="w-20 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-center"
                            />
                            <span className="text-sm text-gray-400">of {totalPages}</span>
                        </div>

                        <button
                            onClick={() => goToPage(currentPage + 1)}
                            disabled={currentPage >= totalPages}
                            className="flex items-center space-x-2 px-4 py-2 bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
                        >
                            <span>Next</span>
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    </div>
                </div>

                {/* Notes Panel */}
                {showNotes && (
                    <div className="w-80 border-l border-gray-700 bg-gray-800 flex flex-col">
                        <div className="p-4 border-b border-gray-700">
                            <h3 className="text-lg font-semibold">Notes & Highlights</h3>
                            <p className="text-sm text-gray-400 mt-1">
                                {notes.length} notes • {highlights.length} highlights
                            </p>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {/* Recent Notes */}
                            {notes.slice().reverse().slice(0, 10).map((note) => (
                                <div key={note.id} className="bg-gray-700 rounded p-3">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs text-gray-400">Page {note.page_number}</span>
                                        <div className={`w-3 h-3 rounded-full bg-${note.color}-400`}></div>
                                    </div>
                                    <p className="text-sm">{note.note_text}</p>
                                    {note.selected_text && (
                                        <p className="text-xs text-gray-400 mt-2 italic">
                                            "{note.selected_text}"
                                        </p>
                                    )}
                                </div>
                            ))}

                            {/* Recent Highlights */}
                            {highlights.slice().reverse().slice(0, 5).map((highlight) => (
                                <div key={highlight.id} className="bg-gray-700 rounded p-3">
                                    <div className="flex items-center justify-between mb-2">
                                        <span className="text-xs text-gray-400">Page {highlight.page_number}</span>
                                        <div className={`w-3 h-3 rounded-full bg-${highlight.color}-400`}></div>
                                    </div>
                                    <p className="text-sm italic">"{highlight.highlighted_text}"</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Note Creation Modal */}
            {noteModalOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-gray-800 rounded-lg p-6 w-96 max-w-md">
                        <h3 className="text-lg font-semibold mb-4">
                            {currentSelection ? 'Add Note to Selected Text' : 'Add Note'}
                        </h3>

                        {/* Show selected text if available */}
                        {currentSelection && (
                            <div className="mb-4 p-3 bg-gray-700 rounded border-l-4 border-blue-500">
                                <p className="text-xs text-gray-400 mb-1">Selected text:</p>
                                <p className="text-sm italic text-gray-300">
                                    "{currentSelection.text}"
                                </p>
                            </div>
                        )}

                        <textarea
                            value={newNoteText}
                            onChange={(e) => setNewNoteText(e.target.value)}
                            placeholder={currentSelection ? "Add your note about this text..." : "Enter your note..."}
                            className="w-full h-32 p-3 bg-gray-700 border border-gray-600 rounded resize-none focus:border-blue-500 focus:outline-none"
                            autoFocus
                        />

                        <div className="flex justify-end space-x-3 mt-4">
                            <button
                                onClick={() => {
                                    setNoteModalOpen(false);
                                    setNewNoteText('');
                                    setSelectedTool('none');
                                    setCurrentSelection(null);
                                    // Clear text selection
                                    window.getSelection()?.removeAllRanges();
                                }}
                                className="px-4 py-2 bg-gray-600 rounded hover:bg-gray-500 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={createNote}
                                disabled={!newNoteText.trim()}
                                className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                Add Note
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PDFBookReader; 