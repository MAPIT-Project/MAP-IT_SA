-- ================================================================
-- PROPOSAL WRITING SYSTEM - DATABASE SCHEMA
-- ================================================================
-- This migration adds complete proposal writing capabilities
-- to the MAP-IT SA system.
--
-- Author: AI Assistant
-- Date: 2025-10-10
-- Version: 1.0
-- ================================================================

-- ================================================================
-- 1. PROPOSALS TABLE
-- ================================================================
-- Main table for storing proposal projects

CREATE TABLE IF NOT EXISTS proposals (
    id SERIAL PRIMARY KEY,
    call_identifier VARCHAR(255) NOT NULL,
    conversation_id INTEGER,
    
    -- Basic information
    proposal_title VARCHAR(500),
    proposal_acronym VARCHAR(50),
    proposal_type VARCHAR(50) NOT NULL, -- 'RIA', 'IA', 'CSA', 'ERC', etc.
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'in_review', 'final', 'submitted'
    completion_percentage INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    submitted_at TIMESTAMP,
    user_id VARCHAR(100),
    
    -- Project details
    project_summary TEXT,
    research_area VARCHAR(255),
    duration_months INTEGER,
    total_budget DECIMAL(15,2),
    
    -- Additional metadata
    metadata JSONB DEFAULT '{}',
    
    -- Indexes
    CONSTRAINT valid_status CHECK (status IN ('draft', 'in_review', 'final', 'submitted', 'archived'))
);

CREATE INDEX idx_proposals_call ON proposals(call_identifier);
CREATE INDEX idx_proposals_conversation ON proposals(conversation_id);
CREATE INDEX idx_proposals_user ON proposals(user_id);
CREATE INDEX idx_proposals_status ON proposals(status);
CREATE INDEX idx_proposals_updated ON proposals(updated_at DESC);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_proposal_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_proposal_timestamp
    BEFORE UPDATE ON proposals
    FOR EACH ROW
    EXECUTE FUNCTION update_proposal_timestamp();

-- ================================================================
-- 2. PROPOSAL SECTIONS TABLE (with versioning)
-- ================================================================

CREATE TABLE IF NOT EXISTS proposal_sections (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    
    -- Section identification
    section_id VARCHAR(100) NOT NULL, -- e.g., 'excellence.objectives'
    section_name VARCHAR(255) NOT NULL,
    section_order INTEGER,
    
    -- Content
    section_content TEXT,
    word_count INTEGER DEFAULT 0,
    
    -- Version control
    version INTEGER DEFAULT 1,
    parent_version_id INTEGER REFERENCES proposal_sections(id),
    is_current BOOLEAN DEFAULT TRUE,
    
    -- Quality metrics
    compliance_score DECIMAL(3,2),
    quality_score DECIMAL(3,2),
    completeness_score DECIMAL(3,2),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    notes TEXT,
    
    -- Unique constraint for current versions
    UNIQUE (proposal_id, section_id, version)
);

CREATE INDEX idx_sections_proposal ON proposal_sections(proposal_id);
CREATE INDEX idx_sections_current ON proposal_sections(proposal_id, is_current) WHERE is_current = TRUE;
CREATE INDEX idx_sections_section_id ON proposal_sections(section_id);

-- Function to calculate word count
CREATE OR REPLACE FUNCTION calculate_word_count()
RETURNS TRIGGER AS $$
BEGIN
    NEW.word_count = array_length(regexp_split_to_array(NEW.section_content, '\s+'), 1);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_word_count
    BEFORE INSERT OR UPDATE OF section_content ON proposal_sections
    FOR EACH ROW
    EXECUTE FUNCTION calculate_word_count();

-- ================================================================
-- 3. EVALUATION CRITERIA TRACKING
-- ================================================================

CREATE TABLE IF NOT EXISTS section_criteria_mapping (
    id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES proposal_sections(id) ON DELETE CASCADE,
    
    -- Criterion information
    criterion_name VARCHAR(255) NOT NULL,
    criterion_category VARCHAR(50), -- 'excellence', 'impact', 'implementation'
    
    -- Coverage assessment
    addressed BOOLEAN DEFAULT FALSE,
    strength_score DECIMAL(3,2), -- 0.00 to 1.00
    
    -- Evidence
    evidence TEXT[], -- Array of quotes/paragraph references
    gaps TEXT[], -- Array of identified gaps
    
    -- Metadata
    last_checked TIMESTAMP DEFAULT NOW(),
    checked_by VARCHAR(100),
    
    UNIQUE (section_id, criterion_name)
);

