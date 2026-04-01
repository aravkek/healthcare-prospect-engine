#!/bin/bash
# MedPort daily discovery run
# Recommended: install via setup_cron.sh to run at 8am daily

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load GROQ_API_KEY from .env if present
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

python3 "$SCRIPT_DIR/customer_discovery.py" \
    --country both \
    --resume \
    --output "$SCRIPT_DIR/medport_prospects.csv"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Discovery run complete" >> "$SCRIPT_DIR/discovery_runs.log"
