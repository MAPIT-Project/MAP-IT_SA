#!/usr/bin/env python3
"""
Script to ingest comprehensive Horizon Europe documents into the vector database.
This enables the RAG system to answer questions about ANY call or topic.
"""

import asyncio
import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ComprehensiveDocumentIngestor:
    """Ingest comprehensive Horizon Europe documents into vector database with optimized performance."""

    def __init__(self, max_concurrent_embeddings: int = 10, batch_size: int = 200):
        self.processed_dir = Path("processed_docs/horizon_europe")
        self.ingestion_file = self.processed_dir / "ingestion_ready.jsonl"

        # Performance configuration
        self.max_concurrent_embeddings = max_concurrent_embeddings
        self.default_batch_size = batch_size

        # Initialize services
        self.supabase = None
        self.embedder = None
        self.vector_search = None

        self._initialize_services()

    def _initialize_services(self):
        """Initialize the required services."""
        try:
            from app.services.embedding_service import EmbeddingService
            from app.services.supabase_client import SupabaseVectorStore
            from app.services.vector_search_service import VectorSearchService

            self.supabase = SupabaseVectorStore()
            self.embedder = EmbeddingService(cache_client=self.supabase)
            self.vector_search = VectorSearchService(self.supabase, self.embedder)

            logger.info("✅ Services initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            raise

    async def check_existing_documents(self, chunks: list[dict[str, Any]]) -> dict[str, Any]:
        """Check which documents and chunks already exist to enable resume capability."""
        logger.info("🔍 Checking for existing documents and chunks...")

        # Get existing document hashes based on file_path
        try:
            existing_docs = await asyncio.to_thread(self.supabase.get_all_documents)
            existing_hashes = {}
            for doc in existing_docs:
                if doc.get("file_path"):
                    # Use file_path for consistent hashing
                    file_hash = hashlib.md5(doc["file_path"].encode()).hexdigest()
                    existing_hashes[file_hash] = doc.get("id")
            logger.info(f"📋 Found {len(existing_hashes)} existing documents")
        except Exception as e:
            logger.error(f"❌ Error checking existing documents: {e}")
            existing_hashes = {}

        # Check which chunks need to be processed
        new_chunks = []
        existing_count = 0

        for chunk in chunks:
            # Use file_path from metadata for consistent hashing
            metadata = chunk.get("metadata", {})
            file_path = metadata.get("filepath")
            if file_path:
                file_hash = hashlib.md5(file_path.encode()).hexdigest()
            else:
                # Fallback to source_document if no file_path
                source_doc = metadata.get("source_document", "")
                file_hash = hashlib.md5(source_doc.encode()).hexdigest()

            if file_hash not in existing_hashes:
                new_chunks.append(chunk)
            else:
                existing_count += 1

        logger.info(
            f"📊 Processing status: {len(new_chunks)} new chunks, {existing_count} already exist"
        )

        return {
            "new_chunks": new_chunks,
            "existing_count": existing_count,
            "existing_doc_map": existing_hashes,
        }

    async def check_database_connection(self) -> bool:
        """Check if database connection is working."""
        try:
            connected = self.supabase.test_connection()
            if connected:
                logger.info("✅ Database connection successful")
                return True
            else:
                logger.error("❌ Database connection failed")
                return False
        except Exception as e:
            logger.error(f"❌ Database connection check failed: {e}")
            return False

    def load_ingestion_data(self) -> list[dict[str, Any]]:
        """Load ingestion-ready data from JSONL file."""
        if not self.ingestion_file.exists():
            logger.error(f"❌ Ingestion file not found: {self.ingestion_file}")
            return []

        ingestion_data = []
        try:
            with open(self.ingestion_file, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line.strip())
                        ingestion_data.append(item)

            logger.info(f"📊 Loaded {len(ingestion_data)} chunks for ingestion")
            return ingestion_data

        except Exception as e:
            logger.error(f"❌ Error loading ingestion data: {e}")
            return []

    async def _create_document_records(self, chunks: list[dict[str, Any]]) -> dict[str, str]:
        """Create document records for all unique source documents and return mapping of source to document ID."""
        document_map = {}
        unique_sources = set()

        # Collect all unique source documents
        for chunk in chunks:
            source_doc = chunk["metadata"].get("source_document")
            if source_doc and source_doc not in unique_sources:
                unique_sources.add(source_doc)

        logger.info(
            f"📄 Creating document records for {len(unique_sources)} unique sources concurrently"
        )

        # Get existing documents to check for duplicates
        try:
            existing_docs = await asyncio.to_thread(self.supabase.get_all_documents)
            existing_by_path = {
                doc.get("file_path"): doc.get("id") for doc in existing_docs if doc.get("file_path")
            }
            logger.info(f"📋 Found {len(existing_by_path)} existing documents by file path")
        except Exception as e:
            logger.error(f"❌ Error checking existing documents: {e}")
            existing_by_path = {}

        # Create tasks for concurrent document creation
        tasks = []
        source_to_metadata = {}

        # Prepare document data for all sources
        for source in unique_sources:
            # Find a chunk from this source to get metadata
            sample_chunk = next(
                (chunk for chunk in chunks if chunk["metadata"].get("source_document") == source),
                None,
            )
            if not sample_chunk:
                continue

            metadata = sample_chunk["metadata"]
            source_to_metadata[source] = metadata

            # Check if document already exists by file_path
            file_path = metadata.get("filepath")
            if file_path and file_path in existing_by_path:
                existing_id = existing_by_path[file_path]
                document_map[source] = existing_id
                title = metadata.get("filename", "Unknown Document")
                logger.info(f"♻️ Using existing document: {title} (ID: {existing_id})")
                continue

            document_data = {
                "title": metadata.get("filename", "Unknown Document"),
                "source_type": "pdf",
                "document_type": metadata.get("document_type", "unknown"),
                "programme_year": metadata.get("programme_year"),
                "file_path": metadata.get("filepath"),
                "file_hash": hashlib.md5((file_path or source).encode()).hexdigest(),
                "total_chunks": metadata.get("total_chunks", 0),
                "metadata": metadata,
            }

            # Create async task for document insertion
            task = self._create_single_document_record(source, document_data)
            tasks.append(task)

        # Execute all document creations concurrently
        if tasks:
            logger.info(f"🚀 Creating {len(tasks)} new document records concurrently...")
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            task_sources = [
                source for source in unique_sources if source not in document_map
            ]  # Only sources that weren't already existing

            for i, result in enumerate(results):
                if i < len(task_sources):
                    source = task_sources[i]
                    if isinstance(result, Exception):
                        logger.error(f"❌ Error creating document record for {source}: {result}")
                    elif result:
                        document_map[source] = result
                        title = source_to_metadata[source].get("filename", "Unknown Document")
                        logger.info(f"✅ Created new document record: {title} (ID: {result})")
                    else:
                        logger.error(f"❌ Failed to create document record for: {source}")

        logger.info(
            f"📊 Document mapping complete: {len(document_map)} total ({len([d for d in document_map.values() if d in existing_by_path.values()])} existing, {len(tasks)} new)"
        )
        return document_map

    def _map_document_type(self, document_type: str) -> str:
        """Map document types to ensure compatibility with database constraints."""
        # Known valid document types in the database
        valid_types = {
            "work_programme",
            "programme_guide",
            "call_text",
            "grant_agreement",
            "faq",
            "manual",
            "policy",
            "template",
        }

        # Document type mapping for unsupported types
        type_mapping = {
            "additional_resource": "manual",  # Map to manual which is closest
            "unknown": "manual",
            "": "manual",
            None: "manual",
        }

        if document_type in valid_types:
            return document_type
        elif document_type in type_mapping:
            mapped_type = type_mapping[document_type]
            logger.info(f"📋 Mapped document type '{document_type}' -> '{mapped_type}'")
            return mapped_type
        else:
            logger.warning(f"⚠️ Unknown document type '{document_type}', using 'manual'")
            return "manual"

    async def _create_single_document_record(
        self, source: str, document_data: dict[str, Any]
    ) -> str | None:
        """Create a single document record asynchronously with retry logic."""
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                # Ensure document type is valid
                document_data["document_type"] = self._map_document_type(
                    document_data.get("document_type", "manual")
                )

                document_record = await asyncio.to_thread(
                    self.supabase.insert_document, document_data
                )

                if document_record and "id" in document_record:
                    return document_record["id"]
                else:
                    logger.warning(
                        f"⚠️ Document creation returned no ID for: {source} (attempt {attempt + 1})"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2

            except Exception as e:
                error_msg = str(e)
                if "violates check constraint" in error_msg:
                    logger.error(f"❌ Database constraint violation for {source}: {error_msg}")
                    # Try with fallback document type
                    if document_data["document_type"] != "manual":
                        logger.info(f"🔄 Retrying {source} with document type 'manual'")
                        document_data["document_type"] = "manual"
                        continue
                else:
                    logger.error(
                        f"❌ Error in document creation attempt {attempt + 1} for {source}: {e}"
                    )

                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2

        logger.error(f"❌ Failed to create document after {max_retries} attempts: {source}")
        return None

    async def _process_batch_concurrent(
        self, batch: list[dict[str, Any]], document_map: dict[str, str]
    ) -> dict[str, Any]:
        """Process a batch of chunks concurrently for maximum performance."""
        logger.info(f"🔄 Processing {len(batch)} chunks concurrently...")

        # Extract texts for batch embedding generation
        texts = []
        chunk_indices = []

        for i, chunk in enumerate(batch):
            if chunk["content"] and chunk["content"].strip():
                texts.append(chunk["content"])
                chunk_indices.append(i)

        if not texts:
            logger.warning("⚠️ No valid texts found in batch")
            return {
                "processed_chunks": [],
                "failed_ids": [chunk.get("id", "unknown") for chunk in batch],
            }

        try:
            # Generate embeddings for all texts in the batch at once
            logger.info(f"🧠 Generating {len(texts)} embeddings in batch...")
            embeddings = await asyncio.to_thread(
                self.embedder.generate_embeddings_batch,
                texts,
                True,  # use_cache
            )

            if len(embeddings) != len(texts):
                logger.error(f"❌ Embedding count mismatch: {len(embeddings)} vs {len(texts)}")
                return {
                    "processed_chunks": [],
                    "failed_ids": [chunk.get("id", "unknown") for chunk in batch],
                }

            # Process chunks concurrently
            processed_chunks = []
            failed_ids = []

            # Create tasks for concurrent chunk processing
            tasks = []
            for i, embedding_idx in enumerate(chunk_indices):
                chunk = batch[embedding_idx]
                embedding = embeddings[i]
                task = self._process_single_chunk_data(chunk, embedding, document_map)
                tasks.append(task)

            # Process all chunks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Chunk processing failed: {result}")
                    failed_ids.append(batch[chunk_indices[i]].get("id", "unknown"))
                elif result is not None:
                    processed_chunks.append(result)
                else:
                    failed_ids.append(batch[chunk_indices[i]].get("id", "unknown"))

            # Handle chunks without valid content
            for i, chunk in enumerate(batch):
                if i not in chunk_indices:
                    failed_ids.append(chunk.get("id", "unknown"))

            logger.info(
                f"✅ Concurrent processing complete: {len(processed_chunks)} processed, {len(failed_ids)} failed"
            )

            return {"processed_chunks": processed_chunks, "failed_ids": failed_ids}

        except Exception as e:
            logger.error(f"❌ Concurrent batch processing failed: {e}")
            return {
                "processed_chunks": [],
                "failed_ids": [chunk.get("id", "unknown") for chunk in batch],
            }

    async def _process_single_chunk_data(
        self, chunk: dict[str, Any], embedding: Any, document_map: dict[str, str]
    ) -> dict[str, Any] | None:
        """Process a single chunk's data preparation (async-safe operations only)."""
        try:
            # Get document ID from the map
            source_doc = chunk["metadata"].get("source_document", "unknown")
            document_id = document_map.get(source_doc)
            if not document_id:
                logger.error(f"❌ No document ID found for source: {source_doc}")
                return None

            # Generate chunk_hash from content
            content_hash = hashlib.md5(chunk["content"].encode("utf-8")).hexdigest()

            chunk_data = {
                "content": chunk["content"],
                "embedding": embedding,
                "document_id": document_id,
                "chunk_index": chunk["metadata"].get("chunk_index", 0),
                "chunk_hash": content_hash,
                "metadata": chunk["metadata"],  # Store all metadata in JSONB field
            }

            # Add optional fields if present
            if "section_title" in chunk["metadata"]:
                chunk_data["section_title"] = chunk["metadata"]["section_title"]
            if "page_number" in chunk["metadata"]:
                chunk_data["page_number"] = chunk["metadata"]["page_number"]
            if "chapter" in chunk["metadata"]:
                chunk_data["chapter"] = chunk["metadata"]["chapter"]
            if "subsection" in chunk["metadata"]:
                chunk_data["subsection"] = chunk["metadata"]["subsection"]

            return chunk_data

        except Exception as e:
            logger.error(f"❌ Error processing single chunk: {e}")
            return None

    async def ingest_chunks(
        self, chunks: list[dict[str, Any]], batch_size: int | None = None
    ) -> dict[str, Any]:
        """Ingest chunks into the vector database with optimized concurrent processing."""
        if not chunks:
            logger.warning("⚠️ No chunks to ingest")
            return {"success": True, "ingested": 0}

        # Use default batch size if not specified
        if batch_size is None:
            batch_size = self.default_batch_size

        total_chunks = len(chunks)
        successful_ingestions = 0
        failed_ingestions = []

        logger.info(f"🚀 Starting optimized ingestion of {total_chunks} chunks...")

        # First, create document records for all unique source documents
        document_map = await self._create_document_records(chunks)
        if not document_map:
            logger.error("❌ Failed to create document records")
            return {
                "success": False,
                "ingested": 0,
                "failed": total_chunks,
                "failed_ids": [chunk.get("id", "unknown") for chunk in chunks],
            }

        # Process in larger batches with concurrent embedding generation
        embedding_batch_size = (
            100  # Process embeddings in smaller sub-batches for memory efficiency
        )

        for batch_start in range(0, total_chunks, batch_size):
            batch_end = min(batch_start + batch_size, total_chunks)
            batch = chunks[batch_start:batch_end]

            logger.info(
                f"📦 Processing optimized batch {batch_start // batch_size + 1}: chunks {batch_start}-{batch_end - 1}"
            )

            try:
                # Process batch concurrently with memory management
                all_processed_chunks = []
                all_failed_ids = []

                # Process in sub-batches for memory efficiency
                for sub_start in range(0, len(batch), embedding_batch_size):
                    sub_end = min(sub_start + embedding_batch_size, len(batch))
                    sub_batch = batch[sub_start:sub_end]

                    batch_result = await self._process_batch_concurrent(sub_batch, document_map)
                    all_processed_chunks.extend(batch_result["processed_chunks"])
                    all_failed_ids.extend(batch_result["failed_ids"])

                # Insert all processed chunks from this batch
                if all_processed_chunks:
                    result = await asyncio.to_thread(
                        self.supabase.insert_chunks, all_processed_chunks
                    )

                    if result:
                        successful_ingestions += len(all_processed_chunks)
                        logger.info(
                            f"✅ Optimized batch ingested: {len(all_processed_chunks)} chunks"
                        )
                    else:
                        failed_ingestions.extend(all_failed_ids)
                        logger.error("❌ Batch insertion failed")
                else:
                    logger.warning("⚠️ No chunks processed in this batch")

                failed_ingestions.extend(all_failed_ids)

                # Progress update every few batches
                if (batch_start // batch_size + 1) % 5 == 0:
                    progress = (batch_end / total_chunks) * 100
                    logger.info(
                        f"📈 Progress: {progress:.1f}% ({successful_ingestions} ingested, {len(failed_ingestions)} failed)"
                    )

            except Exception as e:
                logger.error(f"❌ Exception during batch processing: {e}")
                failed_ingestions.extend([chunk.get("id", "unknown") for chunk in batch])

        # Summary
        logger.info("\n📊 Optimized Ingestion Summary:")
        logger.info(f"✅ Successful: {successful_ingestions}/{total_chunks}")
        logger.info(f"❌ Failed: {len(failed_ingestions)}")

        if failed_ingestions:
            logger.warning(
                f"Failed chunks: {failed_ingestions[:10]}{'...' if len(failed_ingestions) > 10 else ''}"
            )

        return {
            "success": successful_ingestions > 0,
            "ingested": successful_ingestions,
            "failed": len(failed_ingestions),
            "failed_ids": failed_ingestions,
        }

    async def update_document_stats(self):
        """Update and log document statistics after ingestion."""
        try:
            stats = self.supabase.get_document_stats()
            logger.info("📈 Database Statistics:")
            logger.info(f"   Total Documents: {stats.get('total_documents', 0)}")
            logger.info(f"   Total Chunks: {stats.get('total_chunks', 0)}")
            logger.info(
                f"   Documents by Type: {json.dumps(stats.get('documents_by_type', {}), indent=2)}"
            )

            # Save stats to file
            stats_file = self.processed_dir / "post_ingestion_stats.json"
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)

            logger.info(f"💾 Statistics saved to: {stats_file}")

        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")

    async def test_ingestion(self):
        """Test that ingestion was successful by running sample searches."""
        logger.info("🧪 Testing ingestion with sample searches...")

        test_queries = [
            "Horizon Europe eligibility criteria",
            "ERC grant application process",
            "Health cluster funding opportunities",
            "Digital transformation call deadlines",
            "Climate energy mobility evaluation criteria",
        ]

        results = {}
        for query in test_queries:
            try:
                search_results = self.vector_search.search(
                    query=query, search_type="semantic", num_results=3, similarity_threshold=0.6
                )

                results[query] = {
                    "found": len(search_results) > 0,
                    "count": len(search_results),
                    "top_score": search_results[0].score if search_results else 0,
                }

                logger.info(
                    f"   '{query}': {len(search_results)} results (top score: {search_results[0].score if search_results else 0:.3f})"
                )

            except Exception as e:
                logger.error(f"❌ Test search failed for '{query}': {e}")
                results[query] = {"error": str(e)}

        return results

    async def run_comprehensive_ingestion(self):
        """Run optimized comprehensive document ingestion with resume capability."""
        logger.info("🚀 Starting Optimized Comprehensive Document Ingestion")

        # Check database connection
        if not await self.check_database_connection():
            return False

        # Load ingestion data
        chunks = self.load_ingestion_data()
        if not chunks:
            logger.error("❌ No ingestion data found")
            return False

        # Check for existing documents (resume capability)
        check_result = await self.check_existing_documents(chunks)
        chunks_to_process = check_result["new_chunks"]

        if not chunks_to_process:
            logger.info("✅ All documents already ingested!")
            await self.update_document_stats()
            return True

        logger.info(
            f"📋 Processing {len(chunks_to_process)} new chunks (skipping {check_result['existing_count']} existing)"
        )

        # Start timing for performance measurement
        start_time = time.time()

        # Ingest chunks with optimized processing
        ingestion_result = await self.ingest_chunks(chunks_to_process)

        # Calculate performance metrics
        total_time = time.time() - start_time
        chunks_per_second = len(chunks_to_process) / total_time if total_time > 0 else 0

        logger.info("⚡ Performance metrics:")
        logger.info(f"   Total time: {total_time:.2f} seconds")
        logger.info(f"   Chunks per second: {chunks_per_second:.2f}")
        logger.info(f"   Average time per chunk: {total_time / len(chunks_to_process):.3f} seconds")

        if not ingestion_result["success"]:
            logger.error("❌ Optimized ingestion failed")
            return False

        # Update statistics
        await self.update_document_stats()

        # Test ingestion
        test_results = await self.test_ingestion()

        # Save test results
        test_file = self.processed_dir / "ingestion_test_results.json"
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)

        logger.info(f"💾 Test results saved to: {test_file}")

        # Final summary
        logger.info("\n🎉 Optimized Comprehensive Ingestion Completed!")
        logger.info(f"📊 Total chunks ingested: {ingestion_result['ingested']}")
        logger.info(f"⚡ Performance: {chunks_per_second:.2f} chunks/second")
        logger.info("📈 Database now contains comprehensive Horizon Europe documentation")

        return True


async def main():
    """Main function to run comprehensive document ingestion with optimizations."""
    import argparse

    parser = argparse.ArgumentParser(description="Optimized Comprehensive Document Ingestion")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=200,
        help="Number of chunks to process per batch (default: 200)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum concurrent embedding generations (default: 10)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip documents that are already ingested (resume capability)",
    )

    args = parser.parse_args()

    logger.info(
        f"🎯 Starting ingestion with batch_size={args.batch_size}, max_concurrent={args.max_concurrent}"
    )

    ingestor = ComprehensiveDocumentIngestor(
        max_concurrent_embeddings=args.max_concurrent, batch_size=args.batch_size
    )

    try:
        success = await ingestor.run_comprehensive_ingestion()

        if success:
            logger.info("\n💡 Next steps:")
            logger.info("1. Enhance RAG system for call-specific queries")
            logger.info("2. Test with various call and topic questions")
            logger.info("3. Deploy updated system for research managers")
            return True
        else:
            logger.error("💥 Optimized comprehensive ingestion failed!")
            return False

    except Exception as e:
        logger.error(f"💥 Ingestion process failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)
