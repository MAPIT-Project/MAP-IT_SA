-- DDL Schema for MAP-IT SA Local PostgreSQL/Supabase
-- Target database version: PostgreSQL 14+ with pgvector extension

-- Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================================
-- 1. Projects & Organizations Domain (CORDIS Data)
-- =========================================================================

-- Projects Table
CREATE TABLE IF NOT EXISTS projects (
    id VARCHAR(50) PRIMARY KEY,                         -- Project ID (numeric string from CORDIS)
    rcn VARCHAR(50),                                   -- CORDIS Record Control Number
    title TEXT NOT NULL,                               -- Full project title
    acronym VARCHAR(100),                              -- Project acronym
    objective TEXT,                                    -- Detailed project objective
    "startDate" DATE,                                  -- Project start date
    "endDate" DATE,                                    -- Project end date
    status VARCHAR(50),                                -- SIGNED, CLOSED, etc.
    "totalCost" NUMERIC(15, 2),                        -- Total cost in EUR
    "ecMaxContribution" NUMERIC(15, 2),                -- Maximum EC contribution in EUR
    "frameworkProgramme" VARCHAR(100),                  -- H2020, HORIZON, FP7, etc.
    "fundingScheme" VARCHAR(100),                      -- RIA, IA, CSA, ERC, etc.
    topics TEXT                                        -- Topic codes associated with project
);

-- Index for searching framework programmes and status
CREATE INDEX IF NOT EXISTS idx_projects_programme ON projects("frameworkProgramme");
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_rcn ON projects(rcn);

-- Project Description Embeddings (using Gemini 3072-dimension vectors)
CREATE TABLE IF NOT EXISTS project_embeddings (
    project_id VARCHAR(50) PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    combined_embedding vector(3072),                    -- High-dimensional semantic embedding
    model_version VARCHAR(50) DEFAULT 'gemini-embedding-001',
    text_length INTEGER,
    embedding_status VARCHAR(20) DEFAULT 'completed',  -- completed, pending, error
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for vector cosine similarity searches
CREATE INDEX IF NOT EXISTS idx_project_embeddings_cosine
ON project_embeddings USING hnsw (combined_embedding vector_cosine_ops);

-- Organizations Table (participation instances mapping projectID to country details)
CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,                              -- Internal Serial ID
    "projectID" VARCHAR(50) REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,                                 -- Organisation legal name
    short_name VARCHAR(100),                            -- Short name / acronym
    country VARCHAR(10),                                -- Two-letter country code
    city VARCHAR(100),                                  -- City name
    "activityType" VARCHAR(50),                         -- HES, REC, PRC, PUB, etc.
    "SME" BOOLEAN DEFAULT FALSE,                        -- SME indicator flag
    role VARCHAR(50) DEFAULT 'participant',             -- coordinator, participant
    "ecContribution" NUMERIC(15, 2)                     -- Organization contribution in EUR
);

-- Indices for organization lookups
CREATE INDEX IF NOT EXISTS idx_organizations_project_id ON organizations("projectID");
CREATE INDEX IF NOT EXISTS idx_organizations_country ON organizations(country);
CREATE INDEX IF NOT EXISTS idx_organizations_role ON organizations(role);

-- =========================================================================
-- 2. Funding Calls Domain
-- =========================================================================

-- Funding Calls Table
CREATE TABLE IF NOT EXISTS funding_calls (
    id SERIAL PRIMARY KEY,
    topic_code VARCHAR(100) UNIQUE NOT NULL,            -- e.g. HORIZON-CL5-2025-D3-01-04
    title TEXT NOT NULL,
    scope TEXT,                                        -- Detailed description of the call
    expected_outcome TEXT,                             -- Expected impact/outcomes
    deadline TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'open',                 -- open, closed, upcoming
    cluster VARCHAR(50),                               -- CL1-CL6, or programme specific
    action_type VARCHAR(50),                           -- RIA, IA, CSA, etc.
    budget_total NUMERIC(15, 2),                       -- Total budget allocated
    destination TEXT,                                  -- Destination identifier
    portal_url TEXT,                                   -- Direct link to EU Portal page
    call_year INTEGER,                                 -- E.g. 2025, 2026
    embedding vector(768),                             -- Text embedding for call search (using 768-dim model)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_funding_calls_topic_code ON funding_calls(topic_code);
CREATE INDEX IF NOT EXISTS idx_funding_calls_cluster ON funding_calls(cluster);
CREATE INDEX IF NOT EXISTS idx_funding_calls_status ON funding_calls(status);

-- =========================================================================
-- 3. Document Storage & Vector Chunks (RAG Knowledge Base)
-- =========================================================================

-- Official EU Reference Documents
CREATE TABLE IF NOT EXISTS horizon_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    document_type VARCHAR(100),                         -- work_programme, programme_guide, etc.
    programme_year VARCHAR(10),                         -- e.g. 2025, 2026
    file_path TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Document Chunks for Semantic Vector Search
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES horizon_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    document_title VARCHAR(255),
    document_type VARCHAR(100),
    section_title VARCHAR(255),
    page_number INTEGER,
    embedding vector(768),                             -- 768-dim vector embedding
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- Shared Documents (cross-programme reference documents)
CREATE TABLE IF NOT EXISTS shared_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    document_type VARCHAR(100),
    file_path TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS shared_document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES shared_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    document_title VARCHAR(255),
    embedding vector(768),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Embedding Generation Cache
CREATE TABLE IF NOT EXISTS embedding_cache (
    id SERIAL PRIMARY KEY,
    text_hash VARCHAR(64) UNIQUE NOT NULL,              -- SHA256 of text
    embedding vector(768) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embedding_cache_hash ON embedding_cache(text_hash);
