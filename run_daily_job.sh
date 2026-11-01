#!/usr/bin/env bash
# ==============================================================================
# Daily Autonomous Execution Script for Personal Expense Tracking Agent
# ==============================================================================
# Adheres strictly to Capstone Guardrails:
# G1: Read-Only Storage (never modifies original statement files)
# G2: Zero Financial Movement (no payment execution or credential handling)
# G3: Local Fence & No Internet (connectors disabled, strictly air-gapped local)
# G4: Data vs. Instruction Separation (passive data ingestion)
# G5: Zero Invented Numbers (deterministic calculation engine)
# G6: Balance Check Line Verification
# ==============================================================================

set -euo pipefail

# ------------------------------------------------------------------------------
# 1. ENFORCE PRIVACY & LOCAL AIR-GAP (GUARDRAIL G3)
# ------------------------------------------------------------------------------
export DISABLE_WEB_SEARCH=1
export DISABLE_NOTION_CONNECTOR=1
export DISABLE_FIRECRAWL_CONNECTOR=1
export AGENT_NETWORK_ACCESS="none"

# ------------------------------------------------------------------------------
# 2. RESOLVE WORKING DIRECTORY & PATHS
# ------------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

STATEMENTS_DIR="$SCRIPT_DIR/statements"
LOGS_DIR="$SCRIPT_DIR/logs"
PYTHON_ENGINE="$SCRIPT_DIR/process_expenses.py"
LOG_FILE="$LOGS_DIR/daily_job.log"

mkdir -p "$LOGS_DIR"

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================================================" >> "$LOG_FILE"
echo "[$TIMESTAMP] Starting Personal Expense Tracking Agent Daily Job" >> "$LOG_FILE"
echo "[$TIMESTAMP] Air-gap enforced: AGENT_NETWORK_ACCESS=${AGENT_NETWORK_ACCESS}" >> "$LOG_FILE"

# ------------------------------------------------------------------------------
# 3. VERIFY STATEMENTS DIRECTORY & CSV AVAILABILITY (STAGE 1: SCAN)
# ------------------------------------------------------------------------------
if [ ! -d "$STATEMENTS_DIR" ]; then
    echo "[$TIMESTAMP] ERROR: Statements directory '$STATEMENTS_DIR' does not exist." | tee -a "$LOG_FILE"
    exit 1
fi

CSV_COUNT=$(find "$STATEMENTS_DIR" -maxdepth 1 -type f -name "*.csv" | wc -l | tr -d ' ')

if [ "$CSV_COUNT" -eq 0 ]; then
    echo "[$TIMESTAMP] INFO: No CSV statement files found in '$STATEMENTS_DIR'. Exiting cleanly." | tee -a "$LOG_FILE"
    exit 0
fi

echo "[$TIMESTAMP] Discovered $CSV_COUNT statement CSV file(s) in '$STATEMENTS_DIR'." >> "$LOG_FILE"

# ------------------------------------------------------------------------------
# 4. EXECUTE DETERMINISTIC PROCESSING ENGINE (STAGES 2 - 8)
# ------------------------------------------------------------------------------
if [ ! -f "$PYTHON_ENGINE" ]; then
    echo "[$TIMESTAMP] ERROR: Python execution engine '$PYTHON_ENGINE' not found." | tee -a "$LOG_FILE"
    exit 1
fi

echo "[$TIMESTAMP] Launching deterministic Python pipeline..." >> "$LOG_FILE"

if python3 "$PYTHON_ENGINE" >> "$LOG_FILE" 2>&1; then
    COMPLETION_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$COMPLETION_TIME] SUCCESS: Daily expense processing completed successfully." >> "$LOG_FILE"
    echo "[$COMPLETION_TIME] Report generated at '$SCRIPT_DIR/daily_report.md'." >> "$LOG_FILE"
    exit 0
else
    ERROR_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "[$ERROR_TIME] FAILURE: Expense processing pipeline encountered an error. Check log above." >> "$LOG_FILE"
    exit 1
fi
