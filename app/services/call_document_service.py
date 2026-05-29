"""
On-Demand Call Document Service

Automatically fetches, processes, and maps documents for a specific call.

Flow:
1. User asks about call X
2. Check if call X already has documents mapped
3. If not: API call → extract doc URLs → download → process → map
4. If yes: return cached chunks

This eliminates all manual work!
"""

import hashlib
import json
import logging
import re
from pathlib import Path

import requests
from psycopg2.extras import Json

from ..core.config import settings

logger = logging.getLogger(__name__)


class CallDocumentService:
    """Automatic document fetching and processing for calls"""

    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.base_api_url = settings.eu_portal_base_url
        self.shared_docs_dir = Path("data/shared_documents")
        self.shared_docs_dir.mkdir(parents=True, exist_ok=True)

    def get_call_documents(self, call_identifier: str, force_refresh: bool = False) -> dict:
        """
        Get documents for a call - automatically fetch if not cached.

        Returns:
            {
                'call_identifier': str,
                'documents_count': int,
                'chunks_count': int,
                'cached': bool,  # True if already in DB, False if just fetched
                'documents': [...]
            }
        """

        # Check if already mapped
        if not force_refresh:
            cached = self._check_if_mapped(call_identifier)
            if cached:
                logger.info(f"✅ Call {call_identifier} already mapped - using cache")
                return {
                    "call_identifier": call_identifier,
                    "documents_count": cached["doc_count"],
                    "chunks_count": cached["chunk_count"],
                    "cached": True,
                    "documents": cached["documents"],
                }

        # Not cached - fetch and process
        logger.info(f"🔄 Call {call_identifier} not cached - fetching from API")

        try:
            # Step 1: Fetch call data from API
            call_data = self._fetch_call_from_api(call_identifier)

            if not call_data:
                logger.error(f"❌ Call {call_identifier} not found in API")
                return None

            # Step 1.5: Extract and store structured metadata
            self._extract_and_store_call_metadata(call_identifier, call_data)

            # Step 2: Extract document URLs
            doc_urls = self._extract_document_urls(call_data)
            logger.info(f"📋 Found {len(doc_urls)} document URLs from API")

            # Step 3: Download and process documents
            processed_docs = []
            for doc_url in doc_urls:
                doc_id = self._download_and_process_document(doc_url)
                if doc_id:
                    processed_docs.append(doc_id)

            # Step 3.5: SMART FIX - Automatically add cluster-specific Work Programme
            # Even if the API didn't return it
            cluster_doc_id = self._ensure_cluster_work_programme(call_identifier)
            if cluster_doc_id and cluster_doc_id not in processed_docs:
                processed_docs.append(cluster_doc_id)
                logger.info("✅ Added cluster-specific Work Programme (not in API response)")

            # Step 4: Create mappings
            self._create_mappings(call_identifier, processed_docs)

            # Step 5: Return result
            result = self._check_if_mapped(call_identifier)
            if result:
                result["cached"] = False  # Just created
                result["call_identifier"] = call_identifier
                result["documents_count"] = result.pop("doc_count")
                result["chunks_count"] = result.pop("chunk_count")
                logger.info(
                    f"✅ Successfully processed {len(processed_docs)} documents for {call_identifier}"
                )
                return result
            else:
                logger.error(f"❌ Failed to verify mappings for {call_identifier}")
                return None

        except Exception as e:
            logger.error(f"❌ Error processing call {call_identifier}: {e}", exc_info=True)
            return None

    def _check_if_mapped(self, call_identifier: str) -> dict | None:
        """Check if call already has documents mapped"""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(DISTINCT cdm.document_id) as doc_count,
                    COUNT(DISTINCT sdc.id) as chunk_count
                FROM call_document_mappings cdm
                LEFT JOIN shared_document_chunks sdc ON cdm.document_id = sdc.document_id
                WHERE cdm.call_identifier = %s
            """,
                (call_identifier,),
            )

            result = cursor.fetchone()

            if not result or result[0] == 0:
                return None

            # Get document details
            cursor.execute(
                """
                SELECT
                    sd.id,
                    sd.document_key,
                    sd.document_type,
                    sd.document_title
                FROM call_document_mappings cdm
                JOIN shared_documents sd ON cdm.document_id = sd.id
                WHERE cdm.call_identifier = %s
            """,
                (call_identifier,),
            )

            documents = [
                {"id": row[0], "key": row[1], "type": row[2], "title": row[3]}
                for row in cursor.fetchall()
            ]

            return {"doc_count": result[0], "chunk_count": result[1], "documents": documents}

        finally:
            self.db_pool.putconn(conn)

    def _fetch_call_from_api(self, call_identifier: str) -> dict | None:
        """Fetch call data from EU Portal API"""

        try:
            # Build the multipart form data
            boundary = (
                "----WebKitFormBoundary" + hashlib.md5(call_identifier.encode()).hexdigest()[:16]
            )

            query_json = json.dumps(
                {
                    "bool": {
                        "must": [
                            {"terms": {"type": ["1"]}},
                            {"term": {"identifier": call_identifier}},
                        ]
                    }
                }
            )

            languages_json = json.dumps(["en"])

            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="query"; filename="blob"\r\n'
                f"Content-Type: application/json\r\n\r\n"
                f"{query_json}\r\n"
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="languages"; filename="blob"\r\n'
                f"Content-Type: application/json\r\n\r\n"
                f"{languages_json}\r\n"
                f"--{boundary}--\r\n"
            )

            headers = {
                "Accept": "application/json, text/plain, */*",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Origin": "https://ec.europa.eu",
                "Referer": "https://ec.europa.eu/",
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            }

            response = requests.post(
                f"{self.base_api_url}?apiKey=SEDIA&text=***",
                headers=headers,
                data=body.encode("utf-8"),
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            if data.get("totalResults", 0) > 0 and data.get("results"):
                return data["results"][0]

            return None

        except Exception as e:
            logger.error(f"API request failed for {call_identifier}: {e}")
            return None

    def _extract_and_store_call_metadata(self, call_identifier: str, call_data: dict):
        """Extract structured metadata from API response and store in database"""

        try:
            from bs4 import BeautifulSoup

            metadata = call_data.get("metadata", {})

            # Extract basic info
            title = (
                metadata.get("title", [call_data.get("summary", "")])[0]
                if metadata.get("title")
                else call_data.get("summary", "")
            )
            summary = call_data.get("summary", "")
            call_title = metadata.get("callTitle", [""])[0] if metadata.get("callTitle") else ""
            status = metadata.get("status", [""])[0] if metadata.get("status") else ""

            # Extract dates
            deadline_date = None
            opening_date = None
            if metadata.get("deadlineDate"):
                deadline_date = metadata["deadlineDate"][0]
            if metadata.get("startDate"):
                opening_date = metadata["startDate"][0]

            # Parse topicConditions HTML for eligibility
            topic_conditions_html = metadata.get("topicConditions", [""])[0]
            eligible_countries = None
            eligibility_restrictions = None

            if topic_conditions_html:
                soup = BeautifulSoup(topic_conditions_html, "html.parser")

                # Find "Eligible Countries" or "Other Eligible Conditions" section
                for heading in soup.find_all(["h4", "h3"]):
                    heading_text = heading.get_text().strip()

                    if "eligible" in heading_text.lower():
                        # Get the text after this heading
                        next_div = heading.find_next("div")
                        if next_div:
                            text = next_div.get_text(strip=True)

                            # Extract key phrases
                            if "member states and associated countries" in text.lower():
                                eligible_countries = "Member States and Associated Countries"
                            elif "member states" in text.lower():
                                eligible_countries = "Member States only"

                            if "controlled by a non-eligible country" in text.lower():
                                eligibility_restrictions = (
                                    "Entities controlled by non-eligible countries are excluded"
                                )

            # Extract budget info
            budget_overview = metadata.get("budgetOverview", [None])[0]

            # Parse budget if available
            min_contribution = None
            max_contribution = None
            expected_grants = None

            if budget_overview and isinstance(budget_overview, str):
                try:
                    budget_data = json.loads(budget_overview)
                    # Extract from first action in budgetTopicActionMap
                    for actions in budget_data.get("budgetTopicActionMap", {}).values():
                        if actions and len(actions) > 0:
                            action = actions[0]
                            min_contribution = action.get("minContribution")
                            max_contribution = action.get("maxContribution")
                            expected_grants = action.get("expectedGrants")
                            break
                except Exception:
                    pass

            # Extract arrays
            types_of_action = metadata.get("typesOfAction", [])
            cross_cutting_priorities = metadata.get("crossCuttingPriorities", [])
            tags = metadata.get("tags", [])
            keywords = metadata.get("keywords", [])

            # URLs
            topic_url = (
                metadata.get("url", [""])[0] if metadata.get("url") else call_data.get("url", "")
            )

            # Store in database
            conn = self.db_pool.getconn()
            try:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO call_metadata (
                        call_identifier, title, summary, call_title, status,
                        opening_date, deadline_date,
                        budget_overview, min_contribution, max_contribution, expected_grants,
                        eligible_countries, eligibility_restrictions, eligibility_conditions_html,
                        types_of_action, cross_cutting_priorities, tags, keywords,
                        topic_url, api_data_url, raw_api_response,
                        fetched_at, last_updated
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        NOW(), NOW()
                    )
                    ON CONFLICT (call_identifier)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        summary = EXCLUDED.summary,
                        eligible_countries = EXCLUDED.eligible_countries,
                        eligibility_restrictions = EXCLUDED.eligibility_restrictions,
                        eligibility_conditions_html = EXCLUDED.eligibility_conditions_html,
                        deadline_date = EXCLUDED.deadline_date,
                        last_updated = NOW()
                """,
                    (
                        call_identifier,
                        title,
                        summary,
                        call_title,
                        status,
                        opening_date,
                        deadline_date,
                        Json(budget_overview) if budget_overview else None,
                        min_contribution,
                        max_contribution,
                        expected_grants,
                        eligible_countries,
                        eligibility_restrictions,
                        topic_conditions_html,
                        types_of_action,
                        cross_cutting_priorities,
                        tags,
                        keywords,
                        topic_url,
                        call_data.get("url", ""),
                        Json(call_data),
                    ),
                )

                conn.commit()
                cursor.close()
                logger.info(f"✅ Stored structured metadata for {call_identifier}")
                logger.info(f"   Eligibility: {eligible_countries}")
                logger.info(
                    f"   Budget: €{min_contribution:,} - €{max_contribution:,}"
                    if min_contribution
                    else "   Budget: Not specified"
                )

            finally:
                self.db_pool.putconn(conn)

        except Exception as e:
            logger.error(f"❌ Failed to extract/store call metadata: {e}")

    def _extract_document_urls(self, call_data: dict) -> list[dict]:
        """Extract document URLs from API response"""

        doc_urls = []

        try:
            # Parse topicConditions HTML to extract document links
            topic_conditions = call_data.get("metadata", {}).get("topicConditions", [""])[0]

            # Find all PDF links in the HTML
            pdf_pattern = r'href="(https://ec\.europa\.eu/[^"]+\.pdf)"[^>]*>([^<]+)</a>'
            matches = re.findall(pdf_pattern, topic_conditions, re.IGNORECASE)

            for url, title in matches:
                doc_info = self._classify_document_from_url(url, title)
                doc_urls.append(
                    {
                        "url": url,
                        "title": title.strip(),
                        "type": doc_info["type"],
                        "scope": doc_info["scope"],
                        "scope_identifier": doc_info.get("scope_identifier"),
                    }
                )

            # Deduplicate by URL
            seen_urls = set()
            unique_docs = []
            for doc in doc_urls:
                if doc["url"] not in seen_urls:
                    seen_urls.add(doc["url"])
                    unique_docs.append(doc)

            return unique_docs

        except Exception as e:
            logger.error(f"Failed to extract document URLs: {e}")
            return []

    def _classify_document_from_url(self, url: str, title: str) -> dict:
        """Classify document type and scope from URL and title"""

        url_lower = url.lower()
        title_lower = title.lower()

        # Detect type
        if "general-annex" in url_lower or "wp-13" in url_lower:
            return {
                "type": "general_annexes",
                "scope": "global",
                "key": "he_general_annexes_2023-2025",
            }
        elif "programme-guide" in url_lower:
            return {"type": "programme_guide", "scope": "global", "key": "he_programme_guide"}
        elif "wp-" in url_lower or "work" in title_lower and "programme" in title_lower:
            # Extract cluster number
            cluster_match = re.search(r"wp-(\d+)", url_lower)
            if cluster_match:
                cluster_num = cluster_match.group(1)
                return {
                    "type": "work_programme",
                    "scope": "cluster",
                    "scope_identifier": f"CLUSTER-{cluster_num}",
                    "key": f"he_wp_cluster{cluster_num}_2023-2025",
                }
        elif "mga" in url_lower or "grant" in url_lower and "agreement" in url_lower:
            if "annotated" in url_lower or "aga" in url_lower:
                return {
                    "type": "annotated_grant_agreement",
                    "scope": "global",
                    "key": "he_annotated_grant_agreement",
                }
            else:
                return {
                    "type": "model_grant_agreement",
                    "scope": "global",
                    "key": "he_model_grant_agreement",
                }

        # Default: other
        return {
            "type": "other",
            "scope": "unknown",
            "key": hashlib.md5(url.encode()).hexdigest()[:16],
        }

    def _download_and_process_document(self, doc_info: dict) -> int | None:
        """Download and process a document, return document ID"""

        url = doc_info["url"]
        doc_key = doc_info.get("key", hashlib.md5(url.encode()).hexdigest()[:16])

        try:
            # Check if already exists by URL
            doc_id = self._check_document_exists(url)
            if doc_id:
                logger.info(f"⏭️  Document already exists: {doc_key}")
                return doc_id

            # Download PDF
            logger.info(f"📥 Downloading: {doc_info['title']}")
            file_path = self.shared_docs_dir / f"{doc_key}.pdf"

            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()

            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = file_path.stat().st_size / (1024 * 1024)
            logger.info(f"✅ Downloaded {file_size:.2f} MB")

            # Compute hash
            file_hash = self._compute_file_hash(file_path)

            # Parse and chunk
            from scripts.manual_document_upload import SimpleChunker, SimpleDocumentParser

            parser = SimpleDocumentParser()
            parsed = parser.parse_pdf(file_path)

            chunker = SimpleChunker()
            chunks = chunker.chunk_document(parsed, doc_key, doc_info["type"])

            logger.info(f"✅ Created {len(chunks)} chunks")

            # Store in database
            doc_id = self._store_document(
                doc_key=doc_key,
                doc_type=doc_info["type"],
                doc_title=doc_info["title"],
                scope=doc_info["scope"],
                scope_identifier=doc_info.get("scope_identifier"),
                file_path=str(file_path),
                file_hash=file_hash,
                url=url,
                parsed=parsed,
                chunks=chunks,
            )

            logger.info(f"✅ Stored document (ID: {doc_id})")
            return doc_id

        except Exception as e:
            logger.error(f"Failed to process document {url}: {e}", exc_info=True)
            return None

    def _check_document_exists(self, url: str) -> int | None:
        """Check if document already exists by URL"""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM shared_documents WHERE document_url = %s
            """,
                (url,),
            )
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            self.db_pool.putconn(conn)

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def _store_document(
        self,
        doc_key: str,
        doc_type: str,
        doc_title: str,
        scope: str,
        scope_identifier: str | None,
        file_path: str,
        file_hash: str,
        url: str,
        parsed: dict,
        chunks: list,
    ) -> int:
        """Store document and chunks in database"""
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO shared_documents (
                    document_key, document_type, document_title,
                    document_version, scope, scope_identifier,
                    document_content, document_url, file_path, file_hash,
                    last_updated, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
                ON CONFLICT (document_key) DO UPDATE SET
                    document_content = EXCLUDED.document_content,
                    document_url = EXCLUDED.document_url,
                    file_hash = EXCLUDED.file_hash,
                    last_updated = NOW()
                RETURNING id
            """,
                (
                    doc_key,
                    doc_type,
                    doc_title,
                    "2023-2025",
                    scope,
                    scope_identifier,
                    parsed["full_text"],
                    url,
                    file_path,
                    file_hash,
                    Json({"page_count": parsed["metadata"].get("page_count", 0)}),
                ),
            )

            document_id = cursor.fetchone()[0]

            # Delete old chunks
            cursor.execute(
                "DELETE FROM shared_document_chunks WHERE document_id = %s", (document_id,)
            )

            # Insert chunks
            for chunk in chunks:
                cursor.execute(
                    """
                    INSERT INTO shared_document_chunks (
                        document_id, chunk_text, chunk_index,
                        token_count, section_title, page_numbers, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        document_id,
                        chunk["text"],
                        chunk["chunk_index"],
                        chunk["token_count"],
                        chunk.get("section_title"),
                        chunk.get("page_numbers", []),
                        Json(chunk.get("metadata", {})),
                    ),
                )

            conn.commit()
            return document_id

        except Exception:
            conn.rollback()
            raise
        finally:
            self.db_pool.putconn(conn)

    def _create_mappings(self, call_identifier: str, document_ids: list[int]):
        """Create call-to-document mappings"""
        if not document_ids:
            return

        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()

            for doc_id in document_ids:
                # Determine if primary (work programme for this cluster)
                cursor.execute(
                    """
                    SELECT scope, scope_identifier FROM shared_documents WHERE id = %s
                """,
                    (doc_id,),
                )
                scope, scope_id = cursor.fetchone()

                # Check if this doc's cluster matches call's cluster
                call_cluster = self._extract_cluster_from_call_id(call_identifier)
                is_primary = scope == "cluster" and scope_id == call_cluster

                cursor.execute(
                    """
                    INSERT INTO call_document_mappings (
                        call_identifier, document_id, relevance_score,
                        is_primary, mapping_source
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (call_identifier, document_id) DO NOTHING
                """,
                    (call_identifier, doc_id, 1.0, is_primary, "auto"),
                )

            conn.commit()
            logger.info(f"✅ Created {len(document_ids)} mappings for {call_identifier}")

        except Exception:
            conn.rollback()
            raise
        finally:
            self.db_pool.putconn(conn)

    def _extract_cluster_from_call_id(self, call_id: str) -> str | None:
        """Extract cluster from call ID"""
        match = re.search(r"CL(\d+)", call_id, re.IGNORECASE)
        if match:
            return f"CLUSTER-{match.group(1)}"
        return None

    def _ensure_cluster_work_programme(self, call_identifier: str) -> int | None:
        """
        Ensure cluster-specific work programme is available and return its document_id.
        Looks for patterns like: "HE Main Work Programme 2023–2025 – X. [Cluster Name]"
        where X matches the cluster number from the call ID.
        """
        # Extract cluster number from call ID (e.g., CL3 → 3)
        cluster_match = re.search(r"CL(\d+)", call_identifier, re.IGNORECASE)
        if not cluster_match:
            logger.info(f"No cluster detected in call ID: {call_identifier}")
            return None

        cluster_num = cluster_match.group(1)

        # Map cluster numbers to work programme patterns
        # Format: "HE Main Work Programme 2023–2025 – {cluster_num}. {cluster_name}"
        cluster_patterns = {
            "1": "Health",
            "2": "Culture",  # Full: Culture, creativity and inclusive society
            "3": "Civil",  # Full: Civil Security for Society
            "4": "Digital",  # Full: Digital, Industry and Space
            "5": "Climate",  # Full: Climate, Energy and Mobility
            "6": "Food",  # Full: Food, Bioeconomy, Natural Resources...
        }

        # Search for cluster-specific work programme in database
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()

            # Try to find the cluster-specific WP
            pattern = f"%Work Programme%{cluster_num}%"
            if cluster_num in cluster_patterns:
                pattern_with_name = (
                    f"%Work Programme%{cluster_num}%{cluster_patterns[cluster_num]}%"
                )
            else:
                pattern_with_name = pattern

            cursor.execute(
                """
                SELECT id FROM shared_documents
                WHERE document_title ILIKE %s
                   OR document_title ILIKE %s
                ORDER BY document_title
                LIMIT 1
            """,
                (pattern, pattern_with_name),
            )

            result = cursor.fetchone()
            if result:
                doc_id = result[0]
                logger.info(f"✅ Found cluster {cluster_num} work programme (ID: {doc_id})")
                return doc_id
            else:
                logger.warning(f"⚠️ Cluster {cluster_num} work programme not in database")
                logger.info(
                    f"💡 You'll need to manually download and add: 'HE WP Cluster {cluster_num}'"
                )
                return None

        finally:
            self.db_pool.putconn(conn)

    def get_call_metadata(self, call_identifier: str) -> dict | None:
        """
        Get structured metadata for a call (eligibility, budget, deadlines, etc.)
        This is FAST and gives instant answers without searching PDFs.

        Returns:
            {
                'call_identifier': str,
                'title': str,
                'summary': str,
                'eligible_countries': str,  # e.g., "Member States and Associated Countries"
                'eligibility_restrictions': str,  # Any special restrictions
                'deadline_date': str,
                'min_contribution': int,
                'max_contribution': int,
                ...
            }
        """

        try:
            conn = self.db_pool.getconn()
            try:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT
                        call_identifier, title, summary, call_title, status,
                        opening_date, deadline_date,
                        min_contribution, max_contribution, expected_grants,
                        eligible_countries, eligibility_restrictions,
                        types_of_action, cross_cutting_priorities, tags, keywords,
                        topic_url
                    FROM call_metadata
                    WHERE call_identifier = %s
                """,
                    (call_identifier,),
                )

                row = cursor.fetchone()
                cursor.close()

                if row:
                    return {
                        "call_identifier": row[0],
                        "title": row[1],
                        "summary": row[2],
                        "call_title": row[3],
                        "status": row[4],
                        "opening_date": row[5],
                        "deadline_date": row[6],
                        "min_contribution": row[7],
                        "max_contribution": row[8],
                        "expected_grants": row[9],
                        "eligible_countries": row[10],
                        "eligibility_restrictions": row[11],
                        "types_of_action": row[12],
                        "cross_cutting_priorities": row[13],
                        "tags": row[14],
                        "keywords": row[15],
                        "topic_url": row[16],
                    }

                return None

            finally:
                self.db_pool.putconn(conn)

        except Exception as e:
            logger.error(f"❌ Failed to retrieve call metadata: {e}")
            return None

    def search_call_chunks(self, call_identifier: str, query: str, limit: int = 10) -> list[dict]:
        """
        Search chunks for a specific call.
        Automatically fetches documents if not cached.
        """

        # Ensure documents are available
        logger.info(f"🔎 search_call_chunks called for {call_identifier}, query: '{query}'")
        call_docs = self.get_call_documents(call_identifier)
        logger.info(f"🔎 get_call_documents returned: {call_docs}")

        if not call_docs or call_docs.get("chunks_count", 0) == 0:
            logger.warning(f"No documents available for {call_identifier}: call_docs={call_docs}")
            return []

        # Search
        logger.info(
            f"🔎 Executing DB query: get_chunks_for_call({call_identifier}, {query}, {limit})"
        )
        conn = self.db_pool.getconn()
        try:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM get_chunks_for_call(%s, %s, %s)
            """,
                (call_identifier, query, limit),
            )

            rows = cursor.fetchall()
            logger.info(f"🔎 DB query returned {len(rows)} rows")

            chunks = []
            for row in rows:
                chunks.append(
                    {
                        "chunk_id": row[0],
                        "chunk_text": row[1],
                        "section_title": row[2],
                        "document_type": row[3],
                        "document_title": row[4],
                        "relevance_score": float(row[5]),
                    }
                )

            logger.info(f"🔎 Converted to {len(chunks)} chunk dicts")
            return chunks

        finally:
            self.db_pool.putconn(conn)