CREATE INDEX idx_criteria_section ON section_criteria_mapping(section_id);
CREATE INDEX idx_criteria_addressed ON section_criteria_mapping(addressed);

-- ================================================================
-- 4. CONSORTIUM & PARTNERS
-- ================================================================

CREATE TABLE IF NOT EXISTS proposal_consortium (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    
    -- Partner information
    partner_name VARCHAR(255) NOT NULL,
    partner_short_name VARCHAR(50),
    partner_country VARCHAR(3) NOT NULL, -- ISO 3166-1 alpha-3
    partner_type VARCHAR(50) NOT NULL, -- 'HES', 'REC', 'PRC', 'OTH'
    
    -- Role
    is_coordinator BOOLEAN DEFAULT FALSE,
    partner_role TEXT,
    partner_expertise TEXT,
    
    -- Contact
    contact_person VARCHAR(255),
    contact_email VARCHAR(255),
    
    -- Contribution
    person_months DECIMAL(6,2),
    budget_share DECIMAL(3,2), -- 0.00 to 1.00
    
    -- Work packages involved
    work_packages INTEGER[],
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_partner_type CHECK (partner_type IN ('HES', 'REC', 'PRC', 'OTH')),
    CONSTRAINT valid_budget_share CHECK (budget_share >= 0 AND budget_share <= 1)
);

CREATE INDEX idx_consortium_proposal ON proposal_consortium(proposal_id);
CREATE INDEX idx_consortium_coordinator ON proposal_consortium(is_coordinator) WHERE is_coordinator = TRUE;

-- ================================================================
-- 5. BUDGET TABLES
-- ================================================================

CREATE TABLE IF NOT EXISTS proposal_budgets (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    consortium_id INTEGER REFERENCES proposal_consortium(id) ON DELETE CASCADE,
    
    -- Partner identification
    partner_name VARCHAR(255) NOT NULL,
    partner_country VARCHAR(3) NOT NULL,
    partner_type VARCHAR(50) NOT NULL,
    
    -- Cost categories
    personnel_costs DECIMAL(12,2) DEFAULT 0,
    subcontracting_costs DECIMAL(12,2) DEFAULT 0,
    equipment_costs DECIMAL(12,2) DEFAULT 0,
    other_direct_costs DECIMAL(12,2) DEFAULT 0,
    indirect_costs DECIMAL(12,2) DEFAULT 0,
    
    -- Totals
    total_eligible_costs DECIMAL(12,2) GENERATED ALWAYS AS (
        personnel_costs + subcontracting_costs + equipment_costs + 
        other_direct_costs + indirect_costs
    ) STORED,
    
    -- Funding
    funding_rate DECIMAL(3,2) NOT NULL, -- 0.70 or 1.00
    requested_funding DECIMAL(12,2),
    
    -- Justification
    personnel_justification TEXT,
    equipment_justification TEXT,
    other_justification TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT valid_funding_rate CHECK (funding_rate IN (0.70, 1.00))
);

CREATE INDEX idx_budgets_proposal ON proposal_budgets(proposal_id);

-- Auto-calculate requested funding
CREATE OR REPLACE FUNCTION calculate_requested_funding()
RETURNS TRIGGER AS $$
BEGIN
    NEW.requested_funding = NEW.total_eligible_costs * NEW.funding_rate;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_funding
    BEFORE INSERT OR UPDATE ON proposal_budgets
    FOR EACH ROW
    EXECUTE FUNCTION calculate_requested_funding();

-- ================================================================
-- 6. WORK PACKAGES
-- ================================================================

CREATE TABLE IF NOT EXISTS proposal_work_packages (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    
    -- Work package info
    wp_number INTEGER NOT NULL,
    wp_title VARCHAR(255) NOT NULL,
    wp_type VARCHAR(50), -- 'RTD', 'DEM', 'MGT', 'OTHER'
    
    -- Leadership
    lead_partner_id INTEGER REFERENCES proposal_consortium(id),
    
    -- Description
    objectives TEXT,
    description TEXT,
    
    -- Resources
    start_month INTEGER,
    end_month INTEGER,
    person_months DECIMAL(6,2),
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE (proposal_id, wp_number)
);

CREATE INDEX idx_wp_proposal ON proposal_work_packages(proposal_id);

-- ================================================================
-- 7. DELIVERABLES
-- ================================================================

