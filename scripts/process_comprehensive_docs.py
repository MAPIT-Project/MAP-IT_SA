#!/usr/bin/env python3
"""
Script to process comprehensive Horizon Euro        logger.info("🛡️ Memory settings for 32GB system: Threshold=%.1fGB, Max chunks/doc=%s, Chunk size=%d",
                    self.memory_threshold_gb, 
                    "unlimited" if self.max_chunks_per_document is None else self.max_chunks_per_document, 
                    self.chunk_size) documents for RAG ingestion.
Handles PDFs, HTML call pages, and prepares them for vector database ingestion.
"""

import os
import sys
import json
import re
import logging
import gc  # Garbage collection
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Optional psutil import for memory monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("⚠️ psutil not available. Memory monitoring will be limited.")

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveDocumentProcessor:
    """Process comprehensive Horizon Europe documents for RAG ingestion with memory safety."""
    
    def __init__(self):
        self.base_download_dir = Path("downloads/horizon_europe_comprehensive")
        self.processed_dir = Path("processed_docs/horizon_europe")
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Memory safety settings - more generous for 32GB system (12-16GB usage target)
        self.memory_threshold_mb = 14000  # 14GB threshold - plenty of room for 32GB system
        self.max_chunks_per_document = None  # Remove chunk limit to allow full document processing
        self.chunk_size = 400  # Good size for RAG - your friend's recommendation
        self.chunk_overlap = 100  # Good overlap to preserve context at boundaries
        self.max_text_length = 2000000  # 2M characters per document (much more generous)
        self.max_documents_per_batch = 3  # Can process multiple docs
        self.max_file_size_mb = 20.0  # Allow much larger files with more RAM
        
        # Document type mappings
        self.document_types = {
            "work_programme": "Work Programme",
            "programme_guide": "Programme Guide",
            "call_page": "Call Documentation",
            "additional_resource": "Additional Resource",
            "evaluation_manual": "Evaluation Manual",
            "grant_agreement": "Grant Agreement"
        }
        
        # Cluster mappings
        self.cluster_mapping = {
            "health": "Health",
            "digital_industry_space": "Digital, Industry and Space",
            "climate_energy_mobility": "Climate, Energy and Mobility",
            "food_bioeconomy": "Food, Bioeconomy, Natural Resources, Agriculture and Environment",
            "culture_creativity": "Culture, Creativity and Inclusive Society",
            "civil_security": " Civil Security for Society",
            "eic": "European Innovation Council",
            "general": "General Introduction"
        }
        
        logger.info("🛡️ Memory settings for 32GB system: Threshold=%.1fGB, Max chunks/doc=%s, Chunk size=%d",
                   self.memory_threshold_mb/1024, 
                   "unlimited" if self.max_chunks_per_document is None else self.max_chunks_per_document, 
                   self.chunk_size)
        logger.info("📋 Chunk overlap: %d chars, Max text length: %dK chars, Max file size: %.1fMB", 
                   self.chunk_overlap, self.max_text_length//1000, self.max_file_size_mb)
    
    def check_memory_usage(self) -> bool:
        """Check current memory usage focusing on process memory, not system memory."""
        try:
            if not PSUTIL_AVAILABLE:
                # Without psutil, we can't reliably check memory, so be extra conservative
                return True
            
            # Check the current process memory usage instead of system-wide memory
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / (1024 * 1024)
            
            # Also check available system memory
            memory_info = psutil.virtual_memory()
            available_memory_mb = memory_info.available / (1024 * 1024)
            
            logger.info("🧠 Process Memory: %.2fMB, Available System: %.2fMB (Threshold: %.2fMB)",
                       process_memory_mb, available_memory_mb, self.memory_threshold_mb)
            
            # Check if process memory exceeds threshold OR if system has less than 4GB available
            if process_memory_mb > self.memory_threshold_mb:
                logger.warning("⚠️ Process memory exceeded threshold! Used: %.2fMB > Threshold: %.2fMB",
                              process_memory_mb, self.memory_threshold_mb)
                return False
                
            if available_memory_mb < 4096:  # Less than 4GB available system memory
                logger.warning("⚠️ System memory running low! Available: %.2fMB", available_memory_mb)
                return False
                
            return True
        except Exception as e:
            logger.error("❌ Error checking memory usage: %s", e)
            return True  # Continue processing if we can't check memory
    
    def safe_garbage_collection(self):
        """Perform garbage collection with logging."""
        try:
            if PSUTIL_AVAILABLE:
                before = psutil.Process().memory_info().rss / (1024 * 1024)
                gc.collect()
                after = psutil.Process().memory_info().rss / (1024 * 1024)
                logger.info("🗑️ Garbage collection: Before %.2fMB -> After %.2fMB (Freed %.2fMB)",
                           before, after, before - after)
            else:
                gc.collect()
                logger.info("🗑️ Garbage collection performed (memory info unavailable)")
        except Exception as e:
            logger.warning("⚠️ Garbage collection error: %s", e)
            gc.collect()  # Still try to collect
    
    def load_call_metadata(self) -> List[Dict[str, Any]]:
        """Load call metadata from the downloaded JSON file."""
        metadata_file = self.base_download_dir / "all_calls_metadata.json"
        
        if not metadata_file.exists():
            logger.warning(f"⚠️ Call metadata file not found: {metadata_file}")
            return []
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                calls = json.load(f)
            logger.info(f"📊 Loaded metadata for {len(calls)} calls")
            return calls
        except Exception as e:
            logger.error(f"❌ Error loading call metadata: {e}")
            return []
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """Extract text from PDF file in a memory-efficient way with strict size limits."""
        try:
            # Check file size first to prevent loading large files
            file_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                logger.warning(f"⚠️ PDF file too large ({file_size_mb:.2f}MB > {self.max_file_size_mb}MB): {pdf_path.name}")
                return None
                
            logger.info(f"   📄 Processing PDF ({file_size_mb:.2f}MB): {pdf_path.name}")
            
            # Prefer pdfminer for better memory management
            try:
                from pdfminer.high_level import extract_text
                # Extract text directly without loading entire PDF into memory
                text = extract_text(str(pdf_path))
                
                # Allow much more text with more RAM available
                if len(text) > self.max_text_length:
                    logger.info(f"   ✂️ Truncating PDF text from {len(text)} to {self.max_text_length} chars")
                    text = text[:self.max_text_length]
                    
                return text
            except ImportError:
                # Fallback to PyPDF2 with page-by-page processing and early termination
                try:
                    import PyPDF2
                    text = ""
                    with open(pdf_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        total_pages = len(pdf_reader.pages)
                        max_pages = min(total_pages, 100)  # Process up to 100 pages with more RAM
                        
                        logger.info(f"   📖 Processing {max_pages}/{total_pages} pages from PDF")
                        
                        for page_num in range(max_pages):
                            if len(text) > self.max_text_length:
                                logger.info(f"   ✂️ Text limit reached at page {page_num}, stopping")
                                break
                                
                            try:
                                page = pdf_reader.pages[page_num]
                                page_text = page.extract_text()
                                if page_text:
                                    text += page_text + "\n"
                                # Clear memory after each page
                                del page_text, page
                            except Exception as e:
                                logger.warning(f"   ⚠️ Error processing page {page_num}: {e}")
                                continue
                                
                    return text[:self.max_text_length] if text else None
                except ImportError:
                    logger.error("❌ No PDF extraction library available. Install PyPDF2 or pdfminer.six")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error extracting text from {pdf_path.name}: {e}")
            return None
    
    def extract_text_from_html(self, html_path: Path) -> Optional[str]:
        """Extract text from HTML file with size limits."""
        try:
            # Check file size first
            file_size_mb = html_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                logger.warning(f"⚠️ HTML file too large ({file_size_mb:.2f}MB > {self.max_file_size_mb}MB): {html_path.name}")
                return None
            
            from bs4 import BeautifulSoup
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read file in chunks to prevent memory issues with large files
                content = f.read(self.max_text_length)  # Only read up to max length
                
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Ensure we don't exceed our text limit
            if len(text) > self.max_text_length:
                text = text[:self.max_text_length]
            
            return text
                
        except Exception as e:
            logger.error(f"❌ Error extracting text from {html_path.name}: {e}")
            return None
    
    def determine_document_type(self, filename: str, filepath: Path) -> str:
        """Determine the document type based on filename and path."""
        filename_lower = filename.lower()
        
        if "work_programme" in str(filepath.parent).lower():
            return "work_programme"
        elif "programme_guides" in str(filepath.parent).lower():
            return "programme_guide"
        elif "call_pages" in str(filepath.parent).lower():
            return "call_page"
        elif "additional_resources" in str(filepath.parent).lower():
            return "additional_resource"
        
        # Filename-based detection
        if "work_programme" in filename_lower:
            return "work_programme"
        elif "programme_guide" in filename_lower:
            return "programme_guide"
        elif "evaluation_manual" in filename_lower:
            return "evaluation_manual"
        elif "grant_agreement" in filename_lower or "aga" in filename_lower:
            return "grant_agreement"
        elif "call_" in filename_lower and filename.endswith('.html'):
            return "call_page"
        else:
            return "additional_resource"
    
    def determine_cluster(self, filename: str, filepath: Path) -> str:
        """Determine the cluster based on filename and path."""
        filename_lower = filename.lower()
        path_lower = str(filepath).lower()
        
        cluster_keywords = {
            "health": ["health", "medical", "biomed", "pharma"],
            "digital_industry_space": ["digital", "industry", "space", "ict", "ai", "quantum"],
            "climate_energy_mobility": ["climate", "energy", "mobility", "renewable", "green"],
            "food_bioeconomy": ["food", "bioeconomy", "agriculture", "environment", "natural"],
            "culture_creativity": ["culture", "creativity", "inclusive", "society"],
            "civil_security": ["civil", "security", "safety", "defense"],
            "eic": ["eic", "innovation", "startup", "sme"],
            "erc": ["erc", "research", "council"]
        }
        
        # Check filename first
        for cluster, keywords in cluster_keywords.items():
            if any(keyword in filename_lower for keyword in keywords):
                return cluster
        
        # Check path
        for cluster, keywords in cluster_keywords.items():
            if any(keyword in path_lower for keyword in keywords):
                return cluster
        
        return "general"
    
    def extract_year_from_filename(self, filename: str) -> str:
        """Extract programme year from filename."""
        year_pattern = r'20\d{2}[-_]20\d{2}|20\d{2}'
        match = re.search(year_pattern, filename)
        if match:
            return match.group(0)
        return "2021-2027"  # Default Horizon Europe period
    
    def chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 100) -> List[Dict[str, Any]]:
        """Split text into chunks with metadata using character-based sliding window with safety limits."""
        if not text:
            return []
        
        # Additional safety: limit total text size to prevent runaway chunking
        if len(text) > self.max_text_length:
            logger.warning(f"⚠️ Text too long for chunking ({len(text)} chars), truncating to {self.max_text_length}")
            text = text[:self.max_text_length]
        
        chunks = []
        total_chars = len(text)
        start = 0
        
        # Safety limit: prevent infinite loops
        max_iterations = total_chars // (chunk_size // 2) + 10  # Conservative estimate + buffer
        iteration_count = 0
        
        while start < total_chars:
            iteration_count += 1
            if iteration_count > max_iterations:
                logger.warning(f"⚠️ Chunking safety limit reached after {iteration_count} iterations. Stopping.")
                break
            
            # Check if we've reached the maximum chunk limit (if set)
            if self.max_chunks_per_document is not None and len(chunks) >= self.max_chunks_per_document:
                logger.warning(f"⚠️ Maximum chunks per document limit reached ({self.max_chunks_per_document})")
                break
            
            # Calculate end position, ensuring we don't exceed text length
            end = min(start + chunk_size, total_chars)
            
            # Extract chunk text
            chunk_text = text[start:end]
            
            # If we're not at the end, try to avoid cutting in the middle of a word
            if end < total_chars:
                # Find the last space or newline to avoid word breaks
                last_space = chunk_text.rfind(' ')
                last_newline = chunk_text.rfind('\n')
                last_break = max(last_space, last_newline)
                
                if last_break > chunk_size * 0.5:  # Only adjust if we have a reasonable break point
                    end = start + last_break + 1  # +1 to include the space/newline
                    chunk_text = text[start:end]
            
            chunk_data = {
                "content": chunk_text,
                "chunk_index": len(chunks),
                "word_count": len(chunk_text.split()),
                "char_count": len(chunk_text),
                "start_char": start,
                "end_char": end
            }
            
            chunks.append(chunk_data)
            
            # Calculate next start position with overlap
            next_start = end - overlap
            
            # Ensure we're making progress to prevent infinite loops
            if next_start <= start:
                next_start = start + 1  # Force forward progress
                
            start = next_start
        
        return chunks
    
    def process_document(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """Process a single document and return structured data with extensive logging."""
        if not filepath.exists():
            logger.warning(f"⚠️ File does not exist: {filepath}")
            return None

        filename = filepath.name
        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        
        # Check file size before processing - skip large files entirely
        if file_size_mb > self.max_file_size_mb:
            logger.warning(f"⚠️ File too large ({file_size_mb:.2f}MB > {self.max_file_size_mb}MB), skipping: {filename}")
            return None
        
        # Check memory before processing
        if not self.check_memory_usage():
            logger.warning(f"⚠️ Memory threshold exceeded before processing {filename}. Skipping for safety.")
            return None
            
        logger.info(f"📄 START Processing: {filename} (Size: {file_size_mb:.2f} MB)")
        logger.info(f"   🧠 Memory check passed. Proceeding with extraction.")
        
        start_time = time.time()
        
        try:
            # Extract text based on file type
            if filepath.suffix.lower() == '.pdf':
                logger.info(f"   📖 Extracting text from PDF...")
                text = self.extract_text_from_pdf(filepath)
            elif filepath.suffix.lower() == '.html':
                logger.info(f"   📖 Extracting text from HTML...")
                text = self.extract_text_from_html(filepath)
            else:
                logger.warning(f"⚠️ Unsupported file type: {filepath.suffix}")
                return None
            
            if not text:
                logger.warning(f"⚠️ No text extracted from: {filename}")
                return None
            
            # Limit text length to prevent memory issues
            if len(text) > self.max_text_length:
                logger.warning(f"⚠️ Text too long ({len(text)} chars), truncating to {self.max_text_length} chars")
                text = text[:self.max_text_length]
            
            logger.info(f"   ✅ Text extracted: {len(text)} characters")
            
            # Determine document metadata
            doc_type = self.determine_document_type(filename, filepath)
            cluster = self.determine_cluster(filename, filepath)
            programme_year = self.extract_year_from_filename(filename)
            
            logger.info(f"   📋 Metadata: Type={doc_type}, Cluster={cluster}, Year={programme_year}")
            
            # Create chunks
            logger.info(f"   ✂️ Chunking text...")
            chunks = self.chunk_text(text)
            
            # Limit chunks per document (only if limit is set)
            if self.max_chunks_per_document is not None and len(chunks) > self.max_chunks_per_document:
                logger.warning(f"⚠️ Too many chunks ({len(chunks)}), limiting to {self.max_chunks_per_document}")
                chunks = chunks[:self.max_chunks_per_document]
            
            logger.info(f"   ✅ Created {len(chunks)} chunks")
            
            # Build document metadata
            document_metadata = {
                "filename": filename,
                "filepath": str(filepath),
                "file_size": filepath.stat().st_size,
                "file_type": filepath.suffix.lower(),
                "document_type": doc_type,
                "cluster": cluster,
                "cluster_name": self.cluster_mapping.get(cluster, "Unknown"),
                "programme_year": programme_year,
                "processing_date": datetime.now().isoformat(),
                "total_chunks": len(chunks),
                "total_words": len(text.split()),
                "total_characters": len(text)
            }
            
            # For call pages, try to extract additional metadata
            if doc_type == "call_page" and "call_" in filename.lower():
                call_id = filename.replace("call_", "").replace(".html", "")
                document_metadata["call_identifier"] = call_id
                logger.info(f"   📞 Call ID extracted: {call_id}")
            
            result = {
                "metadata": document_metadata,
                "chunks": chunks,
                "full_text": text[:5000] + "..." if len(text) > 5000 else text  # Keep truncated full text
            }
            
            processing_time = time.time() - start_time
            logger.info(f"   ✅ FINISHED Processing: {filename} in {processing_time:.2f}s")
            
            # Force garbage collection after processing each document
            self.safe_garbage_collection()
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ ERROR Processing {filename} after {processing_time:.2f}s: {e}")
            logger.exception("Full traceback:")  # Log full traceback for debugging
            # Force garbage collection even on error
            self.safe_garbage_collection()
            return None
    
    def process_all_documents(self) -> Dict[str, Any]:
        """Process all documents in the comprehensive download directory incrementally to avoid memory issues."""
        logger.info("🚀 STARTING COMPREHENSIVE DOCUMENT PROCESSING")
        logger.info("📊 Memory safety settings: Threshold=%dMB, Max chunks/doc=%s",
                    self.memory_threshold_mb, 
                    "unlimited" if self.max_chunks_per_document is None else self.max_chunks_per_document)
        
        total_start_time = time.time()
        processed_count = 0
        total_chunks = 0
        stats = {
            "total_documents_processed": 0,
            "total_chunks_created": 0,
            "processing_date": datetime.now().isoformat(),
            "document_types_processed": {},
            "clusters_processed": {}
        }
        
        # Process each subdirectory
        subdirectories = [
            "work_programmes",
            "programme_guides",
            "call_pages",
            "additional_resources"
        ]
        
        # File to save processed documents incrementally
        processed_file = self.processed_dir / "processed_documents.json"
        
        # Start with an empty dictionary if file doesn't exist
        if processed_file.exists():
            logger.info("📁 Loading existing processed documents file...")
            try:
                with open(processed_file, 'r', encoding='utf-8') as f:
                    all_processed_docs = json.load(f)
                # Update stats from existing file
                processed_count = len(all_processed_docs)
                for doc in all_processed_docs.values():
                    total_chunks += len(doc["chunks"])
                    doc_type = doc["metadata"]["document_type"]
                    cluster = doc["metadata"]["cluster"]
                    stats["document_types_processed"][doc_type] = stats["document_types_processed"].get(doc_type, 0) + 1
                    stats["clusters_processed"][cluster] = stats["clusters_processed"].get(cluster, 0) + 1
                logger.info("📊 Loaded %d previously processed documents with %d chunks", processed_count, total_chunks)
            except Exception as e:
                logger.error("❌ Error loading existing processed file: %s", e)
                all_processed_docs = {}
        else:
            logger.info("📁 No existing processed file found. Starting fresh.")
            all_processed_docs = {}
        
        # Log initial memory state
        self.check_memory_usage()
        
        for subdir in subdirectories:
            subdir_path = self.base_download_dir / subdir
            if not subdir_path.exists():
                logger.warning("⚠️ Subdirectory not found: %s", subdir)
                continue
            
            logger.info("")
            logger.info("📂 PROCESSING SUBDIRECTORY: %s", subdir.upper())
            logger.info("📁 Path: %s", subdir_path)
            
            files = list(subdir_path.glob("*"))
            logger.info("📄 Found %d files in %s", len(files), subdir)
            
            subdir_processed = 0
            subdir_chunks = 0
            
            for filepath in files:
                if filepath.is_file():
                    doc_key = f"{subdir}_{filepath.name}"
                    
                    # Pre-check file size before memory check
                    file_size_mb = filepath.stat().st_size / (1024 * 1024)
                    if file_size_mb > self.max_file_size_mb:
                        logger.warning("⚠️ Skipping large file ({:.2f}MB > {:.2f}MB): %s", 
                                     file_size_mb, self.max_file_size_mb, filepath.name)
                        continue
                    
                    # Check memory before each file with more aggressive handling
                    if not self.check_memory_usage():
                        logger.warning("⚠️ Memory threshold exceeded. Forcing garbage collection...")
                        self.safe_garbage_collection()
                        time.sleep(3)
                        
                        if not self.check_memory_usage():
                            logger.error("❌ Memory still too high after garbage collection. STOPPING processing for safety.")
                            logger.error("❌ Consider restarting the script or increasing system memory.")
                            return {
                                "success": False,
                                "processed_documents": processed_count,
                                "total_chunks": total_chunks,
                                "error": "Memory threshold exceeded"
                            }
                    
                    # Skip if already processed
                    if doc_key in all_processed_docs:
                        logger.info("⏭️ Skipping already processed: %s", filepath.name)
                        continue
                    
                    logger.info("")
                    logger.info("📄 NEXT FILE: %s", filepath.name)
                    
                    processed_doc = self.process_document(filepath)
                    if processed_doc:
                        all_processed_docs[doc_key] = processed_doc
                        processed_count += 1
                        subdir_processed += 1
                        chunk_count = len(processed_doc["chunks"])
                        total_chunks += chunk_count
                        subdir_chunks += chunk_count
                        
                        # Update stats
                        doc_type = processed_doc["metadata"]["document_type"]
                        cluster = processed_doc["metadata"]["cluster"]
                        stats["document_types_processed"][doc_type] = stats["document_types_processed"].get(doc_type, 0) + 1
                        stats["clusters_processed"][cluster] = stats["clusters_processed"].get(cluster, 0) + 1
                        
                        # Save incrementally after each document with backup
                        try:
                            # Create backup of existing file first
                            backup_file = processed_file.with_suffix('.json.backup')
                            if processed_file.exists():
                                processed_file.rename(backup_file)
                            
                            # Write new file
                            with open(processed_file, 'w', encoding='utf-8') as f:
                                json.dump(all_processed_docs, f, indent=2, ensure_ascii=False)
                            
                            # Remove backup on successful save
                            if backup_file.exists():
                                backup_file.unlink()
                                
                            logger.info("💾 Progress saved: %s (%d chunks)", filepath.name, chunk_count)
                        except Exception as e:
                            logger.error("❌ Error saving progress: %s", e)
                            # Restore backup if save failed
                            backup_file = processed_file.with_suffix('.json.backup')
                            if backup_file.exists() and not processed_file.exists():
                                backup_file.rename(processed_file)
                                logger.info("📁 Restored backup file after save error")
                        
                        # Force garbage collection after each document and longer delay
                        self.safe_garbage_collection()
                        time.sleep(2)  # Increased delay for system recovery
                    else:
                        logger.warning("⚠️ Failed to process: %s", filepath.name)
            
            logger.info("✅ Finished %s: %d documents, %d chunks", subdir, subdir_processed, subdir_chunks)
        
        # Load and process call metadata
        logger.info("")
        logger.info("📋 Processing call metadata...")
        call_metadata = self.load_call_metadata()
        if call_metadata:
            metadata_file = self.processed_dir / "call_metadata_enhanced.json"
            try:
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(call_metadata, f, indent=2, ensure_ascii=False)
                logger.info("💾 Saved enhanced call metadata to: %s", metadata_file)
            except Exception as e:
                logger.error("❌ Error saving call metadata: %s", e)
        
        # Update final stats
        stats["total_documents_processed"] = processed_count
        stats["total_chunks_created"] = total_chunks
        
        # Save final statistics
        stats_file = self.processed_dir / "processing_stats.json"
        try:
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            logger.info("💾 Saved processing statistics to: %s", stats_file)
        except Exception as e:
            logger.error("❌ Error saving statistics: %s", e)
        
        total_time = time.time() - total_start_time
        logger.info("")
        logger.info("🎉 COMPREHENSIVE PROCESSING COMPLETED!")
        logger.info("📊 FINAL SUMMARY:")
        logger.info("✅ Documents processed: %d", processed_count)
        logger.info("📝 Total chunks created: %d", total_chunks)
        logger.info("⏱️ Total processing time: %.2f seconds", total_time)
        logger.info("📁 Processed data saved to: %s", self.processed_dir)
        
        # Log document type distribution
        logger.info("")
        logger.info("📈 DOCUMENT TYPE DISTRIBUTION:")
        for doc_type, count in stats["document_types_processed"].items():
            logger.info("   %s: %d documents", doc_type, count)
        
        # Log cluster distribution
        logger.info("")
        logger.info("📈 CLUSTER DISTRIBUTION:")
        for cluster, count in stats["clusters_processed"].items():
            logger.info("   %s: %d documents", cluster, count)
        
        return {
            "success": True,
            "processed_documents": processed_count,
            "total_chunks": total_chunks,
            "stats": stats
        }
    
    def prepare_for_ingestion(self):
        """Prepare processed documents for vector database ingestion."""
        logger.info("🔄 Preparing documents for vector database ingestion...")
        
        processed_file = self.processed_dir / "processed_documents.json"
        if not processed_file.exists():
            logger.error("❌ Processed documents file not found. Run processing first.")
            return False
        
        try:
            with open(processed_file, 'r', encoding='utf-8') as f:
                all_docs = json.load(f)
            
            # Create ingestion-ready format
            ingestion_data = []
            
            for doc_key, doc_data in all_docs.items():
                metadata = doc_data["metadata"]
                
                for chunk_idx, chunk in enumerate(doc_data["chunks"]):
                    ingestion_item = {
                        "id": f"{doc_key}_chunk_{chunk_idx}",
                        "content": chunk["content"],
                        "metadata": {
                            **metadata,
                            "chunk_index": chunk_idx,
                            "chunk_word_count": chunk["word_count"],
                            "chunk_char_count": chunk["char_count"],
                            "start_char": chunk["start_char"],
                            "end_char": chunk["end_char"],
                            "source_document": doc_key
                        }
                    }
                    ingestion_data.append(ingestion_item)
            
            # Save ingestion-ready data
            ingestion_file = self.processed_dir / "ingestion_ready.jsonl"
            with open(ingestion_file, 'w', encoding='utf-8') as f:
                for item in ingestion_data:
                    f.write(json.dumps(item) + '\n')
            
            logger.info(f"✅ Prepared {len(ingestion_data)} chunks for ingestion")
            logger.info(f"📁 Ingestion file: {ingestion_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error preparing for ingestion: {e}")
            return False

def main():
    """Main function to run comprehensive document processing with safety checks."""
    logger.info("🚀 STARTING DOCUMENT PROCESSING - 32GB RAM OPTIMIZED")
    
    # Check required libraries first
    missing_libs = []
    try:
        from pdfminer.high_level import extract_text
        logger.info("✅ pdfminer available - preferred PDF extraction")
    except ImportError:
        try:
            import PyPDF2
            logger.info("✅ PyPDF2 available - fallback PDF extraction")
        except ImportError:
            missing_libs.append("PyPDF2 or pdfminer.six")
    
    try:
        from bs4 import BeautifulSoup
        logger.info("✅ BeautifulSoup available")
    except ImportError:
        missing_libs.append("beautifulsoup4")
    
    if missing_libs:
        logger.error(f"❌ Missing required libraries: {', '.join(missing_libs)}")
        logger.error("❌ Install with: pip install " + " ".join(missing_libs))
        return False
    
    # Check if psutil is available for better memory monitoring
    if not PSUTIL_AVAILABLE:
        logger.warning("⚠️ psutil not available - running with limited memory monitoring")
        logger.warning("⚠️ Install psutil for better memory safety: pip install psutil")
    
    # Initial memory check
    try:
        if PSUTIL_AVAILABLE:
            memory_info = psutil.virtual_memory()
            available_mb = memory_info.available / (1024 * 1024)
            total_mb = memory_info.total / (1024 * 1024)
            logger.info(f"💾 System Memory: {available_mb:.0f}MB available / {total_mb:.0f}MB total")
            
            if available_mb < 2048:  # Less than 2GB available
                logger.error(f"❌ Insufficient system memory ({available_mb:.0f}MB available)")
                logger.error("❌ Recommend having at least 2GB available memory before running")
                return False
    except Exception as e:
        logger.warning(f"⚠️ Could not check initial memory state: {e}")
    
    try:
        processor = ComprehensiveDocumentProcessor()
        
        # Process all documents
        result = processor.process_all_documents()
        
        if result.get("success"):
            # Prepare for ingestion
            ingestion_success = processor.prepare_for_ingestion()
            
            if ingestion_success:
                logger.info("🎉 Comprehensive document processing completed!")
                logger.info("\n💡 Next steps:")
                logger.info("1. Ingest documents into vector database: python scripts/ingest_comprehensive_docs.py")
                logger.info("2. Enhance RAG system for call-specific queries")
                logger.info("3. Test with various call and topic questions")
                return True
        else:
            logger.error(f"💥 Document processing failed: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        logger.error(f"💥 Unexpected error during processing: {e}")
        logger.exception("Full error traceback:")
    
    return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)