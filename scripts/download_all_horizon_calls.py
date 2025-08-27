#!/usr/bin/env python3
"""
Comprehensive script to download ALL Horizon Europe call documents and documentation.
This enables the RAG system to answer questions about ANY call or topic, past or present.
"""

import os
import sys
import requests
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, quote
import logging
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HorizonEuropeCallDownloader:
    """Comprehensive downloader for ALL Horizon Europe call documents."""
    
    def __init__(self):
        self.base_download_dir = Path("downloads/horizon_europe_comprehensive")
        self.base_download_dir.mkdir(parents=True, exist_ok=True)
        
        # EU Portal API configuration
        self.api_url = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
        self.api_params = {
            "apiKey": "SEDIA",
            "pageSize": "100",  # Maximum page size
            "pageNumber": "1",
            "language": "en"
        }
        
        # Horizon Europe programme years - dynamically generated based on current year
        current_year = datetime.now().year
        self.programme_years = []
        
        # Generate years from 2021 to 2027, and beyond if needed
        start_year = 2021
        end_year = max(2027, current_year + 2)  # Extend to current year + 2 to cover future calls
        
        for year in range(start_year, end_year + 1):
            if year == 2027:
                self.programme_years.append(str(year))
            else:
                # For ranges like 2021-2022, 2023-2024, etc.
                next_year = year + 1
                if next_year <= end_year:
                    self.programme_years.append(f"{year}-{next_year}")
        
        logger.info(f"📅 Programme years covered: {self.programme_years}")
        
        # Cluster mapping
        self.clusters = {
            "health": "Health",
            "digital_industry_space": "Digital, Industry and Space",
            "climate_energy_mobility": "Climate, Energy and Mobility",
            "food_bioeconomy": "Food, Bioeconomy, Natural Resources, Agriculture and Environment",
            "culture_creativity": "Culture, Creativity and Inclusive Society",
            "civil_security": "Civil Security for Society",
            "eic": "European Innovation Council",
            "erc": "European Research Council",
            "missions": "Missions",
            "widening": "Widening Participation and Strengthening the ERA"
        }
        
        # Document types to download
        self.document_types = [
            "work_programme",
            "call_text",
            "topic_description",
            "evaluation_manual",
            "programme_guide",
            "application_guide",
            "faq",
            "template"
        ]
    
    def download_file(self, url: str, filename: str, subdirectory: str = "") -> bool:
        """Download a file from URL to specified subdirectory."""
        try:
            download_dir = self.base_download_dir / subdirectory
            download_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = download_dir / filename
            
            # Skip if file already exists
            if file_path.exists():
                file_size = file_path.stat().st_size
                logger.info(f"⚠️ File already exists: {filename} ({file_size:,} bytes)")
                return True
            
            logger.info(f"📥 Downloading: {filename}")
            logger.info(f"   URL: {url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; HorizonEuropeRAG/1.0; +https://github.com/your-repo)',
                'Accept': 'application/pdf,text/html,application/json,*/*',
                'Referer': 'https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home'
            }
            
            response = requests.get(url, headers=headers, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = file_path.stat().st_size
            logger.info(f"✅ Downloaded: {filename} ({file_size:,} bytes)")
            
            # Be respectful to the server
            time.sleep(1)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to download {filename}: {e}")
            return False
    
    def search_eu_portal_calls(self, search_text: str = "", filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Search EU Portal for ALL Horizon Europe calls (not just open ones)."""
        all_calls = []
        page_number = 1
        
        try:
            while True:
                logger.info(f"🔍 Searching EU Portal page {page_number} for Horizon Europe calls...")
                
                # Build query to get ALL Horizon Europe calls (not filtering by status)
                query = {
                    "bool": {
                        "must": [
                            {"terms": {"type": ["1", "2", "8"]}},  # All call types
                            {"term": {"programmePeriod": "2021 - 2027"}},  # Horizon Europe period
                            {"term": {"frameworkProgramme": "HORIZON"}}  # Horizon programme
                        ]
                    }
                }
                
                # Add search text if provided
                if search_text:
                    query["bool"]["must"].append({
                        "multi_match": {
                            "query": search_text,
                            "fields": ["title", "description", "keywords", "callTitle"],
                            "type": "best_fields"
                        }
                    })
                
                # Add filters if provided
                if filters:
                    for key, value in filters.items():
                        query["bool"]["must"].append({"term": {key: value}})
                
                params = self.api_params.copy()
                params["pageNumber"] = str(page_number)
                
                response = requests.post(
                    self.api_url,
                    params=params,
                    files={
                        "query": ("blob", json.dumps(query), "application/json"),
                        "languages": ("blob", json.dumps(["en"]), "application/json"),
                        "displayFields": ("blob", json.dumps([
                            "type", "identifier", "reference", "callccm2Id", "title", "status", 
                            "caName", "identifier", "projectAcronym", "startDate", "deadlineDate", 
                            "deadlineModel", "frameworkProgramme", "typesOfAction", "callTitle",
                            "callIdentifier", "programmePeriod", "workProgrammepart", "focusArea"
                        ]), "application/json"),
                    },
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                results = data.get("results", [])
                total_results = data.get("totalResults", 0)
                
                logger.info(f"📊 Page {page_number}: Found {len(results)} calls (Total: {total_results})")
                
                if not results:
                    break
                
                # Process results
                for result in results:
                    call_data = self._extract_call_data(result)
                    if call_data:
                        all_calls.append(call_data)
                
                # Check if we have more pages
                if len(results) < int(params["pageSize"]):
                    break
                
                page_number += 1
                time.sleep(0.5)  # Be respectful to the API
                
        except Exception as e:
            logger.error(f"❌ EU Portal search failed: {e}")
        
        return all_calls
    
    def _extract_call_data(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract structured call data from API response."""
        try:
            metadata = result.get('metadata', {})
            
            # Basic call information
            call_data = {
                'identifier': metadata.get('identifier', [None])[0] if isinstance(metadata.get('identifier'), list) else None,
                'call_identifier': metadata.get('callIdentifier', [None])[0] if isinstance(metadata.get('callIdentifier'), list) else None,
                'title': metadata.get('callTitle', [None])[0] if isinstance(metadata.get('callTitle'), list) else result.get('title'),
                'description': result.get('summary') or result.get('content', ''),
                'status': self._decode_call_status(metadata.get('status', [None])[0] if isinstance(metadata.get('status'), list) else None),
                'deadline_date': metadata.get('deadlineDate', [None])[0] if isinstance(metadata.get('deadlineDate'), list) else None,
                'start_date': metadata.get('startDate', [None])[0] if isinstance(metadata.get('startDate'), list) else None,
                'programme_period': metadata.get('programmePeriod', [None])[0] if isinstance(metadata.get('programmePeriod'), list) else None,
                'framework_programme': metadata.get('frameworkProgramme', [None])[0] if isinstance(metadata.get('frameworkProgramme'), list) else None,
                'work_programme_part': metadata.get('workProgrammepart', [None])[0] if isinstance(metadata.get('workProgrammepart'), list) else None,
                'focus_area': metadata.get('focusArea', [None])[0] if isinstance(metadata.get('focusArea'), list) else None,
                'type_of_action': metadata.get('typesOfAction', [None])[0] if isinstance(metadata.get('typesOfAction'), list) else None,
                'url': self._build_call_url(metadata)
            }
            
            # Filter out non-Horizon Europe calls
            if not call_data['identifier'] or not call_data['call_identifier']:
                return None
                
            if call_data['framework_programme'] != 'HORIZON':
                return None
                
            return call_data
            
        except Exception as e:
            logger.error(f"❌ Error extracting call data: {e}")
            return None
    
    def _decode_call_status(self, status_code: str) -> str:
        """Decode status codes to readable format."""
        status_mapping = {
            '31094502': 'Open',
            '31094503': 'Closed', 
            '31094501': 'Forthcoming',
        }
        return status_mapping.get(str(status_code), f"Unknown ({status_code})")
    
    def _build_call_url(self, metadata: Dict[str, Any]) -> str:
        """Build proper EU portal URL for a call."""
        identifier = metadata.get('identifier', [None])[0] if isinstance(metadata.get('identifier'), list) else None
        if identifier:
            return f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{identifier}"
        return "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/home"
    
    def download_work_programmes(self):
        """Download all Horizon Europe Work Programmes for current and future years."""
        logger.info("📚 Downloading Horizon Europe Work Programmes...")
        
        # Base URL pattern for work programmes
        base_url = "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call"
        
        # Work programme types and their URL suffixes
        work_programme_types = [
            {
                "name": "General Introduction",
                "suffix": "wp-1-general-introduction_horizon-{year}_en.pdf",
                "filename": "work_programme_general_introduction_{year}.pdf"
            },
            {
                "name": "Health Cluster",
                "suffix": "wp-3-health_horizon-{year}_en.pdf",
                "filename": "work_programme_health_{year}.pdf"
            },
            {
                "name": "Digital, Industry and Space Cluster",
                "suffix": "wp-4-digital-industry-and-space_horizon-{year}_en.pdf",
                "filename": "work_programme_digital_industry_space_{year}.pdf"
            },
            {
                "name": "Climate, Energy and Mobility Cluster",
                "suffix": "wp-5-climate-energy-and-environment_horizon-{year}_en.pdf",
                "filename": "work_programme_climate_energy_mobility_{year}.pdf"
            },
            {
                "name": "Food, Bioeconomy Cluster",
                "suffix": "wp-7-food-bioeconomy-natural-resources-agriculture-and-environment_horizon-{year}_en.pdf",
                "filename": "work_programme_food_bioeconomy_{year}.pdf"
            },
            {
                "name": "Culture, Creativity Cluster",
                "suffix": "wp-6-culture-creativity-and-inclusive-society_horizon-{year}_en.pdf",
                "filename": "work_programme_culture_creativity_{year}.pdf"
            },
            {
                "name": "Civil Security Cluster",
                "suffix": "wp-8-civil-security-for-society_horizon-{year}_en.pdf",
                "filename": "work_programme_civil_security_{year}.pdf"
            },
            {
                "name": "EIC Work Programme",
                "suffix": "wp-9-european-innovation-council_horizon-{year}_en.pdf",
                "filename": "work_programme_eic_{year}.pdf"
            }
        ]
        
        # Use the dynamically generated programme years from initialization
        years_to_try = self.programme_years
        
        successful_downloads = 0
        total_attempts = 0
        
        for year in years_to_try:
            for wp_type in work_programme_types:
                total_attempts += 1
                url = f"{base_url}/{year}/{wp_type['suffix'].format(year=year)}"
                filename = wp_type['filename'].format(year=year)
                
                if self.download_file(url, filename, "work_programmes"):
                    successful_downloads += 1
                else:
                    logger.warning(f"⚠️ Work programme not available for {year}: {wp_type['name']}")
        
        logger.info(f"✅ Downloaded {successful_downloads}/{total_attempts} work programmes")
        return successful_downloads > 0
    
    def download_programme_guides(self):
        """Download Horizon Europe programme guides and documentation with dynamic version handling."""
        logger.info("📖 Downloading Programme Guides and Documentation...")
        
        # Base URL for programme guides
        base_url = "https://ec.europa.eu/info/funding-tenders/opportunities/docs"
        
        guide_urls = [
            {
                "name": "Horizon Europe Programme Guide",
                "path": "2021-2027/horizon/guidance/programme-guide_horizon_en.pdf",
                "filename": "programme_guide_horizon_europe.pdf"
            },
            {
                "name": "Annotated Grant Agreement",
                "path": "2021-2027/common/guidance/aga_en.pdf",
                "filename": "annotated_grant_agreement.pdf"
            },
            {
                "name": "Model Grant Agreement",
                "path": "2021-2027/common/guidance/mga_horizon_en.pdf",
                "filename": "model_grant_agreement.pdf"
            },
            {
                "name": "Evaluation Manual",
                "path": "2021-2027/common/guidance/ev_manual_horizon_en.pdf",
                "filename": "evaluation_manual.pdf"
            },
            {
                "name": "FAQs - Horizon Europe",
                "path": "2021-2027/horizon/guidance/faq_horizon_en.pdf",
                "filename": "faqs_horizon_europe.pdf"
            }
        ]
        
        successful = 0
        for doc in guide_urls:
            url = f"{base_url}/{doc['path']}"
            if self.download_file(url, doc['filename'], "programme_guides"):
                successful += 1
            else:
                # Try alternative URL patterns for future versions
                current_year = datetime.now().year
                # Try current year range pattern
                alt_path = doc['path'].replace("2021-2027", f"{current_year}-{current_year+1}")
                alt_url = f"{base_url}/{alt_path}"
                if self.download_file(alt_url, doc['filename'], "programme_guides"):
                    successful += 1
                else:
                    logger.warning(f"⚠️ Guide not available: {doc['name']}")
        
        logger.info(f"✅ Downloaded {successful}/{len(guide_urls)} programme guides")
        return successful > 0
    
    def download_call_documents(self, max_calls: int = 500):
        """Download documentation for ALL Horizon Europe calls."""
        logger.info("📋 Searching for ALL Horizon Europe calls...")
        
        # Search for all Horizon Europe calls
        all_calls = self.search_eu_portal_calls()
        
        if not all_calls:
            logger.error("❌ No calls found in EU Portal search")
            return False
        
        logger.info(f"📊 Found {len(all_calls)} Horizon Europe calls")
        
        # Save call metadata for reference
        calls_file = self.base_download_dir / "all_calls_metadata.json"
        with open(calls_file, 'w', encoding='utf-8') as f:
            json.dump(all_calls, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Saved call metadata to: {calls_file}")
        
        # Download call-specific documentation (limited to max_calls for practicality)
        successful_downloads = 0
        processed_calls = 0
        
        for call in all_calls[:max_calls]:
            processed_calls += 1
            call_id = call.get('call_identifier') or call.get('identifier')
            
            if not call_id:
                continue
            
            logger.info(f"📄 Processing call {processed_calls}/{len(all_calls)}: {call_id}")
            
            # Try to download call documentation
            call_url = call.get('url')
            if call_url and 'topic-details' in call_url:
                filename = f"call_{call_id}.html"
                if self.download_file(call_url, filename, "call_pages"):
                    successful_downloads += 1
            
            # Small delay between requests
            time.sleep(0.5)
        
        logger.info(f"✅ Downloaded documentation for {successful_downloads}/{processed_calls} calls")
        return successful_downloads > 0
    
    def download_additional_resources(self):
        """Download additional Horizon Europe resources."""
        logger.info("📚 Downloading Additional Resources...")
        
        additional_resources = [
            {
                "name": "Horizon Europe Strategic Plan",
                "url": "https://ec.europa.eu/info/sites/default/files/research_and_innovation/strategy_on_research_and_innovation/documents/ec_rtd_he-strategic-plan_2021-2024.pdf",
                "filename": "strategic_plan_2021-2024.pdf"
            },
            {
                "name": "Horizon Europe Regulation",
                "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32021R0695",
                "filename": "horizon_europe_regulation.pdf"
            },
            {
                "name": "EU Research and Innovation Policy",
                "url": "https://ec.europa.eu/info/sites/default/files/research_and_innovation/strategy_on_research_and_innovation/documents/ec_rtd_eu-research-and-innovation-policy.pdf",
                "filename": "eu_research_innovation_policy.pdf"
            }
        ]
        
        successful = 0
        for resource in additional_resources:
            if self.download_file(resource['url'], resource['filename'], "additional_resources"):
                successful += 1
        
        logger.info(f"✅ Downloaded {successful}/{len(additional_resources)} additional resources")
        return successful > 0
    
    def run_comprehensive_download(self):
        """Run comprehensive download of ALL Horizon Europe documentation."""
        logger.info("🚀 Starting Comprehensive Horizon Europe Document Download")
        logger.info(f"📁 Download directory: {self.base_download_dir}")
        
        total_success = 0
        total_operations = 4
        
        # 1. Download Work Programmes
        if self.download_work_programmes():
            total_success += 1
        
        # 2. Download Programme Guides
        if self.download_programme_guides():
            total_success += 1
        
        # 3. Download Call Documents (limit to 200 calls for practicality)
        if self.download_call_documents(max_calls=200):
            total_success += 1
        
        # 4. Download Additional Resources
        if self.download_additional_resources():
            total_success += 1
        
        # Summary
        logger.info(f"\n📊 Comprehensive Download Summary:")
        logger.info(f"✅ Successful operations: {total_success}/{total_operations}")
        
        if total_success > 0:
            logger.info("🎉 Comprehensive download completed!")
            logger.info(f"📁 All documents saved to: {self.base_download_dir}")
            logger.info("\n💡 Next steps:")
            logger.info("1. Process documents: python scripts/process_comprehensive_docs.py")
            logger.info("2. Update RAG system to handle call-specific queries")
            logger.info("3. Test with various call and topic questions")
            return True
        else:
            logger.error("💥 Comprehensive download failed!")
            return False

def main():
    """Main function to run the comprehensive download."""
    downloader = HorizonEuropeCallDownloader()
    success = downloader.run_comprehensive_download()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()