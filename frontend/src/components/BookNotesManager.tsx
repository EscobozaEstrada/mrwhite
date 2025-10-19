'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import {
    StickyNote,
    Highlighter,
    Bookmark,
    Search,
    Filter,
    Plus,
    Trash2,
    Edit,
    Save,
    X,
    Tag,
    Calendar,
    MapPin,
    Palette,
    Download,
    Upload,
    MoreVertical,
    Eye,
    EyeOff,
    Copy,
    Share
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import toast from '@/components/ui/sound-toast';

interface BookNote {
    id: number;
    user_book_copy_id: number;
    note_text: string;
    note_type: string;
    color: string;
    page_number?: number;
    chapter_name?: string;
    pdf_coordinates?: any;
    selected_text?: string;
    context_before?: string;
    context_after?: string;
    tags: string[];
    is_private: boolean;
    is_archived: boolean;
    created_at: string;
    updated_at: string;
}

interface BookHighlight {
    id: number;
    user_book_copy_id: number;
    highlighted_text: string;
    color: string;
    highlight_type: string;
    page_number?: number;
    chapter_name?: string;
    pdf_coordinates: any;
    context_before?: string;
    context_after?: string;
    text_length: number;
    tags: string[];
    is_archived: boolean;
    note_id?: number;
    created_at: string;
    updated_at: string;
}

interface NotesManagerProps {
    notes: BookNote[];
    highlights: BookHighlight[];
    onCreateNote: (noteData: Partial<BookNote>) => Promise<void>;
    onUpdateNote: (noteId: number, noteData: Partial<BookNote>) => Promise<void>;
    onDeleteNote: (noteId: number) => Promise<void>;
    onCreateHighlight: (highlightData: Partial<BookHighlight>) => Promise<void>;
    onDeleteHighlight: (highlightId: number) => Promise<void>;
    currentPage?: number;
    currentChapter?: string;
    className?: string;
}

