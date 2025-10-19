"use client"

import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import { motion, AnimatePresence } from 'motion/react';
import {
    BookOpen,
    Tags,
    Calendar,
    FileText,
    Camera,
    MessageSquare,
    Search,
    Sparkles,
    Clock,
    Download,
    Eye,
    Palette,
    Settings,
    ChevronRight,
    CheckCircle,
    X,
    AlertCircle,
    Loader2
} from 'lucide-react';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';
import { useAuth } from '@/context/AuthContext';

interface BookTag {
    id: number;
    name: string;
    description: string;
    color: string;
    icon: string;
    category_order: number;
    is_active: boolean;
}

interface ContentSummary {
    total_items: number;
    chat_messages: number;
    photos: number;
    documents: number;
}

interface BookEstimates {
    estimated_chapters: number;
    estimated_pages: number;
    estimated_words: number;
}

interface PreviewData {
    content_summary: ContentSummary;
    book_estimates: BookEstimates;
    content_samples: {
        recent_messages: any[];
        recent_photos: any[];
        recent_documents: any[];
    };
    selected_tags: number[];
    date_range: {
        start?: string;
        end?: string;
    };
}

interface BookCreationModalProps {
    isOpen: boolean;
    onClose: () => void;
}

type BookCreationStep = 'setup' | 'tags' | 'content' | 'preview' | 'generate' | 'complete';

