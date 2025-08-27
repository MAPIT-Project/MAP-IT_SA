# Horizon Europe RAG System - Maintenance Guide

This guide explains how to keep your Horizon Europe RAG system up-to-date with the latest calls, topics, and documentation for 2025 and beyond.

## Automated Update System

The system includes two key scripts for automated maintenance:

### 1. Manual Update Script
**File**: [`scripts/update_horizon_documents.sh`](scripts/update_horizon_documents.sh)

Run this script manually whenever you want to update the system:
```bash
./scripts/update_horizon_documents.sh
```

This script will:
- Download the latest Horizon Europe documents (work programmes, calls, guides)
- Process new documents for the vector database
- Ingest them into the RAG system
- Create a timestamp file (`.last_update_time`) with the update time

### 2. Automated Cron Job Setup
**File**: [`scripts/setup_cron_job.sh`](scripts/setup_cron_job.sh)

Set up automated updates by running:
```bash
./scripts/setup_cron_job.sh
```

This will configure:
- **Monthly updates**: Runs on the 1st and 15th of each month at 3:00 AM
- **Weekly checks**: Runs every Monday at 4:00 AM to check for new calls
- **Logging**: All activities are logged to the `logs/` directory

## How the System Stays Current

### Dynamic Year Handling
The download script [`download_all_horizon_calls.py`](scripts/download_all_horizon_calls.py) now:

1. **Dynamically generates programme years** based on the current year
2. **Extends to future years** (current year + 2) to cover upcoming calls
3. **Automatically tries multiple URL patterns** for new document versions
4. **Handles both current and future Horizon Europe periods** (2021-2027 and beyond)

### Future-Proof Features

- **Automatic URL pattern detection**: Tries multiple URL formats for new documents
- **Error resilience**: Continues if some documents aren't available yet
- **Incremental updates**: Only downloads new/changed documents
- **Comprehensive coverage**: Includes all clusters, programmes, and document types

## Manual Update Process

If you prefer manual control, here's the step-by-step process:

1. **Download documents**:
   ```bash
   python scripts/download_all_horizon_calls.py
   ```

2. **Process documents**:
   ```bash
   python scripts/process_comprehensive_docs.py
   ```

3. **Ingest into database**:
   ```bash
   python scripts/ingest_comprehensive_docs.py
   ```

## Monitoring and Logs

- **Update logs**: Check `logs/update_*.log` for detailed update information
- **Weekly checks**: `logs/weekly_check_*.log` shows call availability monitoring
- **Last update**: The `.last_update_time` file shows when the system was last updated

## Troubleshooting

If updates fail:

1. **Check internet connection**: The system needs access to EU portals
2. **Verify API access**: Ensure the EU Funding & Tenders Portal is accessible
3. **Review logs**: Check the log files for specific error messages
4. **Manual test**: Run the download script manually to identify issues

## Best Practices

1. **Regular updates**: Run updates at least monthly during active call periods
2. **Monitor new programmes**: Watch for announcements of new Horizon Europe work programmes
3. **Test after updates**: Verify the system works with new call questions
4. **Backup database**: Consider backing up your vector database before major updates

## Support

For issues with the update system:
- Check the script documentation
- Review the log files in `logs/`
- Ensure all dependencies are installed (`requirements.txt`)

The system is designed to automatically handle Horizon Europe updates through 2027 and beyond, adapting to new programme structures and document formats as they become available.