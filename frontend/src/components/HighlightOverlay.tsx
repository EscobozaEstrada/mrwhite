'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
    Highlighter,
    StickyNote,
    Eye,
    EyeOff,
    Trash2,
    Calendar,
    BookOpen
} from 'lucide-react';

interface BookHighlight {
    id: number;
    highlighted_text: string;
    page_number: number;
    color: string;
    pdf_coordinates?: {
        x: number;
        y: number;
        width: number;
        height: number;
    };
    created_at: string;
    book_copy_id: number;
}

interface BookNote {
    id: number;
    note_text: string;
    page_number: number;
    color: string;
    note_type: string;
    pdf_coordinates?: {
        x: number;
        y: number;
    };
    created_at: string;
    book_copy_id: number;
}

interface HighlightOverlayProps {
    currentPage: number;
    highlights: BookHighlight[];
    notes: BookNote[];
    pdfScale: number;
    onHighlightClick: (highlight: BookHighlight) => void;
    onNoteClick: (note: BookNote) => void;
    onDeleteHighlight: (highlightId: number) => void;
    onDeleteNote: (noteId: number) => void;
    showOverlay: boolean;
    onToggleOverlay: (show: boolean) => void;
}

const HighlightOverlay: React.FC<HighlightOverlayProps> = ({
    currentPage,
    highlights,
    notes,
    pdfScale,
    onHighlightClick,
    onNoteClick,
    onDeleteHighlight,
    onDeleteNote,
    showOverlay,
    onToggleOverlay
}) => {
    const [selectedItem, setSelectedItem] = useState<{ type: 'highlight' | 'note', item: BookHighlight | BookNote } | null>(null);

    // Filter highlights and notes for current page using useMemo for performance
    const currentPageHighlights = useMemo(() =>
        highlights.filter(h => h.page_number === currentPage),
        [highlights, currentPage]
    );

    const currentPageNotes = useMemo(() =>
        notes.filter(n => n.page_number === currentPage),
        [notes, currentPage]
    );

    // Get color mapping for highlights and notes
    const getColorStyle = (color: string, opacity: number = 0.3) => {
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

    // Close selection when clicking outside
    useEffect(() => {
        const handleClickOutside = () => setSelectedItem(null);
        document.addEventListener('click', handleClickOutside);
        return () => document.removeEventListener('click', handleClickOutside);
    }, []);

    if (!showOverlay) {
        return (
            <div className="fixed top-20 right-4 z-50">
                <Button
                    onClick={() => onToggleOverlay(true)}
                    variant="outline"
                    size="sm"
                    className="bg-background/80 backdrop-blur-sm"
                >
                    <Eye className="h-4 w-4 mr-1" />
                    Show Annotations
                </Button>
            </div>
        );
    }

    return (
        <>
            {/* Toggle Button */}
            <div className="fixed top-20 right-4 z-50">
                <Button
                    onClick={() => onToggleOverlay(false)}
                    variant="outline"
                    size="sm"
                    className="bg-background/80 backdrop-blur-sm"
                >
                    <EyeOff className="h-4 w-4 mr-1" />
                    Hide Annotations
                </Button>
            </div>

            {/* Highlight Overlays */}
            <div className="absolute inset-0 pointer-events-none z-10">
                <AnimatePresence>
                    {currentPageHighlights.map((highlight) => (
                        <motion.div
                            key={`highlight-${highlight.id}`}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute pointer-events-auto cursor-pointer"
                            style={{
                                left: highlight.pdf_coordinates?.x ? `${highlight.pdf_coordinates.x * pdfScale}px` : '50%',
                                top: highlight.pdf_coordinates?.y ? `${highlight.pdf_coordinates.y * pdfScale}px` : '20%',
                                width: highlight.pdf_coordinates?.width ? `${highlight.pdf_coordinates.width * pdfScale}px` : '200px',
                                height: highlight.pdf_coordinates?.height ? `${highlight.pdf_coordinates.height * pdfScale}px` : '20px',
                                backgroundColor: getColorStyle(highlight.color, 0.4),
                                borderLeft: `3px solid ${getColorStyle(highlight.color, 1)}`,
                            }}
                            onClick={(e) => {
                                e.stopPropagation();
                                setSelectedItem({ type: 'highlight', item: highlight });
                                onHighlightClick(highlight);
                            }}
                            whileHover={{ scale: 1.02, opacity: 0.8 }}
                        >
                            <div className="h-full w-full flex items-center px-2">
                                <Highlighter className="h-3 w-3 text-black/60" />
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>

            {/* Note Markers */}
            <div className="absolute inset-0 pointer-events-none z-20">
                <AnimatePresence>
                    {currentPageNotes.map((note) => (
                        <motion.div
                            key={`note-${note.id}`}
                            initial={{ scale: 0, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0, opacity: 0 }}
                            className="absolute pointer-events-auto cursor-pointer"
                            style={{
                                left: note.pdf_coordinates?.x ? `${note.pdf_coordinates.x * pdfScale}px` : '80%',
                                top: note.pdf_coordinates?.y ? `${note.pdf_coordinates.y * pdfScale}px` : '30%',
                            }}
                            onClick={(e) => {
                                e.stopPropagation();
                                setSelectedItem({ type: 'note', item: note });
                                onNoteClick(note);
                            }}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                        >
                            <div
                                className="w-6 h-6 rounded-full border-2 border-white shadow-lg flex items-center justify-center"
                                style={{ backgroundColor: getColorStyle(note.color, 1) }}
                            >
                                <StickyNote className="h-3 w-3 text-white" />
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>
            </div>

            {/* Selected Item Popup */}
            <AnimatePresence>
                {selectedItem && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 10 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 10 }}
                        className="fixed bottom-20 left-4 right-4 z-50 max-w-md mx-auto"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <Card className="bg-background/95 backdrop-blur-sm border shadow-lg">
                            <CardContent className="p-4">
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-2">
                                        {selectedItem.type === 'highlight' ? (
                                            <>
                                                <Highlighter className="h-4 w-4" />
                                                <Badge variant="secondary" style={{ backgroundColor: getColorStyle((selectedItem.item as BookHighlight).color, 0.2) }}>
                                                    Highlight
                                                </Badge>
                                            </>
                                        ) : (
                                            <>
                                                <StickyNote className="h-4 w-4" />
                                                <Badge variant="secondary" style={{ backgroundColor: getColorStyle((selectedItem.item as BookNote).color, 0.2) }}>
                                                    {(selectedItem.item as BookNote).note_type}
                                                </Badge>
                                            </>
                                        )}
                                    </div>
                                    <Button
                                        onClick={() => {
                                            if (selectedItem.type === 'highlight') {
                                                onDeleteHighlight(selectedItem.item.id);
                                            } else {
                                                onDeleteNote(selectedItem.item.id);
                                            }
                                            setSelectedItem(null);
                                        }}
                                        variant="ghost"
                                        size="sm"
                                        className="h-6 w-6 p-0"
                                    >
                                        <Trash2 className="h-3 w-3" />
                                    </Button>
                                </div>

                                <div className="space-y-2">
                                    <p className="text-sm">
                                        {selectedItem.type === 'highlight'
                                            ? (selectedItem.item as BookHighlight).highlighted_text
                                            : (selectedItem.item as BookNote).note_text
                                        }
                                    </p>

                                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                        <div className="flex items-center gap-1">
                                            <BookOpen className="h-3 w-3" />
                                            Page {selectedItem.item.page_number}
                                        </div>
                                        <div className="flex items-center gap-1">
                                            <Calendar className="h-3 w-3" />
                                            {new Date(selectedItem.item.created_at).toLocaleDateString()}
                                        </div>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Page Summary */}
            {(currentPageHighlights.length > 0 || currentPageNotes.length > 0) && (
                <div className="fixed bottom-4 right-4 z-40">
                    <Card className="bg-background/90 backdrop-blur-sm">
                        <CardContent className="p-3">
                            <div className="text-xs text-muted-foreground">
                                Page {currentPage}:
                                <div className="flex items-center gap-3 mt-1">
                                    {currentPageHighlights.length > 0 && (
                                        <div className="flex items-center gap-1">
                                            <Highlighter className="h-3 w-3" />
                                            {currentPageHighlights.length}
                                        </div>
                                    )}
                                    {currentPageNotes.length > 0 && (
                                        <div className="flex items-center gap-1">
                                            <StickyNote className="h-3 w-3" />
                                            {currentPageNotes.length}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </>
    );
};

export default HighlightOverlay; 