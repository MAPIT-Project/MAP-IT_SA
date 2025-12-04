-- ================================================================
-- GAP TRACKING SCHEMA
-- ================================================================
-- Tracks identified gaps and their resolution status
--
-- Author: AI Assistant
-- Date: 2025-12-04
-- Task: 10_GAP_ANALYSIS
-- ================================================================

CREATE TABLE IF NOT EXISTS gap_tracking (
    id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES proposal_sections(id) ON DELETE CASCADE,
    gap_id VARCHAR(50) NOT NULL,

    -- Gap details (snapshot at time of identification)
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    estimated_impact DECIMAL(2,1),
    effort_level VARCHAR(20),

    -- Status
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,

    -- Metadata
    identified_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT gap_tracking_section_gap_unique UNIQUE(section_id, gap_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_gap_tracking_section ON gap_tracking(section_id);
CREATE INDEX IF NOT EXISTS idx_gap_tracking_resolved ON gap_tracking(resolved);
CREATE INDEX IF NOT EXISTS idx_gap_tracking_severity ON gap_tracking(severity);
CREATE INDEX IF NOT EXISTS idx_gap_tracking_category ON gap_tracking(category);

-- View for gap statistics per section
CREATE OR REPLACE VIEW v_gap_statistics AS
SELECT
    ps.proposal_id,
    ps.id as section_id,
    ps.section_id as section_type,
    COUNT(gt.id) as total_gaps,
    COUNT(gt.id) FILTER (WHERE gt.resolved) as resolved_gaps,
    COUNT(gt.id) FILTER (WHERE gt.severity = 'critical') as critical_gaps,
    COUNT(gt.id) FILTER (WHERE gt.severity = 'critical' AND gt.resolved) as critical_resolved,
    COALESCE(SUM(gt.estimated_impact), 0) as total_potential_impact,
    COALESCE(SUM(gt.estimated_impact) FILTER (WHERE gt.resolved), 0) as realized_impact
FROM proposal_sections ps
LEFT JOIN gap_tracking gt ON ps.id = gt.section_id
GROUP BY ps.proposal_id, ps.id, ps.section_id;

-- Function to calculate gap closure rate for a proposal
CREATE OR REPLACE FUNCTION get_gap_closure_rate(p_proposal_id INTEGER)
RETURNS DECIMAL AS $$
DECLARE
    total_gaps INT;
    resolved_gaps INT;
BEGIN
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE resolved)
    INTO total_gaps, resolved_gaps
    FROM gap_tracking gt
    JOIN proposal_sections ps ON gt.section_id = ps.id
    WHERE ps.proposal_id = p_proposal_id;

    IF total_gaps = 0 THEN
        RETURN 0;
    END IF;

    RETURN ROUND((resolved_gaps::DECIMAL / total_gaps) * 100, 1);
END;
$$ LANGUAGE plpgsql;

-- Summary message
DO $$
BEGIN
    RAISE NOTICE 'Gap tracking migration completed successfully!';
    RAISE NOTICE 'Table created: gap_tracking';
    RAISE NOTICE 'View created: v_gap_statistics';
    RAISE NOTICE 'Function created: get_gap_closure_rate()';
END $$;
