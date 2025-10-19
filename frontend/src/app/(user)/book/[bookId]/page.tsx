'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Progress } from '@/components/ui/progress';
import { motion, AnimatePresence } from 'motion/react';
import { FASTAPI_BASE_URL } from '@/utils/api';
import axios from 'axios';
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
    Download,
    Save,
    Trash2,
    Plus,
    Eye,
    EyeOff,
    RotateCcw,
    Settings,
    Search,
    Filter,
    Calendar,
    Tag,
    ArrowLeft,
    CheckCircle,
    AlertCircle,
    Info,
    Sparkles,
    FileText,
    RefreshCw
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import toast from 'react-hot-toast';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Add custom styles for input visibility
const inputStyles = `
  .ai-chat-input input, .ai-chat-input textarea {
    color: #111827 !important;
    background-color: white !important;
  }
  .ai-chat-input input::placeholder, .ai-chat-input textarea::placeholder {
    color: #6b7280 !important;
  }
  .edit-content-textarea {
    color: #111827 !important;
    background-color: white !important;
  }
  .edit-content-textarea::placeholder {
    color: #6b7280 !important;
  }
`;

// Inject styles
if (typeof document !== 'undefined') {
    const styleElement = document.createElement('style');
    styleElement.textContent = inputStyles;
    document.head.appendChild(styleElement);
}

// Utility function to convert HTML to plain text for editing
const htmlToPlainText = (html: string): string => {
    if (!html) return '';

    // Create a temporary DOM element to parse HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;

    // Replace common HTML elements with appropriate plain text formatting
    const processNode = (node: Node): string => {
        if (node.nodeType === Node.TEXT_NODE) {
            return node.textContent || '';
        }

        if (node.nodeType === Node.ELEMENT_NODE) {
            const element = node as Element;
            const tagName = element.tagName.toLowerCase();
            const childText = Array.from(element.childNodes)
                .map(child => processNode(child))
                .join('');

            switch (tagName) {
                case 'h1':
                case 'h2':
                case 'h3':
                case 'h4':
                case 'h5':
                case 'h6':
                    return `\n\n${childText}\n${'='.repeat(childText.length)}\n\n`;
                case 'p':
                    return `${childText}\n\n`;
                case 'br':
                    return '\n';
                case 'div':
                    return `${childText}\n`;
                case 'li':
                    return `• ${childText}\n`;
                case 'ul':
                case 'ol':
                    return `\n${childText}\n`;
                case 'strong':
                case 'b':
                    return `**${childText}**`;
                case 'em':
                case 'i':
                    return `*${childText}*`;
                case 'blockquote':
                    return `\n> ${childText}\n\n`;
                default:
                    return childText;
            }
        }

        return '';
    };

    const plainText = processNode(tempDiv);

    // Clean up excessive whitespace and line breaks
    return plainText
        .replace(/\n{3,}/g, '\n\n') // Replace 3+ line breaks with 2
        .replace(/^\s+|\s+$/g, '') // Trim whitespace from start/end
        .replace(/[ \t]+/g, ' '); // Replace multiple spaces/tabs with single space
};

// Utility function to convert plain text back to basic HTML for saving
const plainTextToHtml = (text: string): string => {
    if (!text) return '';

    // Split into paragraphs and process each one
    const paragraphs = text.split(/\n\s*\n/);

    return paragraphs
        .map(paragraph => {
            // Handle headers (text followed by === or ---)
            if (paragraph.includes('===') || paragraph.includes('---')) {
                const lines = paragraph.split('\n');
                const titleLine = lines.find(line => !line.match(/^[=\-]+$/));
                if (titleLine) {
                    return `<h3>${titleLine.trim()}</h3>`;
                }
            }

            // Handle bullet points
            if (paragraph.includes('•') || paragraph.match(/^\s*[\-\*]/m)) {
                const bulletPoints = paragraph
                    .split('\n')
                    .filter(line => line.trim())
                    .map(line => {
                        const cleanLine = line.replace(/^\s*[•\-\*]\s*/, '').trim();
                        return cleanLine ? `<li>${cleanLine}</li>` : '';
                    })
                    .filter(line => line);

                if (bulletPoints.length > 0) {
                    return `<ul>${bulletPoints.join('')}</ul>`;
                }
            }

            // Handle regular paragraphs
            const cleanParagraph = paragraph.trim();
            if (cleanParagraph) {
                // Convert basic markdown-style formatting
                let processedText = cleanParagraph
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // **bold**
                    .replace(/\*(.*?)\*/g, '<em>$1</em>') // *italic*
                    .replace(/^>\s*(.+)$/gm, '<blockquote>$1</blockquote>'); // > quotes

                return `<p>${processedText}</p>`;
            }

            return '';
        })
        .filter(html => html)
        .join('');
};

interface BookChapter {
    id: string;
    title: string;
    content: string;
    order: number;
    isVisible: boolean;
    tags: string[];
    dateRange?: {
        start: string;
        end: string;
    };
    contentType: 'chat' | 'photos' | 'documents' | 'mixed';
    aiGenerated: boolean;
    userEdited: boolean;
    originalContent?: string;
}

interface BookData {
    id: number;
    title: string;
    subtitle?: string;
    description?: string;
    coverImageUrl?: string;
    generationStatus: string;
    generationProgress: number;
    totalContentItems: number;
    createdAt: string;
    updatedAt: string;
    chapters: BookChapter[];
    selectedTags: number[];
    dateRange: {
        start?: string;
        end?: string;
    };
    contentTypes: string[];
    bookStyle: 'narrative' | 'timeline' | 'reference';
}

interface ChatMessage {
    id: string;
    type: 'user' | 'ai';
    content: string;
    timestamp: string;
}

