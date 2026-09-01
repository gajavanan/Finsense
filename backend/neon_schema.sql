-- ====================================================================
-- FinSense – AI-Powered Personal Finance Advisor
-- Neon PostgreSQL Production Database Schema
--
-- Target Platform: Neon Serverless PostgreSQL (PostgreSQL 15 / 16)
-- Compatibility: FastAPI + SQLAlchemy + Alembic
-- Generated directly from: backend/app/models/__init__.py & Alembic migrations
-- ====================================================================

BEGIN;

-- --------------------------------------------------------------------
-- 0. EXTENSIONS
-- --------------------------------------------------------------------
-- Enable pgcrypto for server-side UUID generation fallback (gen_random_uuid)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- --------------------------------------------------------------------
-- 1. USERS TABLE (Core Authentication & Identity)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone_number VARCHAR(20) UNIQUE,
    phone_verified BOOLEAN NOT NULL DEFAULT FALSE,
    phone_verified_at TIMESTAMP WITH TIME ZONE,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    verification_token_expires TIMESTAMP WITHOUT TIME ZONE,
    reset_token VARCHAR(255),
    reset_token_expires TIMESTAMP WITHOUT TIME ZONE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_number ON users(phone_number);

-- --------------------------------------------------------------------
-- 2. PROFILES TABLE (User Profile Metadata)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS profiles (
    id VARCHAR(36) PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    full_name VARCHAR(255),
    email VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- --------------------------------------------------------------------
-- 3. TRANSACTIONS TABLE (Manual, CSV Import & ML Categorization)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    type VARCHAR(50) NOT NULL,
    transaction_type VARCHAR(50),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    payment_method VARCHAR(100),
    merchant VARCHAR(255),
    account VARCHAR(100),
    notes TEXT,
    source VARCHAR(50) DEFAULT 'manual',
    confidence_score NUMERIC(5, 4),
    is_anomaly BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions(date);
CREATE INDEX IF NOT EXISTS ix_transactions_user_id_date ON transactions(user_id, date);
CREATE INDEX IF NOT EXISTS ix_transactions_category ON transactions(category);
CREATE INDEX IF NOT EXISTS ix_transactions_transaction_type ON transactions(transaction_type);

-- --------------------------------------------------------------------
-- 4. BUDGETS TABLE (Category Limits & Monthly Budgets)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS budgets (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    monthly_limit NUMERIC(12, 2),
    period VARCHAR(50) DEFAULT 'monthly',
    month VARCHAR(20),
    year VARCHAR(10),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_budgets_user_id ON budgets(user_id);
CREATE INDEX IF NOT EXISTS ix_budgets_category ON budgets(category);

-- --------------------------------------------------------------------
-- 5. SPENDING ALERTS TABLE (Threshold Alerts: 75%, 90%, 100%, Exceeded)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS spending_alerts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL,
    category VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    amount NUMERIC(12, 2),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_spending_alerts_user_id ON spending_alerts(user_id);
CREATE INDEX IF NOT EXISTS ix_spending_alerts_category ON spending_alerts(category);

-- --------------------------------------------------------------------
-- 6. GOALS TABLE (Financial Savings Targets)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS goals (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    target_amount NUMERIC(12, 2) NOT NULL,
    current_amount NUMERIC(12, 2) DEFAULT 0,
    target_date DATE,
    category VARCHAR(100),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_goals_user_id ON goals(user_id);

-- --------------------------------------------------------------------
-- 7. ASSETS TABLE (Investments & Portfolio Assets)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS assets (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    symbol VARCHAR(50),
    type VARCHAR(50) NOT NULL,
    quantity NUMERIC(12, 4) NOT NULL,
    purchase_price NUMERIC(12, 2) NOT NULL,
    current_price NUMERIC(12, 2),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_assets_user_id ON assets(user_id);

-- --------------------------------------------------------------------
-- 8. NOTIFICATIONS TABLE (System & Alert Notifications)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    type VARCHAR(50) DEFAULT 'info',
    read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications(user_id);

-- --------------------------------------------------------------------
-- 9. AGENT INSIGHTS TABLE (AI Financial Insights)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_insights (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    type VARCHAR(50),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_agent_insights_user_id ON agent_insights(user_id);

-- --------------------------------------------------------------------
-- 10. AGENT ACTIONS TABLE (AI Agent Executed Tasks & Logs)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_actions (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL,
    payload JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_agent_actions_user_id ON agent_actions(user_id);

-- --------------------------------------------------------------------
-- 11. CHAT MESSAGES TABLE (AI Advisor Conversation History)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_user_id ON chat_messages(user_id);

-- --------------------------------------------------------------------
-- 12. AGENT PREFERENCES TABLE (AI Financial Personality Settings)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_preferences (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_agent_preferences_user_id ON agent_preferences(user_id);

-- --------------------------------------------------------------------
-- 13. UPI ACCOUNTS TABLE (Linked Indian UPI Handles)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS upi_accounts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    upi_id VARCHAR(255) NOT NULL,
    bank_name VARCHAR(100),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_upi_accounts_user_id ON upi_accounts(user_id);

-- --------------------------------------------------------------------
-- 14. CONNECTED ACCOUNTS TABLE (Bank & Financial Institution Accounts)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS connected_accounts (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(100),
    account_name VARCHAR(255),
    balance NUMERIC(12, 2) DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_connected_accounts_user_id ON connected_accounts(user_id);

-- --------------------------------------------------------------------
-- 15. LOGIN EVENTS TABLE (Security Auditing & New Device Tracking)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS login_events (
    id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255),
    user_agent TEXT,
    ip VARCHAR(100),
    device VARCHAR(50),
    browser VARCHAR(50),
    os VARCHAR(50),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_login_events_user_id ON login_events(user_id);

COMMIT;

-- ====================================================================
-- VERIFICATION QUERIES (Non-destructive inspection)
-- ====================================================================

-- 1. List all created tables in the public schema
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- 2. Inspect all table columns and data types
-- SELECT table_name, column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
-- ORDER BY table_name, ordinal_position;

-- 3. Inspect foreign key relationships
-- SELECT
--     tc.table_name,
--     kcu.column_name,
--     ccu.table_name AS foreign_table_name,
--     ccu.column_name AS foreign_column_name
-- FROM information_schema.table_constraints AS tc
-- JOIN information_schema.key_column_usage AS kcu
--     ON tc.constraint_name = kcu.constraint_name
-- JOIN information_schema.constraint_column_usage AS ccu
--     ON ccu.constraint_name = tc.constraint_name
-- WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
-- ORDER BY tc.table_name;
