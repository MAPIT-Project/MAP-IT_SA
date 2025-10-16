-- Add citations column to message table
-- This migration adds a JSONB column to store citations directly in the message table

-- Add citations column as JSONB to store structured citation data
ALTER TABLE message 
ADD COLUMN IF NOT EXISTS citations JSONB;

-- Create index for better query performance on citations
CREATE INDEX IF NOT EXISTS idx_message_citations 
ON message USING GIN (citations);

-- Add comment to document the column
COMMENT ON COLUMN message.citations IS 'JSONB field storing citations associated with the message response';

-- Migration complete