const BookNotesManager: React.FC<NotesManagerProps> = ({
    notes,
    highlights,
    onCreateNote,
    onUpdateNote,
    onDeleteNote,
    onCreateHighlight,
    onDeleteHighlight,
    currentPage,
    currentChapter,
    className = ''
}) => {
    // State for note creation
    const [newNoteText, setNewNoteText] = useState('');
    const [newNoteType, setNewNoteType] = useState<'note' | 'bookmark' | 'reminder'>('note');
    const [newNoteColor, setNewNoteColor] = useState('yellow');
    const [newNoteTags, setNewNoteTags] = useState<string[]>([]);
    const [isCreatingNote, setIsCreatingNote] = useState(false);

    // State for editing
    const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
    const [editingNoteText, setEditingNoteText] = useState('');

    // State for filtering and search
    const [searchQuery, setSearchQuery] = useState('');
    const [filterBy, setFilterBy] = useState('all');
    const [sortBy, setSortBy] = useState<'date' | 'page' | 'type'>('date');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [showPrivateOnly, setShowPrivateOnly] = useState(false);
    const [selectedTags, setSelectedTags] = useState<string[]>([]);

    // State for highlights
    const [highlightColor, setHighlightColor] = useState('yellow');
    const [highlightType, setHighlightType] = useState<'highlight' | 'underline' | 'strikethrough'>('highlight');

    // Available colors
    const colors = [
        { name: 'yellow', color: '#fbbf24', bg: '#fef3c7' },
        { name: 'blue', color: '#3b82f6', bg: '#dbeafe' },
        { name: 'green', color: '#10b981', bg: '#d1fae5' },
        { name: 'red', color: '#ef4444', bg: '#fee2e2' },
        { name: 'purple', color: '#8b5cf6', bg: '#ede9fe' },
        { name: 'orange', color: '#f97316', bg: '#fed7aa' },
        { name: 'pink', color: '#ec4899', bg: '#fce7f3' }
    ];

    // Get all unique tags from notes and highlights
    const allTags = Array.from(new Set([
        ...notes.flatMap(note => note.tags),
        ...highlights.flatMap(highlight => highlight.tags)
    ])).filter(tag => tag && tag.trim());

    // Filter and sort notes
    const filteredNotes = notes
        .filter(note => {
            // Search filter
            if (searchQuery) {
                const searchLower = searchQuery.toLowerCase();
                if (!note.note_text.toLowerCase().includes(searchLower) &&
                    !note.selected_text?.toLowerCase().includes(searchLower) &&
                    !note.tags.some(tag => tag.toLowerCase().includes(searchLower))) {
                    return false;
                }
            }

            // Type filter
            if (filterBy !== 'all') {
                if (filterBy === 'bookmarks' && note.note_type !== 'bookmark') return false;
                if (filterBy === 'notes' && note.note_type !== 'note') return false;
                if (filterBy === 'reminders' && note.note_type !== 'reminder') return false;
                if (colors.some(c => c.name === filterBy) && note.color !== filterBy) return false;
            }

            // Privacy filter
            if (showPrivateOnly && !note.is_private) return false;

            // Tags filter
            if (selectedTags.length > 0 && !selectedTags.some(tag => note.tags.includes(tag))) return false;

            return !note.is_archived;
        })
        .sort((a, b) => {
            let comparison = 0;

            switch (sortBy) {
                case 'date':
                    comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
                    break;
                case 'page':
                    comparison = (a.page_number || 0) - (b.page_number || 0);
                    break;
                case 'type':
                    comparison = a.note_type.localeCompare(b.note_type);
                    break;
            }

            return sortOrder === 'desc' ? -comparison : comparison;
        });

    // Filter highlights
    const filteredHighlights = highlights
        .filter(highlight => {
            if (searchQuery) {
                const searchLower = searchQuery.toLowerCase();
                if (!highlight.highlighted_text.toLowerCase().includes(searchLower)) {
                    return false;
                }
            }
            return !highlight.is_archived;
        })
        .sort((a, b) => {
            const comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
            return sortOrder === 'desc' ? -comparison : comparison;
        });

    const handleCreateNote = async () => {
        if (!newNoteText.trim()) return;

        setIsCreatingNote(true);
        try {
            await onCreateNote({
                note_text: newNoteText,
                note_type: newNoteType,
                color: newNoteColor,
                page_number: currentPage,
                chapter_name: currentChapter,
                tags: newNoteTags,
                is_private: true
            });

            // Reset form
            setNewNoteText('');
            setNewNoteTags([]);
            toast.success('Note created successfully');
        } catch (error) {
            toast.error('Failed to create note');
        } finally {
            setIsCreatingNote(false);
        }
    };

    const handleEditNote = async (noteId: number) => {
        if (!editingNoteText.trim()) return;

        try {
            await onUpdateNote(noteId, {
                note_text: editingNoteText
            });

            setEditingNoteId(null);
            setEditingNoteText('');
            toast.success('Note updated successfully');
        } catch (error) {
            toast.error('Failed to update note');
        }
    };

    const startEditingNote = (note: BookNote) => {
        setEditingNoteId(note.id);
        setEditingNoteText(note.note_text);
    };

    const cancelEditing = () => {
        setEditingNoteId(null);
        setEditingNoteText('');
    };

    const handleDeleteNote = async (noteId: number) => {
        try {
            await onDeleteNote(noteId);
            toast.success('Note deleted');
        } catch (error) {
            toast.error('Failed to delete note');
        }
    };

    const handleDeleteHighlight = async (highlightId: number) => {
        try {
            await onDeleteHighlight(highlightId);
            toast.success('Highlight removed');
        } catch (error) {
            toast.error('Failed to remove highlight');
        }
    };

    const copyNoteText = (text: string) => {
        navigator.clipboard.writeText(text);
        toast.success('Copied to clipboard');
    };

    const addTag = (tag: string) => {
        if (tag && !newNoteTags.includes(tag)) {
            setNewNoteTags([...newNoteTags, tag]);
        }
    };

    const removeTag = (tag: string) => {
        setNewNoteTags(newNoteTags.filter(t => t !== tag));
    };

    const getColorInfo = (colorName: string) => {
        return colors.find(c => c.name === colorName) || colors[0];
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div className={`space-y-4 ${className}`}>
            <Tabs defaultValue="notes" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="notes" className="flex items-center gap-2">
                        <StickyNote className="h-4 w-4" />
                        Notes ({filteredNotes.length})
                    </TabsTrigger>
                    <TabsTrigger value="highlights" className="flex items-center gap-2">
                        <Highlighter className="h-4 w-4" />
                        Highlights ({filteredHighlights.length})
                    </TabsTrigger>
                </TabsList>

                {/* Notes Tab */}
                <TabsContent value="notes" className="space-y-4">
                    {/* Create Note Section */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Plus className="h-4 w-4" />
                                Create New Note
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <Textarea
                                placeholder="Write your note..."
                                value={newNoteText}
                                onChange={(e) => setNewNoteText(e.target.value)}
                                className="min-h-[80px]"
                                rows={3}
                            />

                            <div className="flex flex-wrap gap-2">
                                <Select value={newNoteType} onValueChange={(value: any) => setNewNoteType(value)}>
                                    <SelectTrigger className="w-32">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="note">📝 Note</SelectItem>
                                        <SelectItem value="bookmark">🔖 Bookmark</SelectItem>
                                        <SelectItem value="reminder">⏰ Reminder</SelectItem>
                                    </SelectContent>
                                </Select>

                                <Select value={newNoteColor} onValueChange={setNewNoteColor}>
                                    <SelectTrigger className="w-32">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {colors.map((color) => (
                                            <SelectItem key={color.name} value={color.name}>
                                                <div className="flex items-center gap-2">
                                                    <div
                                                        className="w-4 h-4 rounded-full"
                                                        style={{ backgroundColor: color.color }}
                                                    />
                                                    {color.name}
                                                </div>
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>

                                <Button
                                    onClick={handleCreateNote}
                                    disabled={!newNoteText.trim() || isCreatingNote}
                                    className="flex-1"
                                >
                                    {isCreatingNote ? 'Creating...' : 'Add Note'}
                                </Button>
                            </div>

                            {/* Tags Input */}
                            <div className="space-y-2">
                                <div className="flex flex-wrap gap-1">
                                    {newNoteTags.map((tag) => (
                                        <Badge key={tag} variant="secondary" className="text-xs">
                                            {tag}
                                            <X
                                                className="h-3 w-3 ml-1 cursor-pointer"
                                                onClick={() => removeTag(tag)}
                                            />
                                        </Badge>
                                    ))}
                                </div>
                                <Input
                                    placeholder="Add tags (press Enter)"
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') {
                                            e.preventDefault();
                                            addTag(e.currentTarget.value);
                                            e.currentTarget.value = '';
                                        }
                                    }}
                                    className="text-sm"
                                />
                            </div>

                            {currentPage && (
                                <div className="text-xs text-muted-foreground flex items-center gap-2">
                                    <MapPin className="h-3 w-3" />
                                    Page {currentPage}
                                    {currentChapter && ` • ${currentChapter}`}
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    {/* Filters and Search */}
                    <Card>
                        <CardContent className="pt-4">
                            <div className="space-y-3">
                                <div className="flex gap-2">
                                    <Input
                                        placeholder="Search notes..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="flex-1"
                                    />
                                    <Select value={filterBy} onValueChange={setFilterBy}>
                                        <SelectTrigger className="w-32">
                                            <Filter className="h-4 w-4" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="all">All</SelectItem>
                                            <SelectItem value="notes">Notes</SelectItem>
                                            <SelectItem value="bookmarks">Bookmarks</SelectItem>
                                            <SelectItem value="reminders">Reminders</SelectItem>
                                            {colors.map((color) => (
                                                <SelectItem key={color.name} value={color.name}>
                                                    <div className="flex items-center gap-2">
                                                        <div
                                                            className="w-3 h-3 rounded-full"
                                                            style={{ backgroundColor: color.color }}
                                                        />
                                                        {color.name}
                                                    </div>
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm">Sort by:</span>
                                        <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
                                            <SelectTrigger className="w-24 h-8">
                                                <SelectValue />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="date">Date</SelectItem>
                                                <SelectItem value="page">Page</SelectItem>
                                                <SelectItem value="type">Type</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                                            className="h-8 px-2"
                                        >
                                            {sortOrder === 'desc' ? '↓' : '↑'}
                                        </Button>
                                    </div>

                                    <div className="flex items-center gap-2">
                                        <span className="text-sm">Private only</span>
                                        <Switch
                                            checked={showPrivateOnly}
                                            onCheckedChange={setShowPrivateOnly}
                                        />
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Notes List */}
                    <ScrollArea className="h-96">
                        <div className="space-y-3">
                            <AnimatePresence>
                                {filteredNotes.map((note) => {
                                    const colorInfo = getColorInfo(note.color);
                                    const isEditing = editingNoteId === note.id;

                                    return (
                                        <motion.div
                                            key={note.id}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, y: -10 }}
                                        >
                                            <Card className="border-l-4" style={{ borderLeftColor: colorInfo.color }}>
                                                <CardContent className="pt-4">
                                                    <div className="space-y-3">
                                                        {/* Note Header */}
                                                        <div className="flex items-start justify-between">
                                                            <div className="flex items-center gap-2">
                                                                <div
                                                                    className="w-3 h-3 rounded-full"
                                                                    style={{ backgroundColor: colorInfo.color }}
                                                                />
                                                                <Badge variant="outline" className="text-xs">
                                                                    {note.note_type === 'note' ? '📝' : note.note_type === 'bookmark' ? '🔖' : '⏰'}
                                                                    {note.note_type}
                                                                </Badge>
                                                                {note.page_number && (
                                                                    <Badge variant="secondary" className="text-xs">
                                                                        Page {note.page_number}
                                                                    </Badge>
                                                                )}
                                                            </div>
                                                            <div className="flex items-center gap-1">
                                                                <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    onClick={() => copyNoteText(note.note_text)}
                                                                    className="h-6 w-6 p-0"
                                                                >
                                                                    <Copy className="h-3 w-3" />
                                                                </Button>
                                                                <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    onClick={() => startEditingNote(note)}
                                                                    className="h-6 w-6 p-0"
                                                                >
                                                                    <Edit className="h-3 w-3" />
                                                                </Button>
                                                                <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    onClick={() => handleDeleteNote(note.id)}
                                                                    className="h-6 w-6 p-0 text-red-500 hover:text-red-700"
                                                                >
                                                                    <Trash2 className="h-3 w-3" />
                                                                </Button>
                                                            </div>
                                                        </div>

                                                        {/* Note Content */}
                                                        {isEditing ? (
                                                            <div className="space-y-2">
                                                                <Textarea
                                                                    value={editingNoteText}
                                                                    onChange={(e) => setEditingNoteText(e.target.value)}
                                                                    className="min-h-[60px]"
                                                                />
                                                                <div className="flex gap-2">
                                                                    <Button
                                                                        size="sm"
                                                                        onClick={() => handleEditNote(note.id)}
                                                                        className="flex-1"
                                                                    >
                                                                        <Save className="h-3 w-3 mr-1" />
                                                                        Save
                                                                    </Button>
                                                                    <Button
                                                                        size="sm"
                                                                        variant="outline"
                                                                        onClick={cancelEditing}
                                                                        className="flex-1"
                                                                    >
                                                                        Cancel
                                                                    </Button>
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <div className="space-y-2">
                                                                <p className="text-sm leading-relaxed">{note.note_text}</p>

                                                                {note.selected_text && (
                                                                    <div className="bg-muted/50 p-2 rounded border-l-2 border-muted">
                                                                        <p className="text-xs italic">"{note.selected_text}"</p>
                                                                    </div>
                                                                )}

                                                                {note.tags.length > 0 && (
                                                                    <div className="flex flex-wrap gap-1">
                                                                        {note.tags.map((tag) => (
                                                                            <Badge key={tag} variant="outline" className="text-xs">
                                                                                <Tag className="h-2 w-2 mr-1" />
                                                                                {tag}
                                                                            </Badge>
                                                                        ))}
                                                                    </div>
                                                                )}

                                                                <div className="flex items-center justify-between text-xs text-muted-foreground">
                                                                    <div className="flex items-center gap-2">
                                                                        <Calendar className="h-3 w-3" />
                                                                        {formatDate(note.created_at)}
                                                                    </div>
                                                                    {note.is_private && (
                                                                        <Badge variant="outline" className="text-xs">
                                                                            <Eye className="h-2 w-2 mr-1" />
                                                                            Private
                                                                        </Badge>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        </motion.div>
                                    );
                                })}
                            </AnimatePresence>

                            {filteredNotes.length === 0 && (
                                <div className="text-center py-8 text-muted-foreground">
                                    <StickyNote className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                    <p>No notes found</p>
                                    <p className="text-sm">Create your first note to get started!</p>
                                </div>
                            )}
                        </div>
                    </ScrollArea>
                </TabsContent>

                {/* Highlights Tab */}
                <TabsContent value="highlights" className="space-y-4">
                    {/* Highlight Settings */}
                    <Card>
                        <CardHeader className="pb-3">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Palette className="h-4 w-4" />
                                Highlight Settings
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <div className="flex gap-2">
                                <Select value={highlightColor} onValueChange={setHighlightColor}>
                                    <SelectTrigger className="flex-1">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {colors.map((color) => (
                                            <SelectItem key={color.name} value={color.name}>
                                                <div className="flex items-center gap-2">
                                                    <div
                                                        className="w-4 h-4 rounded"
                                                        style={{ backgroundColor: color.color }}
                                                    />
                                                    {color.name}
                                                </div>
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>

                                <Select value={highlightType} onValueChange={(value: any) => setHighlightType(value)}>
                                    <SelectTrigger className="flex-1">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="highlight">🎨 Highlight</SelectItem>
                                        <SelectItem value="underline">📝 Underline</SelectItem>
                                        <SelectItem value="strikethrough">❌ Strikethrough</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                            <p className="text-xs text-muted-foreground">
                                Select text in the PDF to create highlights with these settings
                            </p>
                        </CardContent>
                    </Card>

                    {/* Highlights List */}
                    <ScrollArea className="h-96">
                        <div className="space-y-3">
                            <AnimatePresence>
                                {filteredHighlights.map((highlight) => {
                                    const colorInfo = getColorInfo(highlight.color);

                                    return (
                                        <motion.div
                                            key={highlight.id}
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, y: -10 }}
                                        >
                                            <Card>
                                                <CardContent className="pt-4">
                                                    <div className="space-y-3">
                                                        <div className="flex items-start justify-between">
                                                            <div className="flex items-center gap-2">
                                                                <div
                                                                    className="w-3 h-3 rounded"
                                                                    style={{ backgroundColor: colorInfo.color }}
                                                                />
                                                                <Badge variant="outline" className="text-xs">
                                                                    {highlight.highlight_type}
                                                                </Badge>
                                                                {highlight.page_number && (
                                                                    <Badge variant="secondary" className="text-xs">
                                                                        Page {highlight.page_number}
                                                                    </Badge>
                                                                )}
                                                            </div>
                                                            <div className="flex items-center gap-1">
                                                                <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    onClick={() => copyNoteText(highlight.highlighted_text)}
                                                                    className="h-6 w-6 p-0"
                                                                >
                                                                    <Copy className="h-3 w-3" />
                                                                </Button>
                                                                <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    onClick={() => handleDeleteHighlight(highlight.id)}
                                                                    className="h-6 w-6 p-0 text-red-500 hover:text-red-700"
                                                                >
                                                                    <Trash2 className="h-3 w-3" />
                                                                </Button>
                                                            </div>
                                                        </div>

                                                        <div
                                                            className="p-2 rounded text-sm"
                                                            style={{ backgroundColor: colorInfo.bg }}
                                                        >
                                                            "{highlight.highlighted_text}"
                                                        </div>

                                                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                                                            <div className="flex items-center gap-2">
                                                                <Calendar className="h-3 w-3" />
                                                                {formatDate(highlight.created_at)}
                                                            </div>
                                                            <div>
                                                                {highlight.text_length} characters
                                                            </div>
                                                        </div>
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        </motion.div>
                                    );
                                })}
                            </AnimatePresence>

                            {filteredHighlights.length === 0 && (
                                <div className="text-center py-8 text-muted-foreground">
                                    <Highlighter className="h-12 w-12 mx-auto mb-4 opacity-50" />
                                    <p>No highlights found</p>
                                    <p className="text-sm">Select text in the PDF to create highlights!</p>
                                </div>
                            )}
                        </div>
                    </ScrollArea>
                </TabsContent>
            </Tabs>
        </div>
    );
};

export default BookNotesManager; 