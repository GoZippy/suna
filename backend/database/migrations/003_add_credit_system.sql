-- Migration: Add credit system to users and create credit transactions table
-- Created: 2024
-- Description: Adds credit_balance to users table and creates credit_transactions table for tracking credit purchases and usage

BEGIN;

-- Add credit_balance column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS credit_balance DECIMAL(10, 2) DEFAULT 0.00;

-- Create credit_transactions table
CREATE TABLE IF NOT EXISTS credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    balance_before DECIMAL(10, 2) NOT NULL,
    balance_after DECIMAL(10, 2) NOT NULL,
    reference_id VARCHAR(255),
    description TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_id ON credit_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_type ON credit_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_created_at ON credit_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user_type ON credit_transactions(user_id, transaction_type);

-- Add credit_balance to users indexes if needed
CREATE INDEX IF NOT EXISTS idx_users_credit_balance ON users(credit_balance);

-- Grant credits to existing users (give free tier users some starting credits)
UPDATE users SET credit_balance = 10.00 WHERE tier = 'free' AND credit_balance = 0;
UPDATE users SET credit_balance = 50.00 WHERE tier = 'pro' AND credit_balance = 0;
UPDATE users SET credit_balance = 100.00 WHERE tier = 'enterprise' AND credit_balance = 0;

COMMIT;
