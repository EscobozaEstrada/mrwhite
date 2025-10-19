-- ============================================================================
-- CREATE DOCUMENTS TABLES FOR PHASE 4
-- Document pre-processing with upload, extraction, and Pinecone storage
-- ============================================================================

-- Main documents table
CREATE TABLE IF NOT EXISTS ic_documents (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    conversation_id INTEGER REFERENCES ic_conversations(id) ON DELETE CASCADE,
    message_id INTEGER REFERENCES ic_messages(id) ON DELETE SET NULL,
    
    -- File information
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,  -- pdf, image, docx, txt
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    
    -- Storage
    s3_url VARCHAR(500) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    
    -- Processing
    extracted_text TEXT,
    chunk_count INTEGER DEFAULT 0,
    processing_status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    error_message TEXT,
    
    -- Pinecone
    pinecone_vectors_stored BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Junction table for message-document relationships
CREATE TABLE IF NOT EXISTS ic_message_documents (
    id SERIAL PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES ic_messages(id) ON DELETE CASCADE,
    document_id INTEGER NOT NULL REFERENCES ic_documents(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(message_id, document_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ic_documents_user_id ON ic_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_ic_documents_conversation_id ON ic_documents(conversation_id);
CREATE INDEX IF NOT EXISTS idx_ic_documents_message_id ON ic_documents(message_id);
CREATE INDEX IF NOT EXISTS idx_ic_documents_status ON ic_documents(processing_status);
CREATE INDEX IF NOT EXISTS idx_ic_documents_created_at ON ic_documents(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ic_message_docs_message_id ON ic_message_documents(message_id);
CREATE INDEX IF NOT EXISTS idx_ic_message_docs_document_id ON ic_message_documents(document_id);

-- Comments
COMMENT ON TABLE ic_documents IS 'Stores uploaded documents with processing status and S3 links';
COMMENT ON TABLE ic_message_documents IS 'Junction table linking messages to their attached documents';
COMMENT ON COLUMN ic_documents.s3_url IS 'Public/signed S3 URL for document access';
COMMENT ON COLUMN ic_documents.extracted_text IS 'Full text extracted from document for embedding';
COMMENT ON COLUMN ic_documents.pinecone_vectors_stored IS 'Whether document chunks have been stored in Pinecone';






