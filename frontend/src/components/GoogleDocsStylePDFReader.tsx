'use client';

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, BookOpen, MessageSquare, Plus, X, Edit3, Eye, ZoomIn, ZoomOut, RotateCcw, Trash2, GripVertical, HelpCircle, ArrowRight, CheckCircle } from 'lucide-react';
import axios from 'axios';
import { useAuth } from '@/context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import toast from '@/components/ui/sound-toast';
import originalToast from 'react-hot-toast';
import { GiBrain } from 'react-icons/gi';
import { FaSearch } from 'react-icons/fa';
import KnowledgeChatPanel from './KnowledgeChatPanel';

// Simple debounce function
function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  
  return function(...args: Parameters<T>) {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Configure PDF.js worker
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

interface Comment {
	id: number;
	text: string;
	author: string;
	timestamp: string;
	page_number: number;
	selected_text: string;
	position: {
		x: number;
		y: number;
		width: number;
		height: number;
	};
	thread_id?: string;
	resolved: boolean;
}

interface TextSelectionInfo {
	text: string;
	rect: DOMRect;
	range: Range;
	pageNumber: number;
	isValid: boolean;
}

interface HelpTopic {
	id: string;
	title: string;
	description: string;
	icon: React.ReactNode;
}

const GoogleDocsStylePDFReader: React.FC = () => {
	const { user } = useAuth();
	const [userBookCopy, setUserBookCopy] = useState<UserBookCopy | null>(null);
	const [progress, setProgress] = useState<ReadingProgress | null>(null);
	const [comments, setComments] = useState<Comment[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	// PDF state
	const [numPages, setNumPages] = useState<number>(0);
	const [currentPage, setCurrentPage] = useState(1);
	const [scale, setScale] = useState(1.0);
	// Add page input value state here, with the other state declarations
	const [pageInputValue, setPageInputValue] = useState<string>("1");

	// Selection and commenting state
	const [selectedText, setSelectedText] = useState<TextSelectionInfo | null>(null);
	const [showCommentPopover, setShowCommentPopover] = useState(false);
	const [showCommentModal, setShowCommentModal] = useState(false);
	const [newCommentText, setNewCommentText] = useState('');
	const [showCommentsPanel, setShowCommentsPanel] = useState(false); // Changed to false by default on mobile
	const [isSelecting, setIsSelecting] = useState(false);
	const [selectionLocked, setSelectionLocked] = useState(false);
	const [isAddingComment, setIsAddingComment] = useState(false);
	
	// How It Works help section state
	const [showHelpOverlay, setShowHelpOverlay] = useState(false);
	const [currentHelpTopic, setCurrentHelpTopic] = useState<string>('navigation');
	
	// Define help topics
	const helpTopics: HelpTopic[] = [
		{
			id: 'navigation',
			title: 'Navigation & Controls',
			description: 'Navigate through pages using the arrow buttons, page slider, or keyboard shortcuts (← → arrows, Page Up/Down). Zoom with the + and - buttons, or use Ctrl/Cmd + mouse wheel. Press Ctrl/Cmd+0 to reset zoom.',
			icon: <ChevronRight className="w-5 h-5 text-blue-400" />
		},
		{
			id: 'commenting',
			title: 'Adding Comments',
			description: 'Select any text in the document to add comments. A popup will appear allowing you to create a comment. Your comments are saved to your personal knowledge base for future reference.',
			icon: <MessageSquare className="w-5 h-5 text-green-400" />
		},
		{
			id: 'search',
			title: 'Knowledge Search',
			description: 'Use the search tab in the sidebar to find content across all your books and notes. The search uses AI to find relevant information even if your query doesn\'t match the exact wording.',
			icon: <FaSearch className="w-5 h-5 text-purple-400" />
		},
		{
			id: 'chat',
			title: 'Book Chat',
			description: 'Chat with your book using the Chat tab in the sidebar. Ask questions about the content, request summaries, or explore related topics. The AI uses your highlights and notes for context.',
			icon: <GiBrain className="w-5 h-5 text-amber-400" />
		},
		{
			id: 'shortcuts',
			title: 'Keyboard Shortcuts',
			description: 'Arrow Keys: Navigate pages\nSpace: Next page\nHome/End: First/Last page\nCtrl/Cmd + +/-: Zoom in/out\nCtrl/Cmd + 0: Reset zoom\nCtrl/Cmd + Arrow Keys: Jump to first/last page',
			icon: <Edit3 className="w-5 h-5 text-red-400" />
		}
	];
	
	// Responsive state
	const [isMobile, setIsMobile] = useState(false);
	const [isTablet, setIsTablet] = useState(false);

	// Page slider state
	const [isDraggingSlider, setIsDraggingSlider] = useState(false);
	const [sliderValue, setSliderValue] = useState(1);
	const [showPagePreview, setShowPagePreview] = useState(false);
	const [previewPage, setPreviewPage] = useState(1);

	// Knowledge base search state
	const [knowledgeSearchQuery, setKnowledgeSearchQuery] = useState('');
	const [knowledgeSearchResults, setKnowledgeSearchResults] = useState<any[]>([]);
	const [knowledgeSearchLoading, setKnowledgeSearchLoading] = useState(false);
	const [showKnowledgeSearch, setShowKnowledgeSearch] = useState(false);
	const [activeTab, setActiveTab] = useState<'comments' | 'knowledge' | 'chat'>('comments');
	
	// Resizable panel state
	const [panelWidth, setPanelWidth] = useState<number>(320); // Default width of 320px (w-80)
	const [isResizing, setIsResizing] = useState<boolean>(false);
	const resizeRef = useRef<HTMLDivElement>(null);
	const panelRef = useRef<HTMLDivElement>(null);

	// Comments pagination state
	const [commentsCurrentPage, setCommentsCurrentPage] = useState(1);
	const [commentsPerPage] = useState(5); // Fixed number of comments per page
	const [knowledgeCurrentPage, setKnowledgeCurrentPage] = useState(1);
	const [knowledgePerPage] = useState(5); // Fixed number of knowledge results per page

	// Debug logging for state changes
	useEffect(() => {
		console.log('🎯 Modal state changed:', showCommentModal);
		if (showCommentModal) {
			console.log('✅ Modal opened');
		} else {
			console.log('❌ Modal closed');
		}
	}, [showCommentModal]);

	// Lock selection processing when modal opens
	useEffect(() => {
		if (showCommentModal) {
			setSelectionLocked(true);
			setShowCommentPopover(false); // Hide popover when modal opens
			console.log('🔒 Selection locked - modal is open');
		} else {
			// Unlock after a delay to ensure clean state
			setTimeout(() => {
				setSelectionLocked(false);
				console.log('🔓 Selection unlocked - modal is closed');
			}, 300);
		}
	}, [showCommentModal]);

	useEffect(() => {
		console.log('💬 Popover state changed:', showCommentPopover);
	}, [showCommentPopover]);

	useEffect(() => {
		console.log('📝 Selected text changed:', selectedText ? `"${selectedText.text.substring(0, 30)}..."` : 'null');
	}, [selectedText]);

	// Progress tracking
	// const [readingStartTime, setReadingStartTime] = useState<Date | null>(null); // Reading time tracking removed
	const [progressSaving, setProgressSaving] = useState(false);

	// Refs
	const documentRef = useRef<HTMLDivElement>(null);
	const selectionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
	const progressSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
	const popoverRef = useRef<HTMLDivElement>(null);
	const lastSelectionRef = useRef<string>('');
	const modalOpenTimeRef = useRef<number>(0);

	const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

	// Memoized values
	const liveProgressPercentage = useMemo(() =>
		numPages > 0 ? (currentPage / numPages) * 100 : 0
		, [currentPage, numPages]);

	// Reading time calculations removed
	const sessionReadingTime = 0; // Placeholder to avoid errors
	const totalReadingTime = 0; // Placeholder to avoid errors

	// Initialize PDF and load data
	useEffect(() => {
		initializeBook();
	}, []);

	// Sync slider with current page
	useEffect(() => {
		if (!isDraggingSlider) {
			setSliderValue(currentPage);
		}
	}, [currentPage, isDraggingSlider]);

	// Sync page input value with current page
	useEffect(() => {
		setPageInputValue(currentPage.toString());
	}, [currentPage]);

	// Enhanced text selection handling
	useEffect(() => {
		const handleMouseDown = (event: MouseEvent) => {
			// Skip if selection is locked (modal is open)
			if (selectionLocked) {
				console.log('🔒 Selection locked, skipping mousedown');
				return;
			}

			// Check if click is within PDF viewer
			if (documentRef.current?.contains(event.target as Node)) {
				setIsSelecting(true);
				setShowCommentPopover(false);
				setSelectedText(null);
			}
		};

		const handleMouseUp = () => {
			// Skip if selection is locked (modal is open)
			if (selectionLocked) {
				console.log('🔒 Selection locked, skipping mouseup');
				return;
			}

			if (isSelecting) {
				setIsSelecting(false);
				// Small delay to ensure selection is complete
				setTimeout(() => {
					handleTextSelection();
				}, 50);
			}
		};

		const handleSelectionChange = () => {
			// Skip if selection is locked (modal is open)
			if (selectionLocked) {
				console.log('🔒 Selection locked, skipping selectionchange');
				return;
			}

			if (selectionTimeoutRef.current) {
				clearTimeout(selectionTimeoutRef.current);
			}

			// Only process selection if we're not currently selecting
			if (!isSelecting) {
				selectionTimeoutRef.current = setTimeout(() => {
					handleTextSelection();
				}, 200);
			}
		};

		// Handle clicks outside to hide popover (but not modal)
		const handleClickOutside = (event: MouseEvent) => {
			const target = event.target as Node;

			// Don't close if clicking on modal or its children
			if (showCommentModal) {
				// Prevent closing modal if it was just opened (within 500ms)
				if (Date.now() - modalOpenTimeRef.current < 500) {
					console.log('🔒 Modal just opened, preventing close');
					return;
				}
				// Don't reset selection state while modal is open
				console.log('🔒 Modal is open, preserving selection state');
				return;
			}

			// Don't close if clicking on popover or its children
			if (popoverRef.current && popoverRef.current.contains(target)) return;

			// Don't close if clicking on comment indicators
			if ((target as Element).closest('.comment-indicator')) return;

			// Only close if clicking truly outside
			if (popoverRef.current && !popoverRef.current.contains(target)) {
				setShowCommentPopover(false);
				setSelectedText(null);
			}
		};

		document.addEventListener('mousedown', handleMouseDown);
		document.addEventListener('mouseup', handleMouseUp);
		document.addEventListener('selectionchange', handleSelectionChange);
		document.addEventListener('mousedown', handleClickOutside);

		return () => {
			document.removeEventListener('mousedown', handleMouseDown);
			document.removeEventListener('mouseup', handleMouseUp);
			document.removeEventListener('selectionchange', handleSelectionChange);
			document.removeEventListener('mousedown', handleClickOutside);
			if (selectionTimeoutRef.current) {
				clearTimeout(selectionTimeoutRef.current);
			}
		};
	}, [isSelecting, showCommentModal, selectionLocked]);

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
			// setReadingStartTime(new Date()); // Reading time tracking removed

			// Check if user is authenticated
			if (!user) {
				throw new Error('Please log in to access book reading features');
			}

			// Get user's personal book copy (authenticated endpoint)
			const bookCopyResponse = await axios.get(`${apiUrl}/api/user-books/copy?title=The Way of the Dog Anahata&type=public`, {
				withCredentials: true  // Include authentication cookies
			});

			if (!bookCopyResponse.data.success) {
				throw new Error('Failed to get book copy');
			}

			const bookCopy = bookCopyResponse.data.book_copy;
			setUserBookCopy(bookCopy);

			console.log(`✅ Book copy loaded for user ${user.id}:`, bookCopy.id);

			// Load progress and comments (user-specific)
			await Promise.all([
				loadProgress(bookCopy.id),
				loadComments(bookCopy.id)
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
			const response = await axios.get(`${apiUrl}/api/user-books/progress/${bookCopyId}`, {
				withCredentials: true  // Include authentication cookies
			});
			if (response.data.success) {
				const savedProgress = response.data.progress;
				
				// Debug log to identify potential issues (reading time validation removed)
				console.log('📊 Progress data loaded:', {
					current_page: savedProgress.current_page,
					total_pages: savedProgress.total_pages
				});
				
				// Reading time validation removed
				
				setProgress(savedProgress);

				if (savedProgress.current_page && savedProgress.current_page > 1) {
					setCurrentPage(savedProgress.current_page);
				}
				if (savedProgress.pdf_zoom_level) {
					setScale(savedProgress.pdf_zoom_level);
				}

				console.log(`📊 Progress loaded for user ${user?.id}:`, savedProgress);
			}
		} catch (err) {
			console.error('Error loading progress:', err);
		}
	};

	const loadComments = async (bookCopyId: number) => {
		try {
			const response = await axios.get(`${apiUrl}/api/user-books/notes/${bookCopyId}`, {
				withCredentials: true  // Include authentication cookies
			});
			if (response.data.success) {
				// Transform notes to comments format
				const transformedComments = response.data.notes.map((note: any) => {
					const coordinates = note.pdf_coordinates || { x: 50, y: 50, width: 100, height: 20 };

					console.log('📥 Loading user-specific comment from DB:', {
						id: note.id,
						coordinates: coordinates,
						page: note.page_number,
						userId: user?.id
					});

					return {
						id: note.id,
						text: note.note_text,
						author: user?.name || 'Anonymous',
						timestamp: note.created_at,
						page_number: note.page_number,
						selected_text: note.selected_text || '',
						position: {
							x: coordinates.x,
							y: coordinates.y,
							width: coordinates.width,
							height: coordinates.height
						},
						resolved: false
					};
				});

				// Sort comments by timestamp (newest first)
				const sortedComments = transformedComments.sort((a: Comment, b: Comment) => {
					return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
				});

				setComments(sortedComments);
				setCommentsCurrentPage(1); // Reset to first page when loading comments
				console.log(`✅ Loaded ${sortedComments.length} user-specific comments for user ${user?.id}:`, sortedComments);
			}
		} catch (err) {
			console.error('Error loading comments:', err);
		}
	};

	const isValidSelection = (selection: Selection, text: string): boolean => {
		// Check if selection is valid
		if (!selection || !text || text.trim().length < 2) return false;

		// Check if selection is within our PDF viewer
		const range = selection.getRangeAt(0);
		if (!documentRef.current?.contains(range.commonAncestorContainer)) return false;

		// Check if text is the same as last selection (avoid duplicate triggers)
		if (text === lastSelectionRef.current) return false;

		// Check if selection spans too many lines (likely accidental)
		const lines = text.split('\n').filter(line => line.trim().length > 0);
		if (lines.length > 3) return false;

		// Check for excessive whitespace (likely accidental selection)
		const whitespaceRatio = (text.length - text.replace(/\s/g, '').length) / text.length;
		if (whitespaceRatio > 0.5) return false;

		return true;
	};

	const cleanSelectionText = (text: string): string => {
		// Remove excessive whitespace and clean up the text
		return text
			.replace(/\s+/g, ' ')
			.replace(/^\s+|\s+$/g, '')
			.replace(/\n\s*/g, ' ')
			.trim();
	};

	const handleTextSelection = useCallback(() => {
		// Don't process selection if locked (modal is open)
		if (selectionLocked) {
			console.log('🔒 Selection processing locked, skipping');
			return;
		}

		const selection = window.getSelection();

		if (!selection || selection.rangeCount === 0) {
			setShowCommentPopover(false);
			setSelectedText(null);
			lastSelectionRef.current = '';
			return;
		}

		const rawText = selection.toString();
		const cleanedText = cleanSelectionText(rawText);

		if (!isValidSelection(selection, cleanedText)) {
			setShowCommentPopover(false);
			setSelectedText(null);
			return;
		}

		const range = selection.getRangeAt(0);
		const rect = range.getBoundingClientRect();

		// Check if rect is valid (not zero width/height)
		if (rect.width === 0 || rect.height === 0) {
			return;
		}

		// Find which page the selection is on
		const pageElement = range.startContainer.parentElement?.closest('[data-page-number]');
		const pageNumber = pageElement ? parseInt(pageElement.getAttribute('data-page-number') || '1') : currentPage;

		const selectionInfo: TextSelectionInfo = {
			text: cleanedText,
			rect,
			range,
			pageNumber,
			isValid: true
		};

		lastSelectionRef.current = cleanedText;
		setSelectedText(selectionInfo);
		setShowCommentPopover(true);
		console.log('✅ Selection processed:', cleanedText.substring(0, 30) + '...');
	}, [currentPage, selectionLocked]);

	const createComment = async () => {
		if (!userBookCopy || !selectedText || !newCommentText.trim() || isAddingComment) return;

		try {
			setIsAddingComment(true);
			
			// Get PDF page element to calculate relative coordinates
			const pageElement = document.querySelector(`[data-page-number="${selectedText.pageNumber}"]`);
			const pdfContainer = pageElement?.closest('.react-pdf__Page');

			let relativeX = selectedText.rect.left;
			let relativeY = selectedText.rect.top;

			// Convert to PDF-relative coordinates
			if (pdfContainer) {
				const containerRect = pdfContainer.getBoundingClientRect();
				relativeX = selectedText.rect.left - containerRect.left;
				relativeY = selectedText.rect.top - containerRect.top;
			}

			console.log('💾 Creating user-specific comment with coordinates:', {
				screen: { x: selectedText.rect.left, y: selectedText.rect.top },
				relative: { x: relativeX, y: relativeY },
				scale: scale,
				userId: user?.id
			});

			const response = await axios.post(`${apiUrl}/api/user-books/notes`, {
				book_copy_id: userBookCopy.id,
				note_text: newCommentText,
				note_type: 'comment',
				color: 'blue',
				page_number: selectedText.pageNumber,
				selected_text: selectedText.text,
				pdf_coordinates: {
					x: relativeX / scale, // Store unscaled coordinates
					y: relativeY / scale,
					width: selectedText.rect.width / scale,
					height: selectedText.rect.height / scale
				}
			}, {
				withCredentials: true  // Include authentication cookies
			});

			if (response.data.success) {
				const newComment: Comment = {
					id: response.data.note.id,
					text: newCommentText,
					author: user?.name || 'Anonymous',
					timestamp: new Date().toISOString(),
					page_number: selectedText.pageNumber,
					selected_text: selectedText.text,
					position: {
						x: relativeX / scale, // Store unscaled coordinates
						y: relativeY / scale,
						width: selectedText.rect.width / scale,
						height: selectedText.rect.height / scale
					},
					resolved: false
				};

				// Add new comment at the beginning of the array (newest first)
				setComments(prev => [newComment, ...prev]);
				console.log(`✅ User-specific comment created successfully for user ${user?.id}:`, newComment);

				// Show success message indicating knowledge base integration
				const successMessage = response.data.message || 'Comment created successfully and added to knowledge base';
				if (successMessage.includes('knowledge base')) {
					console.log('🧠 Comment saved to user knowledge base for future search');
				}

				// Reset state
				setNewCommentText('');
				setShowCommentModal(false);
				setShowCommentPopover(false);

				// Clear selection
				window.getSelection()?.removeAllRanges();
				setSelectedText(null);
				lastSelectionRef.current = '';
			}
		} catch (error) {
			console.error('Error creating comment:', error);
			if (axios.isAxiosError(error) && error.response?.status === 401) {
				setError('Please log in to create comments');
			}
		} finally {
			setIsAddingComment(false);
		}
	};

	const debouncedSaveProgress = useCallback((page: number, zoom: number) => {
		if (progressSaveTimeoutRef.current) {
			clearTimeout(progressSaveTimeoutRef.current);
		}

		progressSaveTimeoutRef.current = setTimeout(async () => {
			if (!userBookCopy || !user) return;

			setProgressSaving(true);
			try {
				const progressPercentage = numPages > 0 ? (page / numPages) * 100 : 0;
				
				// Reading time calculation removed
				
				await axios.put(`${apiUrl}/api/user-books/progress/${userBookCopy.id}`, {
					current_page: page,
					total_pages: numPages,
					progress_percentage: progressPercentage,
					pdf_zoom_level: zoom,
					// reading_time_minutes: validatedReadingTime, // Reading time removed
					last_read_at: new Date().toISOString()
				}, {
					withCredentials: true  // Include authentication cookies
				});

				console.log(`📊 Progress saved for user ${user.id}: page ${page}`);
			} catch (err) {
				console.error('Error saving progress:', err);
			} finally {
				setProgressSaving(false);
			}
		}, 1000);
	}, [userBookCopy, numPages, apiUrl, user]);

	const goToPage = (page: number) => {
		if (page < 1 || page > numPages) return;
		setCurrentPage(page);
		debouncedSaveProgress(page, scale);

		// Clear any existing selection when changing pages
		window.getSelection()?.removeAllRanges();
		setSelectedText(null);
		setShowCommentPopover(false);
		lastSelectionRef.current = '';
	};

	const handleZoomIn = () => {
		const newScale = Math.min(scale + 0.2, 3.0); // Max zoom 300%
		setScale(newScale);
		debouncedSaveProgress(currentPage, newScale);

		// Clear any existing selection when zooming
		window.getSelection()?.removeAllRanges();
		setSelectedText(null);
		setShowCommentPopover(false);
		lastSelectionRef.current = '';
	};

	const handleZoomOut = () => {
		const newScale = Math.max(scale - 0.2, 0.5); // Min zoom 50%
		setScale(newScale);
		debouncedSaveProgress(currentPage, newScale);

		// Clear any existing selection when zooming
		window.getSelection()?.removeAllRanges();
		setSelectedText(null);
		setShowCommentPopover(false);
		lastSelectionRef.current = '';
	};

	const resetZoom = () => {
		const defaultScale = 1.0;
		setScale(defaultScale);
		debouncedSaveProgress(currentPage, defaultScale);

		// Clear any existing selection when resetting zoom
		window.getSelection()?.removeAllRanges();
		setSelectedText(null);
		setShowCommentPopover(false);
		lastSelectionRef.current = '';
	};

	// Keyboard shortcuts for navigation and zoom
	useEffect(() => {
		const handleKeyDown = (event: KeyboardEvent) => {
			// Check if user is not typing in an input field
			if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
				return;
			}

			// Navigation shortcuts (without modifier keys)
			if (!event.ctrlKey && !event.metaKey && !event.altKey) {
				switch (event.key) {
					case 'ArrowLeft':
					case 'PageUp':
						event.preventDefault();
						if (currentPage > 1) goToPage(currentPage - 1);
						break;
					case 'ArrowRight':
					case 'PageDown':
					case ' ': // Spacebar
						event.preventDefault();
						if (currentPage < numPages) goToPage(currentPage + 1);
						break;
					case 'Home':
						event.preventDefault();
						goToPage(1);
						break;
					case 'End':
						event.preventDefault();
						goToPage(numPages);
						break;
				}
			}

			// Zoom shortcuts
			if (event.ctrlKey || event.metaKey) {
				switch (event.key) {
					case '=':
					case '+':
						event.preventDefault();
						handleZoomIn();
						break;
					case '-':
						event.preventDefault();
						handleZoomOut();
						break;
					case '0':
						event.preventDefault();
						resetZoom();
						break;
					// Navigation shortcuts with modifier
					case 'ArrowLeft':
						event.preventDefault();
						goToPage(1); // Go to first page
						break;
					case 'ArrowRight':
						event.preventDefault();
						goToPage(numPages); // Go to last page
						break;
				}
			}
		};

		document.addEventListener('keydown', handleKeyDown);
		return () => {
			document.removeEventListener('keydown', handleKeyDown);
		};
	}, [currentPage, numPages, goToPage]); // Only include stable dependencies

	// Mouse wheel zoom support
	useEffect(() => {
		const handleWheel = (event: WheelEvent) => {
			// Only zoom when Ctrl/Cmd is held down
			if (event.ctrlKey || event.metaKey) {
				event.preventDefault();

				// Check if the event is over the PDF viewer
				if (documentRef.current?.contains(event.target as Node)) {
					const delta = event.deltaY > 0 ? -0.1 : 0.1; // Smaller increments for smoother zooming
					const newScale = Math.max(0.5, Math.min(3.0, scale + delta));

					if (newScale !== scale) {
						setScale(newScale);
						debouncedSaveProgress(currentPage, newScale);

						// Clear selection when zooming
						window.getSelection()?.removeAllRanges();
						setSelectedText(null);
						setShowCommentPopover(false);
						lastSelectionRef.current = '';
					}
				}
			}
		};

		document.addEventListener('wheel', handleWheel, { passive: false });
		return () => {
			document.removeEventListener('wheel', handleWheel);
		};
	}, [scale, currentPage, debouncedSaveProgress]);

	// Page slider handlers
	const handleSliderChange = (value: number) => {
		setSliderValue(value);
		setPreviewPage(value);
		if (!isDraggingSlider) {
			setShowPagePreview(true);
			// Hide preview after a short delay if not dragging
			setTimeout(() => {
				if (!isDraggingSlider) {
					setShowPagePreview(false);
				}
			}, 1500);
		}
	};

	const handleSliderMouseDown = () => {
		setIsDraggingSlider(true);
		setShowPagePreview(true);
	};

	const handleSliderMouseUp = () => {
		setIsDraggingSlider(false);
		if (sliderValue !== currentPage && sliderValue >= 1 && sliderValue <= numPages) {
			goToPage(sliderValue);
		}
		// Hide preview after navigation
		setTimeout(() => setShowPagePreview(false), 300);
	};

	const handleSliderKeyDown = (event: React.KeyboardEvent) => {
		if (event.key === 'Enter') {
			event.preventDefault();
			if (sliderValue !== currentPage && sliderValue >= 1 && sliderValue <= numPages) {
				goToPage(sliderValue);
			}
		}
	};

	// Knowledge base search function
	const searchKnowledgeBase = async (query: string) => {
		if (!query.trim()) return;

		// Clear previous results before starting new search
		setKnowledgeSearchResults([]);
		setKnowledgeSearchLoading(true);
		try {
			const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
			const response = await axios.post(`${apiUrl}/api/user-books/search`, {
				query: query,
				top_k: 10
			}, {
				withCredentials: true
			});

			if (response.data.success) {
				// Process the actual results from Pinecone
				const results = response.data.results?.matches || [];

				// Transform results for display
				const formattedResults = results.map((result: any) => ({
					id: result.id,
					text: result.text || result.metadata?.text || '',
					book_title: result.metadata?.book_title || 'Unknown Book',
					page_number: result.metadata?.page_number || 'N/A',
					content_type: result.metadata?.content_type || 'note',
					note_type: result.metadata?.note_type || 'note',
					score: result.score || 0
				}));

				setKnowledgeSearchResults(formattedResults);
				setKnowledgeCurrentPage(1); // Reset to first page on new search
				console.log(`🔍 Found ${formattedResults.length} results in knowledge base`);

				if (formattedResults.length === 0) {
					originalToast.success('No results found. Try different keywords or create more notes.');
				}
			} else {
				setKnowledgeSearchResults([]);
				setKnowledgeCurrentPage(1);
				toast.error(response.data.message || 'Search failed');
			}
		} catch (error) {
			console.error('Error searching knowledge base:', error);
			setKnowledgeSearchResults([]);
			setKnowledgeCurrentPage(1);
			toast.error('Failed to search knowledge base');
		} finally {
			setKnowledgeSearchLoading(false);
		}
	};

	const goToComment = (comment: Comment) => {
		if (comment.page_number !== currentPage) {
			setCurrentPage(comment.page_number);
		}
		// Hide comments panel on mobile after navigation
		if (window.innerWidth < 768) {
			setShowCommentsPanel(false);
		}
	};

	const deleteComment = async (commentId: number) => {
		try {
			const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
			const response = await axios.delete(`${apiUrl}/api/user-books/notes/${commentId}`, {
				withCredentials: true
			});

			if (response.data.success) {
				setComments(prev => prev.filter(comment => comment.id !== commentId));
				toast.success('Comment deleted successfully');
			} else {
				toast.error('Failed to delete comment');
			}
		} catch (error) {
			console.error('Error deleting comment:', error);
			toast.error('Failed to delete comment');
		}
	};

	// Pagination utility functions
	const paginateArray = (array: any[], page: number, perPage: number) => {
		// Ensure array is actually an array
		if (!Array.isArray(array)) {
			console.error('Expected array for pagination but got:', typeof array);
			return [];
		}
		const startIndex = (page - 1) * perPage;
		const endIndex = startIndex + perPage;
		return array.slice(startIndex, endIndex);
	};

	const getTotalPages = (totalItems: number, perPage: number) => {
		return Math.ceil(totalItems / perPage);
	};

	// Comments pagination calculations
	// No need to reverse since comments are already sorted newest first
	const totalCommentsPages = getTotalPages(comments.length, commentsPerPage);
	const paginatedComments = paginateArray(comments, commentsCurrentPage, commentsPerPage);

	// Knowledge results pagination calculations
	const totalKnowledgePages = getTotalPages(knowledgeSearchResults.length, knowledgePerPage);
	const paginatedKnowledgeResults = paginateArray(knowledgeSearchResults, knowledgeCurrentPage, knowledgePerPage);

	// Reset pagination when switching tabs
	const handleTabSwitch = (showKnowledge: boolean) => {
		setShowKnowledgeSearch(showKnowledge);
		if (showKnowledge) {
			setKnowledgeCurrentPage(1);
		} else {
			setCommentsCurrentPage(1);
		}
	};
	
	// Handle tab changes
	useEffect(() => {
		// Clear knowledge search results when switching away from knowledge tab
		if (activeTab !== 'knowledge') {
			setKnowledgeSearchResults([]);
		}
	}, [activeTab]);
	
	// Debounced function to save panel width to localStorage
	const debouncedSaveWidth = useCallback(
		debounce((width: number) => {
			localStorage.setItem('commentsPanelWidth', width.toString());
		}, 300),
		[]
	);
	
	// Load saved panel width from localStorage on component mount
	useEffect(() => {
		const savedWidth = localStorage.getItem('commentsPanelWidth');
		if (savedWidth) {
			setPanelWidth(Number(savedWidth));
		}
	}, []);
	
	// Handle panel resize start
	const handleResizeStart = (e: React.MouseEvent) => {
		e.preventDefault();
		setIsResizing(true);
		document.addEventListener('mousemove', handleResizeMove);
		document.addEventListener('mouseup', handleResizeEnd);
	};
	
	// Handle panel resize move
	const handleResizeMove = useCallback((e: MouseEvent) => {
		if (!isResizing || !panelRef.current) return;
		
		// Use direct DOM manipulation for smoother resizing
		// Calculate new width based on mouse position
		const newWidth = window.innerWidth - e.clientX;
		
		// Constrain width between min and max values
		// For tablet, use a narrower range to prevent sidebar from taking too much space
		const minWidth = isTablet ? 280 : 280;
		const maxWidth = isTablet ? 400 : 600;
		const constrainedWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));
		
		// Apply width directly to the DOM element
		panelRef.current.style.width = `${constrainedWidth}px`;
	}, [isResizing, isTablet]);
	
	// Handle panel resize end
	const handleResizeEnd = useCallback(() => {
		if (!panelRef.current) return;
		
		// Get the final width from the DOM element
		const finalWidth = panelRef.current.offsetWidth;
		
		// Update state with the final width
		setPanelWidth(finalWidth);
		
		// Save the width preference to localStorage using debounced function
		debouncedSaveWidth(finalWidth);
		
		// Clean up
		setIsResizing(false);
		document.removeEventListener('mousemove', handleResizeMove);
		document.removeEventListener('mouseup', handleResizeEnd);
	}, [handleResizeMove, debouncedSaveWidth]);
	
	// Clean up event listeners when component unmounts
	useEffect(() => {
		return () => {
			document.removeEventListener('mousemove', handleResizeMove);
			document.removeEventListener('mouseup', handleResizeEnd);
		};
	}, [handleResizeMove, handleResizeEnd]);

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

	// Pagination Component
	const PaginationControls = ({
		currentPage,
		totalPages,
		onPageChange,
		itemType = 'items',
		totalItems = 0,
		itemsPerPage = 5
	}: {
		currentPage: number;
		totalPages: number;
		onPageChange: (page: number) => void;
		itemType?: string;
		totalItems?: number;
		itemsPerPage?: number;
	}) => {
		if (totalPages <= 1) return null;

		const startItem = (currentPage - 1) * itemsPerPage + 1;
		const endItem = Math.min(currentPage * itemsPerPage, totalItems);

		return (
			<div className="flex flex-col sm:flex-row items-center justify-between px-4 py-3 border-t border-gray-700 pagination-controls">
				<div className="text-xs text-gray-400">
					{totalItems > 0 ? `${startItem}-${endItem} of ${totalItems} ${itemType}` : `Page ${currentPage} of ${totalPages}`}
				</div>

				<div className="flex items-center space-x-2">
					<motion.button
						onClick={() => onPageChange(currentPage - 1)}
						disabled={currentPage <= 1}
						className="px-2 py-1 text-xs bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
						whileHover={currentPage > 1 ? { scale: 1.05 } : {}}
						whileTap={currentPage > 1 ? { scale: 0.95 } : {}}
					>
						←
					</motion.button>

					{/* Page Numbers */}
					<div className="flex items-center space-x-1">
						{Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
							let pageNum;
							if (totalPages <= 5) {
								pageNum = i + 1;
							} else if (currentPage <= 3) {
								pageNum = i + 1;
							} else if (currentPage >= totalPages - 2) {
								pageNum = totalPages - 4 + i;
							} else {
								pageNum = currentPage - 2 + i;
							}

							return (
								<motion.button
									key={pageNum}
									onClick={() => onPageChange(pageNum)}
									className={`px-2 py-1 text-xs rounded transition-colors ${pageNum === currentPage
										? 'bg-blue-600 text-white'
										: 'bg-gray-700 hover:bg-gray-600 text-gray-300'
										}`}
									whileHover={{ scale: 1.05 }}
									whileTap={{ scale: 0.95 }}
								>
									{pageNum}
								</motion.button>
							);
						})}
					</div>

					<motion.button
						onClick={() => onPageChange(currentPage + 1)}
						disabled={currentPage >= totalPages}
						className="px-2 py-1 text-xs bg-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
						whileHover={currentPage < totalPages ? { scale: 1.05 } : {}}
						whileTap={currentPage < totalPages ? { scale: 0.95 } : {}}
					>
						→
					</motion.button>
				</div>
			</div>
		);
	};

	// Add responsive detection
	useEffect(() => {
		const handleResize = () => {
			setIsMobile(window.innerWidth < 640);
			setIsTablet(window.innerWidth >= 640 && window.innerWidth < 1024);
			
			// Auto-hide comments panel on mobile
			if (window.innerWidth < 640) {
				setShowCommentsPanel(false);
			}
			
			// Adjust panel width based on screen size
			if (window.innerWidth >= 640 && window.innerWidth < 1024) {
				// For tablet, use a fixed width that fits well
				setPanelWidth(320);
			} else if (window.innerWidth >= 1024) {
				// For desktop, use the stored width preference or default
				const savedWidth = localStorage.getItem('commentsPanelWidth');
				if (savedWidth) {
					setPanelWidth(Number(savedWidth));
				} else {
					setPanelWidth(320); // Default width if no preference is stored
				}
			}
		};
		
		// Initial check
		handleResize();
		
		// Add event listener
		window.addEventListener('resize', handleResize);
		
		// Cleanup
		return () => {
			window.removeEventListener('resize', handleResize);
		};
	}, []);

	// Show authentication required if user is not logged in
	if (!user) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-gray-900 text-white">
				<motion.div
					className="text-center space-y-4"
					initial={{ opacity: 0, scale: 0.8 }}
					animate={{ opacity: 1, scale: 1 }}
					transition={{ duration: 0.5 }}
				>
					<div className="text-amber-500 text-6xl">🔐</div>
					<h2 className="text-2xl font-bold text-amber-400">Authentication Required</h2>
					<p className="text-gray-400 max-w-md">Please log in to access book reading features and create personal comments.</p>
					<motion.button
						onClick={() => window.location.href = '/login'}
						className="bg-amber-600 text-white px-6 py-3 rounded-lg hover:bg-amber-700 transition-colors"
						whileHover={{ scale: 1.05 }}
						whileTap={{ scale: 0.95 }}
					>
						Go to Login
					</motion.button>
				</motion.div>
			</div>
		);
	}

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
					<h2 className="text-2xl font-bold">Loading your personal book...</h2>
					<motion.div
						className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto"
						animate={{ rotate: 360 }}
						transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
					/>
					<p className="text-gray-400">Setting up Google Docs-style commenting for {user.name}...</p>
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
		<div className={`min-h-screen bg-background text-white flex flex-col ${isResizing ? 'select-none resizing' : ''}`}>
			{/* Custom Slider Styles */}
			<style jsx>{`
                .slider-custom::-webkit-slider-thumb {
                    appearance: none;
                    height: 16px;
                    width: 16px;
                    border-radius: 50%;
                    background: #D3B86A;
                    cursor: pointer;
                    border: 2px solid #1e293b;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                    transition: all 0.2s ease;
                }
                
                .slider-custom::-webkit-slider-thumb:hover {
                    background: #D3B86A;
                    transform: scale(1.1);
                    box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
                }
                
                .slider-custom::-moz-range-thumb {
                    height: 16px;
                    width: 16px;
                    border-radius: 50%;
                    background: #3b82f6;
                    cursor: pointer;
                    border: 2px solid #1e293b;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                    transition: all 0.2s ease;
                }
                
                .slider-custom::-moz-range-thumb:hover {
                    background: #2563eb;
                    transform: scale(1.1);
                    box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
                }
                
                .slider-custom:focus {
                    outline: none;
                }
                
                .slider-custom:focus::-webkit-slider-thumb {
                    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
                }

                /* PDF Page Optimization */
                .react-pdf__Page {
                    max-width: 100%;
                    height: auto;
                }
                
                .react-pdf__Page__textContent {
                    top: 0 !important;
                    left: 0 !important;
                }
                
                /* Smooth transition for resizing */
                .resize-transition {
                    transition: width 0.05s linear;
                }
                
                /* Apply resize cursor only when actively resizing */
                .resizing * {
                    cursor: col-resize !important;
                }

                /* Responsive styles */
                @media (max-width: 640px) {
                    .header-content {
                        flex-direction: column;
                        align-items: flex-start;
                    }
                    
                    .zoom-controls {
                        margin-top: 0.5rem;
                    }
                    
                    .react-pdf__Page {
                        padding: 0;
                        margin: 0;
                    }
                    
                    .comment-popover {
                        max-width: 90vw;
                    }
                    
                    .modal-content {
                        width: 95% !important;
                        padding: 1rem !important;
                    }
                    
                    .pagination-controls {
                        flex-direction: column;
                        align-items: center;
                    }
                    
                    .pdf-container {
                        transform-origin: top center;
                        touch-action: pan-y pan-x;
                    }
                }
                
                /* Tablet styles */
                @media (min-width: 641px) and (max-width: 1023px) {
                    .comments-panel {
                        width: 320px !important; /* Force width for tablets */
                    }
                    
                    .pdf-container {
                        max-width: calc(100% - 16px);
                    }
                }
                
                /* Sidebar transition effects */
                .sidebar-enter {
                    transform: translateX(100%);
                    opacity: 0;
                }
                
                .sidebar-enter-active {
                    transform: translateX(0);
                    opacity: 1;
                    transition: transform 300ms, opacity 300ms;
                }
                
                .sidebar-exit {
                    transform: translateX(0);
                    opacity: 1;
                }
                
                .sidebar-exit-active {
                    transform: translateX(100%);
                    opacity: 0;
                    transition: transform 300ms, opacity 300ms;
                }
                
                /* Help overlay styles */
                .help-overlay {
                    backdrop-filter: blur(4px);
                }
                
                .help-topic-button {
                    transition: all 0.2s ease;
                }
                
                .help-topic-button:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
                
                .help-topic-button.active {
                    background-color: var(--mrwhite-primary-color);
                    color: black;
                }
                
                /* Responsive help overlay */
                @media (max-width: 640px) {
                    .help-content {
                        padding: 1rem !important;
                    }
                    
                    .help-navigation {
                        flex-direction: column;
                        gap: 0.5rem;
                    }
                    
                    .help-topic-list {
                        max-height: 200px;
                        overflow-y: auto;
                    }
                }
            `}</style>

			{/* Header */}
			<motion.header
				className="border-b border-gray-700 p-3 bg-gray-800/50 backdrop-blur-sm flex-shrink-0"
				initial={{ y: -100 }}
				animate={{ y: 0 }}
				transition={{ type: "spring", stiffness: 100 }}
			>
				<div className="flex flex-col sm:flex-row items-start sm:items-center justify-between space-y-2 sm:space-y-0 header-content">
					<div className="flex items-center space-x-4">
						<BookOpen className="w-6 h-6 text-blue-400" />

						<div className="flex flex-col">
							<h1 className="text-xl font-bold">The Way of the Dog</h1>
							<p className="text-sm text-gray-400 hidden sm:block">A guide to intuitive bonding</p>
						</div>

						<div className="hidden md:flex items-center space-x-4 text-sm text-gray-400">
							<span>Page {currentPage} of {numPages}</span>
							<span>•</span>
							<span>{Math.round(liveProgressPercentage)}% complete</span>
							<span>•</span>
							<span className="text-purple-400"><FaSearch className="w-4 h-4 inline-block text-white" /> {Math.round(scale * 100)}%</span>
						</div>
						{progressSaving && (
							<motion.div
								className="hidden sm:flex items-center space-x-2 text-blue-400"
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

					<div className="flex items-center space-x-2 w-full sm:w-auto justify-between sm:justify-end zoom-controls">
						{/* Mobile page indicator */}
						<div className="flex sm:hidden items-center space-x-2 text-sm text-gray-400">
							<span>Page {currentPage}/{numPages}</span>
						</div>
						
						{/* Zoom Controls */}
						<div className="flex items-center space-x-1 bg-gray-700/50 rounded-lg p-1">
							<motion.button
								onClick={handleZoomOut}
								disabled={scale <= 0.5}
								className="p-1.5 rounded hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
								title="Zoom Out"
								whileHover={scale > 0.5 ? { scale: 1.05 } : {}}
								whileTap={scale > 0.5 ? { scale: 0.95 } : {}}
							>
								<ZoomOut className="w-4 h-4" />
							</motion.button>

							<span className="text-xs text-gray-300 min-w-[40px] text-center">
								{Math.round(scale * 100)}%
							</span>

							<motion.button
								onClick={handleZoomIn}
								disabled={scale >= 3.0}
								className="p-1.5 rounded hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
								title="Zoom In"
								whileHover={scale < 3.0 ? { scale: 1.05 } : {}}
								whileTap={scale < 3.0 ? { scale: 0.95 } : {}}
							>
								<ZoomIn className="w-4 h-4" />
							</motion.button>

							<motion.button
								onClick={resetZoom}
								className="p-1.5 rounded hover:bg-gray-600 transition-colors"
								title="Reset Zoom (100%)"
								whileHover={{ scale: 1.05 }}
								whileTap={{ scale: 0.95 }}
							>
								<RotateCcw className="w-3 h-3" />
							</motion.button>
						</div>

						<motion.button
							onClick={() => setShowCommentsPanel(!showCommentsPanel)}
							className={`p-2 rounded ${showCommentsPanel ? 'bg-[var(--mrwhite-primary-color)] text-black' : 'bg-gray-700'} hover:bg-[var(--mrwhite-primary-color)]/80 transition-colors`}
							title="Toggle Comments Panel"
							whileHover={{ scale: 1.05 }}
							whileTap={{ scale: 0.95 }}
						>
							<MessageSquare className="w-4 h-4" />
						</motion.button>

						<div className="hidden sm:flex items-center space-x-2 text-sm bg-gray-700/50 rounded-lg px-3 py-1">
							<Edit3 className="w-4 h-4 text-green-400" />
							<span>Select text to comment</span>
						</div>

						<div className="hidden lg:flex items-center space-x-2 text-xs text-gray-500 bg-gray-800/50 rounded-lg px-2 py-1">
							<span>Navigation: ←→ Space | Zoom: Ctrl/⌘ +/-</span>
						</div>
					</div>
					
					{/* Help button */}
					<motion.button
						onClick={() => setShowHelpOverlay(true)}
						className="p-2 rounded bg-gray-700 hover:bg-[var(--mrwhite-primary-color)]/80 transition-colors ml-2"
						title="How It Works"
						whileHover={{ scale: 1.05 }}
						whileTap={{ scale: 0.95 }}
					>
						<HelpCircle className="w-4 h-4" />
					</motion.button>
				</div>
			</motion.header>

			{/* Page Navigation Slider */}
			{numPages > 0 && (
				<motion.div
					className="border-b border-gray-700 bg-gray-800/30 backdrop-blur-sm px-4 py-2 flex-shrink-0"
					initial={{ opacity: 0, y: -20 }}
					animate={{ opacity: 1, y: 0 }}
					transition={{ delay: 0.2, duration: 0.3 }}
				>
					<div className="flex items-center space-x-4">
						<span className="text-sm text-gray-400 whitespace-nowrap hidden sm:inline">Quick Navigate:</span>

						<div className="flex-1 relative">
							{/* Page Progress Bar */}
							<div className="relative">
								<input
									type="range"
									min="1"
									max={numPages}
									value={sliderValue}
									onChange={(e) => handleSliderChange(parseInt(e.target.value))}
									onMouseDown={handleSliderMouseDown}
									onMouseUp={handleSliderMouseUp}
									onKeyDown={handleSliderKeyDown}
									className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider-custom"
									style={{
										background: `linear-gradient(to right, #D3B86A 0%, #D3B86A ${(sliderValue / numPages) * 100}%, #374151 ${(sliderValue / numPages) * 100}%, #374151 100%)`
									}}
								/>

								{/* Page markers for visual reference */}
								<div className="absolute top-0 left-0 w-full h-2 pointer-events-none">
									{Array.from({ length: Math.min(numPages, 20) }, (_, i) => {
										const pageIndex = Math.floor((i / 19) * (numPages - 1)) + 1;
										const position = ((pageIndex - 1) / (numPages - 1)) * 100;
										return (
											<div
												key={i}
												className="absolute w-0.5 h-2 bg-gray-600 opacity-50"
												style={{ left: `${position}%` }}
											/>
										);
									})}
								</div>
							</div>

							{/* Page Preview Tooltip */}
							<AnimatePresence>
								{showPagePreview && (
									<motion.div
										className="absolute -top-12 bg-gray-900 text-white px-3 py-1 rounded-lg shadow-lg border border-gray-600 pointer-events-none z-10"
										style={{
											left: `${((sliderValue - 1) / (numPages - 1)) * 100}%`,
											transform: 'translateX(-50%)'
										}}
										initial={{ opacity: 0, y: 10, scale: 0.8 }}
										animate={{ opacity: 1, y: 0, scale: 1 }}
										exit={{ opacity: 0, y: 10, scale: 0.8 }}
										transition={{ duration: 0.2 }}
									>
										<span className="text-sm font-medium">Page {previewPage}</span>
										<div className="absolute top-full left-1/2 transform -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45 border-r border-b border-gray-600"></div>
									</motion.div>
								)}
							</AnimatePresence>
						</div>

						<div className="flex items-center space-x-2 text-sm text-gray-400">
							<span className="whitespace-nowrap">
								{isDraggingSlider ? `${previewPage} of ${numPages}` : `${currentPage} of ${numPages}`}
							</span>
						</div>
					</div>
				</motion.div>
			)}

			<div className="flex flex-1 overflow-hidden">
				{/* Main PDF Viewer */}
				<motion.div
					className={`flex-1 flex flex-col relative ${!isResizing ? 'resize-transition' : ''}`}
					initial={{ opacity: 0 }}
					animate={{ opacity: 1 }}
					transition={{ duration: 0.5 }}
				>
					{/* PDF Document */}
					<div
						ref={documentRef}
						className="flex-1 overflow-auto bg-background flex items-start justify-center py-2 sm:py-4 px-1 sm:px-6 relative min-h-[300px] sm:min-h-[600px]"
						style={{ userSelect: 'text', WebkitOverflowScrolling: 'touch' }}
					>
						<motion.div
							initial={{ scale: 0.8 }}
							animate={{ scale: 1 }}
							transition={{ type: "spring", stiffness: 100 }}
							className="relative max-w-full sm:max-w-[95vw] pdf-container"
						>
							<Document
								file="/books/the-way-of-the-dog-anahata.pdf"
								onLoadSuccess={onDocumentLoadSuccess}
								onLoadError={onDocumentLoadError}
								className="shadow-2xl"
								loading={<div className="flex items-center justify-center p-4"><div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div></div>}
								externalLinkTarget="_blank"
							>
								<Page
									pageNumber={currentPage}
									scale={isMobile ? Math.min(scale, 0.8) : scale} // Reduce scale on mobile
									renderTextLayer={true}
									renderAnnotationLayer={false}
									className="border border-gray-600 bg-white relative smooth-selection shadow-xl max-w-full"
									data-page-number={currentPage}
									width={isMobile ? window.innerWidth - 32 : undefined} // Adjust width on mobile
								/>
							</Document>

							{/* Comment indicators for current page */}
							{comments
								.filter(comment => comment.page_number === currentPage)
								.map(comment => {
									console.log('📍 Rendering comment indicator:', {
										id: comment.id,
										position: comment.position,
										scaledPosition: {
											x: comment.position.x * scale,
											y: comment.position.y * scale
										}
									});

									return (
										<motion.div
											key={comment.id}
											className="absolute bg-blue-500 rounded-full w-6 h-6 flex items-center justify-center text-white text-xs cursor-pointer hover:bg-blue-600 transition-colors shadow-lg comment-indicator"
											style={{
												left: `${comment.position.x * scale}px`,
												top: `${comment.position.y * scale}px`,
												transform: 'translate(-50%, -50%)',
												zIndex: 10
											}}
											onClick={() => goToComment(comment)}
											whileHover={{ scale: 1.2 }}
											whileTap={{ scale: 0.9 }}
											title={`${comment.author}: ${comment.text.substring(0, 50)}...`}
										>
											<MessageSquare className="w-3 h-3" />
										</motion.div>
									);
								})
							}
						</motion.div>
					</div>

					{/* Enhanced Comment Popover */}
					<AnimatePresence>
						{showCommentPopover && selectedText && selectedText.isValid && (
							<motion.div
								ref={popoverRef}
								className="absolute bg-white text-black rounded-lg shadow-xl border border-gray-200 p-3 z-50 comment-popover max-w-[90vw] sm:max-w-xs"
								style={{
									left: Math.min(
										Math.max(selectedText.rect.left + selectedText.rect.width / 2, 150),
										window.innerWidth - 150
									),
									top: selectedText.rect.bottom + 10,
									transform: 'translateX(-50%)'
								}}
								initial={{ opacity: 0, scale: 0.8, y: -10 }}
								animate={{ opacity: 1, scale: 1, y: 0 }}
								exit={{ opacity: 0, scale: 0.8, y: -10 }}
								transition={{ duration: 0.2 }}
							>
								<div className="flex items-center space-x-2">
									<motion.button
										onClick={(e) => {
											e.stopPropagation();
											e.preventDefault();
											console.log('🔵 Add comment clicked');

											// Open modal - selection lock will prevent interference
											setShowCommentModal(true);
											modalOpenTimeRef.current = Date.now();

											console.log('🔵 Modal opened');
										}}
										className="flex items-center space-x-2 bg-blue-600 text-white px-3 py-2 rounded-md hover:bg-blue-700 transition-colors"
										whileHover={{ scale: 1.05 }}
										whileTap={{ scale: 0.95 }}
									>
										<Plus className="w-4 h-4" />
										<span>Add comment</span>
									</motion.button>
									<motion.button
										onClick={(e) => {
											e.stopPropagation();
											e.preventDefault();
											setShowCommentPopover(false);
											setSelectedText(null);
											window.getSelection()?.removeAllRanges();
											lastSelectionRef.current = '';
										}}
										className="p-2 hover:bg-gray-100 rounded-md transition-colors"
										whileHover={{ scale: 1.1 }}
										whileTap={{ scale: 0.9 }}
									>
										<X className="w-4 h-4" />
									</motion.button>
								</div>
								<div className="mt-2 text-xs text-gray-600 max-w-xs">
									<span className="font-medium">Selected:</span> "{selectedText.text.substring(0, 80)}{selectedText.text.length > 80 ? '...' : ''}"
								</div>

								{/* Popover arrow */}
								<div className="absolute top-[-6px] left-1/2 transform -translate-x-1/2 w-3 h-3 bg-white border-l border-t border-gray-200 rotate-45"></div>
							</motion.div>
						)}
					</AnimatePresence>

					{/* Navigation Controls */}
					<motion.div
						className="border-t border-gray-700 p-3 flex flex-col sm:flex-row items-center justify-between bg-background backdrop-blur-sm space-y-2 sm:space-y-0"
						initial={{ y: 100 }}
						animate={{ y: 0 }}
						transition={{ type: "spring", stiffness: 100 }}
					>
						<div className="flex items-center justify-between w-full sm:w-auto sm:justify-start space-x-2">
							<motion.button
								onClick={() => goToPage(currentPage - 1)}
								disabled={currentPage <= 1}
								className="flex items-center space-x-2 px-4 py-2 bg-[var(--mrwhite-primary-color)] text-black rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
								whileHover={currentPage > 1 ? { scale: 1.05 } : {}}
								whileTap={currentPage > 1 ? { scale: 0.95 } : {}}
							>
								<ChevronLeft className="w-4 h-4" />
								<span className="hidden sm:inline">Previous</span>
							</motion.button>

							<motion.button
								onClick={() => goToPage(currentPage + 1)}
								disabled={currentPage >= numPages}
								className="flex items-center space-x-2 px-4 py-2 bg-[var(--mrwhite-primary-color)] text-black rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-600 transition-colors"
								whileHover={currentPage < numPages ? { scale: 1.05 } : {}}
								whileTap={currentPage < numPages ? { scale: 0.95 } : {}}
							>
								<span className="hidden sm:inline">Next</span>
								<ChevronRight className="w-4 h-4" />
							</motion.button>
						</div>

						<div className="flex items-center space-x-4 w-full sm:w-auto justify-center">
							<span className="text-sm text-gray-400 hidden sm:inline">Jump to page:</span>
							<input
								type="number"
								max={numPages}
								value={pageInputValue}
								onChange={(e) => {
									setPageInputValue(e.target.value);
								}}
								onBlur={() => {
									if (pageInputValue === '') {
										// Reset to current page if empty
										setPageInputValue(currentPage.toString());
										return;
									}

									const page = parseInt(pageInputValue);
									if (page >= 1 && page <= numPages) {
										goToPage(page);
									} else {
										// Reset to current page if invalid
										setPageInputValue(currentPage.toString());
									}
								}}
								onKeyDown={(e) => {
									if (e.key === 'Enter') {
										if (pageInputValue === '') {
											// Reset to current page if empty
											setPageInputValue(currentPage.toString());
											return;
										}

										const page = parseInt(pageInputValue);
										if (page >= 1 && page <= numPages) {
											goToPage(page);
											(e.target as HTMLInputElement).blur();
										} else {
											// Reset to current page if invalid
											setPageInputValue(currentPage.toString());
										}
									}
								}}
								className="w-16 sm:w-20 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-center focus:border-blue-500 focus:outline-none transition-colors"
								title="Enter page number and press Enter"
							/>
							<span className="text-sm text-gray-400">of {numPages}</span>
						</div>
					</motion.div>
				</motion.div>

				{/* Comments Panel */}
				<AnimatePresence>
					{showCommentsPanel && (
						<motion.div
							ref={panelRef}
							className="border-l border-gray-700 bg-gray-800 flex flex-col relative comments-panel"
							style={{ 
								width: isMobile ? '100%' : isTablet ? '320px' : `${panelWidth}px`,
								position: isMobile ? 'fixed' : 'relative',
								top: isMobile ? '0' : 'auto',
								right: isMobile ? '0' : 'auto',
								bottom: isMobile ? '0' : 'auto',
								left: isMobile ? '0' : 'auto',
								height: isMobile ? '100%' : 'auto',
								zIndex: isMobile ? '50' : 'auto'
							}}
							initial={{ x: isMobile ? '100%' : 0, opacity: 0 }}
							animate={{ x: 0, opacity: 1 }}
							exit={{ x: isMobile ? '100%' : 0, opacity: 0 }}
							transition={{ type: "spring", stiffness: 100, damping: 20 }}
						>
							{/* Mobile close button */}
							{isMobile && (
								<motion.button
									onClick={() => setShowCommentsPanel(false)}
									className="absolute top-4 right-4 p-2 bg-gray-700 rounded-full z-10"
									whileHover={{ scale: 1.1 }}
									whileTap={{ scale: 0.9 }}
								>
									<X className="w-5 h-5" />
								</motion.button>
							)}
							
							{/* Tablet close button */}
							{isTablet && !isMobile && (
								<motion.button
									onClick={() => setShowCommentsPanel(false)}
									className="absolute top-4 right-4 p-2 bg-gray-700 rounded-full z-10"
									whileHover={{ scale: 1.1 }}
									whileTap={{ scale: 0.9 }}
								>
									<X className="w-5 h-5" />
								</motion.button>
							)}
							
							{/* Resize Handle - Only on desktop */}
							{!isMobile && !isTablet && (
								<div 
									ref={resizeRef}
									className="absolute left-0 top-0 bottom-0 w-6 hover:bg-blue-500/20 transition-colors group z-10"
									style={{ transform: 'translateX(-50%)', cursor: 'col-resize' }}
									onMouseDown={handleResizeStart}
								>
									<div className="absolute left-1/2 top-0 bottom-0 w-1 bg-gray-600/50 group-hover:bg-blue-500/50"></div>
									<div className="absolute left-1/2 top-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-gray-700 rounded-full p-1 shadow-md opacity-0 group-hover:opacity-100 transition-opacity">
										<GripVertical className="w-4 h-4 text-blue-400" />
									</div>
								</div>
							)}
							
							<div className="p-4 border-b border-gray-700">
								<div className="flex items-center justify-between mb-3">
									<h3 className="text-lg font-semibold flex items-center space-x-2">
										<MessageSquare className="w-5 h-5 text-blue-400" />
										<span>Comments & Search</span>
									</h3>
									{!isMobile && (
										<div className="text-xs text-gray-500 flex items-center">
											<GripVertical className="w-3 h-3 mr-1" />
											<span>Drag to resize</span>
										</div>
									)}
								</div>

								{/* Tab Buttons */}
								<div className="flex flex-wrap gap-1 mb-3">
									<button
										onClick={() => {
											handleTabSwitch(false);
											setActiveTab('comments');
										}}
										className={`px-3 py-1.5 rounded text-sm transition-colors ${activeTab === 'comments'
											? 'bg-[var(--mrwhite-primary-color)] text-black'
											: 'bg-gray-700 text-gray-300 hover:bg-gray-600'
											}`}
									>
										Comments ({comments.length})
									</button>
									<button
										onClick={() => {
											handleTabSwitch(true);
											setActiveTab('knowledge');
										}}
										className={`px-3 py-1.5 rounded text-sm transition-colors ${activeTab === 'knowledge'
											? 'bg-[var(--mrwhite-primary-color)] text-black'
											: 'bg-gray-700 text-gray-300 hover:bg-gray-600'
											}`}
									>
										<GiBrain className="w-4 h-4 inline-block" /> Knowledge
									</button>
									<button
										onClick={() => {
											setActiveTab('chat');
										}}
										className={`px-3 py-1.5 rounded text-sm transition-colors ${activeTab === 'chat'
											? 'bg-[var(--mrwhite-primary-color)] text-black'
											: 'bg-gray-700 text-gray-300 hover:bg-gray-600'
											}`}
									>
										<MessageSquare className="w-4 h-4 inline-block mr-1" /> Chat
									</button>
								</div>

															{showKnowledgeSearch && (
								<div className="flex gap-2 sm:flex-row space-y-2 sm:space-y-0 sm:space-x-2">
										<input
											type="text"
											placeholder="Search your notes & highlights..."
											value={knowledgeSearchQuery}
											onChange={(e) => setKnowledgeSearchQuery(e.target.value)}
											onKeyDown={(e) => {
												if (e.key === 'Enter') {
													searchKnowledgeBase(knowledgeSearchQuery);
												}
											}}
											className="flex-1 px-3 py-2 bg-white/10  border border-white/5 rounded text-sm focus:border-[var(--mrwhite-primary-color)] focus:outline-none mb-0"
										/>
										<button
											onClick={() => searchKnowledgeBase(knowledgeSearchQuery)}
											disabled={knowledgeSearchLoading || !knowledgeSearchQuery.trim()}
											className="px-3 py-2 bg-[var(--mrwhite-primary-color)] text-white rounded text-sm hover:bg-[var(--mrwhite-primary-color)]/80 disabled:opacity-50 disabled:cursor-not-allowed"
										>
											{knowledgeSearchLoading ? (
												<div className="flex items-center space-x-1">
													<span className="w-1 h-1 bg-black rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
													<span className="w-1 h-1 bg-black rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
													<span className="w-1 h-1 bg-black rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
												</div>
											) : (
												<FaSearch className="w-4 h-4 text-black" />
											)}
										</button>
									</div>
								)}
							</div>

							<div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
								{activeTab === 'chat' ? (
									// Knowledge Chat Panel
									<div className="h-full">
										<KnowledgeChatPanel 
											bookId={userBookCopy?.id?.toString()} 
											bookCopyId={userBookCopy?.id} 
										/>
									</div>
								) : activeTab === 'knowledge' ? (
									// Knowledge Base Search Results
									<div>
										{knowledgeSearchLoading && (
											<div className="text-center text-gray-400 py-4">
												<div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
												<p className="text-sm">Searching your knowledge base...</p>
											</div>
										)}

										{!knowledgeSearchLoading && knowledgeSearchResults.length === 0 && knowledgeSearchQuery && (
											<div className="text-center text-gray-500 py-8">
												<div className="text-4xl mb-2"><FaSearch className="w-8 h-8" /></div>
												<p className="text-sm">No results found in your knowledge base</p>
												<p className="text-xs mt-1 text-gray-600">Try different keywords or create more comments</p>
											</div>
										)}

										{!knowledgeSearchQuery && !knowledgeSearchLoading && (
											<div className="text-center text-gray-500 py-8">
												<div className="text-4xl flex items-center justify-center  mb-2 text-center w-full mx-auto"><GiBrain className="w-8 h-8 text-purple-500" /></div>
												<p className="text-sm">Search your personal knowledge base</p>
												<p className="text-xs mt-1 text-gray-600">Find notes and highlights from all your books</p>
											</div>
										)}

										{paginatedKnowledgeResults.map((result, index) => (
											<motion.div
												key={`${knowledgeCurrentPage}-${index}`}
												className="bg-gradient-to-r from-background to-bg-neutral-700 rounded-sm border p-4 hover:bg-gray-600 transition-colors border-l-4 border-purple-500 mb-2"
												initial={{ opacity: 0, y: 20 }}
												animate={{ opacity: 1, y: 0 }}
												transition={{ delay: index * 0.1 }}
											>
												<div className="flex items-center justify-between mb-2">
													<div className="flex items-center space-x-2">
														<div className="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center text-xs text-white">
															{result.content_type === 'book_highlight' ? '🖍️' : <GiBrain className="w-4 h-4" />}
														</div>
														<span className="text-sm font-medium text-purple-300">
															{result.book_title || 'Unknown Book'}
														</span>
													</div>
													<span className="text-xs text-gray-400">
														Page {result.page_number || 'N/A'}
													</span>
												</div>

												{/* Format the text content for better readability */}
												{result.text && (
													<div className="text-sm text-gray-200 mb-3">
														{result.text.includes('Book:') ? (
															<div className="space-y-2">
																{result.text.split('\n').map((line: string, i: number) => {
																	// Skip empty lines
																	if (!line.trim()) return null;

																	// Extract key-value pairs
																	const match = line.trim().match(/^([^:]+):\s*(.+)$/);
																	if (match) {
																		const [_, key, value] = match;
																		// Skip displaying "Book:" since we already show it in the header
																		if (key.trim() === "Book") return null;

																		return (
																			<div key={i} className="flex">
																				<span className="text-purple-300 font-medium mr-2">{key.trim()}:</span>
																				<span>{value.trim()}</span>
																			</div>
																		);
																	}
																	return <p key={i}>{line.trim()}</p>;
																})}
															</div>
														) : (
															<p>{result.text}</p>
														)}
													</div>
												)}

												<div className="flex items-center justify-between mt-2">
													<span className="text-xs text-gray-500">
														Score: {Math.round((result.score || 0) * 100)}%
													</span>
													<span className="text-xs text-purple-400">
														{result.content_type === 'book_highlight' ? 'highlight' : result.note_type || 'note'}
													</span>
												</div>
											</motion.div>
										))}

										{/* Knowledge Search Pagination */}
										<PaginationControls
											currentPage={knowledgeCurrentPage}
											totalPages={totalKnowledgePages}
											onPageChange={setKnowledgeCurrentPage}
											itemType="results"
											totalItems={knowledgeSearchResults.length}
											itemsPerPage={knowledgePerPage}
										/>
									</div>
								) : activeTab === 'comments' ? (
									// Regular Page Comments
									<div>
										{comments.length === 0 ? (
											<div className="text-center text-gray-500 mt-8">
												<MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
												<p className="text-sm">No comments yet</p>
												<p className="text-xs mt-1">Select text to add the first comment</p>
											</div>
										) : (
											paginatedComments.map((comment, index) => (
												<motion.div
													key={`${commentsCurrentPage}-${comment.id}`}
													className="bg-background rounded-sm border border-gray-700 p-4 hover:bg-background/70 transition-colors cursor-pointer mb-2"
													initial={{ opacity: 0, y: 20 }}
													animate={{ opacity: 1, y: 0 }}
													transition={{ delay: index * 0.1 }}
													whileHover={{ scale: 1.02 }}
													onClick={() => goToComment(comment)}
												>
													<div className="flex items-center justify-between mb-2">
														<div className="flex items-center space-x-2">
															<div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-xs text-white">

																{comment.author.charAt(0).toUpperCase()}
															</div>
															<span className="text-sm font-medium">{comment.author}</span>
														</div>
														<span className="text-xs text-gray-400">Page {comment.page_number}</span>
													</div>

													<p className="text-sm text-gray-200 mb-2">{comment.text}</p>

													{comment.selected_text && (
														<div className="text-xs text-gray-400 bg-gray-800 rounded p-2 border-l-2 border-blue-500">
															<span className="text-blue-400">Selected text:</span>
															<p className="mt-1 italic">"{comment.selected_text.substring(0, 100)}{comment.selected_text.length > 100 ? '...' : ''}"</p>
														</div>
													)}

													<div className="flex items-center justify-between mt-3">
														<span className="text-xs text-gray-500">
															{new Date(comment.timestamp).toLocaleDateString()}
														</span>
														<div className="flex items-center space-x-2">
															<motion.button
																className="text-xs text-blue-400 hover:text-blue-300 flex items-center space-x-1"
																whileHover={{ scale: 1.05 }}
																whileTap={{ scale: 0.95 }}
																onClick={(e) => {
																	e.stopPropagation();
																	goToComment(comment);
																}}
															>
																<Eye className="w-3 h-3" />
																<span>View</span>
															</motion.button>
															<motion.button
																className="text-xs text-red-400 hover:text-red-300 flex items-center space-x-1"
																whileHover={{ scale: 1.05 }}
																whileTap={{ scale: 0.95 }}
																onClick={(e) => {
																	e.stopPropagation();
																	deleteComment(comment.id);
																}}
															>
																<Trash2 className="w-3 h-3" />
																<span>Delete</span>
															</motion.button>
														</div>
													</div>
												</motion.div>
											))
										)}

										{/* Comments Pagination */}
										<PaginationControls
											currentPage={commentsCurrentPage}
											totalPages={totalCommentsPages}
											onPageChange={setCommentsCurrentPage}
											itemType="comments"
											totalItems={comments.length}
											itemsPerPage={commentsPerPage}
										/>
									</div>
								) : null}
							</div>
						</motion.div>
					)}
				</AnimatePresence>
			</div>

			{/* Comment Creation Modal */}
			<AnimatePresence>
				{showCommentModal && selectedText && (
					<motion.div
						className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 modal-backdrop"
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						onClick={(e) => {
							// Only close if clicking on backdrop, not modal content
							if (e.target === e.currentTarget) {
								setShowCommentModal(false);
								setNewCommentText('');
								setShowCommentPopover(false);
								setSelectedText(null);
								window.getSelection()?.removeAllRanges();
								lastSelectionRef.current = '';
							}
						}}
					>
						<motion.div
							className="bg-gray-800 rounded-lg p-4 sm:p-6 w-[95%] sm:w-96 max-w-md border border-gray-600 mx-2"
							initial={{ scale: 0.8, y: 50 }}
							animate={{ scale: 1, y: 0 }}
							exit={{ scale: 0.8, y: 50 }}
							transition={{ type: "spring", stiffness: 200, damping: 20 }}
							onClick={(e) => e.stopPropagation()}
						>
							<h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
								<MessageSquare className="w-5 h-5 text-blue-400" />
								<span>Add Comment</span>
							</h3>

							<div className="mb-4 p-3 bg-blue-900/20 border border-blue-600/30 rounded-lg">
								<div className="flex items-center space-x-2 text-blue-300">
									<div className="w-2 h-2 bg-blue-400 rounded-full"></div>
									<span className="text-sm">Your comment will be saved to your personal knowledge base for future search and reference</span>
								</div>
							</div>

							<div className="mb-4 p-3 bg-gray-700 rounded border-l-4 border-blue-500">
								<p className="text-xs text-gray-400 mb-1">Selected text:</p>
								<p className="text-sm italic text-gray-300">
									"{selectedText.text.substring(0, 200)}{selectedText.text.length > 200 ? '...' : ''}"
								</p>
								<p className="text-xs text-gray-500 mt-1">Page {selectedText.pageNumber}</p>
							</div>

							<textarea
								value={newCommentText}
								onChange={(e) => setNewCommentText(e.target.value)}
								placeholder="Write your comment about this text..."
								className="w-full h-32 p-3 bg-gray-700 border border-gray-600 rounded resize-none focus:border-blue-500 focus:outline-none transition-colors text-white placeholder-gray-400"
								autoFocus
								onKeyDown={(e) => {
									if (e.key === 'Escape') {
										setShowCommentModal(false);
										setNewCommentText('');
										setShowCommentPopover(false);
										setSelectedText(null);
										window.getSelection()?.removeAllRanges();
										lastSelectionRef.current = '';
									}
								}}
							/>

							<div className="flex flex-col sm:flex-row justify-end space-y-2 sm:space-y-0 sm:space-x-3 mt-4">
								<motion.button
									onClick={(e) => {
										e.stopPropagation();
										setShowCommentModal(false);
										setNewCommentText('');
										setShowCommentPopover(false);
										setSelectedText(null);
										window.getSelection()?.removeAllRanges();
										lastSelectionRef.current = '';
									}}
									className="px-4 py-2 bg-gray-600 rounded hover:bg-gray-500 transition-colors"
									whileHover={{ scale: 1.05 }}
									whileTap={{ scale: 0.95 }}
								>
									Cancel
								</motion.button>
								<motion.button
									onClick={(e) => {
										e.stopPropagation();
										createComment();
									}}
									disabled={!newCommentText.trim() || isAddingComment}
									className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
									whileHover={newCommentText.trim() && !isAddingComment ? { scale: 1.05 } : {}}
									whileTap={newCommentText.trim() && !isAddingComment ? { scale: 0.95 } : {}}
								>
									{isAddingComment ? (
										<>
											<svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
												<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
												<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
											</svg>
											<span>Adding...</span>
										</>
									) : (
										<>
											<Plus className="w-4 h-4" />
											<span>Add Comment</span>
										</>
									)}
								</motion.button>
							</div>
						</motion.div>
					</motion.div>
				)}
			</AnimatePresence>

			{/* How It Works Help Overlay */}
			<AnimatePresence>
				{showHelpOverlay && (
					<motion.div
						className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50 p-4 sm:p-6 help-overlay"
						initial={{ opacity: 0 }}
						animate={{ opacity: 1 }}
						exit={{ opacity: 0 }}
						onClick={(e) => {
							if (e.target === e.currentTarget) {
								setShowHelpOverlay(false);
							}
						}}
					>
						<motion.div
							className="bg-gray-800 rounded-lg border border-gray-600 w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col"
							initial={{ scale: 0.9, y: 20 }}
							animate={{ scale: 1, y: 0 }}
							exit={{ scale: 0.9, y: 20 }}
							transition={{ type: "spring", stiffness: 300, damping: 30 }}
							onClick={(e) => e.stopPropagation()}
						>
							<div className="p-4 sm:p-6 border-b border-gray-700 flex items-center justify-between">
								<h2 className="text-xl sm:text-2xl font-semibold flex items-center gap-2">
									<HelpCircle className="w-6 h-6 text-[var(--mrwhite-primary-color)]" />
									<span>How It Works</span>
								</h2>
								<motion.button
									onClick={() => setShowHelpOverlay(false)}
									className="p-2 rounded-full hover:bg-gray-700 transition-colors"
									whileHover={{ scale: 1.1 }}
									whileTap={{ scale: 0.9 }}
								>
									<X className="w-5 h-5" />
								</motion.button>
							</div>

							<div className="flex flex-col sm:flex-row flex-1 overflow-hidden">
								{/* Topics Sidebar */}
								<div className="w-full sm:w-64 border-b sm:border-b-0 sm:border-r border-gray-700 bg-gray-900/50">
									<div className="p-4 help-topic-list">
										<h3 className="text-sm uppercase text-gray-400 font-medium mb-2">Topics</h3>
										<div className="space-y-1">
											{helpTopics.map((topic) => (
												<button
													key={topic.id}
													onClick={() => setCurrentHelpTopic(topic.id)}
													className={`w-full text-left p-3 rounded-md flex items-center gap-3 help-topic-button ${
														currentHelpTopic === topic.id ? 'active' : ''
													}`}
												>
													<div className="flex-shrink-0">
														{topic.icon}
													</div>
													<span className="font-medium">{topic.title}</span>
													{currentHelpTopic === topic.id && (
														<CheckCircle className="w-4 h-4 ml-auto" />
													)}
												</button>
											))}
										</div>
									</div>
								</div>

								{/* Topic Content */}
								<div className="flex-1 overflow-y-auto p-4 sm:p-6 help-content">
									{helpTopics.map((topic) => (
										<AnimatePresence key={topic.id}>
											{currentHelpTopic === topic.id && (
												<motion.div
													initial={{ opacity: 0, x: 20 }}
													animate={{ opacity: 1, x: 0 }}
													exit={{ opacity: 0, x: -20 }}
													transition={{ duration: 0.2 }}
													className="space-y-4"
												>
													<h3 className="text-xl font-semibold flex items-center gap-2">
														{topic.icon}
														<span>{topic.title}</span>
													</h3>

													<div className="prose prose-invert max-w-none">
														{topic.description.split('\n').map((paragraph, i) => (
															<p key={i} className="mb-2">{paragraph}</p>
														))}
													</div>

													{topic.id === 'navigation' && (
														<div className="mt-6 p-4 bg-gray-700/50 rounded-lg border border-gray-600">
															<h4 className="text-lg font-medium mb-3">Navigation Tips</h4>
															<ul className="space-y-2 list-disc list-inside">
																<li>Use the slider at the top to quickly jump to any page</li>
																<li>The page number input accepts direct page entry</li>
																<li>Mouse wheel scrolls vertically through the current page</li>
																<li>Ctrl/Cmd + mouse wheel adjusts zoom level</li>
															</ul>
														</div>
													)}

													{topic.id === 'commenting' && (
														<div className="mt-6 p-4 bg-gray-700/50 rounded-lg border border-gray-600">
															<h4 className="text-lg font-medium mb-3">Comment Features</h4>
															<ul className="space-y-2 list-disc list-inside">
																<li>Comments are private to your account</li>
																<li>Blue indicators show where you've added comments</li>
																<li>Click on indicators to view the comment</li>
																<li>Comments are searchable in the knowledge base</li>
															</ul>
														</div>
													)}
												</motion.div>
											)}
										</AnimatePresence>
									))}
								</div>
							</div>

							<div className="p-4 border-t border-gray-700 flex justify-between help-navigation">
								<button
									onClick={() => {
										const currentIndex = helpTopics.findIndex(t => t.id === currentHelpTopic);
										if (currentIndex > 0) {
											setCurrentHelpTopic(helpTopics[currentIndex - 1].id);
										}
									}}
									disabled={helpTopics.findIndex(t => t.id === currentHelpTopic) === 0}
									className="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
								>
									<ChevronLeft className="w-4 h-4" />
									<span>Previous</span>
								</button>

								<button
									onClick={() => setShowHelpOverlay(false)}
									className="px-4 py-2 bg-[var(--mrwhite-primary-color)] text-black rounded hover:bg-[var(--mrwhite-primary-color)]/80 transition-colors"
								>
									Got it!
								</button>

								<button
									onClick={() => {
										const currentIndex = helpTopics.findIndex(t => t.id === currentHelpTopic);
										if (currentIndex < helpTopics.length - 1) {
											setCurrentHelpTopic(helpTopics[currentIndex + 1].id);
										}
									}}
									disabled={helpTopics.findIndex(t => t.id === currentHelpTopic) === helpTopics.length - 1}
									className="px-4 py-2 bg-gray-700 rounded hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
								>
									<span>Next</span>
									<ChevronRight className="w-4 h-4" />
								</button>
							</div>
						</motion.div>
					</motion.div>
				)}
			</AnimatePresence>
		</div>
	);
};

export default GoogleDocsStylePDFReader; 