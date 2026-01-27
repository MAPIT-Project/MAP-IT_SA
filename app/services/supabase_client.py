"""
Supabase client service for vector storage and retrieval.
"""

import logging
from datetime import UTC, datetime
from typing import Any

import numpy as np
from supabase import Client, create_client

from ..core.config import settings

logger = logging.getLogger(__name__)

class SupabaseVectorStore:
    """Supabase client for vector storage and retrieval."""
    
    def __init__(self):
        """Initialize Supabase client with configuration."""
        self.url = settings.supabase_url
        self.key = settings.supabase_service_key
        
        if not self.url or not self.key:
            raise ValueError("Supabase credentials not found in configuration")
        
        try:
            self.client: Client = create_client(self.url, self.key)
            logger.info("✅ Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test the Supabase connection."""
        try:
            # Simple query to test connection
            response = self.client.table("horizon_documents").select("count").execute()
            logger.info("✅ Supabase connection test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Supabase connection test failed: {e}")
            return False
    
    def insert_document(self, document_data: dict[str, Any]) -> dict[str, Any] | None:
        """Insert a new document record."""
        try:
            # Ensure required fields are present
            required_fields = ['title', 'source_type']
            for field in required_fields:
                if field not in document_data:
                    raise ValueError(f"Required field '{field}' missing from document data")
            
            # Add timestamps if not present
            if 'created_at' not in document_data:
                document_data['created_at'] = datetime.now(UTC).isoformat()
            if 'last_updated' not in document_data:
                document_data['last_updated'] = datetime.now(UTC).isoformat()
            
            response = self.client.table("horizon_documents").insert(document_data).execute()
            
            if response.data:
                logger.info(f"✅ Document inserted: {response.data[0]['id']}")
                return response.data[0]
            else:
                logger.error("❌ Document insertion failed: No data returned")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error inserting document: {e}")
            return None
    
    def insert_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Batch insert document chunks with embeddings."""
        try:
            # Convert numpy arrays to lists for JSON serialization
            processed_chunks = []
            for chunk in chunks:
                processed_chunk = chunk.copy()
                
                # Convert embedding if it's a numpy array
                if isinstance(chunk.get('embedding'), np.ndarray):
                    processed_chunk['embedding'] = chunk['embedding'].tolist()
                
                # Add timestamp if not present
                if 'created_at' not in processed_chunk:
                    processed_chunk['created_at'] = datetime.now(UTC).isoformat()
                
                processed_chunks.append(processed_chunk)
            
            # Insert in batches to avoid payload size limits
            batch_size = 100
            all_results = []
            
            for i in range(0, len(processed_chunks), batch_size):
                batch = processed_chunks[i:i + batch_size]
                response = self.client.table("document_chunks").insert(batch).execute()
                
                if response.data:
                    all_results.extend(response.data)
                    logger.info(f"✅ Inserted batch of {len(batch)} chunks")
                else:
                    logger.error(f"❌ Failed to insert batch {i//batch_size + 1}")
            
            logger.info(f"✅ Total chunks inserted: {len(all_results)}")
            return all_results
            
        except Exception as e:
            logger.error(f"❌ Error inserting chunks: {e}")
            return []
    
    def semantic_search(
        self,
        query_embedding: np.ndarray,
        match_threshold: float = 0.7,
        match_count: int = 10,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Perform semantic search using vector similarity."""
        try:
            embedding_list = query_embedding.tolist()
            
            params = {
                'query_embedding': embedding_list,
                'match_threshold': match_threshold,
                'match_count': match_count,
                'filter_document_type': filters.get('document_type') if filters else None,
                'filter_year': filters.get('year') if filters else None
            }
            
            response = self.client.rpc('search_documents', params).execute()
            
            if response.data:
                logger.info(f"✅ Semantic search returned {len(response.data)} results")
                return response.data
            else:
                logger.warning("⚠️ Semantic search returned no results")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error in semantic search: {e}")
            return []
    
    def hybrid_search(
        self,
        query_text: str,
        query_embedding: np.ndarray,
        match_count: int = 10,
        vector_weight: float = 0.5
    ) -> list[dict[str, Any]]:
        """Perform hybrid search combining vector and keyword search."""
        try:
            embedding_list = query_embedding.tolist()
            
            params = {
                'query_embedding': embedding_list,
                'query_text': query_text,
                'match_count': match_count,
                'vector_weight': vector_weight
            }
            
            response = self.client.rpc('hybrid_search', params).execute()
            
            if response.data:
                logger.info(f"✅ Hybrid search returned {len(response.data)} results")
                return response.data
            else:
                logger.warning("⚠️ Hybrid search returned no results")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error in hybrid search: {e}")
            return []
    
    def get_document_by_id(self, document_id: str) -> dict[str, Any] | None:
        """Retrieve a document by ID."""
        try:
            response = self.client.table("horizon_documents")\
                .select("*")\
                .eq("id", document_id)\
                .single()\
                .execute()
            
            if response.data:
                logger.info(f"✅ Retrieved document: {document_id}")
                return response.data
            else:
                logger.warning(f"⚠️ Document not found: {document_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error retrieving document {document_id}: {e}")
            return None
    
    def get_chunks_by_document(self, document_id: str) -> list[dict[str, Any]]:
        """Get all chunks for a specific document."""
        try:
            response = self.client.table("document_chunks")\
                .select("*")\
                .eq("document_id", document_id)\
                .order("chunk_index")\
                .execute()
            
            if response.data:
                logger.info(f"✅ Retrieved {len(response.data)} chunks for document {document_id}")
                return response.data
            else:
                logger.warning(f"⚠️ No chunks found for document: {document_id}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error retrieving chunks for document {document_id}: {e}")
            return []
    
    def update_document_status(
        self, 
        document_id: str, 
        status: str,
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Update document processing status."""
        try:
            update_data = {
                "status": status,
                "last_updated": datetime.now(UTC).isoformat()
            }
            
            if metadata:
                update_data["metadata"] = metadata
            
            if status == "processing":
                update_data["processing_started_at"] = datetime.now(UTC).isoformat()
            elif status in ["active", "failed"]:
                update_data["processing_completed_at"] = datetime.now(UTC).isoformat()
            
            response = self.client.table("horizon_documents")\
                .update(update_data)\
                .eq("id", document_id)\
                .execute()
            
            if response.data:
                logger.info(f"✅ Updated document status: {document_id} -> {status}")
                return response.data[0]
            else:
                logger.error(f"❌ Failed to update document status: {document_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error updating document status {document_id}: {e}")
            return None
    
    def check_duplicate(self, file_hash: str) -> bool:
        """Check if a document with the same hash already exists."""
        try:
            response = self.client.table("horizon_documents")\
                .select("id")\
                .eq("file_hash", file_hash)\
                .execute()
            
            exists = len(response.data) > 0
            if exists:
                logger.info(f"✅ Duplicate document found with hash: {file_hash}")
            
            return exists
            
        except Exception as e:
            logger.error(f"❌ Error checking duplicate: {e}")
            return False
    
    def get_cached_embedding(self, text_hash: str) -> np.ndarray | None:
        """Retrieve cached embedding if it exists."""
        try:
            response = self.client.table("embedding_cache")\
                .select("embedding")\
                .eq("text_hash", text_hash)\
                .single()\
                .execute()
            
            if response.data:
                # Update usage count
                self.client.table("embedding_cache")\
                    .update({
                        "usage_count": response.data.get("usage_count", 0) + 1,
                        "last_used": datetime.now(UTC).isoformat()
                    })\
                    .eq("text_hash", text_hash)\
                    .execute()
                
                logger.debug(f"✅ Retrieved cached embedding for hash: {text_hash}")
                return np.array(response.data["embedding"])
            
            return None
            
        except Exception:
            logger.debug(f"No cached embedding found for hash: {text_hash}")
            return None
    
    def cache_embedding(
        self, 
        text_content: str, 
        text_hash: str, 
        embedding: np.ndarray
    ) -> None:
        """Cache an embedding for future use."""
        try:
            cache_data = {
                "text_hash": text_hash,
                "text_content": text_content[:1000],  # Store first 1000 chars for reference
                "embedding": embedding.tolist(),
                "created_at": datetime.now(UTC).isoformat(),
                "last_used": datetime.now(UTC).isoformat()
            }
            
            self.client.table("embedding_cache").upsert(cache_data).execute()
            logger.debug(f"✅ Cached embedding for hash: {text_hash}")
            
        except Exception as e:
            logger.error(f"❌ Error caching embedding: {e}")
    
    def get_document_stats(self) -> dict[str, Any]:
        """Get database statistics."""
        try:
            response = self.client.rpc('get_document_stats').execute()
            
            if response.data:
                stats = response.data[0]
                logger.info("✅ Retrieved document statistics")
                return stats
            else:
                logger.warning("⚠️ No statistics available")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Error retrieving statistics: {e}")
            return {}
    
    def list_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
        document_type: str | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """List documents with pagination and filtering."""
        try:
            query = self.client.table("horizon_documents").select("*")
            
            # Apply filters
            if status:
                query = query.eq("status", status)
            if document_type:
                query = query.eq("document_type", document_type)
            
            # Apply pagination and ordering
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            
            response = query.execute()
            
            # Get total count for pagination
            count_query = self.client.table("horizon_documents").select("id", count="exact")
            if status:
                count_query = count_query.eq("status", status)
            if document_type:
                count_query = count_query.eq("document_type", document_type)
            
            count_response = count_query.execute()
            total_count = count_response.count or 0
            
            documents = response.data or []
            logger.info(f"✅ Listed {len(documents)} documents (total: {total_count})")
            
            return documents, total_count
            
        except Exception as e:
            logger.error(f"❌ Error listing documents: {e}")
            return [], 0
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks."""
        try:
            # Delete chunks first (due to foreign key constraint)
            chunks_response = self.client.table("document_chunks")\
                .delete()\
                .eq("document_id", document_id)\
                .execute()
            
            # Delete document
            doc_response = self.client.table("horizon_documents")\
                .delete()\
                .eq("id", document_id)\
                .execute()
            
            logger.info(f"✅ Deleted document and chunks: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting document {document_id}: {e}")
            return False
    
    def cleanup_old_cache(self, days_old: int = 30) -> int:
        """Clean up old cached embeddings."""
        try:
            cutoff_date = datetime.now(UTC).replace(day=datetime.now(UTC).day - days_old)
            
            response = self.client.table("embedding_cache")\
                .delete()\
                .lt("last_used", cutoff_date.isoformat())\
                .execute()
            
            deleted_count = len(response.data) if response.data else 0
            logger.info(f"✅ Cleaned up {deleted_count} old cache entries")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up cache: {e}")
            return 0