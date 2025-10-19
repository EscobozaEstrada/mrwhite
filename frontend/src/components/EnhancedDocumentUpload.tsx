'use client';

import React, { useState, useRef } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { ScrollArea } from './ui/scroll-area';
// Alert component removed as it's not available in the current UI library
import {
    Upload,
    FileText,
    CheckCircle,
    AlertCircle,
    MessageCircle,
    Bot,
    Sparkles,
    Heart,
    Search,
    Download,
    X,
    Info
} from 'lucide-react';

interface ProcessingResult {
    document_type: string;
    summary: string;
    key_insights: string[];
    pet_information: any;
    health_information: any;
    care_instructions: any[];
    quality_score: number;
    vector_stored: boolean;
    chunks_created: number;
    workflow_trace: string[];
}

interface DocumentUploadResult {
    success: boolean;
    message: string;
    document: any;
    processing_summary: ProcessingResult;
    s3_url: string;
}

interface DocumentChatResult {
    success: boolean;
    response: string;
    intent: string;
    confidence_score: number;
    documents_found: any[];
    selected_document: any;
    follow_up_suggestions: string[];
    related_documents: any[];
    tools_used: string[];
    workflow_trace: string[];
    response_type: string;
}

export default function EnhancedDocumentUpload() {
    const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'processing' | 'completed' | 'error'>('idle');
    const [uploadProgress, setUploadProgress] = useState(0);
    const [uploadResult, setUploadResult] = useState<DocumentUploadResult | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [dragActive, setDragActive] = useState(false);
    const [chatQuery, setChatQuery] = useState('');
    const [chatResult, setChatResult] = useState<DocumentChatResult | null>(null);
    const [isChating, setIsChating] = useState(false);
    const [activeTab, setActiveTab] = useState('upload');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const allowedTypes = ['pdf', 'txt', 'doc', 'docx', 'csv'];
    const maxSize = 10 * 1024 * 1024; // 10MB

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === 'dragenter' || e.type === 'dragover') {
            setDragActive(true);
        } else if (e.type === 'dragleave') {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);

        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    };

    const handleFileSelect = (file: File) => {
        const fileExtension = file.name.split('.').pop()?.toLowerCase();

        if (!fileExtension || !allowedTypes.includes(fileExtension)) {
            alert(`File type not supported. Please upload: ${allowedTypes.join(', ')}`);
            return;
        }

        if (file.size > maxSize) {
            alert('File size must be less than 10MB');
            return;
        }

        setSelectedFile(file);
        setUploadStatus('idle');
        setUploadResult(null);
    };

    const handleUpload = async () => {
        if (!selectedFile) return;

        setUploadStatus('uploading');
        setUploadProgress(20);

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            // Simulate upload progress
            const progressInterval = setInterval(() => {
                setUploadProgress((prev) => {
                    if (prev < 60) return prev + 10;
                    return prev;
                });
            }, 500);

            const response = await fetch('/api/documents/upload', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            clearInterval(progressInterval);
            setUploadProgress(80);

            if (!response.ok) {
                throw new Error('Upload failed');
            }

            const result: DocumentUploadResult = await response.json();

            setUploadProgress(100);
            setUploadStatus('completed');
            setUploadResult(result);
            setActiveTab('results');

        } catch (error) {
            console.error('Upload error:', error);
            setUploadStatus('error');
            setUploadProgress(0);
        }
    };

    const handleDocumentChat = async () => {
        if (!chatQuery.trim()) return;

        setIsChating(true);

        try {
            // Document chat feature temporarily unavailable 
            const unavailableResult: DocumentChatResult = {
                success: false,
                response: 'Document chat feature is currently unavailable. Please use the main chat interface to ask questions about your uploaded documents.',
                intent: 'feature_unavailable',
                confidence_score: 0,
                documents_found: [],
                selected_document: uploadResult?.document,
                follow_up_suggestions: ['Try using the main chat interface', 'Upload your document and ask questions there'],
                related_documents: [],
                tools_used: [],
                workflow_trace: [],
                response_type: 'info_response'
            };

            setChatResult(unavailableResult);
            setChatQuery('');
            setActiveTab('chat');

        } catch (error) {
            console.error('Chat error:', error);
        } finally {
            setIsChating(false);
        }
    };

    const resetUpload = () => {
        setSelectedFile(null);
        setUploadStatus('idle');
        setUploadProgress(0);
        setUploadResult(null);
        setChatResult(null);
        setChatQuery('');
        setActiveTab('upload');
    };

    const getQualityColor = (score: number) => {
        if (score >= 0.9) return 'bg-green-500';
        if (score >= 0.7) return 'bg-blue-500';
        if (score >= 0.5) return 'bg-yellow-500';
        return 'bg-red-500';
    };

    const getQualityLabel = (score: number) => {
        if (score >= 0.9) return 'Excellent';
        if (score >= 0.7) return 'Good';
        if (score >= 0.5) return 'Fair';
        return 'Poor';
    };

    return (
        <div className="max-w-6xl mx-auto p-6 space-y-6">
            <Card className="bg-gradient-to-br from-blue-50 to-purple-50 border-blue-200">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Sparkles className="w-6 h-6 text-blue-600" />
                        Enhanced Document Processing
                    </CardTitle>
                    <CardDescription>
                        Upload pet care documents for AI-powered analysis with comprehensive insights,
                        pet information extraction, and intelligent chat capabilities.
                    </CardDescription>
                </CardHeader>
            </Card>

            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="upload" className="flex items-center gap-2">
                        <Upload className="w-4 h-4" />
                        Upload
                    </TabsTrigger>
                    <TabsTrigger value="results" disabled={!uploadResult} className="flex items-center gap-2">
                        <FileText className="w-4 h-4" />
                        Results
                    </TabsTrigger>
                    <TabsTrigger value="chat" className="flex items-center gap-2">
                        <MessageCircle className="w-4 h-4" />
                        Chat
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="upload" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Upload className="w-5 h-5" />
                                Document Upload
                            </CardTitle>
                            <CardDescription>
                                Upload PDF, Word, CSV, or text files for comprehensive AI analysis
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div
                                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                                    }`}
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                            >
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    className="hidden"
                                    accept=".pdf,.txt,.doc,.docx,.csv"
                                    onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
                                />

                                {selectedFile ? (
                                    <div className="space-y-4">
                                        <div className="flex items-center justify-center gap-2">
                                            <FileText className="w-8 h-8 text-blue-500" />
                                            <div>
                                                <p className="font-medium">{selectedFile.name}</p>
                                                <p className="text-sm text-gray-500">
                                                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                                                </p>
                                            </div>
                                        </div>

                                        {uploadStatus === 'uploading' || uploadStatus === 'processing' ? (
                                            <div className="space-y-2">
                                                <Progress value={uploadProgress} className="w-full" />
                                                <p className="text-sm text-gray-600">
                                                    {uploadStatus === 'uploading' ? 'Uploading...' : 'Processing with AI...'}
                                                </p>
                                            </div>
                                        ) : (
                                            <div className="flex gap-2 justify-center">
                                                <Button onClick={handleUpload} disabled={uploadStatus !== 'idle'}>
                                                    {uploadStatus === 'completed' ? (
                                                        <>
                                                            <CheckCircle className="w-4 h-4 mr-2" />
                                                            Completed
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Sparkles className="w-4 h-4 mr-2" />
                                                            Process with AI
                                                        </>
                                                    )}
                                                </Button>
                                                <Button variant="outline" onClick={resetUpload}>
                                                    <X className="w-4 h-4 mr-2" />
                                                    Clear
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        <Upload className="w-12 h-12 text-gray-400 mx-auto" />
                                        <div>
                                            <p className="text-lg font-medium">Drop your document here</p>
                                            <p className="text-gray-500">or</p>
                                            <Button
                                                variant="outline"
                                                onClick={() => fileInputRef.current?.click()}
                                                className="mt-2"
                                            >
                                                Choose File
                                            </Button>
                                        </div>
                                        <p className="text-sm text-gray-500">
                                            Supported formats: PDF, Word, CSV, TXT (max 10MB)
                                        </p>
                                    </div>
                                )}
                            </div>

                            {uploadStatus === 'error' && (
                                <div className="mt-4 p-3 border border-red-200 bg-red-50 rounded-md flex items-center gap-2">
                                    <AlertCircle className="w-4 h-4 text-red-500" />
                                    <span className="text-red-700">
                                        Upload failed. Please try again or contact support.
                                    </span>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </TabsContent>

                <TabsContent value="results" className="space-y-4">
                    {uploadResult && (
                        <>
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <CheckCircle className="w-5 h-5 text-green-500" />
                                        Processing Complete
                                    </CardTitle>
                                    <CardDescription>
                                        Your document has been analyzed with AI and added to your knowledge base
                                    </CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                        <div className="text-center">
                                            <Badge variant="outline" className="mb-2">
                                                {uploadResult.processing_summary.document_type}
                                            </Badge>
                                            <p className="text-sm text-gray-600">Document Type</p>
                                        </div>
                                        <div className="text-center">
                                            <div className="flex items-center justify-center gap-2">
                                                <div className={`w-3 h-3 rounded-full ${getQualityColor(uploadResult.processing_summary.quality_score)}`}></div>
                                                <span className="font-medium">
                                                    {getQualityLabel(uploadResult.processing_summary.quality_score)}
                                                </span>
                                            </div>
                                            <p className="text-sm text-gray-600">Quality Score</p>
                                        </div>
                                        <div className="text-center">
                                            <span className="font-medium">{uploadResult.processing_summary.chunks_created}</span>
                                            <p className="text-sm text-gray-600">Chunks Created</p>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Bot className="w-5 h-5 text-blue-500" />
                                        AI Analysis
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-4">
                                        <div>
                                            <h4 className="font-medium mb-2">Document Summary</h4>
                                            <p className="text-gray-700 bg-gray-50 p-3 rounded">
                                                {uploadResult.processing_summary.summary}
                                            </p>
                                        </div>

                                        {uploadResult.processing_summary.key_insights.length > 0 && (
                                            <div>
                                                <h4 className="font-medium mb-2">Key Insights</h4>
                                                <ul className="space-y-1">
                                                    {uploadResult.processing_summary.key_insights.map((insight, index) => (
                                                        <li key={index} className="flex items-start gap-2">
                                                            <Sparkles className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
                                                            <span className="text-sm">{insight}</span>
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        {uploadResult.processing_summary.pet_information?.pets?.length > 0 && (
                                            <div>
                                                <h4 className="font-medium mb-2">Pet Information</h4>
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                    {uploadResult.processing_summary.pet_information.pets.map((pet: any, index: number) => (
                                                        <div key={index} className="bg-blue-50 p-3 rounded-lg">
                                                            <div className="flex items-center gap-2 mb-2">
                                                                <Heart className="w-4 h-4 text-red-500" />
                                                                <span className="font-medium">{pet.name || 'Unnamed Pet'}</span>
                                                            </div>
                                                            <div className="text-sm space-y-1">
                                                                {pet.breed && <p><strong>Breed:</strong> {pet.breed}</p>}
                                                                {pet.age && <p><strong>Age:</strong> {pet.age}</p>}
                                                                {pet.weight && <p><strong>Weight:</strong> {pet.weight}</p>}
                                                                {pet.species && <p><strong>Species:</strong> {pet.species}</p>}
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>

                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Info className="w-5 h-5 text-purple-500" />
                                        Processing Workflow
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <ScrollArea className="h-32">
                                        <div className="space-y-2">
                                            {uploadResult.processing_summary.workflow_trace.map((step, index) => (
                                                <div key={index} className="flex items-center gap-2 text-sm">
                                                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                                    <span>{step}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </ScrollArea>
                                </CardContent>
                            </Card>
                        </>
                    )}
                </TabsContent>

                <TabsContent value="chat" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <MessageCircle className="w-5 h-5 text-green-500" />
                                Document Chat
                            </CardTitle>
                            <CardDescription>
                                Ask questions about your documents or search for specific information
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-4">
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={chatQuery}
                                        onChange={(e) => setChatQuery(e.target.value)}
                                        placeholder="Ask about your documents or search for specific files..."
                                        className="flex-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        onKeyPress={(e) => e.key === 'Enter' && handleDocumentChat()}
                                    />
                                    <Button onClick={handleDocumentChat} disabled={isChating || !chatQuery.trim()}>
                                        {isChating ? (
                                            <>
                                                <Bot className="w-4 h-4 mr-2 animate-spin" />
                                                Thinking...
                                            </>
                                        ) : (
                                            <>
                                                <Search className="w-4 h-4 mr-2" />
                                                Ask
                                            </>
                                        )}
                                    </Button>
                                </div>

                                {chatResult && (
                                    <div className="space-y-4">
                                        <Card className="bg-green-50 border-green-200">
                                            <CardContent className="pt-4">
                                                <div className="flex items-start gap-3">
                                                    <Bot className="w-6 h-6 text-green-600 mt-1 flex-shrink-0" />
                                                    <div className="flex-1">
                                                        <p className="text-gray-800 whitespace-pre-wrap">{chatResult.response}</p>
                                                        <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
                                                            <span>Intent: {chatResult.intent}</span>
                                                            <span>Confidence: {(chatResult.confidence_score * 100).toFixed(1)}%</span>
                                                            <span>Tools: {chatResult.tools_used.join(', ')}</span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </CardContent>
                                        </Card>

                                        {chatResult.selected_document && (
                                            <Card className="bg-blue-50 border-blue-200">
                                                <CardContent className="pt-4">
                                                    <h4 className="font-medium mb-2">Referenced Document</h4>
                                                    <div className="flex items-center gap-2">
                                                        <FileText className="w-4 h-4 text-blue-500" />
                                                        <span>{chatResult.selected_document.filename}</span>
                                                        <Badge variant="outline">{chatResult.selected_document.document_type}</Badge>
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        )}

                                        {chatResult.follow_up_suggestions.length > 0 && (
                                            <Card>
                                                <CardHeader>
                                                    <CardTitle className="text-sm">Follow-up Suggestions</CardTitle>
                                                </CardHeader>
                                                <CardContent>
                                                    <div className="space-y-2">
                                                        {chatResult.follow_up_suggestions.map((suggestion, index) => (
                                                            <Button
                                                                key={index}
                                                                variant="outline"
                                                                size="sm"
                                                                onClick={() => setChatQuery(suggestion)}
                                                                className="text-left h-auto p-2 justify-start whitespace-normal"
                                                            >
                                                                {suggestion}
                                                            </Button>
                                                        ))}
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        )}
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
} 