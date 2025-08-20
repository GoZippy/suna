-- Migration: Create authentication tables for local auth system
-- This replaces Supabase Auth with local JWT-based authentication

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (replaces Supabase auth.users)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user' NOT NULL,
    tier VARCHAR(50) DEFAULT 'free' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Constraints
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT valid_role CHECK (role IN ('user', 'moderator', 'admin')),
    CONSTRAINT valid_tier CHECK (tier IN ('free', 'pro', 'enterprise'))
);

-- User sessions table for refresh token management
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Indexes for performance
    UNIQUE(token_hash)
);

-- User tiers configuration table
CREATE TABLE IF NOT EXISTS user_tiers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    max_monthly_usage DECIMAL(10,2),
    max_concurrent_agents INTEGER,
    features JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Usage tracking table (replaces Stripe billing)
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_type VARCHAR(50) NOT NULL,
    amount DECIMAL(10,4) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON usage_logs(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_tiers_updated_at 
    BEFORE UPDATE ON user_tiers 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default user tiers
INSERT INTO user_tiers (name, max_monthly_usage, max_concurrent_agents, features) VALUES
    ('free', 100.00, 1, '{"api_access": false, "priority_support": false, "advanced_features": false}'),
    ('pro', 1000.00, 5, '{"api_access": true, "priority_support": false, "advanced_features": true}'),
    ('enterprise', NULL, NULL, '{"api_access": true, "priority_support": true, "advanced_features": true, "unlimited_usage": true}')
ON CONFLICT (name) DO NOTHING;

-- Create default admin user (password: Admin123!)
-- Note: In production, this should be changed immediately
INSERT INTO users (id, email, password_hash, role, tier) VALUES
    ('00000000-0000-0000-0000-000000000001', 'admin@localhost', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK.s5uO8G', 'admin', 'enterprise')
ON CONFLICT (email) DO NOTHING;

-- Function to clean up expired sessions (can be called by a cron job)
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create a view for user statistics (useful for admin dashboard)
CREATE OR REPLACE VIEW user_stats AS
SELECT 
    u.tier,
    u.role,
    COUNT(*) as user_count,
    COUNT(CASE WHEN u.is_active THEN 1 END) as active_users,
    COUNT(CASE WHEN u.created_at > NOW() - INTERVAL '30 days' THEN 1 END) as new_users_30d
FROM users u
GROUP BY u.tier, u.role;

-- Grant necessary permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON users TO your_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON user_sessions TO your_app_user;
-- GRANT SELECT ON user_tiers TO your_app_user;
-- GRANT SELECT, INSERT ON usage_logs TO your_app_user;

COMMENT ON TABLE users IS 'Local user authentication table replacing Supabase auth.users';
COMMENT ON TABLE user_sessions IS 'JWT refresh token storage for session management';
COMMENT ON TABLE user_tiers IS 'User tier configuration for local billing replacement';
COMMENT ON TABLE usage_logs IS 'Usage tracking for local resource management';
COMMENT ON COLUMN users.password_hash IS 'bcrypt hashed password';
COMMENT ON COLUMN user_sessions.token_hash IS 'bcrypt hashed refresh token';
COMMENT ON FUNCTION cleanup_expired_sessions() IS 'Utility function to clean up expired refresh tokens';