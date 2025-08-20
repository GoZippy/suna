-- Migration: Create vector database tables and functions for pgvector
-- This implements vector storage and similarity search functionality

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Projects table (core entity for organizing work)
CREATE TABLE IF NOT EXISTS projects (
    project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active' NOT NULL,
    sandbox_config JSONB DEFAULT '{}',
    is_public BOOLEAN DEFAULT FALSE,
    repository_url VARCHAR(500),
    branch VARCHAR(100) DEFAULT 'main',
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT valid_status CHECK (status IN ('active', 'archived', 'deleted'))
);

-- Threads table for conversations
CREATE TABLE IF NOT EXISTS threads (
    thread_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    summary TEXT,
    is_archived BOOLEAN DEFAULT FALSE,
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Messages table for thread conversations
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    parent_message_id UUID REFERENCES messages(message_id),
    type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    role VARCHAR(50),
    model VARCHAR(100),
    tokens_used INTEGER DEFAULT 0,
    cost DECIMAL(10,6) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    metadata JSONB DEFAULT '{}'
);

-- Knowledge base table with vector embeddings
CREATE TABLE IF NOT EXISTS knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    title VARCHAR(500),
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text',
    source_url VARCHAR(1000),
    source_type VARCHAR(50),
    embedding vector(1536), -- OpenAI ada-002 embedding dimension
    chunk_index INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 1,
    file_path VARCHAR(1000),
    file_size INTEGER,
    file_hash VARCHAR(64),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT valid_content_type CHECK (content_type IN ('text', 'code', 'markdown', 'pdf', 'docx', 'html')),
    CONSTRAINT valid_source_type CHECK (source_type IN ('manual', 'file', 'url', 'git_repo', 'zip_extracted'))
);

-- Project collaborators table
CREATE TABLE IF NOT EXISTS project_collaborators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'viewer' NOT NULL,
    invited_by UUID REFERENCES users(id),
    invited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accepted_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(project_id, user_id),
    CONSTRAINT valid_collaborator_role CHECK (role IN ('viewer', 'editor', 'admin'))
);

-- Sandbox instances table for container management
CREATE TABLE IF NOT EXISTS sandbox_instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    container_id VARCHAR(255),
    container_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'creating' NOT NULL,
    port_mappings JSONB DEFAULT '{}',
    resource_limits JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE,
    stopped_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT valid_sandbox_status CHECK (status IN ('creating', 'running', 'stopped', 'error', 'deleted'))
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at);
CREATE INDEX IF NOT EXISTS idx_projects_last_accessed_at ON projects(last_accessed_at);

CREATE INDEX IF NOT EXISTS idx_threads_project_id ON threads(project_id);
CREATE INDEX IF NOT EXISTS idx_threads_user_id ON threads(user_id);
CREATE INDEX IF NOT EXISTS idx_threads_created_at ON threads(created_at);
CREATE INDEX IF NOT EXISTS idx_threads_last_message_at ON threads(last_message_at);

CREATE INDEX IF NOT EXISTS idx_messages_thread_id ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_parent_message_id ON messages(parent_message_id);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

