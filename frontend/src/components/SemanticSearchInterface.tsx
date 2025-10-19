'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    Search,
    Loader2,
    BookOpen,
    Calendar,
    Highlighter,
    StickyNote,
    ArrowRight,
    Filter,
    X,
    Brain,
    Lightbulb
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useAuth } from '@/context/AuthContext';
import axios from 'axios';
import toast from '@/components/ui/sound-toast';

interface SearchResult {
    id: string;
    score: number;
    metadata: {
        content_type: 'book_note' | 'book_highlight';
        page_number: number;
        color: string;
        book_title: string;
        created_at: string;
        note_type?: string;
    };
    text: string;
    highlighted_text?: string;
}

interface SemanticSearchInterfaceProps {
    isOpen: boolean;
    onClose: () => void;
    onNavigateToPage: (pageNumber: number) => void;
    currentBookCopyId?: number;
}

const SemanticSearchInterface: React.FC<SemanticSearchInterfaceProps> = ({
    isOpen,
    onClose,
    onNavigateToPage,
    currentBookCopyId
}) => {
    const { user } = useAuth();
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [selectedFilter, setSelectedFilter] = useState<'all' | 'notes' | 'highlights'>('all');
    const [relatedContent, setRelatedContent] = useState<SearchResult[]>([]);
    const [showRelated, setShowRelated] = useState(false);

    const apiUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';

    // Debounced search using useCallback and useEffect (Context7 pattern)
    const debouncedSearch = useCallback(
        debounce((query: string) => {
            if (query.trim()) {
                performSearch(query);
            } else {
                setSearchResults([]);
            }
        }, 300),
        []
    );

    useEffect(() => {
        debouncedSearch(searchQuery);
    }, [searchQuery, debouncedSearch]);

    // Perform semantic search
    const performSearch = async (query: string) => {
        if (!user) return;

        setIsSearching(true);
        try {
            const response = await axios.post(`${apiUrl}/api/user-books/search`, {
                query,
                book_copy_id: currentBookCopyId,
                top_k: 20
            }, {
                withCredentials: true
            });

            if (response.data.success) {
                setSearchResults(response.data.results.matches || []);
                console.log('🔍 Search results:', response.data.results);
            }
        } catch (error) {
            console.error('❌ Search error:', error);
            toast.error('Search failed');
        } finally {
            setIsSearching(false);
        }
    };

    // Filter results based on selected filter
    const filteredResults = useMemo(() => {
        if (selectedFilter === 'all') return searchResults;
        return searchResults.filter(result => {
            if (selectedFilter === 'notes') return result.metadata.content_type === 'book_note';
            if (selectedFilter === 'highlights') return result.metadata.content_type === 'book_highlight';
            return true;
        });
    }, [searchResults, selectedFilter]);

    // Get related content for a search result
    const getRelatedContent = async (resultId: string) => {
        try {
            const response = await axios.get(`${apiUrl}/api/user-books/related/${resultId}`, {
                withCredentials: true
            });

            if (response.data.success) {
                setRelatedContent(response.data.related_items || []);
                setShowRelated(true);
            }
        } catch (error) {
            console.error('❌ Related content error:', error);
        }
    };

    // Get color style for items
    const getColorStyle = (color: string, opacity: number = 0.2) => {
        const colorMap: Record<string, string> = {
            yellow: `rgba(255, 235, 59, ${opacity})`,
            blue: `rgba(33, 150, 243, ${opacity})`,
            green: `rgba(76, 175, 80, ${opacity})`,
            pink: `rgba(233, 30, 99, ${opacity})`,
            red: `rgba(244, 67, 54, ${opacity})`,
            purple: `rgba(156, 39, 176, ${opacity})`,
            orange: `rgba(255, 152, 0, ${opacity})`
        };
        return colorMap[color] || colorMap.yellow;
    };

    if (!isOpen) return null;

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                onClick={(e) => e.stopPropagation()}
                className="w-full max-w-4xl max-h-[90vh] bg-background rounded-lg border shadow-xl"
            >
                <Card className="h-full">
                    <CardHeader className="border-b">
                        <div className="flex items-center justify-between">
                            <CardTitle className="flex items-center gap-2">
                                <Brain className="h-5 w-5" />
                                Semantic Search
                            </CardTitle>
                            <Button onClick={onClose} variant="ghost" size="sm">
                                <X className="h-4 w-4" />
                            </Button>
                        </div>

                        {/* Search Input */}
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search your notes and highlights..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-10 pr-4"
                                autoFocus
                            />
                            {isSearching && (
                                <Loader2 className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 animate-spin" />
                            )}
                        </div>

                        {/* Filters */}
                        <div className="flex items-center gap-2">
                            <Filter className="h-4 w-4 text-muted-foreground" />
                            <Button
                                onClick={() => setSelectedFilter('all')}
                                variant={selectedFilter === 'all' ? 'default' : 'outline'}
                                size="sm"
                            >
                                All ({searchResults.length})
                            </Button>
                            <Button
                                onClick={() => setSelectedFilter('notes')}
                                variant={selectedFilter === 'notes' ? 'default' : 'outline'}
                                size="sm"
                            >
                                <StickyNote className="h-3 w-3 mr-1" />
                                Notes ({searchResults.filter(r => r.metadata.content_type === 'book_note').length})
                            </Button>
                            <Button
                                onClick={() => setSelectedFilter('highlights')}
                                variant={selectedFilter === 'highlights' ? 'default' : 'outline'}
                                size="sm"
                            >
                                <Highlighter className="h-3 w-3 mr-1" />
                                Highlights ({searchResults.filter(r => r.metadata.content_type === 'book_highlight').length})
                            </Button>
                        </div>
                    </CardHeader>

                    <CardContent className="p-0 h-[60vh]">
                        <Tabs value={showRelated ? 'related' : 'results'} className="h-full flex flex-col">
                            <TabsList className="grid w-full grid-cols-2 m-4 mb-0">
                                <TabsTrigger
                                    value="results"
                                    onClick={() => setShowRelated(false)}
                                    className="flex items-center gap-1"
                                >
                                    <Search className="h-3 w-3" />
                                    Search Results
                                </TabsTrigger>
                                <TabsTrigger
                                    value="related"
                                    onClick={() => setShowRelated(true)}
                                    className="flex items-center gap-1"
                                    disabled={relatedContent.length === 0}
                                >
                                    <Lightbulb className="h-3 w-3" />
                                    Related Content ({relatedContent.length})
                                </TabsTrigger>
                            </TabsList>

                            <TabsContent value="results" className="flex-1 m-4 mt-0">
                                <ScrollArea className="h-full">
                                    {searchQuery && filteredResults.length === 0 && !isSearching && (
                                        <div className="text-center py-8 text-muted-foreground">
                                            <Search className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                            <p>No results found for "{searchQuery}"</p>
                                        </div>
                                    )}

                                    <div className="space-y-3">
                                        <AnimatePresence>
                                            {filteredResults.map((result, index) => (
                                                <motion.div
                                                    key={result.id}
                                                    initial={{ opacity: 0, y: 20 }}
                                                    animate={{ opacity: 1, y: 0 }}
                                                    exit={{ opacity: 0, y: -20 }}
                                                    transition={{ delay: index * 0.05 }}
                                                >
                                                    <Card className="hover:shadow-md transition-shadow cursor-pointer">
                                                        <CardContent className="p-4">
                                                            <div className="flex items-start justify-between mb-2">
                                                                <div className="flex items-center gap-2">
                                                                    {result.metadata.content_type === 'book_note' ? (
                                                                        <StickyNote className="h-4 w-4" />
                                                                    ) : (
                                                                        <Highlighter className="h-4 w-4" />
                                                                    )}
                                                                    <Badge
                                                                        variant="secondary"
                                                                        style={{ backgroundColor: getColorStyle(result.metadata.color) }}
                                                                    >
                                                                        {result.metadata.content_type === 'book_note'
                                                                            ? result.metadata.note_type || 'Note'
                                                                            : 'Highlight'
                                                                        }
                                                                    </Badge>
                                                                    <Badge variant="outline">
                                                                        {Math.round(result.score * 100)}% match
                                                                    </Badge>
                                                                </div>

                                                                <div className="flex items-center gap-2">
                                                                    <Button
                                                                        onClick={() => getRelatedContent(result.id)}
                                                                        variant="ghost"
                                                                        size="sm"
                                                                    >
                                                                        <Lightbulb className="h-3 w-3" />
                                                                    </Button>
                                                                    <Button
                                                                        onClick={() => {
                                                                            onNavigateToPage(result.metadata.page_number);
                                                                            onClose();
                                                                        }}
                                                                        variant="ghost"
                                                                        size="sm"
                                                                    >
                                                                        <ArrowRight className="h-3 w-3" />
                                                                    </Button>
                                                                </div>
                                                            </div>

                                                            <p className="text-sm mb-3 line-clamp-3">
                                                                {result.highlighted_text || result.text}
                                                            </p>

                                                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                                                <div className="flex items-center gap-1">
                                                                    <BookOpen className="h-3 w-3" />
                                                                    Page {result.metadata.page_number}
                                                                </div>
                                                                <div className="flex items-center gap-1">
                                                                    <Calendar className="h-3 w-3" />
                                                                    {new Date(result.metadata.created_at).toLocaleDateString()}
                                                                </div>
                                                            </div>
                                                        </CardContent>
                                                    </Card>
                                                </motion.div>
                                            ))}
                                        </AnimatePresence>
                                    </div>
                                </ScrollArea>
                            </TabsContent>

                            <TabsContent value="related" className="flex-1 m-4 mt-0">
                                <ScrollArea className="h-full">
                                    {relatedContent.length === 0 ? (
                                        <div className="text-center py-8 text-muted-foreground">
                                            <Lightbulb className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                            <p>Click the lightbulb icon on search results to find related content</p>
                                        </div>
                                    ) : (
                                        <div className="space-y-3">
                                            {relatedContent.map((item, index) => (
                                                <motion.div
                                                    key={item.id}
                                                    initial={{ opacity: 0, x: 20 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    transition={{ delay: index * 0.1 }}
                                                >
                                                    <Card className="hover:shadow-md transition-shadow">
                                                        <CardContent className="p-4">
                                                            <div className="flex items-start justify-between mb-2">
                                                                <div className="flex items-center gap-2">
                                                                    {item.metadata.content_type === 'book_note' ? (
                                                                        <StickyNote className="h-4 w-4" />
                                                                    ) : (
                                                                        <Highlighter className="h-4 w-4" />
                                                                    )}
                                                                    <Badge
                                                                        variant="secondary"
                                                                        style={{ backgroundColor: getColorStyle(item.metadata.color) }}
                                                                    >
                                                                        {item.metadata.content_type === 'book_note'
                                                                            ? item.metadata.note_type || 'Note'
                                                                            : 'Highlight'
                                                                        }
                                                                    </Badge>
                                                                </div>

                                                                <Button
                                                                    onClick={() => {
                                                                        onNavigateToPage(item.metadata.page_number);
                                                                        onClose();
                                                                    }}
                                                                    variant="ghost"
                                                                    size="sm"
                                                                >
                                                                    <ArrowRight className="h-3 w-3" />
                                                                </Button>
                                                            </div>

                                                            <p className="text-sm mb-3">
                                                                {item.highlighted_text || item.text}
                                                            </p>

                                                            <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                                                <div className="flex items-center gap-1">
                                                                    <BookOpen className="h-3 w-3" />
                                                                    Page {item.metadata.page_number}
                                                                </div>
                                                                <div className="flex items-center gap-1">
                                                                    <Calendar className="h-3 w-3" />
                                                                    {new Date(item.metadata.created_at).toLocaleDateString()}
                                                                </div>
                                                            </div>
                                                        </CardContent>
                                                    </Card>
                                                </motion.div>
                                            ))}
                                        </div>
                                    )}
                                </ScrollArea>
                            </TabsContent>
                        </Tabs>
                    </CardContent>
                </Card>
            </motion.div>
        </motion.div>
    );
};

// Debounce utility function (Context7 pattern)
function debounce<T extends (...args: any[]) => any>(func: T, wait: number): T {
    let timeout: NodeJS.Timeout;
    return ((...args: any[]) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(...args), wait);
    }) as T;
}

export default SemanticSearchInterface; 