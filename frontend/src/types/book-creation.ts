// Book Creation Types and Interfaces

export interface BookTag {
    id: number;
    name: string;
    description: string;
    color: string;
    icon: string;
    category_order: number;
    is_active: boolean;
}

export interface ContentSummary {
    total_items: number;
    chat_messages: number;
    photos: number;
    documents: number;
}

export interface BookEstimates {
    estimated_chapters: number;
    estimated_pages: number;
    estimated_words: number;
}

export interface ContentSample {
    id: number;
    content: string;
    type: 'chat' | 'photo' | 'document';
    created_at: string;
    [key: string]: any;
}

export interface PreviewData {
    content_summary: ContentSummary;
    book_estimates: BookEstimates;
    content_samples: {
        recent_messages: ContentSample[];
        recent_photos: ContentSample[];
        recent_documents: ContentSample[];
    };
    selected_tags: number[];
    date_range: {
        start?: string;
        end?: string;
    };
}

export interface BookChapter {
    id: number;
    chapter_number: number;
    title: string;
    subtitle?: string;
    description?: string;
    primary_tag_id?: number;
    date_range_start?: string;
    date_range_end?: string;
    content_summary?: string;
    word_count: number;
    content_item_count: number;
    created_at: string;
    updated_at: string;
    content_items: BookContentItem[];
    primary_tag?: BookTag;
}

export interface BookContentItem {
    id: number;
    content_type: string;
    source_id: number;
    source_table: string;
    title?: string;
    content_text?: string;
    content_url?: string;
    thumbnail_url?: string;
    original_date: string;
    tags?: string[];
    ai_analysis?: string;
    item_order: number;
    include_in_export: boolean;
    processing_notes?: string;
    created_at: string;
}

export interface CustomBook {
    id: number;
    user_id: number;
    title: string;
    subtitle?: string;
    description?: string;
    cover_image_url?: string;
    selected_tags?: number[];
    date_range_start?: string;
    date_range_end?: string;
    content_types?: string[];
    book_style: 'narrative' | 'timeline' | 'reference';
    include_photos: boolean;
    include_documents: boolean;
    include_chat_history: boolean;
    auto_organize_by_date: boolean;
    generation_status: 'draft' | 'generating' | 'completed' | 'failed';
    generation_progress: number;
    generation_started_at?: string;
    generation_completed_at?: string;
    generation_error?: string;
    pdf_url?: string;
    epub_url?: string;
    html_content?: string;
    total_content_items: number;
    total_photos: number;
    total_documents: number;
    total_chat_messages: number;
    word_count: number;
    created_at: string;
    updated_at: string;
    chapters: BookChapter[];
}

export interface BookCreationFilters {
    selected_tags?: number[];
    date_range_start?: string;
    date_range_end?: string;
    content_types?: string[];
}

export interface BookCreationConfig {
    title: string;
    subtitle?: string;
    description?: string;
    selected_tags?: number[];
    date_range_start?: string;
    date_range_end?: string;
    content_types?: string[];
    book_style?: 'narrative' | 'timeline' | 'reference';
    include_photos?: boolean;
    include_documents?: boolean;
    include_chat_history?: boolean;
    auto_organize_by_date?: boolean;
}

export interface BookCreationResponse {
    success: boolean;
    book_id?: number;
    book?: CustomBook;
    response?: string;
    processing_metadata?: {
        workflow_trace: string[];
        agent_notes: Record<string, any>;
        completion_percentage: number;
    };
    error?: string;
    message?: string;
}

export interface ContentSearchResponse {
    success: boolean;
    total_content_found: number;
    content_summary?: {
        chat_messages: number;
        photos: number;
        documents: number;
    };
    content_preview?: {
        chat_messages: ContentSample[];
        photos: ContentSample[];
        documents: ContentSample[];
    };
    response?: string;
    processing_metadata?: {
        workflow_trace: string[];
        agent_notes: Record<string, any>;
        completion_percentage: number;
    };
    error?: string;
    message?: string;
}

export interface BookPreviewResponse {
    success: boolean;
    preview?: PreviewData;
    response?: string;
    error?: string;
    message?: string;
}

export interface BookTagsResponse {
    success: boolean;
    tags: BookTag[];
    total_tags: number;
    error?: string;
    message?: string;
}

export interface UserBooksResponse {
    success: boolean;
    books: CustomBook[];
    total_books: number;
    error?: string;
    message?: string;
}

export interface BookStatusResponse {
    success: boolean;
    book_id: number;
    generation_status: string;
    generation_progress: number;
    generation_started_at?: string;
    generation_completed_at?: string;
    generation_error?: string;
    total_content_items: number;
    word_count: number;
    error?: string;
    message?: string;
}

export interface BookDownloadResponse {
    success: boolean;
    content?: string;
    download_url?: string;
    format: 'html' | 'pdf' | 'epub';
    filename: string;
    error?: string;
    message?: string;
}

// API Hook types
export interface UseBookCreation {
    isLoading: boolean;
    error: string | null;
    createBook: (config: BookCreationConfig) => Promise<BookCreationResponse>;
    searchContent: (filters: BookCreationFilters) => Promise<ContentSearchResponse>;
    previewBook: (filters: BookCreationFilters) => Promise<BookPreviewResponse>;
}

export interface UseBookTags {
    tags: BookTag[];
    isLoading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
}

export interface UseUserBooks {
    books: CustomBook[];
    isLoading: boolean;
    error: string | null;
    refetch: () => Promise<void>;
    deleteBook: (bookId: number) => Promise<boolean>;
} 