CREATE INDEX IF NOT EXISTS idx_knowledge_base_user_id ON knowledge_base(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_project_id ON knowledge_base(project_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_content_type ON knowledge_base(content_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_source_type ON knowledge_base(source_type);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_created_at ON knowledge_base(created_at);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_file_hash ON knowledge_base(file_hash);

-- Vector similarity search index (HNSW for better performance)
CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding_hnsw ON knowledge_base 
USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- Alternative IVFFlat index for smaller datasets
-- CREATE INDEX IF NOT EXISTS idx_knowledge_base_embedding_ivfflat ON knowledge_base 
-- USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_project_collaborators_project_id ON project_collaborators(project_id);
CREATE INDEX IF NOT EXISTS idx_project_collaborators_user_id ON project_collaborators(user_id);

CREATE INDEX IF NOT EXISTS idx_sandbox_instances_project_id ON sandbox_instances(project_id);
CREATE INDEX IF NOT EXISTS idx_sandbox_instances_status ON sandbox_instances(status);
CREATE INDEX IF NOT EXISTS idx_sandbox_instances_container_id ON sandbox_instances(container_id);

-- Create triggers for updated_at columns
CREATE TRIGGER update_projects_updated_at 
    BEFORE UPDATE ON projects 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_threads_updated_at 
    BEFORE UPDATE ON threads 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at 
    BEFORE UPDATE ON knowledge_base 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sandbox_instances_updated_at 
    BEFORE UPDATE ON sandbox_instances 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Vector similarity search function
CREATE OR REPLACE FUNCTION search_knowledge_base_by_similarity(
    query_embedding vector(1536),
    similarity_threshold float DEFAULT 0.7,
    max_results integer DEFAULT 10,
    target_user_id uuid DEFAULT NULL,
    target_project_id uuid DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    title varchar(500),
    content text,
    content_type varchar(50),
    source_type varchar(50),
    similarity float,
    metadata jsonb,
    created_at timestamp with time zone
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kb.id,
        kb.title,
        kb.content,
        kb.content_type,
        kb.source_type,
        1 - (kb.embedding <=> query_embedding) as similarity,
        kb.metadata,
        kb.created_at
    FROM knowledge_base kb
    WHERE 
        kb.embedding IS NOT NULL
        AND (target_user_id IS NULL OR kb.user_id = target_user_id)
        AND (target_project_id IS NULL OR kb.project_id = target_project_id)
        AND (1 - (kb.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY kb.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Hybrid search function combining text and vector similarity
CREATE OR REPLACE FUNCTION hybrid_search_knowledge_base(
    query_text text,
    query_embedding vector(1536),
    similarity_threshold float DEFAULT 0.7,
    max_results integer DEFAULT 10,
    target_user_id uuid DEFAULT NULL,
    target_project_id uuid DEFAULT NULL,
    text_weight float DEFAULT 0.3,
    vector_weight float DEFAULT 0.7
)
RETURNS TABLE (
    id uuid,
    title varchar(500),
    content text,
    content_type varchar(50),
    source_type varchar(50),
    text_score float,
    vector_score float,
    combined_score float,
    metadata jsonb,
    created_at timestamp with time zone
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        kb.id,
        kb.title,
        kb.content,
        kb.content_type,
        kb.source_type,
        ts_rank_cd(to_tsvector('english', kb.content || ' ' || COALESCE(kb.title, '')), plainto_tsquery('english', query_text)) as text_score,
        (1 - (kb.embedding <=> query_embedding)) as vector_score,
        (text_weight * ts_rank_cd(to_tsvector('english', kb.content || ' ' || COALESCE(kb.title, '')), plainto_tsquery('english', query_text))) +
        (vector_weight * (1 - (kb.embedding <=> query_embedding))) as combined_score,
        kb.metadata,
        kb.created_at
    FROM knowledge_base kb
    WHERE 
        kb.embedding IS NOT NULL
        AND (target_user_id IS NULL OR kb.user_id = target_user_id)
        AND (target_project_id IS NULL OR kb.project_id = target_project_id)
        AND (
            (1 - (kb.embedding <=> query_embedding)) >= similarity_threshold
            OR to_tsvector('english', kb.content || ' ' || COALESCE(kb.title, '')) @@ plainto_tsquery('english', query_text)
        )
    ORDER BY combined_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function to get knowledge base statistics
CREATE OR REPLACE FUNCTION get_knowledge_base_stats(
    target_user_id uuid DEFAULT NULL,
    target_project_id uuid DEFAULT NULL
)
RETURNS TABLE (
    total_entries bigint,
    entries_with_embeddings bigint,
    total_content_length bigint,
    avg_content_length numeric,
    content_types jsonb,
    source_types jsonb
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_entries,
        COUNT(kb.embedding) as entries_with_embeddings,
        SUM(LENGTH(kb.content)) as total_content_length,
        AVG(LENGTH(kb.content)) as avg_content_length,
        jsonb_object_agg(kb.content_type, type_counts.count) as content_types,
        jsonb_object_agg(kb.source_type, source_counts.count) as source_types
    FROM knowledge_base kb
    LEFT JOIN (
        SELECT content_type, COUNT(*) as count
        FROM knowledge_base
        WHERE (target_user_id IS NULL OR user_id = target_user_id)
        AND (target_project_id IS NULL OR project_id = target_project_id)
        GROUP BY content_type
    ) type_counts ON kb.content_type = type_counts.content_type
    LEFT JOIN (
        SELECT source_type, COUNT(*) as count
        FROM knowledge_base
        WHERE (target_user_id IS NULL OR user_id = target_user_id)
        AND (target_project_id IS NULL OR project_id = target_project_id)
        GROUP BY source_type
    ) source_counts ON kb.source_type = source_counts.source_type
    WHERE 
        (target_user_id IS NULL OR kb.user_id = target_user_id)
        AND (target_project_id IS NULL OR kb.project_id = target_project_id);
END;
$$ LANGUAGE plpgsql;

-- Full-text search index for hybrid search
CREATE INDEX IF NOT EXISTS idx_knowledge_base_content_fts ON knowledge_base 
USING gin(to_tsvector('english', content || ' ' || COALESCE(title, '')));

-- Function to batch update embeddings (useful for migration)
CREATE OR REPLACE FUNCTION batch_update_embeddings()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER := 0;
BEGIN
    -- This function can be called by the embedding service
    -- to update embeddings for entries that don't have them yet
    SELECT COUNT(*) INTO updated_count
    FROM knowledge_base
    WHERE embedding IS NULL;
    
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE knowledge_base IS 'Vector-enabled knowledge base with pgvector similarity search';
COMMENT ON COLUMN knowledge_base.embedding IS 'Vector embedding for similarity search (1536 dimensions for OpenAI ada-002)';
COMMENT ON INDEX idx_knowledge_base_embedding_hnsw IS 'HNSW index for fast vector similarity search';
COMMENT ON FUNCTION search_knowledge_base_by_similarity IS 'Pure vector similarity search function';
COMMENT ON FUNCTION hybrid_search_knowledge_base IS 'Hybrid search combining text and vector similarity';
COMMENT ON FUNCTION get_knowledge_base_stats IS 'Get statistics about knowledge base content and embeddings';