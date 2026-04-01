#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_JOB="0 8 * * * $SCRIPT_DIR/run_daily.sh"
# Add to crontab if not already there
(crontab -l 2>/dev/null | grep -v "run_daily.sh"; echo "$CRON_JOB") | crontab -
echo "Cron job installed: runs daily at 8am"
echo "View cron jobs: crontab -l"
echo "Remove: crontab -e and delete the line"
