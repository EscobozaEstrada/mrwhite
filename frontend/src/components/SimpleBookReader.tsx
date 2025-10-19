'use client';

import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, BookOpen, Settings } from 'lucide-react';
import axios from 'axios';

interface BookChapter {
    id: number;
    title: string;
    content: string;
    html_content: string;
    chapter_number: number;
}

interface BookData {
    id: number;
    title: string;
    description?: string;
    total_chapters: number;
    chapters: BookChapter[];
}

const SimpleBookReader: React.FC = () => {
    const [bookData, setBookData] = useState<BookData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [currentChapter, setCurrentChapter] = useState(1);
    const [fontSize, setFontSize] = useState(16);

    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

    useEffect(() => {
        const loadBook = async () => {
            try {
                console.log('📚 Loading book...');
                const response = await axios.get(`${apiUrl}/api/book-content/book-content/9`);

                if (response.data.success) {
                    console.log('✅ Book loaded:', response.data.book.title);
                    setBookData(response.data.book);
                } else {
                    throw new Error('Failed to load book');
                }
            } catch (err: any) {
                console.error('❌ Error:', err);
                setError('Failed to load book content');
            } finally {
                setLoading(false);
            }
        };

        loadBook();
    }, []);

    const getCurrentChapter = () => {
        if (!bookData?.chapters) return null;
        return bookData.chapters.find(ch => ch.chapter_number === currentChapter) || bookData.chapters[0];
    };

    const navigateChapter = (direction: 'prev' | 'next') => {
        if (!bookData) return;

        if (direction === 'prev' && currentChapter > 1) {
            setCurrentChapter(currentChapter - 1);
        } else if (direction === 'next' && currentChapter < bookData.total_chapters) {
            setCurrentChapter(currentChapter + 1);
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center space-y-4">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="text-lg text-gray-600">Loading your book...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center space-y-4">
                    <div className="text-red-500 text-6xl">⚠️</div>
                    <h2 className="text-2xl font-bold text-gray-800">Error Loading Book</h2>
                    <p className="text-gray-600">{error}</p>
                    <button
                        onClick={() => window.location.reload()}
                        className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600"
                    >
                        Try Again
                    </button>
                </div>
            </div>
        );
    }

    const chapter = getCurrentChapter();

    return (
        <div className="min-h-screen bg-gray-50">
            {/* Header */}
            <div className="bg-white shadow-sm border-b">
                <div className="max-w-4xl mx-auto px-4 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                            <BookOpen className="w-6 h-6 text-blue-600" />
                            <div>
                                <h1 className="text-xl font-bold text-gray-800">
                                    {bookData?.title || 'Book Reader'}
                                </h1>
                                <p className="text-sm text-gray-600">
                                    Chapter {currentChapter} of {bookData?.total_chapters}
                                </p>
                            </div>
                        </div>

                        {/* Controls */}
                        <div className="flex items-center space-x-4">
                            <div className="flex items-center space-x-2">
                                <Settings className="w-4 h-4 text-gray-500" />
                                <input
                                    type="range"
                                    min="12"
                                    max="24"
                                    value={fontSize}
                                    onChange={(e) => setFontSize(Number(e.target.value))}
                                    className="w-20"
                                />
                                <span className="text-sm text-gray-600">{fontSize}px</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="max-w-4xl mx-auto px-4 py-8">
                <div className="bg-white rounded-lg shadow-sm p-8">
                    {chapter ? (
                        <>
                            <h2 className="text-2xl font-bold mb-6 text-gray-800">
                                {chapter.title}
                            </h2>

                            <div
                                className="prose prose-lg max-w-none"
                                style={{ fontSize: `${fontSize}px`, lineHeight: 1.7 }}
                                dangerouslySetInnerHTML={{
                                    __html: chapter.html_content || chapter.content
                                }}
                            />
                        </>
                    ) : (
                        <div className="text-center py-12">
                            <p className="text-gray-500">Chapter not found</p>
                        </div>
                    )}
                </div>

                {/* Navigation */}
                <div className="flex items-center justify-between mt-8">
                    <button
                        onClick={() => navigateChapter('prev')}
                        disabled={currentChapter <= 1}
                        className="flex items-center space-x-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <ChevronLeft className="w-4 h-4" />
                        <span>Previous Chapter</span>
                    </button>

                    <div className="text-center">
                        <div className="text-sm text-gray-600 mb-2">Progress</div>
                        <div className="w-64 bg-gray-200 rounded-full h-2">
                            <div
                                className="bg-blue-500 h-2 rounded-full"
                                style={{
                                    width: `${(currentChapter / (bookData?.total_chapters || 1)) * 100}%`
                                }}
                            ></div>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                            {Math.round((currentChapter / (bookData?.total_chapters || 1)) * 100)}% complete
                        </div>
                    </div>

                    <button
                        onClick={() => navigateChapter('next')}
                        disabled={currentChapter >= (bookData?.total_chapters || 0)}
                        className="flex items-center space-x-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <span>Next Chapter</span>
                        <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SimpleBookReader; 