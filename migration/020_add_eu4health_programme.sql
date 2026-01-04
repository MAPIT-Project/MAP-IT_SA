-- Migration: Add EU4Health to valid programmes
-- EU4Health is the EU health programme (2021-2027) with €4.4 billion budget

-- Drop existing constraint and recreate with eu4health added
ALTER TABLE funding_calls DROP CONSTRAINT IF EXISTS valid_programme;

ALTER TABLE funding_calls ADD CONSTRAINT valid_programme CHECK (
    programme IN (
        'horizon_europe',
        'horizon_plus',
        'digital_europe',
        'life',
        'creative_europe',
        'edf',
        'euratom',
        'erasmus',
        'cef',
        'interreg',
        'eu4health',  -- Added: EU4Health Programme
        'other'
    )
);

-- Also add to horizon_documents if it has a similar constraint
ALTER TABLE horizon_documents DROP CONSTRAINT IF EXISTS valid_programme;

-- Note: horizon_documents uses 'programme' metadata field, not a constraint
-- The programme filter is applied via metadata.programme = 'eu4health'

COMMENT ON CONSTRAINT valid_programme ON funding_calls IS
    'Valid EU funding programmes including EU4Health (added 2026-01-04)';
