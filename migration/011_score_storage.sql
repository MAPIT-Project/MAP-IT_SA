-- ================================================================
-- SCORE STORAGE FOR EVALUATOR PREDICTIONS
-- ================================================================
-- Tracks current and historical scores for each proposal section
--
-- Author: AI Assistant
-- Date: 2025-12-04
-- Task: 09_SCORE_INTEGRATION
-- ================================================================

-- Current scores for each section
CREATE TABLE IF NOT EXISTS section_scores (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
    section_id INTEGER NOT NULL REFERENCES proposal_sections(id) ON DELETE CASCADE,
    section_type VARCHAR(50) NOT NULL,

    -- Score data
    predicted_score DECIMAL(2,1) NOT NULL,  -- 0.0 to 5.0
    confidence DECIMAL(3,2) NOT NULL,        -- 0.00 to 1.00
    score_tier VARCHAR(20) NOT NULL,         -- threshold, good, excellent

    -- Breakdown
    criterion_scores JSONB,  -- Per-criterion breakdown
    strengths JSONB,         -- List of identified strengths
    weaknesses JSONB,        -- List of identified weaknesses
    evaluator_comments TEXT, -- ESR-style comments

    -- Metadata
    content_hash VARCHAR(64) NOT NULL,  -- Hash of content that was scored
    model_version VARCHAR(20) DEFAULT 'v1.0',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT section_scores_section_unique UNIQUE(section_id)
);

-- Historical scores for tracking improvement
CREATE TABLE IF NOT EXISTS section_score_history (
    id SERIAL PRIMARY KEY,
    section_id INTEGER NOT NULL REFERENCES proposal_sections(id) ON DELETE CASCADE,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,

    -- Score snapshot
    predicted_score DECIMAL(2,1) NOT NULL,
    confidence DECIMAL(3,2) NOT NULL,
    content_length INT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,

    -- Context
    trigger_type VARCHAR(20) NOT NULL,  -- manual, auto, save, batch
    created_at TIMESTAMP DEFAULT NOW()
);

-- Proposal-level aggregated scores
CREATE TABLE IF NOT EXISTS proposal_scores (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,

    -- Aggregated scores by criterion
    excellence_score DECIMAL(2,1),
    impact_score DECIMAL(2,1),
    implementation_score DECIMAL(2,1),
    overall_score DECIMAL(2,1),

    -- Derived metrics
    funding_probability DECIMAL(3,2),  -- 0.00 to 1.00
    threshold_distance DECIMAL(2,1),   -- Points from threshold
    estimated_rank VARCHAR(20),        -- top_10, top_25, etc.

    -- Metadata
    sections_scored INT DEFAULT 0,
    total_sections INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT NOW(),

    CONSTRAINT proposal_scores_proposal_unique UNIQUE(proposal_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_section_scores_proposal ON section_scores(proposal_id);
CREATE INDEX IF NOT EXISTS idx_section_scores_section ON section_scores(section_id);
CREATE INDEX IF NOT EXISTS idx_section_scores_tier ON section_scores(score_tier);
CREATE INDEX IF NOT EXISTS idx_score_history_section ON section_score_history(section_id);
CREATE INDEX IF NOT EXISTS idx_score_history_created ON section_score_history(created_at);
CREATE INDEX IF NOT EXISTS idx_proposal_scores_proposal ON proposal_scores(proposal_id);

-- Function to update proposal aggregate scores
CREATE OR REPLACE FUNCTION update_proposal_aggregate_scores()
RETURNS TRIGGER AS $$
BEGIN
    -- Recalculate proposal-level scores
    INSERT INTO proposal_scores (
        proposal_id,
        excellence_score,
        impact_score,
        implementation_score,
        overall_score,
        sections_scored,
        total_sections,
        last_updated
    )
    SELECT
        NEW.proposal_id,
        AVG(CASE WHEN section_type LIKE 'excellence%' THEN predicted_score END),
        AVG(CASE WHEN section_type LIKE 'impact%' THEN predicted_score END),
        AVG(CASE WHEN section_type LIKE 'implementation%' THEN predicted_score END),
        AVG(predicted_score),
        COUNT(*),
        (SELECT COUNT(*) FROM proposal_sections WHERE proposal_id = NEW.proposal_id),
        NOW()
    FROM section_scores
    WHERE proposal_id = NEW.proposal_id
    GROUP BY proposal_id
    ON CONFLICT (proposal_id) DO UPDATE SET
        excellence_score = EXCLUDED.excellence_score,
        impact_score = EXCLUDED.impact_score,
        implementation_score = EXCLUDED.implementation_score,
        overall_score = EXCLUDED.overall_score,
        sections_scored = EXCLUDED.sections_scored,
        total_sections = EXCLUDED.total_sections,
        last_updated = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update aggregates
DROP TRIGGER IF EXISTS trg_update_proposal_scores ON section_scores;
CREATE TRIGGER trg_update_proposal_scores
AFTER INSERT OR UPDATE ON section_scores
FOR EACH ROW EXECUTE FUNCTION update_proposal_aggregate_scores();

-- View for easy score access
CREATE OR REPLACE VIEW v_section_scores AS
SELECT
    ss.id,
    ss.proposal_id,
    ss.section_id,
    ss.section_type,
    ps.section_name as section_title,
    ss.predicted_score,
    ss.confidence,
    ss.score_tier,
    ss.criterion_scores,
    ss.strengths,
    ss.weaknesses,
    ss.evaluator_comments,
    ss.created_at,
    p.proposal_title
FROM section_scores ss
JOIN proposal_sections ps ON ss.section_id = ps.id
JOIN proposals p ON ss.proposal_id = p.id;

-- View for score history with context
CREATE OR REPLACE VIEW v_score_history AS
SELECT
    sh.id,
    sh.section_id,
    sh.proposal_id,
    ps.section_id as section_type,
    ps.section_name as section_title,
    sh.predicted_score,
    sh.confidence,
    sh.content_length,
    sh.trigger_type,
    sh.created_at,
    LAG(sh.predicted_score) OVER (
        PARTITION BY sh.section_id ORDER BY sh.created_at
    ) as previous_score,
    sh.predicted_score - LAG(sh.predicted_score) OVER (
        PARTITION BY sh.section_id ORDER BY sh.created_at
    ) as score_change
FROM section_score_history sh
JOIN proposal_sections ps ON sh.section_id = ps.id
ORDER BY sh.created_at DESC;

-- Summary message
DO $$
BEGIN
    RAISE NOTICE 'Score storage migration completed successfully!';
    RAISE NOTICE 'Tables created: section_scores, section_score_history, proposal_scores';
    RAISE NOTICE 'Views created: v_section_scores, v_score_history';
    RAISE NOTICE 'Trigger: trg_update_proposal_scores for automatic aggregation';
END $$;
