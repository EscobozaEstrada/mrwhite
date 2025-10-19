-- ============================================================================
-- INTELLIGENT CHAT SYSTEM - COMPREHENSIVE SCHEMA
-- Version: 2.0.0
-- Prefix: ic_ (intelligent_chat)
-- Description: Complete database schema for the Intelligent Chat system
-- ============================================================================
-- This file creates all tables needed for the Intelligent Chat functionality
-- including conversations, messages, documents, feedback, preferences, reminders, etc.
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
    
    CONSTRAINT unique_user_conversation UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_ic_conversations_user_id ON ic_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_ic_conversations_updated_at ON ic_conversations(updated_at DESC);

COMMENT ON TABLE ic_conversations IS 'Single conversation per user for intelligent chat';
COMMENT ON COLUMN ic_conversations.user_id IS 'User who owns this conversation';
COMMENT ON COLUMN ic_conversations.title IS 'Conversation title (usually "Chat with Mr. White")';

-- ============================================================================
-- 2. MESSAGES TABLE
-- All messages with rich metadata, search vector, and date grouping
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ic_conversations(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    
    -- Message metadata
    tokens_used INTEGER DEFAULT 0,
    credits_used INTEGER DEFAULT 0,
    model_used VARCHAR(100),
    response_time_ms INTEGER,
    
    -- Document references
    has_documents BOOLEAN DEFAULT FALSE,
    document_ids INTEGER[],
    
    -- Mode context
    active_mode VARCHAR(50), -- 'reminders', 'health', 'wayofdog', null
    dog_profile_id INTEGER REFERENCES pet_profiles(id) ON DELETE SET NULL,
    
    -- Timestamps (date_group auto-populated by trigger)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    date_group DATE,
    
    -- Full-text search (auto-populated by trigger)
    search_vector TSVECTOR,
    
    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ic_messages_conversation_id ON ic_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ic_messages_user_id ON ic_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_ic_messages_created_at ON ic_messages(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ic_messages_date_group ON ic_messages(date_group DESC);
CREATE INDEX IF NOT EXISTS idx_ic_messages_role ON ic_messages(role);
CREATE INDEX IF NOT EXISTS idx_ic_messages_active_mode ON ic_messages(active_mode);
CREATE INDEX IF NOT EXISTS idx_ic_messages_dog_profile_id ON ic_messages(dog_profile_id);
CREATE INDEX IF NOT EXISTS idx_ic_messages_search_vector ON ic_messages USING GIN(search_vector);

COMMENT ON TABLE ic_messages IS 'All chat messages with metadata for intelligent chat';
COMMENT ON COLUMN ic_messages.search_vector IS 'Full-text search vector auto-populated by trigger';
COMMENT ON COLUMN ic_messages.date_group IS 'Date grouping for messages (auto-populated by trigger)';

-- ============================================================================
-- 3. TRIGGERS FOR MESSAGES TABLE
-- Auto-populate date_group and search_vector
-- ============================================================================

-- Trigger function for date_group
CREATE OR REPLACE FUNCTION ic_update_message_date_group()
RETURNS TRIGGER AS $$
BEGIN
    NEW.date_group = DATE(NEW.created_at);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ic_messages_set_date_group ON ic_messages;
CREATE TRIGGER ic_messages_set_date_group
    BEFORE INSERT ON ic_messages
    FOR EACH ROW
    EXECUTE FUNCTION ic_update_message_date_group();

-- Trigger function for search_vector
CREATE OR REPLACE FUNCTION ic_update_message_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector = to_tsvector('english', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ic_messages_update_search_vector ON ic_messages;
CREATE TRIGGER ic_messages_update_search_vector
    BEFORE INSERT OR UPDATE OF content ON ic_messages
    FOR EACH ROW
    EXECUTE FUNCTION ic_update_message_search_vector();

-- ============================================================================
-- 4. CONVERSATION CONTEXT TABLE
-- Track active mode and conversation state
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_conversation_context (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES ic_conversations(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Active state
    active_mode VARCHAR(50), -- 'reminders', 'health', 'wayofdog', null
    selected_dog_profile_id INTEGER REFERENCES pet_profiles(id) ON DELETE CASCADE,
    
    -- Conversation memory
    recent_topics JSONB DEFAULT '[]'::JSONB,
    mentioned_dogs VARCHAR(100)[],
    
    -- Session state
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_conversation_context UNIQUE (conversation_id)
);

CREATE INDEX IF NOT EXISTS idx_ic_context_conversation_id ON ic_conversation_context(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ic_context_user_id ON ic_conversation_context(user_id);

COMMENT ON TABLE ic_conversation_context IS 'Track active mode and state for each conversation';

-- ============================================================================
-- 5. DOG PROFILES TABLE (Intelligent Chat specific)
-- Lightweight dog profiles for chat context
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_dog_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    breed VARCHAR(100),
    age INTEGER,
    date_of_birth DATE,
    weight NUMERIC(6, 2),
    gender VARCHAR(10),
    color VARCHAR(100),
    image_url VARCHAR(500),
    image_description TEXT,
    comprehensive_profile JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ic_dog_profiles_user_id ON ic_dog_profiles(user_id);

COMMENT ON TABLE ic_dog_profiles IS 'Dog profiles for intelligent chat context';

-- ============================================================================
-- 6. DOCUMENTS TABLE
-- Documents uploaded during chat conversations
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
    pinecone_ids TEXT[],
    
    -- Extracted content
    extracted_text TEXT,
    image_analysis JSONB,
    
    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    chunk_count INTEGER DEFAULT 0,
    pinecone_vectors_stored BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Document metadata
    doc_metadata JSONB DEFAULT '{}'::JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Soft delete
    is_deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_ic_documents_user_id ON ic_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_ic_documents_conversation_id ON ic_documents(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ic_documents_message_id ON ic_documents(message_id);
CREATE INDEX IF NOT EXISTS idx_ic_documents_created_at ON ic_documents(created_at DESC);

COMMENT ON TABLE ic_documents IS 'Documents uploaded during intelligent chat conversations';

-- ============================================================================
-- 7. MESSAGE-DOCUMENTS JUNCTION TABLE
-- Links messages to their attached documents
-- ============================================================================
CREATE TABLE IF NOT EXISTS ic_message_documents (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES ic_messages(id) ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES ic_documents(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_message_document UNIQUE (message_id, document_id)
);

CREATE INDEX IF NOT EXISTS idx_ic_message_docs_message_id ON ic_message_documents(message_id);
CREATE INDEX IF NOT EXISTS idx_ic_message_docs_document_id ON ic_message_documents(document_id);

COMMENT ON TABLE ic_message_documents IS 'Junction table linking messages to their attached documents';

-- ============================================================================
-- 8. VET REPORTS TABLE
-- Vet reports for health mode functionality
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

CREATE INDEX IF NOT EXISTS idx_ic_vet_reports_user_id ON ic_vet_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_ic_vet_reports_dog_profile_id ON ic_vet_reports(dog_profile_id);
CREATE INDEX IF NOT EXISTS idx_ic_vet_reports_report_date ON ic_vet_reports(report_date DESC);

COMMENT ON TABLE ic_vet_reports IS 'Vet reports for health mode in intelligent chat';

-- ============================================================================
-- 9. MESSAGE FEEDBACK TABLE
-- Like/dislike feedback on AI responses
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
    
    CONSTRAINT unique_message_feedback UNIQUE (message_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_ic_message_feedback_message_id ON ic_message_feedback(message_id);
CREATE INDEX IF NOT EXISTS idx_ic_message_feedback_user_id ON ic_message_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_ic_message_feedback_type ON ic_message_feedback(feedback_type);

COMMENT ON TABLE ic_message_feedback IS 'User feedback (like/dislike) on AI responses';

-- ============================================================================
-- 10. USER CORRECTIONS TABLE
-- User corrections to help AI learn
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

CREATE INDEX IF NOT EXISTS idx_ic_corrections_user_id ON ic_user_corrections(user_id);
CREATE INDEX IF NOT EXISTS idx_ic_corrections_message_id ON ic_user_corrections(message_id);
CREATE INDEX IF NOT EXISTS idx_ic_corrections_is_applied ON ic_user_corrections(is_applied);

COMMENT ON TABLE ic_user_corrections IS 'User corrections to help improve AI responses';

-- ============================================================================
-- 11. USER PREFERENCES TABLE
-- User communication preferences and learned patterns
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
    preferred_topics JSONB DEFAULT '[]'::JSONB,
    avoided_topics JSONB DEFAULT '[]'::JSONB,
    
    -- Context
    typical_dog_concerns VARCHAR(100)[],
    common_questions VARCHAR(200)[],
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_user_preference UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS idx_ic_preferences_user_id ON ic_user_preferences(user_id);

COMMENT ON TABLE ic_user_preferences IS 'User communication preferences and learned behavior patterns';

-- ============================================================================
-- 12. REMINDERS TABLE
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
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'completed', 'cancelled')),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Created from chat context
    created_from_message BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ic_reminders_user_id ON ic_reminders(user_id);
CREATE INDEX IF NOT EXISTS idx_ic_reminders_conversation_id ON ic_reminders(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ic_reminders_dog_profile_id ON ic_reminders(dog_profile_id);
CREATE INDEX IF NOT EXISTS idx_ic_reminders_status ON ic_reminders(status);
CREATE INDEX IF NOT EXISTS idx_ic_reminders_datetime ON ic_reminders(reminder_datetime);

COMMENT ON TABLE ic_reminders IS 'Reminders created through intelligent chat reminder mode';

-- ============================================================================
-- 13. BOOK COMMENTS ACCESS TABLE
-- Track which book notes are accessible in wayofdog mode
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
    
    CONSTRAINT unique_book_comment_access UNIQUE (user_id, book_note_id)
);

CREATE INDEX IF NOT EXISTS idx_ic_book_access_user_id ON ic_book_comments_access(user_id);
CREATE INDEX IF NOT EXISTS idx_ic_book_access_book_note_id ON ic_book_comments_access(book_note_id);

COMMENT ON TABLE ic_book_comments_access IS 'Track user book notes accessibility in wayofdog mode';

-- ============================================================================
-- 14. CREDIT USAGE TABLE
-- Credit consumption tracking per message
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

CREATE INDEX IF NOT EXISTS idx_ic_credit_usage_user_id ON ic_credit_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_ic_credit_usage_message_id ON ic_credit_usage(message_id);
CREATE INDEX IF NOT EXISTS idx_ic_credit_usage_action_type ON ic_credit_usage(action_type);
CREATE INDEX IF NOT EXISTS idx_ic_credit_usage_created_at ON ic_credit_usage(created_at DESC);

COMMENT ON TABLE ic_credit_usage IS 'Credit consumption tracking for intelligent chat actions';

-- ============================================================================
-- 15. UPDATE TRIGGER FOR CONVERSATIONS
-- Auto-update updated_at timestamp
-- ============================================================================
CREATE OR REPLACE FUNCTION ic_update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS ic_conversations_updated_at ON ic_conversations;
CREATE TRIGGER ic_conversations_updated_at
    BEFORE UPDATE ON ic_conversations
    FOR EACH ROW
    EXECUTE FUNCTION ic_update_updated_at_column();

DROP TRIGGER IF NOT EXISTS ic_conversation_context_updated_at ON ic_conversation_context;
CREATE TRIGGER ic_conversation_context_updated_at
    BEFORE UPDATE ON ic_conversation_context
    FOR EACH ROW
    EXECUTE FUNCTION ic_update_updated_at_column();

DROP TRIGGER IF NOT EXISTS ic_user_preferences_updated_at ON ic_user_preferences;
CREATE TRIGGER ic_user_preferences_updated_at
    BEFORE UPDATE ON ic_user_preferences
    FOR EACH ROW
    EXECUTE FUNCTION ic_update_updated_at_column();

DROP TRIGGER IF NOT EXISTS ic_reminders_updated_at ON ic_reminders;
CREATE TRIGGER ic_reminders_updated_at
    BEFORE UPDATE ON ic_reminders
    FOR EACH ROW
    EXECUTE FUNCTION ic_update_updated_at_column();

DROP TRIGGER IF NOT EXISTS ic_documents_updated_at ON ic_documents;
CREATE TRIGGER ic_documents_updated_at
    BEFORE UPDATE ON ic_documents
    FOR EACH ROW
    EXECUTE FUNCTION ic_update_updated_at_column();

DROP TRIGGER IF NOT EXISTS ic_vet_reports_updated_at ON ic_vet_reports;
CREATE TRIGGER ic_vet_reports_updated_at
    BEFORE UPDATE ON ic_vet_reports
    FOR EACH ROW
    EXECUTE FUNCTION ic_update_updated_at_column();

DROP TRIGGER IF NOT EXISTS ic_dog_profiles_updated_at ON ic_dog_profiles;
CREATE TRIGGER ic_dog_profiles_updated_at
    BEFORE UPDATE ON ic_dog_profiles
    FOR EACH ROW
    EXECUTE FUNCTION ic_update_updated_at_column();

-- ============================================================================
-- COMPLETION MESSAGE
-- ============================================================================
DO $$ 
BEGIN 
    RAISE NOTICE '✅ Intelligent Chat Schema Migration Complete!';
    RAISE NOTICE 'Created Tables:';
    RAISE NOTICE '  1. ic_conversations - Conversation management';
    RAISE NOTICE '  2. ic_messages - All chat messages';
    RAISE NOTICE '  3. ic_conversation_context - Active state tracking';
    RAISE NOTICE '  4. ic_dog_profiles - Dog profile context';
    RAISE NOTICE '  5. ic_documents - Document uploads';
    RAISE NOTICE '  6. ic_message_documents - Message-document links';
    RAISE NOTICE '  7. ic_vet_reports - Health mode vet reports';
    RAISE NOTICE '  8. ic_message_feedback - Like/dislike feedback';
    RAISE NOTICE '  9. ic_user_corrections - User corrections';
    RAISE NOTICE ' 10. ic_user_preferences - User preferences';
    RAISE NOTICE ' 11. ic_reminders - Reminder mode reminders';
    RAISE NOTICE ' 12. ic_book_comments_access - Wayofdog book notes';
    RAISE NOTICE ' 13. ic_credit_usage - Credit tracking';
END $$;

