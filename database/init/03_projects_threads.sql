-- Projects and Threads Tables

-- Projects table (replacing Supabase projects)
CREATE TABLE projects (
    project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status project_status DEFAULT 'active',
    sandbox_config JSONB DEFAULT '{}'::jsonb,
    is_public BOOLEAN DEFAULT FALSE,
    repository_url VARCHAR(500),
    branch VARCHAR(100) DEFAULT 'main',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Threads table for conversations
CREATE TABLE threads (
    thread_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    summary TEXT,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Messages table for thread conversations
CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES threads(thread_id) ON DELETE CASCADE,
    parent_message_id UUID REFERENCES messages(message_id),
    type message_type NOT NULL,
    content JSONB NOT NULL,
    role VARCHAR(50),
    model VARCHAR(100),
    tokens_used INTEGER DEFAULT 0,
    cost DECIMAL(10,6) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Project collaborators for shared access
CREATE TABLE project_collaborators (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'viewer', -- owner, editor, viewer
    invited_by UUID REFERENCES users(id),
    invited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    accepted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(project_id, user_id)
);

-- Sandbox instances for projects
CREATE TABLE sandbox_instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    container_id VARCHAR(255),
    container_name VARCHAR(255),
    status sandbox_status DEFAULT 'creating',
    port_mappings JSONB DEFAULT '{}'::jsonb,
    resource_limits JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    stopped_at TIMESTAMP WITH TIME ZONE,
    last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for projects and threads
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created_at ON projects(created_at);
CREATE INDEX idx_projects_last_accessed_at ON projects(last_accessed_at);

CREATE INDEX idx_threads_project_id ON threads(project_id);
CREATE INDEX idx_threads_user_id ON threads(user_id);
CREATE INDEX idx_threads_created_at ON threads(created_at);
CREATE INDEX idx_threads_last_message_at ON threads(last_message_at);

CREATE INDEX idx_messages_thread_id ON messages(thread_id);
CREATE INDEX idx_messages_parent_message_id ON messages(parent_message_id);
CREATE INDEX idx_messages_type ON messages(type);
CREATE INDEX idx_messages_created_at ON messages(created_at);

CREATE INDEX idx_project_collaborators_project_id ON project_collaborators(project_id);
CREATE INDEX idx_project_collaborators_user_id ON project_collaborators(user_id);

CREATE INDEX idx_sandbox_instances_project_id ON sandbox_instances(project_id);
CREATE INDEX idx_sandbox_instances_status ON sandbox_instances(status);
CREATE INDEX idx_sandbox_instances_container_id ON sandbox_instances(container_id);

-- Apply updated_at triggers
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_threads_updated_at BEFORE UPDATE ON threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();