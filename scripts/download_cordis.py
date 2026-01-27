#!/usr/bin/env python3
"""
Download CORDIS Horizon Europe dataset from EU Open Data Portal.
Downloads projects, deliverables, publications, and report summaries.
"""

import json
import logging
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# CORDIS Horizon Europe dataset URLs
# These are direct download links from data.europa.eu
DATASET_URLS = {
    "projects_csv": "https://cordis.europa.eu/data/cordis-HORIZONprojects-csv.zip",
    "projects_json": "https://cordis.europa.eu/data/cordis-HORIZONprojects-json.zip",
    "deliverables": "https://cordis.europa.eu/data/cordis-HORIZONprojectDeliverables-csv.zip",
    "publications": "https://cordis.europa.eu/data/cordis-HORIZONprojectPublications-csv.zip",
    "reports": "https://cordis.europa.eu/data/cordis-HORIZONreportSummaries-csv.zip",
}

# Reference data
REFERENCE_URLS = {
    "programmes": "https://cordis.europa.eu/data/reference/cordisref-programmes.json",
    "topics": "https://cordis.europa.eu/data/reference/cordisref-topics.json",
    "countries": "https://cordis.europa.eu/data/reference/cordisref-countries.json",
    "organizationTypes": "https://cordis.europa.eu/data/reference/cordisref-organizationTypes.json",
    "fundingSchemes": "https://cordis.europa.eu/data/reference/cordisref-fundingSchemes.json",
}


def download_file(url: str, dest_path: Path, chunk_size: int = 8192) -> bool:
    """
    Download a file from URL to destination path.

    Args:
        url: Source URL
        dest_path: Destination file path
        chunk_size: Download chunk size in bytes

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"📥 Downloading: {url}")
        logger.info(f"   Destination: {dest_path}")

        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r   Progress: {progress:.1f}%", end="", flush=True)

        print()  # New line after progress
        logger.info(f"✅ Downloaded: {dest_path.name} ({downloaded / 1024 / 1024:.1f} MB)")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Download failed: {e}")
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> bool:
    """
    Extract a ZIP file to destination directory.

    Args:
        zip_path: Path to ZIP file
        extract_to: Destination directory

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"📦 Extracting: {zip_path.name}")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)

        logger.info(f"✅ Extracted to: {extract_to}")

        # List extracted files
        for f in extract_to.iterdir():
            if f.is_file() and f.suffix in [".csv", ".json"]:
                size_mb = f.stat().st_size / 1024 / 1024
                logger.info(f"   📄 {f.name} ({size_mb:.1f} MB)")

        return True

    except zipfile.BadZipFile as e:
        logger.error(f"❌ Invalid ZIP file: {e}")
        return False


