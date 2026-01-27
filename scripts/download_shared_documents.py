#!/usr/bin/env python3
"""
Download common Horizon Europe documents once to a shared repository.

This script downloads frequently-used documents that are shared across many calls:
- General Annexes (used by ALL calls)
- Programme Guide (used by ALL calls)
- Work Programmes for each cluster (used by all calls in that cluster)

Usage:
    python scripts/download_shared_documents.py [--all] [--cluster N]
"""

import argparse
import hashlib
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Common document URLs (these are typically stable URLs)
SHARED_DOCUMENTS = {
    'general_annexes': {
        'title': 'Horizon Europe General Annexes 2023-2025',
        'url': 'https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2025/wp-13-general-annexes_horizon-2023-2025_en.pdf',
        'type': 'general_annexes',
        'scope': 'global',
        'key': 'he_general_annexes_2023-2025'
    },
    'programme_guide': {
        'title': 'Horizon Europe Programme Guide',
        'url': 'https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/programme-guide_horizon_en.pdf',
        'type': 'programme_guide',
        'scope': 'global',
        'key': 'he_programme_guide'
    },
    'wp_cluster_1': {
        'title': 'Work Programme Cluster 1 - Health',
        'url': 'https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2025/wp-4-health_horizon-2023-2025_en.pdf',
        'type': 'work_programme',
        'scope': 'cluster',
        'scope_id': 'CLUSTER-1',
        'key': 'he_wp_cluster1_health_2023-2025'
    },
    'wp_cluster_6': {
        'title': 'Work Programme Cluster 6 - Civil Security',
        'url': 'https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2025/wp-6-civil-security_horizon-2023-2025_en.pdf',
        'type': 'work_programme',
        'scope': 'cluster',
        'scope_id': 'CLUSTER-6',
        'key': 'he_wp_cluster6_civil_security_2023-2025'
    },
    # Add more clusters as needed
}


def download_document(url: str, output_path: Path) -> bool:
    """Download a document from URL"""
    try:
        import requests
        
        logger.info(f"📥 Downloading: {url}")
        
        response = requests.get(url, timeout=60, stream=True)
        response.raise_for_status()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"✅ Downloaded: {output_path.name} ({file_size:.2f} MB)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to download {url}: {e}")
        return False


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def manual_download_instructions():
    """Print instructions for manual download"""
    print("\n" + "="*70)
    print("📥 MANUAL DOWNLOAD INSTRUCTIONS")
    print("="*70)
    print("\nSome documents need to be downloaded manually from the portal.")
    print("\n1. Go to: https://ec.europa.eu/info/funding-tenders/opportunities/portal/")
    print("2. Navigate to: Support > Reference Documents")
    print("\n3. Download these files:\n")
    
    for key, doc in SHARED_DOCUMENTS.items():
        print(f"   📄 {doc['title']}")
        print(f"      URL: {doc['url']}")
        print(f"      Save as: data/shared_documents/{key}.pdf\n")
    
    print("\n4. Then run:")
    print("   python scripts/process_shared_documents.py")
    print("="*70 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Download shared Horizon Europe documents')
    parser.add_argument('--all', action='store_true', help='Download all documents')
    parser.add_argument('--cluster', type=int, help='Download specific cluster work programme (1-12)')
    parser.add_argument('--manual', action='store_true', help='Show manual download instructions')
    
    args = parser.parse_args()
    
    if args.manual:
        manual_download_instructions()
        return
    
    # Create output directory
    output_dir = Path("data/shared_documents")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n🚀 Horizon Europe Shared Documents Downloader")
    print("="*70 + "\n")
    
    # Determine what to download
    to_download = {}
    
    if args.all:
        to_download = SHARED_DOCUMENTS
    elif args.cluster:
        key = f'wp_cluster_{args.cluster}'
        if key in SHARED_DOCUMENTS:
            to_download[key] = SHARED_DOCUMENTS[key]
        else:
            logger.error(f"❌ Cluster {args.cluster} not configured")
            return
    else:
        # Default: download global documents
        to_download = {
            k: v for k, v in SHARED_DOCUMENTS.items() 
            if v.get('scope') == 'global'
        }
    
    # Download
    results = {'success': 0, 'failed': 0, 'skipped': 0}
    
    for key, doc in to_download.items():
        output_path = output_dir / f"{key}.pdf"
        
        if output_path.exists():
            logger.info(f"⏭️  Skipping (already exists): {output_path.name}")
            results['skipped'] += 1
            continue
        
        if download_document(doc['url'], output_path):
            results['success'] += 1
        else:
            results['failed'] += 1
    
    # Summary
    print("\n" + "="*70)
    print("📊 DOWNLOAD SUMMARY")
    print("="*70)
    print(f"✅ Downloaded: {results['success']}")
    print(f"⏭️  Skipped (already exists): {results['skipped']}")
    print(f"❌ Failed: {results['failed']}")
    print("="*70 + "\n")
    
    if results['success'] > 0:
        print("Next step: Process downloaded documents")
        print("  python scripts/process_shared_documents.py")
    elif results['failed'] > 0:
        print("\n⚠️  Some downloads failed. You may need to download manually:")
        print("  python scripts/download_shared_documents.py --manual")


if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("❌ Missing dependency: requests")
        print("Install with: pip install requests")
        sys.exit(1)
    
    main()


