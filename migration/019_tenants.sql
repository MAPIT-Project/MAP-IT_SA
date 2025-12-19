-- Migration: Multi-tenancy Support
-- Creates tables for organization-based data isolation

-- Tenants (Organizations) table
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'pending', 'trial')),
    plan VARCHAR(20) NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'basic', 'premium', 'enterprise')),

    -- Contact information
    admin_email VARCHAR(255),
    admin_name VARCHAR(255),

    -- Configuration
    settings JSONB DEFAULT '{}',
    features JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Trial/billing information
    trial_ends_at TIMESTAMP WITH TIME ZONE,
    billing_email VARCHAR(255)
);

-- Indexes for tenants
CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON tenants(status);
CREATE INDEX IF NOT EXISTS idx_tenants_plan ON tenants(plan);

-- Add organization_id to key tables for multi-tenancy
-- Note: These should be run carefully in production with data migration

-- Add to conversations if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversations' AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE conversations ADD COLUMN organization_id UUID REFERENCES tenants(id);
        CREATE INDEX idx_conversations_org ON conversations(organization_id);
    END IF;
END $$;

-- Add to proposal_sessions if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'proposal_sessions' AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE proposal_sessions ADD COLUMN organization_id UUID REFERENCES tenants(id);
        CREATE INDEX idx_proposal_sessions_org ON proposal_sessions(organization_id);
    END IF;
END $$;

-- Add to saved_searches if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'saved_searches' AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE saved_searches ADD COLUMN organization_id UUID REFERENCES tenants(id);
        CREATE INDEX idx_saved_searches_org ON saved_searches(organization_id);
    END IF;
END $$;

-- Tenant users mapping table
CREATE TABLE IF NOT EXISTS tenant_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    permissions JSONB DEFAULT '[]',
    invited_by VARCHAR(255),
    invited_at TIMESTAMP WITH TIME ZONE,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,

    UNIQUE(tenant_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_tenant_users_tenant ON tenant_users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_users_user ON tenant_users(user_id);

-- Tenant usage tracking
CREATE TABLE IF NOT EXISTS tenant_usage (
    id SERIAL PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Usage metrics
    conversations_count INTEGER DEFAULT 0,
    queries_count INTEGER DEFAULT 0,
    proposals_count INTEGER DEFAULT 0,
    storage_bytes BIGINT DEFAULT 0,
    api_calls INTEGER DEFAULT 0,

    -- Limits at time of period
    max_conversations INTEGER,
    max_queries INTEGER,
    max_proposals INTEGER,
    max_storage_bytes BIGINT,
    max_api_calls INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(tenant_id, period_start)
);

CREATE INDEX IF NOT EXISTS idx_tenant_usage_tenant ON tenant_usage(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_usage_period ON tenant_usage(period_start DESC);

-- Tenant API keys
CREATE TABLE IF NOT EXISTS tenant_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,  -- First few chars for identification
    permissions JSONB DEFAULT '[]',
    rate_limit_override JSONB,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tenant_api_keys_tenant ON tenant_api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_api_keys_prefix ON tenant_api_keys(key_prefix);

-- Row Level Security policies (optional, for PostgreSQL RLS)
-- Enable RLS on tenant-scoped tables
-- ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE proposal_sessions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY;

-- Create policies (example)
-- CREATE POLICY tenant_isolation ON conversations
--     USING (organization_id = current_setting('app.current_tenant_id')::uuid);

-- View for tenant overview
CREATE OR REPLACE VIEW tenant_overview AS
SELECT
    t.id,
    t.name,
    t.slug,
    t.status,
    t.plan,
    t.created_at,
    COUNT(DISTINCT tu.user_id) as user_count,
    COALESCE(u.queries_count, 0) as current_queries,
    COALESCE(u.proposals_count, 0) as current_proposals
FROM tenants t
LEFT JOIN tenant_users tu ON t.id = tu.tenant_id AND tu.is_active = true
LEFT JOIN tenant_usage u ON t.id = u.tenant_id AND u.period_start = DATE_TRUNC('month', CURRENT_DATE)
GROUP BY t.id, t.name, t.slug, t.status, t.plan, t.created_at, u.queries_count, u.proposals_count;

-- Function to increment usage counter
CREATE OR REPLACE FUNCTION increment_tenant_usage(
    p_tenant_id UUID,
    p_metric VARCHAR(50),
    p_amount INTEGER DEFAULT 1
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO tenant_usage (tenant_id, period_start, period_end)
    VALUES (p_tenant_id, DATE_TRUNC('month', CURRENT_DATE), DATE_TRUNC('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day')
    ON CONFLICT (tenant_id, period_start) DO NOTHING;

    EXECUTE format(
        'UPDATE tenant_usage SET %I = COALESCE(%I, 0) + $1, updated_at = CURRENT_TIMESTAMP
         WHERE tenant_id = $2 AND period_start = DATE_TRUNC(''month'', CURRENT_DATE)',
        p_metric || '_count', p_metric || '_count'
    ) USING p_amount, p_tenant_id;
END;
$$ LANGUAGE plpgsql;

-- Function to check if tenant is within limits
CREATE OR REPLACE FUNCTION check_tenant_limit(
    p_tenant_id UUID,
    p_metric VARCHAR(50)
)
RETURNS BOOLEAN AS $$
DECLARE
    current_usage INTEGER;
    max_limit INTEGER;
    tenant_plan VARCHAR(20);
BEGIN
    -- Get tenant plan
    SELECT plan INTO tenant_plan FROM tenants WHERE id = p_tenant_id;

    -- Get current usage
    EXECUTE format(
        'SELECT COALESCE(%I, 0) FROM tenant_usage WHERE tenant_id = $1 AND period_start = DATE_TRUNC(''month'', CURRENT_DATE)',
        p_metric || '_count'
    ) INTO current_usage USING p_tenant_id;

    -- Define limits by plan
    IF p_metric = 'queries' THEN
        CASE tenant_plan
            WHEN 'free' THEN max_limit := 50;
            WHEN 'basic' THEN max_limit := 200;
            WHEN 'premium' THEN max_limit := 1000;
            WHEN 'enterprise' THEN max_limit := 100000;
            ELSE max_limit := 50;
        END CASE;
    ELSIF p_metric = 'proposals' THEN
        CASE tenant_plan
            WHEN 'free' THEN max_limit := 5;
            WHEN 'basic' THEN max_limit := 50;
            WHEN 'premium' THEN max_limit := 500;
            WHEN 'enterprise' THEN max_limit := 100000;
            ELSE max_limit := 5;
        END CASE;
    ELSE
        max_limit := 1000000;
    END IF;

    RETURN COALESCE(current_usage, 0) < max_limit;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_tenant_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_tenants_updated_at ON tenants;
CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_tenant_timestamp();

COMMENT ON TABLE tenants IS 'Organizations/tenants for multi-tenancy support';
COMMENT ON TABLE tenant_users IS 'User membership in tenants with roles';
COMMENT ON TABLE tenant_usage IS 'Monthly usage tracking per tenant';
COMMENT ON TABLE tenant_api_keys IS 'API keys for tenant authentication';
