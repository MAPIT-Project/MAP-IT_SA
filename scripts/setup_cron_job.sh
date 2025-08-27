#!/bin/bash
# Script to set up automated cron job for Horizon Europe document updates

echo "🔄 Setting up automated Horizon Europe document updates..."

# Get the absolute path to the project directory
PROJECT_DIR="/home/anmar/Documents/VSCODE_REPOS/MAP-IT_SA-1"
UPDATE_SCRIPT="$PROJECT_DIR/scripts/update_horizon_documents.sh"

# Make the update script executable
chmod +x "$UPDATE_SCRIPT"
echo "✅ Made update script executable: $UPDATE_SCRIPT"

# Create log directory for cron job outputs
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
echo "✅ Created log directory: $LOG_DIR"

# Determine the best time for updates (early morning when system is less busy)
# Update twice a month: 1st and 15th at 3:00 AM
CRON_SCHEDULE="0 3 1,15 * *"  # 3:00 AM on 1st and 15th of each month

# Create the cron job entry
CRON_JOB="$CRON_SCHEDULE $UPDATE_SCRIPT >> $LOG_DIR/update_$(date +\%Y\%m\%d).log 2>&1"

# Check if cron job already exists
if crontab -l | grep -q "$UPDATE_SCRIPT"; then
    echo "⚠️  Cron job already exists. Updating..."
    # Remove existing entry
    (crontab -l | grep -v "$UPDATE_SCRIPT") | crontab -
fi

# Add the new cron job
(crontab -l; echo "$CRON_JOB") | crontab -

if [ $? -eq 0 ]; then
    echo "✅ Cron job successfully installed!"
    echo "📅 Schedule: $CRON_SCHEDULE (3:00 AM on 1st and 15th of each month)"
    echo "📁 Logs will be saved to: $LOG_DIR/"
    echo ""
    echo "📋 Current crontab:"
    crontab -l
    echo ""
    echo "💡 To manually run the update: ./scripts/update_horizon_documents.sh"
    echo "📊 To check update status: tail -f $LOG_DIR/update_*.log"
else
    echo "❌ Failed to install cron job"
    exit 1
fi

# Also create a weekly check for new calls (more frequent but lighter)
WEEKLY_CRON="0 4 * * 1"  # 4:00 AM every Monday
WEEKLY_SCRIPT="$PROJECT_DIR/scripts/check_new_calls.sh"

# Create a lightweight weekly check script
cat > "$WEEKLY_SCRIPT" << 'EOF'
#!/bin/bash
# Weekly check for new Horizon Europe calls
echo "🔍 Weekly check for new Horizon Europe calls - $(date)"
cd /home/anmar/Documents/VSCODE_REPOS/MAP-IT_SA-1
python -c "
import sys
sys.path.append('.')
from scripts.download_all_horizon_calls import HorizonEuropeCallDownloader
downloader = HorizonEuropeCallDownloader()
new_calls = downloader.search_eu_portal_calls()
print(f'📊 Found {len(new_calls)} total calls in weekly check')
# Check if we have significantly more calls than before (placeholder logic)
# In a real implementation, you'd compare with previous count and trigger update if needed
"
EOF

chmod +x "$WEEKLY_SCRIPT"
(crontab -l; echo "$WEEKLY_CRON $WEEKLY_SCRIPT >> $LOG_DIR/weekly_check_$(date +\%Y\%m\%d).log 2>&1") | crontab -

echo "✅ Weekly check cron job installed!"
echo "📅 Weekly schedule: $WEEKLY_CRON (4:00 AM every Monday)"

echo ""
echo "🎉 Automated update system setup complete!"
echo "📋 The system will now:"
echo "   • Update documents twice monthly (1st and 15th at 3:00 AM)"
echo "   • Check for new calls weekly (Mondays at 4:00 AM)"
echo "   • Log all activities to: $LOG_DIR/"