CREATE TABLE IF NOT EXISTS proposal_deliverables (
    id SERIAL PRIMARY KEY,
    work_package_id INTEGER NOT NULL REFERENCES proposal_work_packages(id) ON DELETE CASCADE,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    
    -- Deliverable info
    deliverable_number VARCHAR(20) NOT NULL, -- e.g., 'D1.1'
    deliverable_title VARCHAR(255) NOT NULL,
    deliverable_type VARCHAR(50), -- 'Report', 'Software', 'Dataset', etc.
    
    -- Dissemination
    dissemination_level VARCHAR(20), -- 'PU', 'CO', 'CI'
    
    -- Timeline
    due_month INTEGER NOT NULL,
    
    -- Description
    description TEXT,
    
    UNIQUE (proposal_id, deliverable_number)
);

CREATE INDEX idx_deliverables_wp ON proposal_deliverables(work_package_id);
CREATE INDEX idx_deliverables_proposal ON proposal_deliverables(proposal_id);

-- ================================================================
-- 8. MILESTONES
-- ================================================================

CREATE TABLE IF NOT EXISTS proposal_milestones (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    work_package_id INTEGER REFERENCES proposal_work_packages(id),
    
    -- Milestone info
    milestone_number VARCHAR(20) NOT NULL, -- e.g., 'MS1'
    milestone_title VARCHAR(255) NOT NULL,
    
    -- Verification
    means_of_verification TEXT,
    
    -- Timeline
    due_month INTEGER NOT NULL,
    
    -- Related deliverables
    related_deliverables INTEGER[],
    
    UNIQUE (proposal_id, milestone_number)
);

CREATE INDEX idx_milestones_proposal ON proposal_milestones(proposal_id);

-- ================================================================
-- 9. COMPLIANCE CHECKS
-- ================================================================

CREATE TABLE IF NOT EXISTS compliance_checks (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    
    -- Check information
    check_type VARCHAR(100) NOT NULL,
    check_category VARCHAR(50), -- 'mandatory', 'recommended', 'optional'
    
    -- Result
    check_result VARCHAR(20) NOT NULL, -- 'pass', 'fail', 'warning', 'info'
    result_message TEXT,
    
    -- Details
    details JSONB DEFAULT '{}',
    
    -- Metadata
    checked_at TIMESTAMP DEFAULT NOW(),
    checked_by VARCHAR(100),
    
    CONSTRAINT valid_check_result CHECK (check_result IN ('pass', 'fail', 'warning', 'info'))
);

CREATE INDEX idx_compliance_proposal ON compliance_checks(proposal_id);
CREATE INDEX idx_compliance_result ON compliance_checks(check_result);
CREATE INDEX idx_compliance_checked ON compliance_checks(checked_at DESC);

-- ================================================================
-- 10. IMPROVEMENT SUGGESTIONS
-- ================================================================

CREATE TABLE IF NOT EXISTS improvement_suggestions (
    id SERIAL PRIMARY KEY,
    section_id INTEGER REFERENCES proposal_sections(id) ON DELETE CASCADE,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    
    -- Suggestion details
    suggestion_type VARCHAR(100) NOT NULL, -- 'readability', 'terminology', 'structure', etc.
    suggestion_text TEXT NOT NULL,
    priority VARCHAR(20) NOT NULL, -- 'critical', 'high', 'medium', 'low'
    
    -- Context
    affected_text TEXT,
    suggested_replacement TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'applied', 'dismissed', 'reviewing'
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),
    
    CONSTRAINT valid_priority CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    CONSTRAINT valid_status CHECK (status IN ('pending', 'applied', 'dismissed', 'reviewing'))
);

CREATE INDEX idx_suggestions_section ON improvement_suggestions(section_id);
CREATE INDEX idx_suggestions_proposal ON improvement_suggestions(proposal_id);
CREATE INDEX idx_suggestions_status ON improvement_suggestions(status);
CREATE INDEX idx_suggestions_priority ON improvement_suggestions(priority);

-- ================================================================
-- 11. PROPOSAL TEMPLATES (Call-specific)
-- ================================================================

CREATE TABLE IF NOT EXISTS proposal_templates (
    id SERIAL PRIMARY KEY,
    call_identifier VARCHAR(255) NOT NULL,
    
    -- Template info
    template_type VARCHAR(50) NOT NULL, -- 'RIA', 'IA', 'CSA', etc.
    template_version VARCHAR(20) DEFAULT '1.0',
    
    -- Structure
    template_structure JSONB NOT NULL,
    evaluation_criteria JSONB,
    
    -- Limits
    page_limits JSONB,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    
    UNIQUE (call_identifier, template_version)
);