const BookCreationModal: React.FC<BookCreationModalProps> = ({ isOpen, onClose }) => {
    const { user } = useAuth();

    // State management
    const [currentStep, setCurrentStep] = useState<BookCreationStep>('setup');
    const [bookTags, setBookTags] = useState<BookTag[]>([]);
    const [selectedTags, setSelectedTags] = useState<number[]>([]);
    const [contentTypes, setContentTypes] = useState<string[]>(['chat', 'photos', 'documents']);
    const [dateRange, setDateRange] = useState<{ start?: string, end?: string }>({});

    // Book configuration
    const [bookTitle, setBookTitle] = useState('');
    const [bookSubtitle, setBookSubtitle] = useState('');
    const [bookDescription, setBookDescription] = useState('');
    const [bookStyle, setBookStyle] = useState<'narrative' | 'timeline' | 'reference'>('narrative');
    const [includePhotos, setIncludePhotos] = useState(true);
    const [includeDocuments, setIncludeDocuments] = useState(true);
    const [includeChatHistory, setIncludeChatHistory] = useState(true);
    const [autoOrganizeByDate, setAutoOrganizeByDate] = useState(true);

    // Preview and generation state
    const [previewData, setPreviewData] = useState<PreviewData | null>(null);
    const [isLoadingPreview, setIsLoadingPreview] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [generationProgress, setGenerationProgress] = useState(0);
    const [generatedBookId, setGeneratedBookId] = useState<number | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Load book tags on component mount
    useEffect(() => {
        if (isOpen && bookTags.length === 0) {
            fetchBookTags();
        }
    }, [isOpen]);

    // Reset state when modal closes
    useEffect(() => {
        if (!isOpen) {
            setCurrentStep('setup');
            setError(null);
            setPreviewData(null);
            setIsGenerating(false);
            setGenerationProgress(0);
            setGeneratedBookId(null);
        }
    }, [isOpen]);

    const fetchBookTags = async () => {
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            const response = await axios.get(`${apiUrl}/api/book-creation/tags`, {
                withCredentials: true
            });

            if (response.data.success) {
                setBookTags(response.data.tags);
            } else {
                toast.error('Failed to load book categories');
            }
        } catch (error) {
            console.error('Error fetching book tags:', error);
            toast.error('Failed to load book categories');
        }
    };

    const generatePreview = async () => {
        setIsLoadingPreview(true);
        setError(null);

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            const response = await axios.post(`${apiUrl}/api/book-creation/preview`, {
                selected_tags: selectedTags,
                date_range_start: dateRange.start,
                date_range_end: dateRange.end,
                content_types: contentTypes
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                setPreviewData(response.data.preview);
                setCurrentStep('preview');
            } else {
                setError(response.data.message || 'Failed to generate preview');
            }
        } catch (error: any) {
            console.error('Error generating preview:', error);
            setError(error.response?.data?.message || 'Failed to generate preview');
        } finally {
            setIsLoadingPreview(false);
        }
    };

    const generateBook = async () => {
        setIsGenerating(true);
        setGenerationProgress(0);
        setError(null);

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
            const response = await axios.post(`${apiUrl}/api/book-creation/generate`, {
                title: bookTitle,
                subtitle: bookSubtitle,
                description: bookDescription,
                selected_tags: selectedTags,
                date_range_start: dateRange.start,
                date_range_end: dateRange.end,
                content_types: contentTypes,
                book_style: bookStyle,
                include_photos: includePhotos,
                include_documents: includeDocuments,
                include_chat_history: includeChatHistory,
                auto_organize_by_date: autoOrganizeByDate
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                setGeneratedBookId(response.data.book_id);
                setGenerationProgress(100);
                setCurrentStep('complete');
                toast.success('Your custom book has been generated successfully!');
            } else {
                setError(response.data.message || 'Failed to generate book');
            }
        } catch (error: any) {
            console.error('Error generating book:', error);
            setError(error.response?.data?.message || 'Failed to generate book');
        } finally {
            setIsGenerating(false);
        }
    };

    const toggleTag = (tagId: number) => {
        setSelectedTags(prev =>
            prev.includes(tagId)
                ? prev.filter(id => id !== tagId)
                : [...prev, tagId]
        );
    };

    const toggleContentType = (type: string) => {
        setContentTypes(prev =>
            prev.includes(type)
                ? prev.filter(t => t !== type)
                : [...prev, type]
        );
    };

    const getStepTitle = () => {
        switch (currentStep) {
            case 'setup': return 'Book Setup';
            case 'tags': return 'Choose Categories';
            case 'content': return 'Content Selection';
            case 'preview': return 'Preview & Customize';
            case 'generate': return 'Generating Book';
            case 'complete': return 'Book Complete';
            default: return 'Create Your Book';
        }
    };

    const canProceed = () => {
        switch (currentStep) {
            case 'setup': return bookTitle.trim().length > 0;
            case 'tags': return true; // Allow proceeding with or without tags selected
            case 'content': return contentTypes.length > 0;
            case 'preview': return true;
            default: return false;
        }
    };

    const nextStep = () => {
        if (currentStep === 'setup') {
            setCurrentStep('tags');
        } else if (currentStep === 'tags') {
            setCurrentStep('content');
        } else if (currentStep === 'content') {
            generatePreview();
        } else if (currentStep === 'preview') {
            setCurrentStep('generate');
            generateBook();
        }
    };

    const prevStep = () => {
        if (currentStep === 'tags') {
            setCurrentStep('setup');
        } else if (currentStep === 'content') {
            setCurrentStep('tags');
        } else if (currentStep === 'preview') {
            setCurrentStep('content');
        }
    };

    const renderStepContent = () => {
        switch (currentStep) {
            case 'setup':
                return (
                    <div className="space-y-6">
                        <div className="text-center mb-6">
                            <BookOpen className="h-16 w-16 mx-auto text-primary mb-4" />
                            <h3 className="text-xl font-semibold mb-2">Create Your Custom Book</h3>
                            <p className="text-muted-foreground">
                                Transform your pet's memories into a beautiful, personalized book
                            </p>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">Book Title *</label>
                                <Input
                                    value={bookTitle}
                                    onChange={(e) => setBookTitle(e.target.value)}
                                    placeholder="e.g., Adventures with Max"
                                    className="text-lg"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Subtitle (Optional)</label>
                                <Input
                                    value={bookSubtitle}
                                    onChange={(e) => setBookSubtitle(e.target.value)}
                                    placeholder="e.g., A Journey of Love and Companionship"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Description (Optional)</label>
                                <Textarea
                                    value={bookDescription}
                                    onChange={(e) => setBookDescription(e.target.value)}
                                    placeholder="Describe what this book means to you..."
                                    rows={3}
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">Book Style</label>
                                <Select value={bookStyle} onValueChange={(value: any) => setBookStyle(value)}>
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="narrative">Narrative - Story-like flow</SelectItem>
                                        <SelectItem value="timeline">Timeline - Chronological order</SelectItem>
                                        <SelectItem value="reference">Reference - Organized by category</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                    </div>
                );

            case 'tags':
                return (
                    <div className="space-y-6">
                        <div className="text-center mb-6">
                            <Tags className="h-16 w-16 mx-auto text-primary mb-4" />
                            <h3 className="text-xl font-semibold mb-2">Choose Content Categories</h3>
                            <p className="text-muted-foreground">
                                Select categories to organize your book, or leave unselected to include all content
                            </p>
                        </div>

                        {/* Tag selection explanation */}
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                            <div className="flex items-start gap-2">
                                <Sparkles className="h-5 w-5 text-blue-600 mt-0.5" />
                                <div>
                                    <div className="text-sm font-medium text-blue-800">How category selection works:</div>
                                    <div className="text-sm text-blue-700 mt-1">
                                        • <strong>No categories selected:</strong> Include ALL your photos, documents, and conversations<br />
                                        • <strong>Categories selected:</strong> Filter content to match your chosen themes<br />
                                        • <strong>Tip:</strong> Start with no selection to see all your content, then add specific categories if needed
                                    </div>
                                </div>
                            </div>
                        </div>

                        {error && (
                            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                                <div className="flex items-center gap-2">
                                    <X className="h-4 w-4 text-red-600" />
                                    <span className="text-red-800 text-sm">{error}</span>
                                </div>
                            </div>
                        )}

                        {bookTags.length === 0 ? (
                            <div className="text-center py-8">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                                <p className="text-muted-foreground">Loading categories...</p>
                            </div>
                        ) : (
                            <ScrollArea className="h-96">
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {bookTags.map((tag) => (
                                        <div
                                            key={tag.id}
                                            onClick={() => toggleTag(tag.id)}
                                            className={`p-4 rounded-lg border cursor-pointer transition-all hover:shadow-md ${selectedTags.includes(tag.id)
                                                ? 'border-primary bg-primary/10 ring-2 ring-primary/20'
                                                : 'border-gray-200 hover:border-gray-300'
                                                }`}
                                        >
                                            <div className="flex items-start gap-3">
                                                <div
                                                    className="w-4 h-4 rounded-full mt-1 flex-shrink-0"
                                                    style={{ backgroundColor: tag.color }}
                                                />
                                                <div className="flex-1">
                                                    <div className="font-medium text-sm">{tag.name}</div>
                                                    {tag.description && (
                                                        <div className="text-xs text-muted-foreground mt-1">
                                                            {tag.description}
                                                        </div>
                                                    )}
                                                </div>
                                                {selectedTags.includes(tag.id) && (
                                                    <div className="text-primary">
                                                        <CheckCircle className="h-5 w-5" />
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </ScrollArea>
                        )}

                        <div className="text-center text-sm text-muted-foreground">
                            {selectedTags.length === 0 ? (
                                <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                                    <div className="text-green-800 font-medium">All content will be included</div>
                                    <div className="text-green-700 text-xs mt-1">Perfect for comprehensive books with all your memories</div>
                                </div>
                            ) : (
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                                    <div className="text-blue-800 font-medium">{selectedTags.length} categories selected</div>
                                    <div className="text-blue-700 text-xs mt-1">Content will be filtered to match these themes</div>
                                </div>
                            )}
                        </div>
                    </div>
                );

            case 'content':
                return (
                    <div className="space-y-6">
                        <div className="text-center mb-6">
                            <Settings className="h-16 w-16 mx-auto text-primary mb-4" />
                            <h3 className="text-xl font-semibold mb-2">Content Selection</h3>
                            <p className="text-muted-foreground">
                                Choose what types of content to include in your book
                            </p>
                        </div>

                        <div className="space-y-6">
                            {/* Content Types */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <FileText className="h-5 w-5" />
                                        Content Types
                                    </CardTitle>
                                    <CardDescription>
                                        Select the types of content to include
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center space-x-3">
                                            <MessageSquare className="h-5 w-5 text-blue-500" />
                                            <div>
                                                <p className="font-medium">Chat Messages</p>
                                                <p className="text-sm text-muted-foreground">
                                                    Conversations and interactions
                                                </p>
                                            </div>
                                        </div>
                                        <Switch
                                            checked={contentTypes.includes('chat')}
                                            onCheckedChange={() => toggleContentType('chat')}
                                        />
                                    </div>

                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center space-x-3">
                                            <Camera className="h-5 w-5 text-green-500" />
                                            <div>
                                                <p className="font-medium">Photos</p>
                                                <p className="text-sm text-muted-foreground">
                                                    Images and visual memories
                                                </p>
                                            </div>
                                        </div>
                                        <Switch
                                            checked={contentTypes.includes('photos')}
                                            onCheckedChange={() => toggleContentType('photos')}
                                        />
                                    </div>

                                    <div className="flex items-center justify-between">
                                        <div className="flex items-center space-x-3">
                                            <FileText className="h-5 w-5 text-purple-500" />
                                            <div>
                                                <p className="font-medium">Documents</p>
                                                <p className="text-sm text-muted-foreground">
                                                    Uploaded files and records
                                                </p>
                                            </div>
                                        </div>
                                        <Switch
                                            checked={contentTypes.includes('documents')}
                                            onCheckedChange={() => toggleContentType('documents')}
                                        />
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Date Range */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Calendar className="h-5 w-5" />
                                        Date Range (Optional)
                                    </CardTitle>
                                    <CardDescription>
                                        Limit content to a specific time period
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4">
                                        <div>
                                            <label className="block text-sm font-medium mb-2">Start Date</label>
                                            <Input
                                                type="date"
                                                value={dateRange.start || ''}
                                                onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                                                className="[&::-webkit-calendar-picker-indicator]:filter [&::-webkit-calendar-picker-indicator]:invert"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium mb-2">End Date</label>
                                            <Input
                                                type="date"
                                                value={dateRange.end || ''}
                                                onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                                                className="[&::-webkit-calendar-picker-indicator]:filter [&::-webkit-calendar-picker-indicator]:invert"
                                            />
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            {/* Additional Options */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Organization Options</CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex items-center justify-between">
                                        <div>
                                            <p className="font-medium">Auto-organize by date</p>
                                            <p className="text-sm text-muted-foreground">
                                                Automatically sort content chronologically
                                            </p>
                                        </div>
                                        <Switch
                                            checked={autoOrganizeByDate}
                                            onCheckedChange={setAutoOrganizeByDate}
                                        />
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                );

            case 'preview':
                return (
                    <div className="space-y-6">
                        <div className="text-center mb-6">
                            <Eye className="h-16 w-16 mx-auto text-primary mb-4" />
                            <h3 className="text-xl font-semibold mb-2">Book Preview</h3>
                            <p className="text-muted-foreground">
                                Review your book configuration and content
                            </p>
                        </div>

                        {previewData && (
                            <div className="space-y-6">
                                {/* Book Info */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle>{bookTitle}</CardTitle>
                                        {bookSubtitle && <CardDescription>{bookSubtitle}</CardDescription>}
                                    </CardHeader>
                                    <CardContent>
                                        {bookDescription && <p className="text-sm text-muted-foreground mb-4">{bookDescription}</p>}
                                        <div className="flex items-center gap-4 text-sm">
                                            <span className="flex items-center gap-1">
                                                <Palette className="h-4 w-4" />
                                                {bookStyle}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <Tags className="h-4 w-4" />
                                                {selectedTags.length} categories
                                            </span>
                                        </div>
                                    </CardContent>
                                </Card>

                                {/* Content Summary */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <FileText className="h-5 w-5" />
                                            Content Summary
                                        </CardTitle>
                                        <CardDescription>
                                            Based on your selected filters, we found the following content to include in your book
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div className="text-center">
                                                <div className="text-2xl font-bold text-primary">
                                                    {previewData.content_summary.total_items}
                                                </div>
                                                <div className="text-sm text-muted-foreground">Total Items</div>
                                            </div>
                                            <div className="text-center">
                                                <div className={`text-2xl font-bold ${previewData.content_summary.chat_messages > 0 ? 'text-blue-500' : 'text-gray-400'}`}>
                                                    {previewData.content_summary.chat_messages}
                                                </div>
                                                <div className="text-sm text-muted-foreground flex items-center justify-center gap-1">
                                                    <MessageSquare className="h-3 w-3" />
                                                    Messages
                                                </div>
                                                {previewData.content_summary.chat_messages === 0 && (
                                                    <div className="text-xs text-muted-foreground mt-1">
                                                        No chat history found
                                                    </div>
                                                )}
                                            </div>
                                            <div className="text-center">
                                                <div className={`text-2xl font-bold ${previewData.content_summary.photos > 0 ? 'text-green-500' : 'text-gray-400'}`}>
                                                    {previewData.content_summary.photos}
                                                </div>
                                                <div className="text-sm text-muted-foreground flex items-center justify-center gap-1">
                                                    <Camera className="h-3 w-3" />
                                                    Photos
                                                </div>
                                                {previewData.content_summary.photos === 0 && (
                                                    <div className="text-xs text-muted-foreground mt-1">
                                                        Try uploading photos to Gallery
                                                    </div>
                                                )}
                                            </div>
                                            <div className="text-center">
                                                <div className={`text-2xl font-bold ${previewData.content_summary.documents > 0 ? 'text-purple-500' : 'text-gray-400'}`}>
                                                    {previewData.content_summary.documents}
                                                </div>
                                                <div className="text-sm text-muted-foreground flex items-center justify-center gap-1">
                                                    <FileText className="h-3 w-3" />
                                                    Documents
                                                </div>
                                                {previewData.content_summary.documents === 0 && (
                                                    <div className="text-xs text-muted-foreground mt-1">
                                                        Try uploading documents
                                                    </div>
                                                )}
                                            </div>
                                        </div>

                                        {/* Show total content status */}
                                        {previewData.content_summary.total_items === 0 && (
                                            <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                                                <div className="flex items-center gap-2">
                                                    <AlertCircle className="h-5 w-5 text-yellow-600" />
                                                    <div className="text-sm font-medium text-yellow-800">No content found</div>
                                                </div>
                                                <div className="text-sm text-yellow-700 mt-2">
                                                    To create your book, please:
                                                    <ul className="list-disc list-inside mt-1 space-y-1">
                                                        <li>Have conversations in the chat</li>
                                                        <li>Upload photos to your Gallery</li>
                                                        <li>Upload documents to your Care Archive</li>
                                                    </ul>
                                                </div>
                                            </div>
                                        )}

                                        {previewData.content_summary.total_items > 0 && (
                                            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                                                <div className="flex items-center gap-2">
                                                    <CheckCircle className="h-5 w-5 text-green-600" />
                                                    <div className="text-sm font-medium text-green-800">
                                                        Great! We found {previewData.content_summary.total_items} items to include in your book
                                                    </div>
                                                </div>
                                                <div className="text-sm text-green-700 mt-1">
                                                    Your book will be organized into chapters based on your selected categories and dates.
                                                </div>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>

                                {/* Book Estimates */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle>Estimated Book Details</CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="grid grid-cols-3 gap-4">
                                            <div className="text-center">
                                                <div className="text-xl font-bold">
                                                    {previewData.book_estimates.estimated_chapters}
                                                </div>
                                                <div className="text-sm text-muted-foreground">Chapters</div>
                                            </div>
                                            <div className="text-center">
                                                <div className="text-xl font-bold">
                                                    {previewData.book_estimates.estimated_pages}
                                                </div>
                                                <div className="text-sm text-muted-foreground">Pages</div>
                                            </div>
                                            <div className="text-center">
                                                <div className="text-xl font-bold">
                                                    {previewData.book_estimates.estimated_words.toLocaleString()}
                                                </div>
                                                <div className="text-sm text-muted-foreground">Words</div>
                                            </div>
                                        </div>
                                    </CardContent>
                                </Card>
                            </div>
                        )}
                    </div>
                );

            case 'generate':
                return (
                    <div className="space-y-6 text-center">
                        <div className="mb-6">
                            <Sparkles className="h-16 w-16 mx-auto text-primary mb-4 animate-pulse" />
                            <h3 className="text-xl font-semibold mb-2">Generating Your Book</h3>
                            <p className="text-muted-foreground">
                                Please wait while we create your personalized book...
                            </p>
                        </div>

                        <div className="space-y-4">
                            <Progress value={generationProgress} className="w-full" />
                            <p className="text-sm text-muted-foreground">
                                {generationProgress}% complete
                            </p>
                        </div>

                        <div className="flex items-center justify-center space-x-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm">Processing your memories...</span>
                        </div>
                    </div>
                );

            case 'complete':
                return (
                    <div className="space-y-6 text-center">
                        <div className="mb-6">
                            <CheckCircle className="h-16 w-16 mx-auto text-green-500 mb-4" />
                            <h3 className="text-xl font-semibold mb-2">Book Generated Successfully!</h3>
                            <p className="text-muted-foreground">
                                Your personalized book "{bookTitle}" is ready
                            </p>
                        </div>

                        <div className="space-y-4">
                            <Button
                                onClick={() => {
                                    // Navigate to the specific book editor page
                                    if (generatedBookId) {
                                        window.location.href = `/book/${generatedBookId}`;
                                    } else {
                                        toast.error('Book ID not available');
                                    }
                                }}
                                className="w-full"
                                disabled={!generatedBookId}
                            >
                                <BookOpen className="h-4 w-4 mr-2" />
                                View My Book
                            </Button>

                            <Button
                                variant="outline"
                                onClick={onClose}
                                className="w-full"
                            >
                                Create Another Book
                            </Button>
                        </div>
                    </div>
                );

            default:
                return null;
        }
    };

    return (
        <Dialog open={isOpen} onOpenChange={onClose}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto custom-scrollbar">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <BookOpen className="h-5 w-5" />
                        {getStepTitle()}
                    </DialogTitle>
                </DialogHeader>

                <div className="mt-6">
                    {/* Step Indicator */}
                    {currentStep !== 'complete' && (
                        <div className="flex items-center justify-center mb-8">
                            <div className="flex items-center space-x-2">
                                {['setup', 'tags', 'content', 'preview'].map((step, index) => (
                                    <React.Fragment key={step}>
                                        <div className={`
                                            w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium
                                            ${currentStep === step
                                                ? 'bg-primary text-primary-foreground'
                                                : ['setup', 'tags', 'content', 'preview'].indexOf(currentStep) > index
                                                    ? 'bg-green-500 text-white'
                                                    : 'bg-muted text-muted-foreground'
                                            }
                                        `}>
                                            {['setup', 'tags', 'content', 'preview'].indexOf(currentStep) > index ? (
                                                <CheckCircle className="h-4 w-4" />
                                            ) : (
                                                index + 1
                                            )}
                                        </div>
                                        {index < 3 && (
                                            <div className={`
                                                w-8 h-0.5 
                                                ${['setup', 'tags', 'content', 'preview'].indexOf(currentStep) > index
                                                    ? 'bg-green-500'
                                                    : 'bg-muted'
                                                }
                                            `} />
                                        )}
                                    </React.Fragment>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Error Display */}
                    {error && (
                        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2">
                            <AlertCircle className="h-4 w-4 text-red-500" />
                            <span className="text-red-700">{error}</span>
                        </div>
                    )}

                    {/* Step Content */}
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={currentStep}
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            transition={{ duration: 0.3 }}
                        >
                            {renderStepContent()}
                        </motion.div>
                    </AnimatePresence>

                    {/* Navigation Buttons */}
                    {currentStep !== 'generate' && currentStep !== 'complete' && (
                        <div className="flex justify-between mt-8">
                            <Button
                                variant="outline"
                                onClick={prevStep}
                                disabled={currentStep === 'setup'}
                            >
                                Previous
                            </Button>

                            <Button
                                onClick={nextStep}
                                disabled={!canProceed() || isLoadingPreview}
                                className="flex items-center gap-2"
                            >
                                {isLoadingPreview ? (
                                    <>
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                        Loading...
                                    </>
                                ) : currentStep === 'preview' ? (
                                    <>
                                        <Sparkles className="h-4 w-4" />
                                        Generate Book
                                    </>
                                ) : (
                                    <>
                                        Next
                                        <ChevronRight className="h-4 w-4" />
                                    </>
                                )}
                            </Button>
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
};

export default BookCreationModal; 