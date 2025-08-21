#!/usr/bin/env python3
"""
Simplified script to set up the Horizon Europe RAG database tables in Supabase.
"""

import os
import sys
import psycopg2
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_database():
    """Set up the database tables and functions."""
    
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    print(f"🔗 Connecting to database: {db_url}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("✅ Connected to database")
        
        # Enable extensions
        print("🔧 Enabling extensions...")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")
        print("✅ Extensions enabled")
        
        # Create horizon_documents table
        print("📄 Creating horizon_documents table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS horizon_documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_type TEXT NOT NULL CHECK (source_type IN ('pdf', 'web', 'cordis', 'manual')),
                source_url TEXT,
                file_path TEXT,
                title TEXT NOT NULL,
                document_type TEXT CHECK (document_type IN (
                    'work_programme', 
                    'programme_guide', 
                    'call_text',
                    'grant_agreement',
                    'faq',
                    'manual',
                    'policy',
                    'template'
                )),
                programme_year TEXT,
                programme_part TEXT,
                language TEXT DEFAULT 'en',
                version TEXT,
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'processing', 'failed')),
                file_hash TEXT,
                total_chunks INTEGER DEFAULT 0,
                metadata JSONB DEFAULT '{}',
                processing_started_at TIMESTAMP WITH TIME ZONE,
                processing_completed_at TIMESTAMP WITH TIME ZONE,
                last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_by UUID
            );
        """)
        print("✅ horizon_documents table created")
        
        # Create document_chunks table
        print("📝 Creating document_chunks table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id UUID NOT NULL REFERENCES horizon_documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                chunk_hash TEXT NOT NULL,
                content TEXT NOT NULL,
                content_length INTEGER,
                embedding vector(768),
                section_title TEXT,
                page_number INTEGER,
                chapter TEXT,
                subsection TEXT,
                content_tokens tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
                metadata JSONB DEFAULT '{}',
                token_count INTEGER,
                embedding_model TEXT DEFAULT 'text-embedding-004',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        print("✅ document_chunks table created")
        
        # Create other tables
        print("📊 Creating supporting tables...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_queries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                query_text TEXT NOT NULL,
                query_embedding vector(768),
                search_type TEXT CHECK (search_type IN ('semantic', 'keyword', 'hybrid')),
                filters JSONB,
                results_count INTEGER,
                top_chunk_ids UUID[],
                response_time_ms INTEGER,
                user_feedback INTEGER CHECK (user_feedback BETWEEN 1 AND 5),
                session_id TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id UUID REFERENCES horizon_documents(id) ON DELETE CASCADE,
                job_type TEXT CHECK (job_type IN ('pdf_extraction', 'web_scraping', 'embedding_generation', 'chunking')),
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
                progress INTEGER DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
                error_message TEXT,
                started_at TIMESTAMP WITH TIME ZONE,
                completed_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                metadata JSONB DEFAULT '{}'
            );
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embedding_cache (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                text_hash TEXT UNIQUE NOT NULL,
                text_content TEXT NOT NULL,
                embedding vector(768) NOT NULL,
                model_version TEXT DEFAULT 'text-embedding-004',
                usage_count INTEGER DEFAULT 1,
                last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        print("✅ Supporting tables created")
        
        # Create indexes
        print("🔍 Creating indexes...")
        
        # Vector indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_embedding_cosine ON document_chunks 
            USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """)
        
        # Text search indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chunks_content_gin ON document_chunks USING gin(content_tokens);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_title_trgm ON horizon_documents USING gin(title gin_trgm_ops);
        """)
        
        # Metadata indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_type ON horizon_documents(document_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON horizon_documents(status);")
        
        print("✅ Indexes created")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name LIKE 'horizon_%' OR table_name LIKE '%chunk%' OR table_name LIKE '%embedding%')
        """)
        
        tables = cursor.fetchall()
        table_names = [t[0] for t in tables]
        print(f"✅ Database setup completed. Tables created: {table_names}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Setting up Horizon Europe RAG database...")
    success = setup_database()
    
    if success:
        print("🎉 Database setup completed successfully!")
    else:
        print("💥 Database setup failed!")
        sys.exit(1)