const BookEditorPage: React.FC = () => {
    const { user } = useAuth();
    const params = useParams();
    const router = useRouter();
    const bookId = params.bookId as string;

    // State management
    const [bookData, setBookData] = useState<BookData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'read' | 'edit' | 'chat' | 'settings'>('read');

    // Editing state
    const [editingChapter, setEditingChapter] = useState<string | null>(null);
    const [editContent, setEditContent] = useState('');
    const [isEditing, setIsEditing] = useState(false);
    const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
    const [showPreview, setShowPreview] = useState(false);

    // AI Chat state
    const [chatQuery, setChatQuery] = useState('');
    const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
    const [chatLoading, setChatLoading] = useState(false);

    // AI Editing state
    const [aiEditInstruction, setAiEditInstruction] = useState('');
    const [aiEditType, setAiEditType] = useState<'content' | 'style' | 'structure' | 'expand' | 'summarize'>('content');
    const [aiEditLoading, setAiEditLoading] = useState(false);

    // Enhanced AI Chat for Editing
    const [aiChatMessages, setAiChatMessages] = useState<ChatMessage[]>([]);
    const [aiChatInput, setAiChatInput] = useState('');
    const [aiChatLoading, setAiChatLoading] = useState(false);
    const [showAiChat, setShowAiChat] = useState(false);
    const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);
    const [pendingAiEdit, setPendingAiEdit] = useState<string>('');

    // Content filtering
    const [filterVisible, setFilterVisible] = useState(false);
    const [selectedChapters, setSelectedChapters] = useState<string[]>([]);
    const [searchQuery, setSearchQuery] = useState('');

    // Confirm dialog states
    const [deleteChapterConfirm, setDeleteChapterConfirm] = useState<{isOpen: boolean, chapterId: string | null}>({
        isOpen: false,
        chapterId: null
    });
    const [deleteSelectedChaptersConfirm, setDeleteSelectedChaptersConfirm] = useState(false);
    const [regenerateFilesConfirm, setRegenerateFilesConfirm] = useState<{isOpen: boolean, format: string}>({
        isOpen: false,
        format: ''
    });

    // Fetch book data
    useEffect(() => {
            fetchBookData();
    }, [bookId]);

    const fetchBookData = async () => {
        try {
            setLoading(true);
            setError(null);

            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

            // Use the content endpoint that provides structured chapter data
            const response = await axios.get(`${apiUrl}/api/book-creation/books/${bookId}/content`, {
                withCredentials: true
            });

            if (response.data.success) {
                setBookData(response.data.book);
                
                // Initialize selected chapters to all visible chapters
                setSelectedChapters(
                    response.data.book.chapters
                        ?.filter((c: BookChapter) => c.isVisible)
                        ?.map((c: BookChapter) => c.id) || []
                );

                // Initialize chat with welcome message
                setChatHistory([{
                    id: '0',
                    type: 'ai',
                    content: `Welcome! Ask me anything about "${response.data.book.title}"`,
                    timestamp: new Date().toISOString()
                }]);
            } else {
                setError(response.data.message || 'Failed to load book data');
            }
        } catch (error: any) {
            console.error('Error fetching book data:', error);
            setError(error.response?.data?.message || 'Error loading book');
            if (error.response?.status === 404) {
                toast.error('Book not found');
                router.push('/my-hub');
            } else if (error.response?.status === 401) {
                toast.error('Please log in to view your book');
                router.push('/login');
            } else {
                toast.error('Failed to load book data');
            }
        } finally {
            setLoading(false);
        }
    };

    const searchKnowledgeBase = async (query: string, tags: string[] = [], dateRange?: { start: string, end: string }) => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            const response = await axios.post(`${apiUrl}/api/book-creation/search-content`, {
                query,
                selected_tags: bookData?.selectedTags || [],
                date_range_start: dateRange?.start || bookData?.dateRange.start,
                date_range_end: dateRange?.end || bookData?.dateRange.end,
                content_types: bookData?.contentTypes || ['chat', 'photos', 'documents'],
                limit: 50
            }, {
                withCredentials: true
            });

            return response.data;
        } catch (error) {
            console.error('Error searching knowledge base:', error);
            throw error;
        }
    };

    const saveChapterEdit = async (chapterId: string, newContent: string) => {
        try {
            setIsEditing(true);

            // Convert plain text back to HTML for storage
            const htmlContent = plainTextToHtml(newContent);

            // Update the chapter content locally first
            setBookData(prev => {
                if (!prev) return null;
                return {
                    ...prev,
                    chapters: prev.chapters.map(chapter =>
                        chapter.id === chapterId
                            ? { ...chapter, content: htmlContent, userEdited: true }
                            : chapter
                    )
                };
            });

            // Save to backend using the new chapter update API
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            const response = await axios.put(`${apiUrl}/api/book-creation/books/${bookId}/chapters/${chapterId}`, {
                content: htmlContent
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                toast.success('Chapter saved successfully');
                setHasUnsavedChanges(false);
                setEditingChapter(null);
                setEditContent('');
                setShowPreview(false);

                console.log('✅ Chapter saved:', {
                    chapterId,
                    contentLength: newContent.length,
                    updatedAt: response.data.updated_at
                });
            } else {
                toast.error(response.data.message || 'Failed to save chapter');
                // Revert local changes if save failed
                setBookData(prev => {
                    if (!prev) return null;
                    return {
                        ...prev,
                        chapters: prev.chapters.map(chapter =>
                            chapter.id === chapterId
                                ? { ...chapter, content: chapter.originalContent || chapter.content, userEdited: false }
                                : chapter
                        )
                    };
                });
            }
        } catch (error: any) {
            console.error('Error saving chapter:', error);
            toast.error(error.response?.data?.message || 'Failed to save chapter');

            // Revert local changes on error
            setBookData(prev => {
                if (!prev) return null;
                return {
                    ...prev,
                    chapters: prev.chapters.map(chapter =>
                        chapter.id === chapterId
                            ? { ...chapter, content: chapter.originalContent || chapter.content, userEdited: false }
                            : chapter
                    )
                };
            });
        } finally {
            setIsEditing(false);
        }
    };

    const deleteChapter = async (chapterId: string) => {
        setDeleteChapterConfirm({ isOpen: true, chapterId });
    };

    const confirmDeleteChapter = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            
            // Call the backend API to delete the chapter
            const response = await axios.delete(
                `${apiUrl}/api/book-creation/books/${bookId}/chapters/${deleteChapterConfirm.chapterId}`,
                { withCredentials: true }
            );
            
            if (response.data.success) {
                // Update local state to remove the chapter
                setBookData(prev => {
                    if (!prev) return null;
                    return {
                        ...prev,
                        chapters: prev.chapters.filter(chapter => chapter.id !== deleteChapterConfirm.chapterId)
                    };
                });
                
                toast.success('Chapter deleted successfully');
            } else {
                toast.error(response.data.message || 'Failed to delete chapter');
            }
        } catch (error) {
            console.error('Error deleting chapter:', error);
            toast.error('Failed to delete chapter');
        } finally {
            setDeleteChapterConfirm({ isOpen: false, chapterId: null });
        }
    };

    // Function to handle deleting multiple chapters
    const deleteMultipleChapters = async () => {
        try {
            // Show loading toast
            toast.success(`Deleting ${selectedChapters.length} chapters...`);
            
            // Delete each chapter sequentially
            for (const chapterId of selectedChapters) {
                await deleteChapter(chapterId);
            }
            
            // Clear selected chapters
            setSelectedChapters([]);
            toast.success(`${selectedChapters.length} chapters deleted successfully`);
        } catch (error) {
            console.error('Error deleting multiple chapters:', error);
            toast.error('Failed to delete some chapters');
        } finally {
            setDeleteSelectedChaptersConfirm(false);
        }
    };

    const toggleChapterVisibility = (chapterId: string) => {
        setBookData(prev => {
            if (!prev) return null;
            return {
                ...prev,
                chapters: prev.chapters.map(chapter =>
                    chapter.id === chapterId
                        ? { ...chapter, isVisible: !chapter.isVisible }
                        : chapter
                )
            };
        });
        setHasUnsavedChanges(true);
    };

    const handleAIEdit = async (chapterId: string, instruction: string, editType: string) => {
        try {
            setAiEditLoading(true);

            const chapter = bookData?.chapters.find(c => c.id === chapterId);
            if (!chapter) return;

            const aiPrompt = `
            Edit this book chapter based on the user's instruction.
            
            Edit Type: ${editType}
            User Instruction: ${instruction}
            
            Current Content:
            ${chapter.content}
            
            Please provide the edited content that maintains the book's style and flow while following the user's instruction.
            `;

            // TODO: Implement AI editing API call
            // For now, simulate AI editing
            const editedContent = chapter.content + `\n\n[AI Edit Applied: ${instruction}]`;

            setBookData(prev => {
                if (!prev) return null;
                return {
                    ...prev,
                    chapters: prev.chapters.map(c =>
                        c.id === chapterId
                            ? { ...c, content: editedContent, userEdited: true }
                            : c
                    )
                };
            });

            toast.success('AI edit applied successfully');
            setAiEditInstruction('');
        } catch (error) {
            console.error('Error applying AI edit:', error);
            toast.error('Failed to apply AI edit');
        } finally {
            setAiEditLoading(false);
        }
    };

    // Enhanced AI Chat for Story Editing
    const sendAiChatMessage = async (message: string, chapterId: string) => {
        if (!message.trim() || aiChatLoading) return;

        try {
            setAiChatLoading(true);

            const chapter = bookData?.chapters.find(c => c.id === chapterId);
            if (!chapter) return;

            // Add user message to chat
            const userMessage: ChatMessage = {
                id: Date.now().toString(),
                type: 'user',
                content: message,
                timestamp: new Date().toISOString()
            };

            setAiChatMessages(prev => [...prev, userMessage]);
            setAiChatInput('');

            // Prepare context for AI
            const currentContent = htmlToPlainText(editContent || chapter.content);

            const response = await axios.post(`${FASTAPI_BASE_URL}/api/book/ai-chat-edit`, {
                message,
                chapterId,
                bookId,
                currentContent,
                chatHistory: aiChatMessages.slice(-5), // Last 5 messages for context
                editContext: {
                    bookTitle: bookData?.title,
                    chapterTitle: chapter.title,
                    contentType: chapter.contentType
                }
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                // Add AI response to chat
                const aiMessage: ChatMessage = {
                    id: (Date.now() + 1).toString(),
                    type: 'ai',
                    content: response.data.response,
                    timestamp: new Date().toISOString()
                };

                setAiChatMessages(prev => [...prev, aiMessage]);

                // If AI provides a suggested edit, store it
                if (response.data.suggestedEdit) {
                    setPendingAiEdit(response.data.suggestedEdit);
                }

                // If AI provides quick suggestions
                if (response.data.suggestions) {
                    setAiSuggestions(response.data.suggestions);
                }
            } else {
                throw new Error(response.data.message || 'AI chat failed');
            }
        } catch (error: any) {
            console.error('Error in AI chat:', error);

            // Add error message to chat
            const errorMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                type: 'ai',
                content: 'I apologize, but I encountered an error while processing your request. Please try again or rephrase your question.',
                timestamp: new Date().toISOString()
            };

            setAiChatMessages(prev => [...prev, errorMessage]);
            toast.error('AI chat error - please try again');
        } finally {
            setAiChatLoading(false);
        }
    };

    const applyAiSuggestion = (suggestion: string) => {
        setEditContent(suggestion);
        setHasUnsavedChanges(true);
        setPendingAiEdit('');
        toast.success('AI suggestion applied to your content');
    };

    const startAiChat = (chapterId: string) => {
        setShowAiChat(true);

        // Add welcome message if this is the first time opening chat for this chapter
        if (aiChatMessages.length === 0) {
            const chapter = bookData?.chapters.find(c => c.id === chapterId);
            const welcomeMessage: ChatMessage = {
                id: 'welcome',
                type: 'ai',
                content: `Hi! I'm your AI writing assistant. I'm here to help you edit and improve "${chapter?.title || 'this chapter'}". 

You can ask me to:
• ✍️ Rewrite sections in different styles
• 📝 Add more details or descriptions  
• 🎭 Change the tone or mood
• 📚 Improve grammar and flow
• 💡 Suggest new ideas or plot points
• 🔄 Reorganize content structure

What would you like me to help you with?`,
                timestamp: new Date().toISOString()
            };
            setAiChatMessages([welcomeMessage]);
        }
    };

    const clearAiChat = () => {
        setAiChatMessages([]);
        setAiSuggestions([]);
        setPendingAiEdit('');
        setAiChatInput('');
    };

    const chatAboutBook = async (query: string) => {
        try {
            setChatLoading(true);

            // Add user message to chat
            const userMessage: ChatMessage = {
                id: Date.now().toString(),
                type: 'user',
                content: query,
                timestamp: new Date().toISOString()
            };

            setChatHistory(prev => [...prev, userMessage]);

            // Use the new book chat API endpoint
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            const response = await axios.post(`${apiUrl}/api/book-creation/books/${bookId}/chat`, {
                query: query
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                const aiMessage: ChatMessage = {
                    id: (Date.now() + 1).toString(),
                    type: 'ai',
                    content: response.data.response,
                    timestamp: new Date().toISOString()
                };

                setChatHistory(prev => [...prev, aiMessage]);
            } else {
                // Fallback response if API fails
                const aiMessage: ChatMessage = {
                    id: (Date.now() + 1).toString(),
                    type: 'ai',
                    content: response.data.message || "I'm sorry, I couldn't process your question right now. Please try again.",
                    timestamp: new Date().toISOString()
                };

                setChatHistory(prev => [...prev, aiMessage]);
            }

            setChatQuery('');
        } catch (error: any) {
            console.error('Error in book chat:', error);

            // Add error message to chat
            const errorMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                type: 'ai',
                content: `I encountered an error while processing your question about "${query}". Please try rephrasing your question or try again later.`,
                timestamp: new Date().toISOString()
            };

            setChatHistory(prev => [...prev, errorMessage]);
            toast.error('Failed to process chat message');
        } finally {
            setChatLoading(false);
        }
    };

    const downloadBook = async (format: 'html' | 'pdf' | 'epub') => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            const response = await axios.get(`${apiUrl}/api/book-creation/books/${bookId}/download/${format}`, {
                withCredentials: true
            });

            if (response.data.success) {
                if (response.data.download_url) {
                    // Extract the S3 URL from the response
                    const downloadUrl = response.data.download_url;
                    
                    // Check if the URL is a tuple format with success message
                    if (typeof downloadUrl === 'string' && downloadUrl.includes(',')) {
                        // Extract just the URL part
                        const urlMatch = downloadUrl.match(/https:\/\/[^,)]+/);
                        if (urlMatch && urlMatch[0]) {
                            window.open(urlMatch[0], '_blank');
                        } else {
                            window.open(downloadUrl, '_blank');
                        }
                    } else {
                        // Use the URL as is
                        window.open(downloadUrl, '_blank');
                    }
                } else if (response.data.content) {
                    // For HTML content, create a blob and download
                    const blob = new Blob([response.data.content], { type: 'text/html' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = response.data.filename || `book.${format}`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }
                toast.success(`Book downloaded in ${format.toUpperCase()} format`);
            } else {
                toast.error(response.data.message || 'Download failed');
                
                // If PDF or EPUB is not available, offer to regenerate
                if ((format === 'pdf' || format === 'epub') && 
                    response.data.message && 
                    response.data.message.includes('not available')) {
                    
                    setRegenerateFilesConfirm({
                        isOpen: true,
                        format: format
                    });
                }
            }
        } catch (error) {
            console.error(`Error downloading book in ${format} format:`, error);
            toast.error(`Failed to download book in ${format.toUpperCase()} format`);
        }
    };
    
    const regenerateBookFiles = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            toast.loading('Generating book files...');
            
            const response = await axios.post(`${apiUrl}/api/book-creation/books/${bookId}/regenerate-files`, {}, {
                withCredentials: true
            });
            
            if (response.data.success) {
                toast.success('Book files generated successfully!');
                // Update book data to reflect new URLs
                fetchBookData();
            } else {
                toast.error(response.data.message || 'Failed to generate book files');
            }
        } catch (error) {
            console.error('Error generating book files:', error);
            toast.error('Failed to generate book files');
        }
    };
    
    const regenerateAllBookFiles = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            toast.loading('Regenerating all book files...');
            
            const response = await axios.post(`${apiUrl}/api/book-creation/books/regenerate-all-files`, {}, {
                withCredentials: true
            });
            
            if (response.data.success) {
                toast.success(`Successfully regenerated files for ${response.data.results.filter((r: any) => r.success).length} books`);
                // Update book data to reflect new URLs
                fetchBookData();
            } else {
                toast.error(response.data.message || 'Failed to regenerate book files');
            }
        } catch (error) {
            console.error('Error regenerating all book files:', error);
            toast.error('Failed to regenerate all book files');
        }
    };
    
    // Function to save book settings
    const saveBookSettings = async () => {
        try {
            if (!bookData) return;
            
            setIsEditing(true); // Reuse the existing loading state
            
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            
            // Prepare the data to be sent
            const bookSettings = {
                title: bookData.title,
                subtitle: bookData.subtitle || '',
                description: bookData.description || '',
                bookStyle: bookData.bookStyle
            };
            
            // Since there's no specific endpoint for updating book settings,
            // we'll create a new endpoint on the backend later.
            // For now, we'll use a POST request to update the book
            const response = await axios.put(
                `${apiUrl}/api/book-creation/books/${bookId}`,
                bookSettings,
                { withCredentials: true }
            );
            
            if (response.data.success) {
                toast.success('Book settings saved successfully');
                setHasUnsavedChanges(false);
                
                // Update local book data with the response if needed
                if (response.data.book) {
                    setBookData(prev => {
                        if (!prev) return null;
                        return {
                            ...prev,
                            ...response.data.book
                        };
                    });
                }
            } else {
                toast.error(response.data.message || 'Failed to save book settings');
            }
        } catch (error: any) {
            console.error('Error saving book settings:', error);
            toast.error(error.response?.data?.message || 'Failed to save book settings');
        } finally {
            setIsEditing(false);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center space-y-4">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto" />
                    <p>Loading your book...</p>
                </div>
            </div>
        );
    }

    if (error || !bookData) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center space-y-4">
                    <AlertCircle className="h-8 w-8 text-red-500 mx-auto" />
                    <p className="text-red-500">{error || 'Book not found'}</p>
                    <Button onClick={() => router.push('/my-hub')} variant="outline">
                        <ArrowLeft className="h-4 w-4 mr-2" />
                        Back to Hub
                    </Button>
                </div>
            </div>
        );
    }

    const filteredChapters = bookData.chapters.filter(chapter => {
        const matchesSearch = searchQuery === '' ||
            chapter.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
            chapter.content.toLowerCase().includes(searchQuery.toLowerCase());

        const isSelected = selectedChapters.includes(chapter.id);

        return matchesSearch && (filterVisible ? isSelected : true);
    });

    return (
        <div className="min-h-screen bg-background">
            {/* Header */}
            <div className="border-b bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/50">
                <div className="container mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => router.push('/my-hub')}
                            >
                                <ArrowLeft className="h-4 w-4 mr-2" />
                                Back to Hub
                            </Button>
                            <div>
                                <h1 className="text-2xl font-bold">{bookData.title}</h1>
                                {bookData.subtitle && (
                                    <p className="text-muted-foreground">{bookData.subtitle}</p>
                                )}
                            </div>
                        </div>

                        <div className="flex items-center gap-2">
                            <Badge variant={bookData.generationStatus === 'completed' ? 'default' : 'secondary'}>
                                {bookData.generationStatus}
                            </Badge>
                            {hasUnsavedChanges && (
                                <Badge variant="outline" className="text-orange-500 border-orange-500">
                                    Unsaved Changes
                                </Badge>
                            )}
                            <Button size="sm" variant="outline" onClick={() => downloadBook('pdf')}>
                                <Download className="h-4 w-4 mr-2" />
                                Download
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="container mx-auto px-4 py-6">
                <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as any)} className="space-y-6">
                    <TabsList className="grid w-full grid-cols-4">
                        <TabsTrigger value="read" className="flex items-center gap-2">
                            <Eye className="h-4 w-4" />
                            Read
                        </TabsTrigger>
                        <TabsTrigger value="edit" className="flex items-center gap-2">
                            <Edit className="h-4 w-4" />
                            Edit
                        </TabsTrigger>
                        <TabsTrigger value="chat" className="flex items-center gap-2">
                            <MessageCircle className="h-4 w-4" />
                            Chat with AI
                        </TabsTrigger>
                        <TabsTrigger value="settings" className="flex items-center gap-2">
                            <Settings className="h-4 w-4" />
                            Settings
                        </TabsTrigger>
                    </TabsList>

                    {/* Read Tab */}
                    <TabsContent value="read" className="space-y-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-semibold">Book Content</h2>
                            <div className="flex items-center gap-2">
                                <Input
                                    placeholder="Search chapters..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-64"
                                />
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setFilterVisible(!filterVisible)}
                                >
                                    <Filter className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-4">
                            {filteredChapters.map((chapter) => (
                                <Card key={chapter.id} className={`transition-all ${!chapter.isVisible ? 'opacity-50' : ''}`}>
                                    <CardHeader>
                                        <div className="flex items-center justify-between">
                                            <CardTitle className="flex items-center gap-2">
                                                {chapter.title}
                                                {chapter.userEdited && (
                                                    <Badge variant="outline" className="text-xs">
                                                        Edited
                                                    </Badge>
                                                )}
                                                {chapter.aiGenerated && (
                                                    <Badge variant="secondary" className="text-xs">
                                                        <Sparkles className="h-3 w-3 mr-1" />
                                                        AI
                                                    </Badge>
                                                )}
                                            </CardTitle>
                                            <div className="flex items-center gap-2">
                                                <Badge variant="outline">{chapter.contentType}</Badge>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => toggleChapterVisibility(chapter.id)}
                                                >
                                                    {chapter.isVisible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                                                </Button>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: chapter.content }} />
                                        {chapter.tags.length > 0 && (
                                            <div className="flex items-center gap-2 mt-4 pt-4 border-t">
                                                <Tag className="h-4 w-4 text-muted-foreground" />
                                                {chapter.tags.map(tag => (
                                                    <Badge key={tag} variant="outline" className="text-xs">
                                                        {tag}
                                                    </Badge>
                                                ))}
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    </TabsContent>

                    {/* Edit Tab */}
                    <TabsContent value="edit" className="space-y-6">
                        <div className="flex items-center justify-between">
                            <h2 className="text-xl font-semibold">Edit Your Book</h2>
                            <div className="flex items-center gap-2">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => {
                                        setSelectedChapters(bookData.chapters.map(c => c.id));
                                    }}
                                >
                                    Select All
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setSelectedChapters([])}
                                >
                                    Clear Selection
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-4">
                            {bookData.chapters.map((chapter) => (
                                <Card key={chapter.id} className="group">
                                    <CardHeader>
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <input
                                                    type="checkbox"
                                                    checked={selectedChapters.includes(chapter.id)}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setSelectedChapters(prev => [...prev, chapter.id]);
                                                        } else {
                                                            setSelectedChapters(prev => prev.filter(id => id !== chapter.id));
                                                        }
                                                    }}
                                                    className="rounded border-gray-300"
                                                />
                                                <CardTitle>{chapter.title}</CardTitle>
                                            </div>
                                            <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => {
                                                        setEditingChapter(chapter.id);
                                                        // Convert HTML to plain text for editing
                                                        const plainTextContent = htmlToPlainText(chapter.content);
                                                        setEditContent(plainTextContent);
                                                    }}
                                                >
                                                    <Edit className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => deleteChapter(chapter.id)}
                                                    className="text-red-500 hover:text-red-700"
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        {editingChapter === chapter.id ? (
                                            <div className="space-y-4">
                                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center gap-2 text-blue-700 text-sm">
                                                            <Info className="h-4 w-4" />
                                                            <span>Editing Mode: HTML content has been converted to plain text for easy editing</span>
                                                        </div>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => setShowPreview(!showPreview)}
                                                            className="text-blue-700 border-blue-300 hover:text-blue-500"
                                                        >
                                                            {showPreview ? <EyeOff className="h-4 w-4 mr-1" /> : <Eye className="h-4 w-4 mr-1" />}
                                                            {showPreview ? 'Hide Preview' : 'Show Preview'}
                                                        </Button>
                                                    </div>
                                                </div>

                                                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                                                    <div>
                                                        <label className="text-sm font-medium mb-2 block">Edit Content</label>
                                                        <Textarea
                                                            value={editContent}
                                                            onChange={(e) => {
                                                                setEditContent(e.target.value);
                                                                setHasUnsavedChanges(true);
                                                            }}
                                                            className="min-h-[200px] bg-white text-gray-900 border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                                                            placeholder="Edit chapter content... Use **text** for bold, *text* for italic, • for bullet points"
                                                            style={{ color: '#111827' }}
                                                        />
                                                    </div>

                                                    {showPreview && (
                                                        <div>
                                                            <label className="text-sm font-medium mb-2 block">Preview</label>
                                                            <div
                                                                className="min-h-[200px] p-3 border rounded-lg bg-gray-50 overflow-auto prose prose-sm max-w-none text-black"
                                                                dangerouslySetInnerHTML={{
                                                                    __html: plainTextToHtml(editContent) || '<p class="text-gray-400 italic">Preview will appear here as you type...</p>'
                                                                }}
                                                            />
                                                        </div>
                                                    )}
                                                </div>

                                                {/* Enhanced AI Assistant Section */}
                                                <div className="border-t pt-4">
                                                    <div className="flex items-center justify-between mb-4">
                                                        <h4 className="font-medium flex items-center gap-2">
                                                            <Bot className="h-4 w-4" />
                                                            AI Writing Assistant
                                                        </h4>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => {
                                                                if (showAiChat) {
                                                                    setShowAiChat(false);
                                                                } else {
                                                                    startAiChat(chapter.id);
                                                                }
                                                            }}
                                                        >
                                                            {showAiChat ? (
                                                                <>
                                                                    <EyeOff className="h-4 w-4 mr-1" />
                                                                    Hide Chat
                                                                </>
                                                            ) : (
                                                                <>
                                                                    <MessageCircle className="h-4 w-4 mr-1" />
                                                                    Start Chat
                                                                </>
                                                            )}
                                                        </Button>
                                                    </div>

                                                    {/* Quick Action Buttons */}
                                                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2 mb-4">
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => {
                                                                startAiChat(chapter.id);
                                                                setAiChatInput("Please improve the writing style and flow of this chapter");
                                                            }}
                                                            className="text-xs"
                                                        >
                                                            ✨ Improve Style
                                                        </Button>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => {
                                                                startAiChat(chapter.id);
                                                                setAiChatInput("Add more descriptive details and imagery to make this more engaging");
                                                            }}
                                                            className="text-xs"
                                                        >
                                                            📝 Add Details
                                                        </Button>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => {
                                                                startAiChat(chapter.id);
                                                                setAiChatInput("Fix any grammar errors and improve sentence structure");
                                                            }}
                                                            className="text-xs"
                                                        >
                                                            📚 Fix Grammar
                                                        </Button>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => {
                                                                startAiChat(chapter.id);
                                                                setAiChatInput("Make this chapter more emotionally engaging and compelling");
                                                            }}
                                                            className="text-xs"
                                                        >
                                                            💝 Add Emotion
                                                        </Button>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => {
                                                                startAiChat(chapter.id);
                                                                setAiChatInput("Reorganize this content for better flow and structure");
                                                            }}
                                                            className="text-xs"
                                                        >
                                                            🔄 Restructure
                                                        </Button>
                                                        <Button
                                                            variant="outline"
                                                            size="sm"
                                                            onClick={() => {
                                                                startAiChat(chapter.id);
                                                                setAiChatInput("Suggest creative ideas to enhance this chapter");
                                                            }}
                                                            className="text-xs"
                                                        >
                                                            💡 Get Ideas
                                                        </Button>
                                                    </div>

                                                    {/* AI Chat Interface */}
                                                    {showAiChat && (
                                                        <div className="border rounded-lg p-4 bg-gray-50 space-y-4">
                                                            <div className="flex items-center justify-between">
                                                                <h5 className="font-medium text-sm">Chat with AI Assistant</h5>
                                                                <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    onClick={clearAiChat}
                                                                    className="text-xs"
                                                                >
                                                                    Clear Chat
                                                                </Button>
                                                            </div>

                                                            {/* Chat Messages */}
                                                            <ScrollArea className="h-64 w-full border rounded bg-white p-3">
                                                                <div className="space-y-3">
                                                                    {aiChatMessages.map((message) => (
                                                                        <div
                                                                            key={message.id}
                                                                            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                                                                        >
                                                                            <div
                                                                                className={`max-w-[80%] rounded-lg p-3 text-sm ${message.type === 'user'
                                                                                    ? 'bg-blue-500 text-white'
                                                                                    : 'bg-gray-100 text-gray-800'
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
                                                                                    <div className="whitespace-pre-wrap">{message.content}</div>
                                                                                )}
                                                                                <div className="text-xs opacity-70 mt-1">
                                                                                    {(() => {
                                                                                        if (message.timestamp) {
                                                                                            const utcDate = new Date(message.timestamp);
                                                                                            if (!isNaN(utcDate.getTime())) {
                                                                                                return utcDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                                                                                            }
                                                                                        }
                                                                                        return '';
                                                                                    })()}
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    ))}
                                                                    {aiChatLoading && (
                                                                        <div className="flex justify-start">
                                                                            <div className="bg-gray-100 rounded-lg p-3">
                                                                                <Loader2 className="h-4 w-4 animate-spin" />
                                                                            </div>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </ScrollArea>

                                                            {/* Pending AI Suggestion */}
                                                            {pendingAiEdit && (
                                                                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                                                                    <div className="flex items-center justify-between mb-2">
                                                                        <span className="text-sm font-medium text-green-800">AI Suggestion Ready</span>
                                                                        <Button
                                                                            size="sm"
                                                                            onClick={() => applyAiSuggestion(pendingAiEdit)}
                                                                            className="bg-green-600 hover:bg-green-700"
                                                                        >
                                                                            Apply to Content
                                                                        </Button>
                                                                    </div>
                                                                    <div className="text-sm text-green-700 max-h-32 overflow-auto">
                                                                        {pendingAiEdit.substring(0, 200)}...
                                                                    </div>
                                                                </div>
                                                            )}

                                                            {/* Quick Suggestions */}
                                                            {aiSuggestions.length > 0 && (
                                                                <div className="space-y-2">
                                                                    <span className="text-sm font-medium">Quick Suggestions:</span>
                                                                    <div className="flex flex-wrap gap-2">
                                                                        {aiSuggestions.map((suggestion, index) => (
                                                                            <Button
                                                                                key={index}
                                                                                variant="outline"
                                                                                size="sm"
                                                                                onClick={() => {
                                                                                    setAiChatInput(suggestion);
                                                                                }}
                                                                                className="text-xs"
                                                                            >
                                                                                {suggestion}
                                                                            </Button>
                                                                        ))}
                                                                    </div>
                                                                </div>
                                                            )}

                                                            {/* Chat Input */}
                                                            <div className="flex gap-2">
                                                                <Input
                                                                    placeholder="Ask AI to edit your story... (e.g., 'Make this more dramatic', 'Add dialogue', 'Change the tone')"
                                                                    value={aiChatInput}
                                                                    onChange={(e) => setAiChatInput(e.target.value)}
                                                                    onKeyPress={(e) => {
                                                                        if (e.key === 'Enter' && !e.shiftKey) {
                                                                            e.preventDefault();
                                                                            sendAiChatMessage(aiChatInput, chapter.id);
                                                                        }
                                                                    }}
                                                                    className="flex-1 bg-white text-gray-900 border-gray-300 focus:border-blue-500 focus:ring-blue-500 placeholder-gray-500 font-medium"
                                                                    style={{
                                                                        color: '#111827 !important',
                                                                        backgroundColor: 'white !important',
                                                                        fontSize: '14px',
                                                                        fontWeight: '500'
                                                                    }}
                                                                />
                                                                <Button
                                                                    onClick={() => sendAiChatMessage(aiChatInput, chapter.id)}
                                                                    disabled={!aiChatInput.trim() || aiChatLoading}
                                                                    size="sm"
                                                                >
                                                                    {aiChatLoading ? (
                                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                                    ) : (
                                                                        <Send className="h-4 w-4" />
                                                                    )}
                                                                </Button>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>

                                                <div className="flex gap-2">
                                                    <Button
                                                        onClick={() => saveChapterEdit(chapter.id, editContent)}
                                                        disabled={isEditing}
                                                    >
                                                        {isEditing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
                                                        Save Changes
                                                    </Button>
                                                    <Button
                                                        variant="outline"
                                                        onClick={() => {
                                                            setEditingChapter(null);
                                                            setEditContent('');
                                                            setAiEditInstruction('');
                                                            setHasUnsavedChanges(false);
                                                            setShowPreview(false);
                                                        }}
                                                    >
                                                        Cancel
                                                    </Button>
                                                    {chapter.originalContent && (
                                                        <Button
                                                            variant="ghost"
                                                            onClick={() => {
                                                                setEditContent(chapter.originalContent || chapter.content);
                                                                setHasUnsavedChanges(true);
                                                            }}
                                                        >
                                                            <RotateCcw className="h-4 w-4 mr-2" />
                                                            Restore Original
                                                        </Button>
                                                    )}
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: chapter.content }} />
                                        )}
                                    </CardContent>
                                </Card>
                            ))}
                        </div>

                        {selectedChapters.length > 0 && (
                            <div className="fixed bottom-6 right-6 bg-card border rounded-lg shadow-lg p-4">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm">{selectedChapters.length} chapters selected</span>
                                    <Button
                                        size="sm"
                                        variant="destructive"
                                        onClick={() => setDeleteSelectedChaptersConfirm(true)}
                                    >
                                        <Trash2 className="h-4 w-4 mr-2" />
                                        Delete Selected
                                    </Button>
                                </div>
                            </div>
                        )}
                    </TabsContent>

                    {/* Chat Tab */}
                    <TabsContent value="chat" className="space-y-6">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Chat About Your Book</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <ScrollArea className="h-[400px] mb-4">
                                        <div className="space-y-4">
                                            {chatHistory.map((message) => (
                                                <div
                                                    key={message.id}
                                                    className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                                                >
                                                    <div
                                                        className={`max-w-[80%] p-3 rounded-lg ${message.type === 'user'
                                                            ? 'bg-primary text-primary-foreground'
                                                            : 'bg-muted'
                                                            }`}
                                                    >
                                                        <p className="text-sm">{message.content}</p>
                                                        <span className="text-xs opacity-70">
                                                            {new Date(message.timestamp).toLocaleTimeString()}
                                                        </span>
                                                    </div>
                                                </div>
                                            ))}
                                            {chatLoading && (
                                                <div className="flex justify-start">
                                                    <div className="bg-muted p-3 rounded-lg">
                                                        <Loader2 className="h-4 w-4 animate-spin" />
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </ScrollArea>

                                    <div className="flex gap-2">
                                        <Input
                                            placeholder="Ask about your book content..."
                                            value={chatQuery}
                                            onChange={(e) => setChatQuery(e.target.value)}
                                            onKeyPress={(e) => {
                                                if (e.key === 'Enter' && chatQuery.trim()) {
                                                    chatAboutBook(chatQuery);
                                                }
                                            }}
                                        />
                                        <Button
                                            onClick={() => chatAboutBook(chatQuery)}
                                            disabled={!chatQuery.trim() || chatLoading}
                                        >
                                            <Send className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader>
                                    <CardTitle>Quick Actions</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-3">
                                    <Button
                                        variant="outline"
                                        className="w-full justify-start"
                                        onClick={() => chatAboutBook("What are the main themes in my book?")}
                                    >
                                        <Sparkles className="h-4 w-4 mr-2" />
                                        Analyze main themes
                                    </Button>
                                    <Button
                                        variant="outline"
                                        className="w-full justify-start"
                                        onClick={() => chatAboutBook("Suggest improvements to my book structure")}
                                    >
                                        <Edit className="h-4 w-4 mr-2" />
                                        Suggest improvements
                                    </Button>
                                    <Button
                                        variant="outline"
                                        className="w-full justify-start"
                                        onClick={() => chatAboutBook("Create a summary of my book")}
                                    >
                                        <FileText className="h-4 w-4 mr-2" />
                                        Generate summary
                                    </Button>
                                    <Button
                                        variant="outline"
                                        className="w-full justify-start"
                                        onClick={() => chatAboutBook("Find gaps in my pet's story")}
                                    >
                                        <Search className="h-4 w-4 mr-2" />
                                        Find story gaps
                                    </Button>
                                </CardContent>
                            </Card>
                        </div>
                    </TabsContent>

                    {/* Settings Tab */}
                    <TabsContent value="settings" className="space-y-6">
                        <Card>
                            <CardHeader>
                                <CardTitle>Book Settings</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-sm font-medium">Book Title</label>
                                        <Input
                                            value={bookData.title}
                                            onChange={(e) => {
                                                setBookData(prev => prev ? { ...prev, title: e.target.value } : null);
                                                setHasUnsavedChanges(true);
                                            }}
                                        />
                                    </div>
                                    <div>
                                        <label className="text-sm font-medium">Subtitle</label>
                                        <Input
                                            value={bookData.subtitle || ''}
                                            onChange={(e) => {
                                                setBookData(prev => prev ? { ...prev, subtitle: e.target.value } : null);
                                                setHasUnsavedChanges(true);
                                            }}
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="text-sm font-medium">Description</label>
                                    <Textarea
                                        value={bookData.description || ''}
                                        onChange={(e) => {
                                            setBookData(prev => prev ? { ...prev, description: e.target.value } : null);
                                            setHasUnsavedChanges(true);
                                        }}
                                    />
                                </div>

                                <div>
                                    <label className="text-sm font-medium">Book Style</label>
                                    <Select
                                        value={bookData.bookStyle}
                                        onValueChange={(value: any) => {
                                            setBookData(prev => prev ? { ...prev, bookStyle: value } : null);
                                            setHasUnsavedChanges(true);
                                        }}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="narrative">Narrative</SelectItem>
                                            <SelectItem value="timeline">Timeline</SelectItem>
                                            <SelectItem value="reference">Reference</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="pt-4 border-t">
                                    <h4 className="font-medium mb-4">Download Options</h4>
                                    <div className="flex gap-2">
                                        <Button onClick={() => downloadBook('html')} variant="outline">
                                            <Download className="h-4 w-4 mr-2" />
                                            HTML
                                        </Button>
                                        <Button onClick={() => downloadBook('pdf')} variant="outline">
                                            <Download className="h-4 w-4 mr-2" />
                                            PDF
                                        </Button>
                                        <Button onClick={() => downloadBook('epub')} variant="outline">
                                            <Download className="h-4 w-4 mr-2" />
                                            EPUB
                                        </Button>
                                        <Button onClick={regenerateBookFiles} variant="outline">
                                            <RefreshCw className="h-4 w-4 mr-2" />
                                            Regenerate Files
                                        </Button>
                                        <Button onClick={regenerateAllBookFiles} variant="outline" className="ml-auto">
                                            <RefreshCw className="h-4 w-4 mr-2" />
                                            Regenerate All Files
                                        </Button>
                                    </div>
                                </div>
                                
                                {/* Save Settings Button */}
                                <div className="pt-4 border-t">
                                    <div className="flex justify-between items-center">
                                        <div>
                                            {hasUnsavedChanges && (
                                                <span className="text-orange-500 font-medium">
                                                    You have unsaved changes
                                                </span>
                                            )}
                                        </div>
                                        <Button 
                                            onClick={saveBookSettings} 
                                            disabled={!hasUnsavedChanges || isEditing}
                                            className="ml-auto"
                                        >
                                            {isEditing ? (
                                                <>
                                                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                                                    Saving...
                                                </>
                                            ) : (
                                                <>
                                                    <Save className="h-4 w-4 mr-2" />
                                                    Save Settings
                                                </>
                                            )}
                                        </Button>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        <Card>
                            <CardHeader>
                                <CardTitle>Book Statistics</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div className="text-center">
                                        <div className="text-2xl font-bold">{bookData.chapters.length}</div>
                                        <div className="text-sm text-muted-foreground">Chapters</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-2xl font-bold">{bookData.totalContentItems}</div>
                                        <div className="text-sm text-muted-foreground">Content Items</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-2xl font-bold">
                                            {bookData.chapters.filter(c => c.userEdited).length}
                                        </div>
                                        <div className="text-sm text-muted-foreground">Edited Chapters</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-2xl font-bold">
                                            {Math.round(bookData.chapters.reduce((acc, c) => acc + c.content.length, 0) / 1000)}k
                                        </div>
                                        <div className="text-sm text-muted-foreground">Characters</div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </TabsContent>
                </Tabs>
            </div>

            {/* Confirm Dialogs */}
            <ConfirmDialog
                isOpen={deleteChapterConfirm.isOpen}
                onClose={() => setDeleteChapterConfirm({ isOpen: false, chapterId: null })}
                onConfirm={confirmDeleteChapter}
                title="Confirm Deletion"
                message="Are you sure you want to delete this chapter? This action cannot be undone."
            />
            <ConfirmDialog
                isOpen={deleteSelectedChaptersConfirm}
                onClose={() => setDeleteSelectedChaptersConfirm(false)}
                onConfirm={deleteMultipleChapters}
                title="Confirm Deletion"
                message="Are you sure you want to delete the selected chapters? This action cannot be undone."
            />
            <ConfirmDialog
                isOpen={regenerateFilesConfirm.isOpen}
                onClose={() => setRegenerateFilesConfirm({ isOpen: false, format: '' })}
                onConfirm={() => {
                    regenerateBookFiles();
                    setRegenerateFilesConfirm({ isOpen: false, format: '' });
                }}
                title="Generate Book Files"
                message={`${regenerateFilesConfirm.format.toUpperCase()} file is not available. Would you like to generate it now?`}
            />
        </div>
    );
};

export default BookEditorPage; 