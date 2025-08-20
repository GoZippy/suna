-- Knowledge Base and Vector Storage Tables

-- Knowledge base entries with vector embeddings
CREATE TABLE knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    title VARCHAR(500),
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text', -- text, code, markdown, pdf, etc.
    source_url VARCHAR(1000),
    source_type VARCHAR(50), -- file, url, manual, api
    embedding vector(1536), -- OpenAI ada-002 dimension
    chunk_index INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 1,
    file_path VARCHAR(1000),
    file_size BIGINT,
    file_hash VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Document collections for organizing knowledge
CREATE TABLE document_collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Many-to-many relationship between knowledge base and collections
CREATE TABLE knowledge_collection_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID NOT NULL REFERENCES document_collections(id) ON DELETE CASCADE,
    knowledge_id UUID NOT NULL REFERENCES knowledge_base(id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(collection_id, knowledge_id)
);

-- Search history for improving results
CREATE TABLE search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    query_embedding vector(1536),
    results_count INTEGER DEFAULT 0,
    clicked_result_ids UUID[],
    search_type VARCHAR(50) DEFAULT 'semantic', -- semantic, keyword, hybrid
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for knowledge base and vector operations
CREATE INDEX idx_knowledge_base_user_id ON knowledge_base(user_id);
CREATE INDEX idx_knowledge_base_project_id ON knowledge_base(project_id);
CREATE INDEX idx_knowledge_base_content_type ON knowledge_base(content_type);
CREATE INDEX idx_knowledge_base_source_type ON knowledge_base(source_type);
CREATE INDEX idx_knowledge_base_created_at ON knowledge_base(created_at);
CREATE INDEX idx_knowledge_base_file_hash ON knowledge_base(file_hash);

-- Vector similarity search index (HNSW for better performance)
CREATE INDEX idx_knowledge_base_embedding ON knowledge_base 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Full-text search index for content
CREATE INDEX idx_knowledge_base_content_fts ON knowledge_base 
USING gin(to_tsvector('english', content));

-- Combined GIN index for metadata queries
CREATE INDEX idx_knowledge_base_metadata ON knowledge_base USING gin(metadata);

CREATE INDEX idx_document_collections_user_id ON document_collections(user_id);
CREATE INDEX idx_document_collections_project_id ON document_collections(project_id);

CREATE INDEX idx_knowledge_collection_items_collection_id ON knowledge_collection_items(collection_id);
CREATE INDEX idx_knowledge_collection_items_knowledge_id ON knowledge_collection_items(knowledge_id);

CREATE INDEX idx_search_history_user_id ON search_history(user_id);
CREATE INDEX idx_search_history_project_id ON search_history(project_id);
CREATE INDEX idx_search_history_created_at ON search_history(created_at);

-- Vector similarity search index for search history
CREATE INDEX idx_search_history_embedding ON search_history 
USING hnsw (query_embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Apply updated_at triggers
CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_document_collections_updated_at BEFORE UPDATE ON document_collections
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function for hybrid search (combining vector and text search)
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(1536),
    user_id_param UUID DEFAULT NULL,
    project_id_param UUID DEFAULT NULL,
    limit_param INTEGER DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    id UUID,
    title VARCHAR(500),
    content TEXT,
    similarity_score FLOAT,
    text_rank FLOAT,
    combined_score FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    WITH vector_search AS (
        SELECT 
            kb.id,
            kb.title,
            kb.content,
            1 - (kb.embedding <=> query_embedding) as similarity_score,
            kb.metadata
        FROM knowledge_base kb
        WHERE 
            (user_id_param IS NULL OR kb.user_id = user_id_param)
            AND (project_id_param IS NULL OR kb.project_id = project_id_param)
            AND (1 - (kb.embedding <=> query_embedding)) > similarity_threshold
    ),
    text_search AS (
        SELECT 
            kb.id,
            ts_rank(to_tsvector('english', kb.content), plainto_tsquery('english', query_text)) as text_rank
        FROM knowledge_base kb
        WHERE 
            (user_id_param IS NULL OR kb.user_id = user_id_param)
            AND (project_id_param IS NULL OR kb.project_id = project_id_param)
            AND to_tsvector('english', kb.content) @@ plainto_tsquery('english', query_text)
    )
    SELECT 
        vs.id,
        vs.title,
        vs.content,
        vs.similarity_score,
        COALESCE(ts.text_rank, 0) as text_rank,
        (vs.similarity_score * 0.7 + COALESCE(ts.text_rank, 0) * 0.3) as combined_score,
        vs.metadata
    FROM vector_search vs
    LEFT JOIN text_search ts ON vs.id = ts.id
    ORDER BY combined_score DESC
    LIMIT limit_param;
END;
$$ LANGUAGE plpgsql;