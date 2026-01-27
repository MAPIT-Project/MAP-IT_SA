"""
Document ingestion service that orchestrates the complete pipeline.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..core.config import settings
from .chunking_service import TextChunker
from .document_processor import DocumentProcessor
from .embedding_service import EmbeddingService
from .supabase_client import SupabaseVectorStore

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """Complete document ingestion pipeline."""

    def __init__(self):
        """Initialize the ingestion service with all components."""
        self.supabase = SupabaseVectorStore()
        self.processor = DocumentProcessor()
        self.chunker = TextChunker()
        self.embedder = EmbeddingService(cache_client=self.supabase)

        # Create upload directory if it doesn't exist
        self.upload_dir = Path(settings.upload_dir)
        self.upload_dir.mkdir(exist_ok=True)

        logger.info("✅ Document ingestion service initialized")

    def ingest_file(
        self,
        file_path: str,
        document_type: str | None = None,
        programme_year: str | None = None,
        source_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ingest a single file through the complete pipeline."""
        try:
            logger.info(f"🚀 Starting ingestion for: {file_path}")

            # Step 1: Process document
            text_content, doc_metadata = self.processor.process_file(file_path, document_type)

            # Check for duplicates
            file_hash = doc_metadata.get("file_hash")
            if file_hash and self.supabase.check_duplicate(file_hash):
                logger.warning(f"⚠️ Duplicate document detected: {file_hash}")
                return {
                    "success": False,
                    "error": "Document already exists",
                    "file_hash": file_hash,
                }

            # Step 2: Create document record
            document_data = {
                "title": self._extract_title(text_content, doc_metadata, file_path),
                "source_type": "pdf" if file_path.endswith(".pdf") else "file",
                "source_url": source_url,
                "file_path": file_path,
                "document_type": document_type or self._infer_document_type(text_content),
                "programme_year": programme_year or self._infer_programme_year(text_content),
                "status": "processing",
                "file_hash": file_hash,
                "metadata": {**doc_metadata, **(metadata or {})},
            }

            document = self.supabase.insert_document(document_data)
            if not document:
                raise Exception("Failed to create document record")

            document_id = document["id"]
            logger.info(f"📄 Document created: {document_id}")

            # Step 3: Chunk text
            chunks = self.chunker.chunk_text(
                text_content, metadata=doc_metadata, document_id=document_id
            )

            if not chunks:
                self.supabase.update_document_status(
                    document_id, "failed", {"error": "No chunks created"}
                )
                raise Exception("No chunks were created from the document")

            logger.info(f"📝 Created {len(chunks)} chunks")

            # Step 4: Generate embeddings
            chunk_texts = [chunk["content"] for chunk in chunks]
            embeddings = self.embedder.generate_embeddings_batch(chunk_texts)

            if len(embeddings) != len(chunks):
                self.supabase.update_document_status(
                    document_id, "failed", {"error": "Embedding generation failed"}
                )
                raise Exception("Embedding generation failed")

            # Step 5: Prepare chunks for database insertion
            db_chunks = []
            for chunk, embedding in zip(chunks, embeddings, strict=False):
                chunk["embedding"] = embedding
                db_chunks.append(chunk)

            # Step 6: Insert chunks into database
            inserted_chunks = self.supabase.insert_chunks(db_chunks)

            if not inserted_chunks:
                self.supabase.update_document_status(
                    document_id, "failed", {"error": "Chunk insertion failed"}
                )
                raise Exception("Failed to insert chunks into database")

            # Step 7: Update document status
            final_metadata = {
                **doc_metadata,
                "total_chunks": len(inserted_chunks),
                "chunking_stats": self.chunker.get_chunking_stats(chunks),
                "ingestion_completed_at": datetime.now(UTC).isoformat(),
            }

            self.supabase.update_document_status(document_id, "active", final_metadata)

            logger.info(f"✅ Ingestion completed: {document_id}")

            return {
                "success": True,
                "document_id": document_id,
                "chunks_created": len(inserted_chunks),
                "title": document_data["title"],
                "document_type": document_data["document_type"],
                "programme_year": document_data["programme_year"],
            }

        except Exception as e:
            logger.error(f"❌ Ingestion failed for {file_path}: {e}")

            # Update document status if we have a document_id
            if "document_id" in locals():
                self.supabase.update_document_status(
                    document_id,
                    "failed",
                    {"error": str(e), "failed_at": datetime.now(UTC).isoformat()},
                )

            return {"success": False, "error": str(e), "file_path": file_path}

    def ingest_web_page(
        self,
        url: str,
        document_type: str | None = None,
        programme_year: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Ingest a web page through the complete pipeline."""
        try:
            logger.info(f"🌐 Starting web ingestion for: {url}")

            # Step 1: Scrape web page
            text_content, doc_metadata = self.processor.scrape_web_page(url, document_type)

            # Check for duplicates using content hash
            content_hash = doc_metadata.get("content_hash")
            if content_hash and self.supabase.check_duplicate(content_hash):
                logger.warning(f"⚠️ Duplicate web content detected: {content_hash}")
                return {
                    "success": False,
                    "error": "Web content already exists",
                    "content_hash": content_hash,
                }

            # Step 2: Create document record
            document_data = {
                "title": doc_metadata.get("page_title") or self._extract_title_from_url(url),
                "source_type": "web",
                "source_url": url,
                "document_type": document_type or "web",
                "programme_year": programme_year or self._infer_programme_year(text_content),
                "status": "processing",
                "file_hash": content_hash,
                "metadata": {**doc_metadata, **(metadata or {})},
            }

            document = self.supabase.insert_document(document_data)
            if not document:
                raise Exception("Failed to create document record")

            document_id = document["id"]
            logger.info(f"🌐 Web document created: {document_id}")

            # Continue with same pipeline as file ingestion
            return self._complete_ingestion_pipeline(
                document_id, text_content, doc_metadata, document_data
            )

        except Exception as e:
            logger.error(f"❌ Web ingestion failed for {url}: {e}")
            return {"success": False, "error": str(e), "url": url}

    def ingest_batch(
        self,
        file_paths: list[str],
        document_type: str | None = None,
        programme_year: str | None = None,
        max_workers: int = 3,
    ) -> list[dict[str, Any]]:
        """Ingest multiple files in parallel."""
        logger.info(f"📦 Starting batch ingestion for {len(file_paths)} files")

        results = []

        # Process files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for file_path in file_paths:
                future = executor.submit(self.ingest_file, file_path, document_type, programme_year)
                futures.append((file_path, future))

            # Collect results
            for file_path, future in futures:
                try:
                    result = future.result(timeout=300)  # 5 minute timeout per file
                    result["file_path"] = file_path
                    results.append(result)
                except Exception as e:
                    logger.error(f"❌ Batch ingestion failed for {file_path}: {e}")
                    results.append({"success": False, "error": str(e), "file_path": file_path})

        successful = len([r for r in results if r.get("success")])
        logger.info(f"✅ Batch ingestion completed: {successful}/{len(file_paths)} successful")

        return results

    async def ingest_file_async(
        self,
        file_path: str,
        document_type: str | None = None,
        programme_year: str | None = None,
        source_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Async version of file ingestion."""
        loop = asyncio.get_event_loop()

        return await loop.run_in_executor(
            None, self.ingest_file, file_path, document_type, programme_year, source_url, metadata
        )

    def _complete_ingestion_pipeline(
        self,
        document_id: str,
        text_content: str,
        doc_metadata: dict[str, Any],
        document_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Complete the ingestion pipeline after document creation."""
        try:
            # Step 3: Chunk text
            chunks = self.chunker.chunk_text(
                text_content, metadata=doc_metadata, document_id=document_id
            )

            if not chunks:
                self.supabase.update_document_status(
                    document_id, "failed", {"error": "No chunks created"}
                )
                raise Exception("No chunks were created from the document")

            logger.info(f"📝 Created {len(chunks)} chunks for document {document_id}")

            # Step 4: Generate embeddings
            chunk_texts = [chunk["content"] for chunk in chunks]
            embeddings = self.embedder.generate_embeddings_batch(chunk_texts)

            if len(embeddings) != len(chunks):
                self.supabase.update_document_status(
                    document_id, "failed", {"error": "Embedding generation failed"}
                )
                raise Exception("Embedding generation failed")

            # Step 5: Prepare chunks for database insertion
            db_chunks = []
            for chunk, embedding in zip(chunks, embeddings, strict=False):
                chunk["embedding"] = embedding
                db_chunks.append(chunk)

            # Step 6: Insert chunks into database
            inserted_chunks = self.supabase.insert_chunks(db_chunks)

            if not inserted_chunks:
                self.supabase.update_document_status(
                    document_id, "failed", {"error": "Chunk insertion failed"}
                )
                raise Exception("Failed to insert chunks into database")

            # Step 7: Update document status
            final_metadata = {
                **doc_metadata,
                "total_chunks": len(inserted_chunks),
                "chunking_stats": self.chunker.get_chunking_stats(chunks),
                "ingestion_completed_at": datetime.now(UTC).isoformat(),
            }

            self.supabase.update_document_status(document_id, "active", final_metadata)

            logger.info(f"✅ Pipeline completed for document: {document_id}")

            return {
                "success": True,
                "document_id": document_id,
                "chunks_created": len(inserted_chunks),
                "title": document_data["title"],
                "document_type": document_data["document_type"],
                "programme_year": document_data["programme_year"],
            }

        except Exception as e:
            logger.error(f"❌ Pipeline failed for document {document_id}: {e}")

            self.supabase.update_document_status(
                document_id, "failed", {"error": str(e), "failed_at": datetime.now(UTC).isoformat()}
            )

            raise e

    def _extract_title(self, text_content: str, metadata: dict[str, Any], file_path: str) -> str:
        """Extract or generate a title for the document."""
        # Try PDF metadata first
        if "pdf_metadata" in metadata and "title" in metadata["pdf_metadata"]:
            title = metadata["pdf_metadata"]["title"]
            if title and len(title.strip()) > 3:
                return title.strip()

        # Try HTML title
        if "html_title" in metadata:
            title = metadata["html_title"]
            if title and len(title.strip()) > 3:
                return title.strip()

        # Try to extract from first lines of content
        lines = text_content.split("\n")[:10]  # First 10 lines
        for line in lines:
            line = line.strip()
            if len(line) > 10 and len(line) < 200:  # Reasonable title length
                # Skip page markers and common headers
                if not line.startswith("[Page") and not line.lower().startswith("page "):
                    return line

        # Fallback to filename
        return Path(file_path).stem.replace("_", " ").replace("-", " ").title()

    def _extract_title_from_url(self, url: str) -> str:
        """Extract a title from URL."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]

        if path_parts:
            # Use last path component as title
            title = path_parts[-1].replace("-", " ").replace("_", " ")
            return title.title()

        return f"Web Page from {parsed.netloc}"

    def _infer_document_type(self, text_content: str) -> str:
        """Infer document type from content."""
        content_lower = text_content.lower()

        # Check for specific document types
        if "work programme" in content_lower:
            return "work_programme"
        elif "call for proposals" in content_lower or "call text" in content_lower:
            return "call_text"
        elif "programme guide" in content_lower:
            return "programme_guide"
        elif "grant agreement" in content_lower:
            return "grant_agreement"
        elif "frequently asked questions" in content_lower or "faq" in content_lower:
            return "faq"
        elif "manual" in content_lower:
            return "manual"
        else:
            return "unknown"

    def _infer_programme_year(self, text_content: str) -> str | None:
        """Infer programme year from content."""
        import re

        # Look for Horizon Europe years
        horizon_match = re.search(
            r"horizon\s+europe\s+(\d{4}[-–]\d{4})", text_content, re.IGNORECASE
        )
        if horizon_match:
            return horizon_match.group(1)

        # Look for year ranges
        year_match = re.search(r"(\d{4}[-–]\d{4})", text_content)
        if year_match:
            year_range = year_match.group(1)
            # Check if it's a reasonable programme year range
            start_year = int(year_range.split("[-–]")[0])
            if 2020 <= start_year <= 2030:
                return year_range

        # Look for single years
        current_year = datetime.now().year
        for year in range(2021, current_year + 5):
            if str(year) in text_content:
                return str(year)

        return None

    def get_ingestion_status(self, document_id: str) -> dict[str, Any]:
        """Get the status of a document ingestion."""
        document = self.supabase.get_document_by_id(document_id)

        if not document:
            return {"error": "Document not found"}

        status_info = {
            "document_id": document_id,
            "status": document["status"],
            "title": document["title"],
            "document_type": document["document_type"],
            "created_at": document["created_at"],
            "last_updated": document["last_updated"],
        }

        if document["status"] == "active":
            chunks = self.supabase.get_chunks_by_document(document_id)
            status_info["chunks_count"] = len(chunks)
            status_info["processing_completed_at"] = document.get("processing_completed_at")
        elif document["status"] == "failed":
            status_info["error"] = document.get("metadata", {}).get("error", "Unknown error")
        elif document["status"] == "processing":
            status_info["processing_started_at"] = document.get("processing_started_at")

        return status_info

    def reprocess_document(self, document_id: str) -> dict[str, Any]:
        """Reprocess a failed or existing document."""
        document = self.supabase.get_document_by_id(document_id)

        if not document:
            return {"success": False, "error": "Document not found"}

        # Delete existing chunks
        existing_chunks = self.supabase.get_chunks_by_document(document_id)
        if existing_chunks:
            logger.info(f"🗑️ Deleting {len(existing_chunks)} existing chunks")
            # Note: Chunks will be deleted automatically due to CASCADE

        # Update status to processing
        self.supabase.update_document_status(document_id, "processing")

        # Reprocess based on source type
        if document["source_type"] == "web":
            return self.ingest_web_page(
                document["source_url"], document["document_type"], document["programme_year"]
            )
        else:
            return self.ingest_file(
                document["file_path"],
                document["document_type"],
                document["programme_year"],
                document["source_url"],
            )

    def get_service_stats(self) -> dict[str, Any]:
        """Get statistics about the ingestion service."""
        stats = {
            "supabase_connected": self.supabase.test_connection(),
            "embedding_stats": self.embedder.get_embedding_stats(),
            "supported_formats": self.processor.supported_formats,
            "upload_directory": str(self.upload_dir),
            "chunking_config": {
                "chunk_size": self.chunker.config.chunk_size,
                "chunk_overlap": self.chunker.config.chunk_overlap,
            },
        }

        # Get database stats
        try:
            db_stats = self.supabase.get_document_stats()
            stats["database_stats"] = db_stats
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            stats["database_stats"] = {"error": str(e)}

        return stats
