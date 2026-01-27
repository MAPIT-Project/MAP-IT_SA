#!/usr/bin/env python3
"""
Download Missing Horizon Europe Work Programmes

This script downloads the work programmes you're missing:
- ERC (European Research Council) - Pillar 1
- MSCA (Marie Skłodowska-Curie Actions) - Pillar 1
- EIC (European Innovation Council) - Pillar 3

Run: python scripts/download_missing_workprogrammes.py
"""

import sys
from pathlib import Path

import requests

# Base URL for Horizon Europe work programmes
BASE_URL = (
    "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2025"
)

# Work programmes to download (what you're missing)
WORK_PROGRAMMES = {
    # Pillar 1: Excellent Science
    "wp-1-erc_horizon-2025_en.pdf": {
        "name": "ERC (European Research Council)",
        "description": "Frontier research grants for individual researchers",
        "url": f"{BASE_URL}/wp-1-erc_horizon-2025_en.pdf",
    },
    "wp-2-msca_horizon-2025_en.pdf": {
        "name": "MSCA (Marie Skłodowska-Curie Actions)",
        "description": "Researcher training, mobility, and career development",
        "url": f"{BASE_URL}/wp-2-msca_horizon-2025_en.pdf",
    },
    # Pillar 3: Innovative Europe
    "wp-eic_horizon-2025_en.pdf": {
        "name": "EIC (European Innovation Council)",
        "description": "Innovation funding for startups, SMEs, breakthrough tech",
        "url": f"{BASE_URL}/wp-eic_horizon-2025_en.pdf",
    },
}

# Alternative URLs in case the main ones don't work
ALTERNATIVE_URLS = {
    "wp-eic_horizon-2025_en.pdf": [
        "https://eic.ec.europa.eu/system/files/2024-03/EIC-Work-Programme-2024.pdf",
        "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2024/wp-13-eic_horizon-2024_en.pdf",
    ]
}


def download_file(url: str, dest_path: Path, name: str) -> bool:
    """Download a file from URL to destination path."""
    try:
        print(f"  📥 Downloading from: {url}")

        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        response = requests.get(url, headers=headers, timeout=60, stream=True)

        if response.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = dest_path.stat().st_size / (1024 * 1024)  # MB
            print(f"  ✅ Downloaded: {dest_path.name} ({file_size:.1f} MB)")
            return True
        else:
            print(f"  ❌ HTTP {response.status_code}: {url}")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    print("=" * 70)
    print("📥 DOWNLOADING MISSING HORIZON EUROPE WORK PROGRAMMES")
    print("=" * 70)
    print()

    # Determine output directory
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / "newdocs" / "2025_work_programmes"

    # Create directory if needed
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")
    print()

    # Track results
    downloaded = []
    failed = []
    skipped = []

    for filename, info in WORK_PROGRAMMES.items():
        dest_path = output_dir / filename

        print(f"\n{'=' * 50}")
        print(f"📄 {info['name']}")
        print(f"   {info['description']}")
        print(f"{'=' * 50}")

        # Check if already exists
        if dest_path.exists():
            file_size = dest_path.stat().st_size / (1024 * 1024)
            print(f"  ⏭️  Already exists: {filename} ({file_size:.1f} MB)")
            skipped.append(filename)
            continue

        # Try main URL
        success = download_file(info["url"], dest_path, info["name"])

        # Try alternative URLs if main fails
        if not success and filename in ALTERNATIVE_URLS:
            print("  🔄 Trying alternative URLs...")
            for alt_url in ALTERNATIVE_URLS[filename]:
                success = download_file(alt_url, dest_path, info["name"])
                if success:
                    break

        if success:
            downloaded.append(filename)
        else:
            failed.append(filename)

    # Summary
    print("\n" + "=" * 70)
    print("📊 DOWNLOAD SUMMARY")
    print("=" * 70)

    if downloaded:
        print(f"\n✅ Downloaded ({len(downloaded)}):")
        for f in downloaded:
            print(f"   - {f}")

    if skipped:
        print(f"\n⏭️  Already existed ({len(skipped)}):")
        for f in skipped:
            print(f"   - {f}")

    if failed:
        print(f"\n❌ Failed ({len(failed)}):")
        for f in failed:
            print(f"   - {f}")
        print("\n💡 Manual download links:")
        print(
            "   https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/how-to-participate/reference-documents;programCode=HORIZON"
        )

    # Next steps
    print("\n" + "=" * 70)
    print("🚀 NEXT STEPS")
    print("=" * 70)
    print(
        """
After downloading, ingest the new documents into the vector database:

    cd /home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA
    source venv/bin/activate
    PYTHONPATH=. python scripts/ingest_newdocs.py

This will:
1. Parse the PDFs
2. Create embeddings
3. Store in the vector database
4. Make them searchable!
"""
    )

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
