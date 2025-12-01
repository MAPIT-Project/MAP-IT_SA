#!/bin/bash
#
# Download Missing Horizon Europe Cluster Work Programmes
#
# This script downloads Cluster 3, 4, and 6 Work Programmes
# which are currently missing from the database.
#

set -e

echo "================================================"
echo "📥 Downloading Missing Cluster Work Programmes"
echo "================================================"
echo ""

# Create directory
mkdir -p data/shared_documents
cd data/shared_documents

echo "Missing Clusters: 3 (Civil Security), 4 (Digital, Industry & Space), 6 (Food, Bioeconomy)"
echo ""

# Cluster 3: Civil Security for Society
echo "📄 Cluster 3: Civil Security for Society"
echo "   URL: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-3-civil-security-for-society_horizon-2023-2024_en.pdf"
echo ""
wget -nc "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-3-civil-security-for-society_horizon-2023-2024_en.pdf" \
  -O "HE_WP_2023-2024_Cluster3_Civil_Security.pdf" 2>&1 || echo "⚠️  Failed to download Cluster 3 (might need manual download)"

# Cluster 4: Digital, Industry and Space  
echo "📄 Cluster 4: Digital, Industry and Space"
echo "   URL: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-7-digital-industry-and-space_horizon-2023-2024_en.pdf"
echo ""
wget -nc "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-7-digital-industry-and-space_horizon-2023-2024_en.pdf" \
  -O "HE_WP_2023-2024_Cluster4_Digital_Industry_Space.pdf" 2>&1 || echo "⚠️  Failed to download Cluster 4 (might need manual download)"

# Cluster 6: Food, Bioeconomy, Natural Resources
echo "📄 Cluster 6: Food, Bioeconomy, Natural Resources"
echo "   URL: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-9-food-bioeconomy-natural-resources-agriculture-and-environment_horizon-2023-2024_en.pdf"
echo ""
wget -nc "https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-9-food-bioeconomy-natural-resources-agriculture-and-environment_horizon-2023-2024_en.pdf" \
  -O "HE_WP_2023-2024_Cluster6_Food_Bioeconomy.pdf" 2>&1 || echo "⚠️  Failed to download Cluster 6 (might need manual download)"

echo ""
echo "================================================"
echo "✅ Download Complete!"
echo "================================================"
echo ""
echo "Downloaded files:"
ls -lh HE_WP_2023-2024_Cluster*.pdf 2>/dev/null || echo "⚠️  No files downloaded - URLs might have changed"
echo ""
echo "📝 IMPORTANT NOTES:"
echo ""
echo "If downloads failed (URLs changed), manually download from:"
echo "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/programmes/horizon"
echo ""
echo "Search for:"
echo "  - 'Horizon Europe Work Programme 2023-2024 - Cluster 3: Civil Security'"
echo "  - 'Horizon Europe Work Programme 2023-2024 - Cluster 4: Digital, Industry & Space'"
echo "  - 'Horizon Europe Work Programme 2023-2024 - Cluster 6: Food, Bioeconomy'"
echo ""
echo "Save them in: $(pwd)"
echo ""
echo "Next steps:"
echo "  1. Verify PDFs are downloaded: ls -lh data/shared_documents/"
echo "  2. Process documents: python3 scripts/process_shared_documents.py"
echo "  3. Restart API: docker restart \$(docker ps -q -f name=map-it_sa-api)"
echo "  4. Test: Ask about HORIZON-CL3-2025-02-CS-ECCC-01"
echo ""




