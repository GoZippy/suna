-- Usage Tracking and Analytics Tables (replacing Stripe billing)

-- Usage logs for tracking resource consumption
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL, -- tokens, storage, compute, api_calls
    resource_subtype VARCHAR(50), -- gpt-4, gpt-3.5, embedding, etc.
    amount DECIMAL(15,6) NOT NULL,
    unit VARCHAR(20) NOT NULL, -- tokens, bytes, seconds, requests
    cost DECIMAL(10,6) DEFAULT 0,
    provider VARCHAR(50), -- openai, local, anthropic, etc.
    model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Monthly usage aggregations for billing/limits
CREATE TABLE monthly_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    total_amount DECIMAL(15,6) NOT NULL DEFAULT 0,
    total_cost DECIMAL(10,6) NOT NULL DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(user_id, year, month, resource_type)
);

-- API keys for external integrations
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    key_prefix VARCHAR(20) NOT NULL,
    permissions JSONB DEFAULT '[]'::jsonb,
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    rate_limit_per_day INTEGER DEFAULT 10000,
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Rate limiting tracking
CREATE TABLE rate_limit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    api_key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint VARCHAR(255) NOT NULL,
    ip_address INET,
    requests_count INTEGER DEFAULT 1,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    window_end TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- System-wide usage statistics
CREATE TABLE system_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stat_date DATE NOT NULL UNIQUE,
    total_users INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    total_projects INTEGER DEFAULT 0,
    active_projects INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_tokens_used BIGINT DEFAULT 0,
    total_storage_bytes BIGINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for usage tracking
CREATE INDEX idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX idx_usage_logs_project_id ON usage_logs(project_id);
CREATE INDEX idx_usage_logs_resource_type ON usage_logs(resource_type);
CREATE INDEX idx_usage_logs_created_at ON usage_logs(created_at);
CREATE INDEX idx_usage_logs_user_created ON usage_logs(user_id, created_at);

CREATE INDEX idx_monthly_usage_user_id ON monthly_usage(user_id);
CREATE INDEX idx_monthly_usage_year_month ON monthly_usage(year, month);
CREATE INDEX idx_monthly_usage_user_year_month ON monthly_usage(user_id, year, month);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_key_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_is_active ON api_keys(is_active);

CREATE INDEX idx_rate_limit_logs_user_id ON rate_limit_logs(user_id);
CREATE INDEX idx_rate_limit_logs_api_key_id ON rate_limit_logs(api_key_id);
CREATE INDEX idx_rate_limit_logs_endpoint ON rate_limit_logs(endpoint);
CREATE INDEX idx_rate_limit_logs_window_start ON rate_limit_logs(window_start);

CREATE INDEX idx_system_stats_stat_date ON system_stats(stat_date);

-- Function to update monthly usage aggregations
CREATE OR REPLACE FUNCTION update_monthly_usage()
RETURNS TRIGGER AS $$
DECLARE
    usage_year INTEGER;
    usage_month INTEGER;
BEGIN
    usage_year := EXTRACT(YEAR FROM NEW.created_at);
    usage_month := EXTRACT(MONTH FROM NEW.created_at);
    
    INSERT INTO monthly_usage (user_id, year, month, resource_type, total_amount, total_cost)
    VALUES (NEW.user_id, usage_year, usage_month, NEW.resource_type, NEW.amount, NEW.cost)
    ON CONFLICT (user_id, year, month, resource_type)
    DO UPDATE SET
        total_amount = monthly_usage.total_amount + NEW.amount,
        total_cost = monthly_usage.total_cost + NEW.cost,
        last_updated = NOW();
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update monthly usage
CREATE TRIGGER update_monthly_usage_trigger
    AFTER INSERT ON usage_logs
    FOR EACH ROW
    EXECUTE FUNCTION update_monthly_usage();

-- Function to check user tier limits
CREATE OR REPLACE FUNCTION check_user_limits(
    user_id_param UUID,
    resource_type_param VARCHAR(50),
    requested_amount DECIMAL(15,6)
)
RETURNS BOOLEAN AS $$
DECLARE
    user_tier_name VARCHAR(50);
    tier_limit DECIMAL(10,2);
    current_usage DECIMAL(15,6);
    current_year INTEGER;
    current_month INTEGER;
BEGIN
    -- Get user tier
    SELECT tier INTO user_tier_name FROM users WHERE id = user_id_param;
    
    -- Get tier limit
    SELECT max_monthly_usage INTO tier_limit 
    FROM user_tiers 
    WHERE name = user_tier_name;
    
    -- If no limit (enterprise), allow
    IF tier_limit IS NULL THEN
        RETURN TRUE;
    END IF;
    
    -- Get current month usage
    current_year := EXTRACT(YEAR FROM NOW());
    current_month := EXTRACT(MONTH FROM NOW());
    
    SELECT COALESCE(total_amount, 0) INTO current_usage
    FROM monthly_usage
    WHERE user_id = user_id_param 
        AND year = current_year 
        AND month = current_month 
        AND resource_type = resource_type_param;
    
    -- Check if adding requested amount would exceed limit
    RETURN (current_usage + requested_amount) <= tier_limit;
END;
$$ LANGUAGE plpgsql;