CREATE INDEX idx_templates_call ON proposal_templates(call_identifier);
CREATE INDEX idx_templates_active ON proposal_templates(is_active) WHERE is_active = TRUE;

-- ================================================================
-- 12. PROPOSAL EXAMPLES (Learning from success)
-- ================================================================

CREATE TABLE IF NOT EXISTS proposal_examples (
    id SERIAL PRIMARY KEY,
    
    -- Context
    call_identifier VARCHAR(255),
    section_id VARCHAR(100) NOT NULL,
    section_name VARCHAR(255),
    
    -- Content
    example_text TEXT NOT NULL,
    
    -- Quality
    evaluation_score DECIMAL(3,1), -- e.g., 14.5 out of 15
    success_factors TEXT[],
    
    -- Meta
    is_public BOOLEAN DEFAULT FALSE,
    is_anonymized BOOLEAN DEFAULT TRUE,
    added_at TIMESTAMP DEFAULT NOW(),
    added_by VARCHAR(100),
    
    -- Tags for searching
    tags TEXT[]
);

CREATE INDEX idx_examples_section ON proposal_examples(section_id);
CREATE INDEX idx_examples_call ON proposal_examples(call_identifier);
CREATE INDEX idx_examples_score ON proposal_examples(evaluation_score DESC);
CREATE INDEX idx_examples_tags ON proposal_examples USING GIN(tags);

-- ================================================================
-- 13. ACTIVITY LOG (Audit trail)
-- ================================================================

