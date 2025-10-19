export interface CareRecord {
    id: number;
    title: string;
    category: string;
    date_occurred: string;
    description?: string;
    metadata?: Record<string, any>;
    reminder_date?: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    documents: Document[];
}

export interface Document {
    id: number;
    filename: string;
    original_filename: string;
    file_type: string;
    file_size: number;
    s3_url: string;
    content_summary?: string;
    metadata?: Record<string, any>;
    is_processed: boolean;
    processing_status: 'pending' | 'processing' | 'completed' | 'failed';
    created_at: string;
    updated_at: string;
}

export interface KnowledgeBaseStats {
    total_documents: number;
    total_care_records: number;
    processed_documents: number;
    last_updated?: string;
    categories: Record<string, number>;
}

export interface CareCategory {
    value: string;
    label: string;
    icon: string;
}

export interface TimelineItem {
    type: 'care_record' | 'document';
    data: CareRecord | Document;
    date: string;
}

export interface SearchResults {
    documents: any[];
    care_records: CareRecord[];
    total_found: number;
}

export interface ChatContext {
    conversation_id: number;
    thread_id: string;
    context_used: {
        current_message: string;
        chat_history: ChatMessage[];
        relevant_documents: any[];
        relevant_care_records: CareRecord[];
        user_stats: KnowledgeBaseStats;
        sources: ContextSource[];
        documents_count: number;
        care_records_count: number;
        upcoming_reminders?: CareRecord[];
    };
    sources: ContextSource[];
    care_records_referenced: number;
    documents_referenced: number;
}

export interface ContextSource {
    type: 'document' | 'care_record' | 'reminder';
    title: string;
    content_preview?: string;
    relevance_score?: number;
    category?: string;
    date?: string;
    description?: string;
}

export interface ChatMessage {
    type: 'user' | 'ai';
    content: string;
    timestamp: string;
}

export interface EnhancedChatResponse {
    success: boolean;
    response: string;
    context_info: ChatContext;
}

export interface CareSummary {
    knowledge_base_stats: KnowledgeBaseStats;
    recent_timeline: TimelineItem[];
    upcoming_reminders: CareRecord[];
    recent_conversations: any[];
    summary_generated_at: string;
}

export interface IntentAnalysis {
    primary_intent: 'care_history' | 'medical_records' | 'reminders' | 'document_search' | 'general_question';
    intents: Record<string, boolean>;
    requires_context: boolean;
}

export interface UploadDocumentRequest {
    file: File;
    care_record_id?: number;
}

export interface CreateCareRecordRequest {
    title: string;
    category: string;
    date_occurred: string;
    description?: string;
    metadata?: Record<string, any>;
    reminder_date?: string;
} 