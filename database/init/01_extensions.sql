-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create custom types
CREATE TYPE user_role AS ENUM ('admin', 'user', 'agent');
CREATE TYPE user_tier AS ENUM ('free', 'pro', 'enterprise');
CREATE TYPE message_type AS ENUM ('user', 'assistant', 'system', 'tool_call', 'tool_result');
CREATE TYPE project_status AS ENUM ('active', 'archived', 'deleted');
CREATE TYPE sandbox_status AS ENUM ('creating', 'running', 'stopped', 'error', 'deleted');