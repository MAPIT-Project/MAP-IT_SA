#!/usr/bin/env python3
"""
Script to download key Horizon Europe documents for the RAG system.
"""

import sys
import time
from pathlib import Path

import requests

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))


def download_file(url: str, filename: str, download_dir: Path) -> bool:
    """Download a file from URL."""
    try:
        print(f"📥 Downloading: {filename}")
        print(f"   URL: {url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; HorizonEuropeRAG/1.0)",
            "Accept": "application/pdf,*/*",
        }

        response = requests.get(url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        file_path = download_dir / filename

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        file_size = file_path.stat().st_size
        print(f"✅ Downloaded: {filename} ({file_size:,} bytes)")

        return True

    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")
        return False


def download_horizon_europe_documents():
    """Download key Horizon Europe documents."""

    # Create downloads directory
    download_dir = Path("downloads/horizon_europe")
    download_dir.mkdir(parents=True, exist_ok=True)

    print(f"📁 Download directory: {download_dir}")

    # Key Horizon Europe documents to download
    documents = [
        {
            "name": "Horizon Europe Work Programme 2023-2024 - General Introduction",
            "filename": "horizon_europe_work_programme_2023_2024_general.pdf",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-1-general-introduction_horizon-2023-2024_en.pdf",
        },
        {
            "name": "Horizon Europe Work Programme 2023-2024 - Climate, Energy and Environment",
            "filename": "horizon_europe_work_programme_2023_2024_climate_energy.pdf",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-5-climate-energy-and-environment_horizon-2023-2024_en.pdf",
        },
        {
            "name": "Horizon Europe Programme Guide",
            "filename": "horizon_europe_programme_guide.pdf",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf",
        },
        {
            "name": "EU Grants AGA - Annotated Grant Agreement",
            "filename": "eu_grants_aga_annotated_grant_agreement.pdf",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf",
        },
        {
            "name": "Horizon Europe Work Programme 2023-2024 - Digital, Industry and Space",
            "filename": "horizon_europe_work_programme_2023_2024_digital_industry.pdf",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-4-digital-industry-and-space_horizon-2023-2024_en.pdf",
        },
        {
            "name": "Horizon Europe Work Programme 2023-2024 - Health",
            "filename": "horizon_europe_work_programme_2023_2024_health.pdf",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-3-health_horizon-2023-2024_en.pdf",
        },
        {
            "name": "Horizon Europe Work Programme 2023-2024 - Culture, Creativity and Inclusive Society",
            "filename": "horizon_europe_work_programme_2023_2024_culture.pdf",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-6-culture-creativity-and-inclusive-society_horizon-2023-2024_en.pdf",
        },
        {
            "name": "Horizon Europe Work Programme 2023-2024 - Food, Bioeconomy, Natural Resources",
            "filename": "horizon_europe_work_programme_2023_2024_food_bioeconomy.pdf",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-7-food-bioeconomy-natural-resources-agriculture-and-environment_horizon-2023-2024_en.pdf",
        },
        {
            "name": "Horizon Europe Work Programme 2023-2024 - Civil Security for Society",
            "filename": "horizon_europe_work_programme_2023_2024_civil_security.pdf",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-8-civil-security-for-society_horizon-2023-2024_en.pdf",
        },
        {
            "name": "Horizon Europe Work Programme 2023-2024 - European Innovation Council",
            "filename": "horizon_europe_work_programme_2023_2024_eic.pdf",
            "url": "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-9-european-innovation-council_horizon-2023-2024_en.pdf",
        },
    ]

    # Download documents
    successful_downloads = 0
    failed_downloads = []

    for doc in documents:
        print(f"\n📄 Processing: {doc['name']}")

        # Check if file already exists
        file_path = download_dir / doc["filename"]
        if file_path.exists():
            print(f"⚠️ File already exists: {doc['filename']}")
            successful_downloads += 1
            continue

        # Download the file
        if download_file(doc["url"], doc["filename"], download_dir):
            successful_downloads += 1
            time.sleep(2)  # Be respectful to the server
        else:
            failed_downloads.append(doc["name"])

    # Summary
    print("\n📊 Download Summary:")
    print(f"✅ Successful: {successful_downloads}/{len(documents)}")
    print(f"❌ Failed: {len(failed_downloads)}")

    if failed_downloads:
        print("Failed downloads:")
        for name in failed_downloads:
            print(f"  - {name}")

    return successful_downloads > 0


if __name__ == "__main__":
    print("🚀 Starting Horizon Europe document download...")
    success = download_horizon_europe_documents()

    if success:
        print("🎉 Document download completed!")
        print("📁 Documents saved to: downloads/horizon_europe/")
        print("\n💡 Next steps:")
        print("1. Run the database setup: python scripts/setup_database.py")
        print("2. Ingest documents: python scripts/ingest_documents.py")
    else:
        print("💥 Document download failed!")
        sys.exit(1)
