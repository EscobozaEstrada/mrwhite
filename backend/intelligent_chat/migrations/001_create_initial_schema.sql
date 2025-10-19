-- ============================================================================
-- INTELLIGENT CHAT SYSTEM - INITIAL SCHEMA
-- Version: 1.0.0
-- Prefix: ic_ (intelligent_chat)
-- ============================================================================

-- ============================================================================
-- 1. CONVERSATIONS TABLE
-- Single conversation per user with all messages
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) DEFAULT 'Chat with Mr. White',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT FALSE,
    
    -- Indexes
    CONSTRAINT unique_user_conversation UNIQUE (user_id)
);

CREATE INDEX idx_ic_conversations_user_id ON ic_conversations(user_id);
CREATE INDEX idx_ic_conversations_updated_at ON ic_conversations(updated_at DESC);

-- ============================================================================
-- 2. MESSAGES TABLE
-- All messages with rich metadata and date grouping
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ic_conversations(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    
    -- Message metadata
    tokens_used INTEGER DEFAULT 0,
    credits_used DECIMAL(10, 4) DEFAULT 0,
    model_used VARCHAR(100),
    response_time_ms INTEGER,
    
    -- Document references
    has_documents BOOLEAN DEFAULT FALSE,
    document_ids INTEGER[],
    
    -- Mode context
    active_mode VARCHAR(50), -- 'reminders', 'health', 'wayofdog', null
    dog_profile_id INTEGER REFERENCES pet_profiles(id) ON DELETE SET NULL,
    
    -- Timestamps for date grouping
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    date_group DATE,
    
    -- Search
    search_vector tsvector,
    
    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_ic_messages_conversation_id ON ic_messages(conversation_id);
CREATE INDEX idx_ic_messages_user_id ON ic_messages(user_id);
CREATE INDEX idx_ic_messages_created_at ON ic_messages(created_at DESC);
CREATE INDEX idx_ic_messages_date_group ON ic_messages(date_group DESC);
CREATE INDEX idx_ic_messages_search_vector ON ic_messages USING gin(search_vector);
CREATE INDEX idx_ic_messages_role ON ic_messages(role);

-- Trigger for search vector and date_group
CREATE OR REPLACE FUNCTION ic_messages_search_trigger() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
    NEW.date_group := NEW.created_at::date;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ic_messages_search_update
    BEFORE INSERT OR UPDATE ON ic_messages
    FOR EACH ROW
    EXECUTE FUNCTION ic_messages_search_trigger();

-- ============================================================================
-- 3. DOCUMENTS TABLE
-- All uploaded documents with S3 links and Pinecone IDs
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES ic_messages(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES ic_conversations(id) ON DELETE CASCADE,
    
    -- File information
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL, -- 'image', 'pdf', 'docx', 'txt'
    file_size BIGINT,
    mime_type VARCHAR(100),
    
    -- S3 storage
    s3_key VARCHAR(500) NOT NULL,
    s3_url TEXT NOT NULL,
    
    -- Pinecone storage
    pinecone_namespace VARCHAR(200),
    pinecone_ids TEXT[], -- Array of vector IDs
    
    -- Extracted content
    extracted_text TEXT,
    image_analysis JSONB, -- For image content analysis
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_ic_documents_user_id ON ic_documents(user_id);
CREATE INDEX idx_ic_documents_message_id ON ic_documents(message_id);
CREATE INDEX idx_ic_documents_conversation_id ON ic_documents(conversation_id);
CREATE INDEX idx_ic_documents_file_type ON ic_documents(file_type);
CREATE INDEX idx_ic_documents_created_at ON ic_documents(created_at DESC);

-- ============================================================================
-- 4. VET REPORTS TABLE
-- Separate table for vet reports attached to dog profiles
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_vet_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    dog_profile_id INTEGER NOT NULL REFERENCES pet_profiles(id) ON DELETE CASCADE,
    
    -- File information
    report_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    
    -- S3 storage
    s3_key VARCHAR(500) NOT NULL,
    s3_url TEXT NOT NULL,
    
    -- Pinecone storage
    pinecone_namespace VARCHAR(200),
    pinecone_ids TEXT[],
    
    -- Extracted information
    extracted_text TEXT,
    key_findings JSONB,
    
    -- Report date
    report_date DATE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ic_vet_reports_user_id ON ic_vet_reports(user_id);
CREATE INDEX idx_ic_vet_reports_dog_profile_id ON ic_vet_reports(dog_profile_id);
CREATE INDEX idx_ic_vet_reports_report_date ON ic_vet_reports(report_date DESC);

-- ============================================================================
-- 5. REMINDERS TABLE
-- Reminders created through reminder mode
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_reminders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES ic_conversations(id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES ic_messages(id) ON DELETE SET NULL,
    dog_profile_id INTEGER REFERENCES pet_profiles(id) ON DELETE CASCADE,
    
    -- Reminder details
    title VARCHAR(255) NOT NULL,
    description TEXT,
    reminder_type VARCHAR(50), -- 'vet_appointment', 'medication', 'grooming', 'custom'
    
    -- Timing
    reminder_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    recurrence VARCHAR(50), -- 'once', 'daily', 'weekly', 'monthly'
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'completed', 'cancelled'
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Created from chat context
    created_from_message BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ic_reminders_user_id ON ic_reminders(user_id);
CREATE INDEX idx_ic_reminders_dog_profile_id ON ic_reminders(dog_profile_id);
CREATE INDEX idx_ic_reminders_reminder_datetime ON ic_reminders(reminder_datetime);
CREATE INDEX idx_ic_reminders_status ON ic_reminders(status);

-- ============================================================================
-- 6. USER CORRECTIONS TABLE
-- Learn from user corrections and mistakes
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_user_corrections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES ic_messages(id) ON DELETE CASCADE,
    
    -- Correction details
    incorrect_response TEXT,
    correction_text TEXT,
    correction_type VARCHAR(50), -- 'factual', 'tone', 'format', 'recommendation'
    
    -- Context
    context_summary TEXT,
    
    -- Applied
    is_applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ic_user_corrections_user_id ON ic_user_corrections(user_id);
CREATE INDEX idx_ic_user_corrections_is_applied ON ic_user_corrections(is_applied);

-- ============================================================================
-- 7. MESSAGE FEEDBACK TABLE
-- Like/Dislike feedback on messages
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_message_feedback (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES ic_messages(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Feedback
    feedback_type VARCHAR(20) NOT NULL CHECK (feedback_type IN ('like', 'dislike')),
    feedback_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    CONSTRAINT unique_message_feedback UNIQUE (message_id, user_id)
);

CREATE INDEX idx_ic_message_feedback_message_id ON ic_message_feedback(message_id);
CREATE INDEX idx_ic_message_feedback_user_id ON ic_message_feedback(user_id);
CREATE INDEX idx_ic_message_feedback_type ON ic_message_feedback(feedback_type);

-- ============================================================================
-- 8. USER PREFERENCES TABLE
-- Store user preferences and learned behaviors
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Communication preferences
    response_style VARCHAR(50) DEFAULT 'balanced', -- 'concise', 'detailed', 'balanced'
    tone_preference VARCHAR(50) DEFAULT 'friendly', -- 'professional', 'friendly', 'casual'
    
    -- Feature preferences
    enable_curiosity BOOLEAN DEFAULT TRUE,
    enable_followup_questions BOOLEAN DEFAULT TRUE,
    enable_pawtree_links BOOLEAN DEFAULT TRUE,
    
    -- Learned patterns
    preferred_topics JSONB DEFAULT '[]'::jsonb,
    avoided_topics JSONB DEFAULT '[]'::jsonb,
    
    -- Context
    typical_dog_concerns TEXT[],
    common_questions TEXT[],
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    CONSTRAINT unique_user_preferences UNIQUE (user_id)
);

CREATE INDEX idx_ic_user_preferences_user_id ON ic_user_preferences(user_id);

-- ============================================================================
-- 9. CONVERSATION CONTEXT TABLE
-- Store current conversation state and active mode
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_conversation_context (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ic_conversations(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Active state
    active_mode VARCHAR(50), -- 'reminders', 'health', 'wayofdog', null
    selected_dog_profile_id INTEGER REFERENCES pet_profiles(id) ON DELETE SET NULL,
    
    -- Conversation memory
    recent_topics JSONB DEFAULT '[]'::jsonb,
    mentioned_dogs TEXT[],
    
    -- Session state
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    CONSTRAINT unique_conversation_context UNIQUE (conversation_id)
);

CREATE INDEX idx_ic_conversation_context_conversation_id ON ic_conversation_context(conversation_id);
CREATE INDEX idx_ic_conversation_context_user_id ON ic_conversation_context(user_id);

-- ============================================================================
-- 10. CREDIT USAGE TABLE
-- Track credit consumption per message
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_credit_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES ic_messages(id) ON DELETE CASCADE,
    
    -- Usage details
    action_type VARCHAR(50) NOT NULL, -- 'chat', 'document_upload', 'image_analysis', 'voice_transcription'
    credits_used DECIMAL(10, 4) NOT NULL,
    tokens_used INTEGER,
    
    -- Model information
    model_used VARCHAR(100),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ic_credit_usage_user_id ON ic_credit_usage(user_id);
CREATE INDEX idx_ic_credit_usage_message_id ON ic_credit_usage(message_id);
CREATE INDEX idx_ic_credit_usage_created_at ON ic_credit_usage(created_at DESC);

-- ============================================================================
-- 11. BOOK COMMENTS ACCESS TABLE
-- Track which book_notes are accessible in wayofdog mode
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_book_comments_access (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_note_id INTEGER NOT NULL REFERENCES book_notes(id) ON DELETE CASCADE,
    
    -- Access metadata
    last_accessed TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0,
    
    -- Pinecone reference
    pinecone_namespace VARCHAR(200),
    pinecone_id VARCHAR(200),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    CONSTRAINT unique_book_comment_access UNIQUE (user_id, book_note_id)
);

CREATE INDEX idx_ic_book_comments_access_user_id ON ic_book_comments_access(user_id);
CREATE INDEX idx_ic_book_comments_access_book_note_id ON ic_book_comments_access(book_note_id);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER update_ic_conversations_updated_at
    BEFORE UPDATE ON ic_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ic_vet_reports_updated_at
    BEFORE UPDATE ON ic_vet_reports
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ic_reminders_updated_at
    BEFORE UPDATE ON ic_reminders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ic_user_preferences_updated_at
    BEFORE UPDATE ON ic_user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ic_conversation_context_updated_at
    BEFORE UPDATE ON ic_conversation_context
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ic_book_comments_access_updated_at
    BEFORE UPDATE ON ic_book_comments_access
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE ic_conversations IS 'Single conversation per user containing all messages';
COMMENT ON TABLE ic_messages IS 'All chat messages with rich metadata and search capabilities';
COMMENT ON TABLE ic_documents IS 'Documents uploaded during chat (images, PDFs, etc.)';
COMMENT ON TABLE ic_vet_reports IS 'Vet reports attached to dog profiles for health mode';
COMMENT ON TABLE ic_reminders IS 'Reminders created through reminder mode';
COMMENT ON TABLE ic_user_corrections IS 'User corrections to learn from mistakes';
COMMENT ON TABLE ic_message_feedback IS 'Like/dislike feedback on assistant messages';
COMMENT ON TABLE ic_user_preferences IS 'User preferences and learned behaviors';
COMMENT ON TABLE ic_conversation_context IS 'Current conversation state and active mode';
COMMENT ON TABLE ic_credit_usage IS 'Credit consumption tracking per message';
COMMENT ON TABLE ic_book_comments_access IS 'Access tracking for book comments in wayofdog mode';

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- No initial data needed, tables will be populated as users interact