CREATE TABLE IF NOT EXISTS proposal_activity_log (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    
    -- Activity details
    activity_type VARCHAR(100) NOT NULL,
    activity_description TEXT,
    
    -- User
    user_id VARCHAR(100),
    
    -- Changes
    changes_made JSONB,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_activity_proposal ON proposal_activity_log(proposal_id);
CREATE INDEX idx_activity_timestamp ON proposal_activity_log(created_at DESC);
CREATE INDEX idx_activity_type ON proposal_activity_log(activity_type);

-- ================================================================
-- 14. USEFUL VIEWS
-- ================================================================

-- View: Proposal overview with statistics
CREATE OR REPLACE VIEW proposal_overview AS
SELECT 
    p.id,
    p.call_identifier,
    p.proposal_title,
    p.proposal_acronym,
    p.proposal_type,
    p.status,
    p.completion_percentage,
    p.created_at,
    p.updated_at,
    
    -- Section stats
    COUNT(DISTINCT ps.id) FILTER (WHERE ps.is_current = TRUE) as section_count,
    SUM(ps.word_count) FILTER (WHERE ps.is_current = TRUE) as total_words,
    AVG(ps.quality_score) FILTER (WHERE ps.is_current = TRUE) as avg_quality_score,
    
    -- Consortium stats
    COUNT(DISTINCT pc.id) as partner_count,
    COUNT(DISTINCT pc.partner_country) as country_count,
    
    -- Budget stats
    SUM(pb.total_eligible_costs) as total_budget,
    SUM(pb.requested_funding) as total_funding_requested,
    
    -- Compliance
    COUNT(cc.id) FILTER (WHERE cc.check_result = 'fail') as critical_issues,
    COUNT(cc.id) FILTER (WHERE cc.check_result = 'warning') as warnings
FROM proposals p
LEFT JOIN proposal_sections ps ON p.id = ps.proposal_id
LEFT JOIN proposal_consortium pc ON p.id = pc.proposal_id
LEFT JOIN proposal_budgets pb ON p.id = pb.proposal_id
LEFT JOIN compliance_checks cc ON p.id = cc.proposal_id
GROUP BY p.id;

-- View: Section quality summary
CREATE OR REPLACE VIEW section_quality_summary AS
SELECT 
    ps.id,
    ps.proposal_id,
    ps.section_id,
    ps.section_name,
    ps.word_count,
    ps.quality_score,
    ps.compliance_score,
    ps.completeness_score,
    
    -- Criteria coverage
    COUNT(scm.id) as total_criteria,
    COUNT(scm.id) FILTER (WHERE scm.addressed = TRUE) as addressed_criteria,
    AVG(scm.strength_score) as avg_criteria_strength,
    
    -- Suggestions
    COUNT(isug.id) FILTER (WHERE isug.status = 'pending') as pending_suggestions,
    COUNT(isug.id) FILTER (WHERE isug.priority = 'critical') as critical_suggestions
FROM proposal_sections ps
LEFT JOIN section_criteria_mapping scm ON ps.id = scm.section_id
LEFT JOIN improvement_suggestions isug ON ps.id = isug.section_id
WHERE ps.is_current = TRUE
GROUP BY ps.id;

-- ================================================================
-- 15. HELPER FUNCTIONS
-- ================================================================

-- Function: Get current sections for a proposal
CREATE OR REPLACE FUNCTION get_current_sections(p_proposal_id INTEGER)
RETURNS TABLE (
    section_id VARCHAR(100),
    section_name VARCHAR(255),
    section_content TEXT,
    word_count INTEGER,
    quality_score DECIMAL(3,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ps.section_id,
        ps.section_name,
        ps.section_content,
        ps.word_count,
        ps.quality_score
    FROM proposal_sections ps
    WHERE ps.proposal_id = p_proposal_id
    AND ps.is_current = TRUE
    ORDER BY ps.section_order;
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate proposal completion percentage
CREATE OR REPLACE FUNCTION calculate_completion_percentage(p_proposal_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    total_sections INTEGER;
    completed_sections INTEGER;
BEGIN
    -- Get expected number of sections (simplified - assumes RIA)
    total_sections := 7; -- Excellence (3) + Impact (2) + Implementation (2)
    
    -- Count completed sections (>100 words and quality score >0.5)
    SELECT COUNT(*)
    INTO completed_sections
    FROM proposal_sections
    WHERE proposal_id = p_proposal_id
    AND is_current = TRUE
    AND word_count >= 100
    AND (quality_score >= 0.5 OR quality_score IS NULL);
    
    RETURN LEAST(100, (completed_sections * 100 / total_sections));
END;
$$ LANGUAGE plpgsql;

-- Function: Update proposal completion
CREATE OR REPLACE FUNCTION update_proposal_completion()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE proposals
    SET completion_percentage = calculate_completion_percentage(NEW.proposal_id)
    WHERE id = NEW.proposal_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_completion
    AFTER INSERT OR UPDATE ON proposal_sections
    FOR EACH ROW
    EXECUTE FUNCTION update_proposal_completion();

-- ================================================================
-- 16. SAMPLE DATA FOR TESTING (Optional)
-- ================================================================

-- Insert a sample proposal template for testing
INSERT INTO proposal_templates (call_identifier, template_type, template_structure, evaluation_criteria, page_limits)
VALUES (
    'HORIZON-CL3-2025-02-CS-ECCC-01',
    'RIA',
    '{
        "sections": [
            {"id": "excellence", "name": "Excellence", "order": 1, "subsections": [
                {"id": "excellence.objectives", "name": "Objectives and ambition", "order": 1},
                {"id": "excellence.methodology", "name": "Methodology", "order": 2},
                {"id": "excellence.beyond_sota", "name": "Beyond the state of the art", "order": 3}
            ]},
            {"id": "impact", "name": "Impact", "order": 2, "subsections": [
                {"id": "impact.pathways", "name": "Pathways to impact", "order": 1},
                {"id": "impact.dissemination", "name": "Dissemination and exploitation", "order": 2}
            ]},
            {"id": "implementation", "name": "Implementation", "order": 3, "subsections": [
                {"id": "implementation.work_plan", "name": "Work plan and resources", "order": 1},
                {"id": "implementation.consortium", "name": "Consortium and management", "order": 2}
            ]}
        ]
    }',
    '{
        "excellence": ["Clarity and pertinence of objectives", "Soundness of methodology", "Credibility of approach"],
        "impact": ["Credibility of impact pathways", "Suitability of measures"],
        "implementation": ["Coherence of work plan", "Quality of consortium"]
    }',
    '{
        "excellence": 30,
        "impact": 10,
        "implementation": 15,
        "total": 45
    }'
)
ON CONFLICT (call_identifier, template_version) DO NOTHING;

-- ================================================================
-- MIGRATION COMPLETE
-- ================================================================

-- Grant permissions (adjust as needed)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

-- Summary message
DO $$
BEGIN
    RAISE NOTICE '✅ Proposal Writing System migration completed successfully!';
    RAISE NOTICE '📊 Created 16 tables, 3 views, and 6 functions';
    RAISE NOTICE '🚀 System ready for proposal creation and management';
END $$;

