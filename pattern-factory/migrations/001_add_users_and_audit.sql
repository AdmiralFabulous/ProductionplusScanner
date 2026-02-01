-- Migration: 001_add_users_and_audit
-- Description: Add users table and audit_logs table for security
-- Date: 2026-01-31
-- Author: Claude

-- ============================================================================
-- USERS TABLE
-- ============================================================================

-- Create users table for authentication
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'readonly',
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_role CHECK (role IN ('admin', 'operator', 'qc_tech', 'maintenance', 'readonly'))
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Enable RLS for users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything
CREATE POLICY "Service role full access to users" ON users
    FOR ALL
    USING (auth.role() = 'service_role');

-- Policy: Authenticated users can read their own data
CREATE POLICY "Users can read own data" ON users
    FOR SELECT
    USING (auth.uid()::text = id::text);

-- ============================================================================
-- AUDIT LOGS TABLE
-- ============================================================================

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    username TEXT,
    user_id TEXT,
    user_role TEXT,
    ip_address TEXT,
    user_agent TEXT,
    resource TEXT,
    action TEXT,
    outcome TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    request_id TEXT,
    
    -- Indexes for common queries
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for audit logs
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_logs(username);
CREATE INDEX IF NOT EXISTS idx_audit_outcome ON audit_logs(outcome);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource);

-- Partitioning by time (optional, for high-volume systems)
-- CREATE INDEX IF NOT EXISTS idx_audit_timestamp_partition ON audit_logs(timestamp) WHERE timestamp > NOW() - INTERVAL '30 days';

-- Enable RLS for audit logs
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Policy: Only service role can insert audit logs
CREATE POLICY "Service role can insert audit logs" ON audit_logs
    FOR INSERT
    USING (auth.role() = 'service_role');

-- Policy: Admins can read all audit logs
CREATE POLICY "Admins can read audit logs" ON audit_logs
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id::text = auth.uid()::text 
            AND users.role = 'admin'
        )
    );

-- ============================================================================
-- UPDATE ORDERS TABLE FOR ENCRYPTION
-- ============================================================================

-- Add encrypted flag to orders if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'orders' AND column_name = 'measurements_encrypted'
    ) THEN
        ALTER TABLE orders ADD COLUMN measurements_encrypted BOOLEAN DEFAULT false;
    END IF;
END $$;

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- DEFAULT ADMIN USER (for initial setup)
-- ============================================================================

-- Insert default admin user if not exists
-- Password: admin123456 (bcrypt hash)
-- IMPORTANT: Change this password immediately after deployment!
INSERT INTO users (username, email, password_hash, role, is_active)
VALUES (
    'admin',
    'admin@samedaysuits.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4URFyLGH0xOG1SHi',
    'admin',
    true
)
ON CONFLICT (username) DO NOTHING;

-- Insert default operator user
INSERT INTO users (username, email, password_hash, role, is_active)
VALUES (
    'operator',
    'operator@samedaysuits.com',
    '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi',
    'operator',
    true
)
ON CONFLICT (username) DO NOTHING;

-- ============================================================================
-- GRANTS
-- ============================================================================

-- Grant necessary permissions (adjust based on your Supabase setup)
-- GRANT SELECT, INSERT, UPDATE ON users TO authenticated;
-- GRANT SELECT, INSERT ON audit_logs TO authenticated;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify tables were created
DO $$
DECLARE
    users_exists BOOLEAN;
    audit_exists BOOLEAN;
BEGIN
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') INTO users_exists;
    SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_logs') INTO audit_exists;
    
    IF NOT users_exists THEN
        RAISE EXCEPTION 'users table was not created';
    END IF;
    
    IF NOT audit_exists THEN
        RAISE EXCEPTION 'audit_logs table was not created';
    END IF;
    
    RAISE NOTICE 'Migration 001 completed successfully';
END $$;