def download_cordis_dataset(data_dir: Path, include_json: bool = False) -> dict:
    """
    Download complete CORDIS Horizon Europe dataset.

    Args:
        data_dir: Directory to store downloaded data
        include_json: Also download JSON format (larger but more detailed)

    Returns:
        Dictionary with download status for each dataset
    """
    data_dir.mkdir(parents=True, exist_ok=True)

    results = {"downloaded": [], "failed": [], "skipped": []}

    logger.info("=" * 60)
    logger.info("CORDIS Horizon Europe Dataset Downloader")
    logger.info(f"Target directory: {data_dir}")
    logger.info("=" * 60)

    # Download main datasets
    datasets_to_download = ["projects_csv", "deliverables", "publications", "reports"]
    if include_json:
        datasets_to_download.append("projects_json")

    for dataset_name in datasets_to_download:
        url = DATASET_URLS.get(dataset_name)
        if not url:
            continue

        zip_filename = f"{dataset_name}.zip"
        zip_path = data_dir / zip_filename

        # Skip if already downloaded and extracted
        # Check for common extracted filenames
        if dataset_name == "projects_csv":
            check_files = list(data_dir.glob("*project*.csv"))
        elif dataset_name == "projects_json":
            check_files = list(data_dir.glob("*project*.json"))
        elif dataset_name == "deliverables":
            check_files = list(data_dir.glob("*[Dd]eliver*.csv"))
        elif dataset_name == "publications":
            check_files = list(data_dir.glob("*[Pp]ublic*.csv"))
        elif dataset_name == "reports":
            check_files = list(data_dir.glob("*[Rr]eport*.csv")) + list(
                data_dir.glob("*[Ss]ummar*.csv")
            )
        else:
            check_files = []

        if check_files:
            logger.info(f"⏭️ Skipping {dataset_name} (already exists: {check_files[0].name})")
            results["skipped"].append(dataset_name)
            continue

        # Download
        if download_file(url, zip_path):
            # Extract
            if extract_zip(zip_path, data_dir):
                results["downloaded"].append(dataset_name)
                # Remove ZIP after extraction to save space
                zip_path.unlink()
                logger.info(f"🗑️ Removed ZIP file: {zip_filename}")
            else:
                results["failed"].append(dataset_name)
        else:
            results["failed"].append(dataset_name)

    # Download reference data (smaller JSON files)
    logger.info("\n📚 Downloading reference data...")
    ref_dir = data_dir / "reference"
    ref_dir.mkdir(exist_ok=True)

    for ref_name, url in REFERENCE_URLS.items():
        ref_path = ref_dir / f"{ref_name}.json"

        if ref_path.exists():
            logger.info(f"⏭️ Skipping {ref_name} (already exists)")
            continue

        if download_file(url, ref_path):
            results["downloaded"].append(f"ref_{ref_name}")
        else:
            results["failed"].append(f"ref_{ref_name}")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Downloaded: {len(results['downloaded'])} files")
    logger.info(f"⏭️ Skipped: {len(results['skipped'])} files")
    logger.info(f"❌ Failed: {len(results['failed'])} files")

    if results["failed"]:
        logger.warning(f"Failed datasets: {results['failed']}")

    # Save download metadata
    metadata = {
        "download_date": datetime.now().isoformat(),
        "source": "https://data.europa.eu/data/datasets/cordis-eu-research-projects-under-horizon-europe-2021-2027",
        "results": results,
        "files": [str(f.name) for f in data_dir.rglob("*") if f.is_file()],
    }

    metadata_path = data_dir / "download_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"\n📋 Metadata saved to: {metadata_path}")

    return results


def verify_download(data_dir: Path) -> bool:
    """
    Verify that required files are present.

    Args:
        data_dir: Directory containing downloaded data

    Returns:
        True if all required files present, False otherwise
    """
    # Check for any project file
    project_files = list(data_dir.glob("*project*.csv")) + list(data_dir.glob("*project*.json"))

    if not project_files:
        logger.error("❌ No project data files found!")
        return False

    logger.info(f"✅ Found project files: {[f.name for f in project_files]}")

    # Check reference data
    ref_dir = data_dir / "reference"
    if ref_dir.exists():
        ref_files = list(ref_dir.glob("*.json"))
        logger.info(f"✅ Found {len(ref_files)} reference files")

    # List all files with sizes
    logger.info("\n📁 Downloaded files:")
    total_size = 0
    for f in sorted(data_dir.rglob("*")):
        if f.is_file():
            size_mb = f.stat().st_size / 1024 / 1024
            total_size += size_mb
            rel_path = f.relative_to(data_dir)
            logger.info(f"   {rel_path}: {size_mb:.1f} MB")

    logger.info(f"\n📊 Total size: {total_size:.1f} MB")

    return True


def main():
    """Main entry point."""
    # Determine data directory
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / "data" / "cordis"

    # Allow override via command line
    if len(sys.argv) > 1:
        data_dir = Path(sys.argv[1])

    # Download dataset
    download_cordis_dataset(data_dir, include_json=False)  # CSV is usually sufficient

    # Verify
    if verify_download(data_dir):
        logger.info("\n✅ CORDIS dataset ready for ingestion!")
        logger.info(f"   Location: {data_dir}")
        logger.info("   Next step: Run TASK_03 (CORDIS Data Ingestion)")
        return 0
    else:
        logger.error("\n❌ Download verification failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
