-- System Configuration and Settings Tables

-- System-wide configuration settings
CREATE TABLE system_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User preferences and settings
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key VARCHAR(255) NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, key)
);

-- Audit log for security and compliance
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Background jobs and task queue
CREATE TABLE background_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    priority INTEGER DEFAULT 0,
    payload JSONB NOT NULL,
    result JSONB,
    error_message TEXT,
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Email queue for notifications
CREATE TABLE email_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    to_email VARCHAR(255) NOT NULL,
    from_email VARCHAR(255),
    subject VARCHAR(500) NOT NULL,
    body_text TEXT,
    body_html TEXT,
    template_name VARCHAR(100),
    template_data JSONB,
    status VARCHAR(50) DEFAULT 'pending', -- pending, sent, failed, cancelled
    priority INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- WebSocket connections tracking
CREATE TABLE websocket_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    connection_id VARCHAR(255) UNIQUE NOT NULL,
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    ip_address INET,
    user_agent TEXT,
    connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_ping_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    disconnected_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Insert default system configuration
INSERT INTO system_config (key, value, description, is_public) VALUES
('app_name', '"Suna Self-Hosted"', 'Application name', true),
('app_version', '"1.0.0"', 'Application version', true),
('max_file_upload_size', '104857600', 'Maximum file upload size in bytes (100MB)', false),
('default_model', '"gpt-3.5-turbo"', 'Default AI model for new users', false),
('registration_enabled', 'true', 'Whether new user registration is enabled', true),
('email_verification_required', 'false', 'Whether email verification is required for new users', false),
('max_projects_per_user', '10', 'Maximum projects per user (overridden by tier)', false),
('session_timeout_hours', '24', 'JWT session timeout in hours', false),
('vector_similarity_threshold', '0.7', 'Default similarity threshold for vector search', false),
('backup_retention_days', '30', 'Number of days to retain database backups', false);

-- Indexes for system tables
CREATE INDEX idx_system_config_key ON system_config(key);
CREATE INDEX idx_system_config_is_public ON system_config(is_public);

CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_key ON user_preferences(key);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

CREATE INDEX idx_background_jobs_status ON background_jobs(status);
CREATE INDEX idx_background_jobs_job_type ON background_jobs(job_type);
CREATE INDEX idx_background_jobs_scheduled_at ON background_jobs(scheduled_at);
CREATE INDEX idx_background_jobs_priority ON background_jobs(priority);

CREATE INDEX idx_email_queue_status ON email_queue(status);
CREATE INDEX idx_email_queue_scheduled_at ON email_queue(scheduled_at);
CREATE INDEX idx_email_queue_priority ON email_queue(priority);
CREATE INDEX idx_email_queue_to_email ON email_queue(to_email);

CREATE INDEX idx_websocket_connections_user_id ON websocket_connections(user_id);
CREATE INDEX idx_websocket_connections_connection_id ON websocket_connections(connection_id);
CREATE INDEX idx_websocket_connections_project_id ON websocket_connections(project_id);
CREATE INDEX idx_websocket_connections_connected_at ON websocket_connections(connected_at);

-- Apply updated_at triggers
CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to log audit events
CREATE OR REPLACE FUNCTION log_audit_event(
    user_id_param UUID,
    action_param VARCHAR(100),
    resource_type_param VARCHAR(50) DEFAULT NULL,
    resource_id_param UUID DEFAULT NULL,
    old_values_param JSONB DEFAULT NULL,
    new_values_param JSONB DEFAULT NULL,
    ip_address_param INET DEFAULT NULL,
    user_agent_param TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    audit_id UUID;
BEGIN
    INSERT INTO audit_logs (
        user_id, action, resource_type, resource_id, 
        old_values, new_values, ip_address, user_agent
    ) VALUES (
        user_id_param, action_param, resource_type_param, resource_id_param,
        old_values_param, new_values_param, ip_address_param, user_agent_param
    ) RETURNING id INTO audit_id;
    
    RETURN audit_id;
END;
$$ LANGUAGE plpgsql;