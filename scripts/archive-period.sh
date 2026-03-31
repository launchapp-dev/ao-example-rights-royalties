#!/usr/bin/env bash
# archive-period.sh — Archives current period's royalty data to data/history/YYYY-MM/
# Usage: bash scripts/archive-period.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Determine period from normalized-usage.json
PERIOD=$(python3 -c "
import json, sys
try:
    with open('data/normalized-usage.json') as f:
        d = json.load(f)
    print(d.get('period', ''))
except Exception as e:
    print('', end='')
")

if [ -z "$PERIOD" ]; then
    echo "ERROR: Could not determine period from data/normalized-usage.json" >&2
    exit 1
fi

ARCHIVE_DIR="data/history/${PERIOD}"
echo "Archiving period ${PERIOD} to ${ARCHIVE_DIR}/"
mkdir -p "$ARCHIVE_DIR"

# Archive royalty ledger
if [ -f "data/royalty-ledger.json" ]; then
    cp "data/royalty-ledger.json" "${ARCHIVE_DIR}/royalty-ledger.json"
    echo "  Archived: royalty-ledger.json"
fi

# Archive normalized usage
if [ -f "data/normalized-usage.json" ]; then
    cp "data/normalized-usage.json" "${ARCHIVE_DIR}/normalized-usage.json"
    echo "  Archived: normalized-usage.json"
fi

# Archive payment batch
if [ -f "data/payment-batch.json" ]; then
    cp "data/payment-batch.json" "${ARCHIVE_DIR}/payment-batch.json"
    echo "  Archived: payment-batch.json"
fi

# Archive advance balances snapshot
if [ -f "data/advance-balances.json" ]; then
    cp "data/advance-balances.json" "${ARCHIVE_DIR}/advance-balances-snapshot.json"
    echo "  Archived: advance-balances-snapshot.json"
fi

# Archive statements
STATEMENT_ARCHIVE="${ARCHIVE_DIR}/statements"
mkdir -p "$STATEMENT_ARCHIVE"
STMT_COUNT=0
for f in statements/${PERIOD}-*.md; do
    if [ -f "$f" ]; then
        cp "$f" "$STATEMENT_ARCHIVE/"
        STMT_COUNT=$((STMT_COUNT + 1))
    fi
done
echo "  Archived: ${STMT_COUNT} statement(s)"

# Archive usage reports for this period
REPORTS_ARCHIVE="${ARCHIVE_DIR}/usage-reports"
mkdir -p "$REPORTS_ARCHIVE"
REPORT_COUNT=0
for f in data/usage-reports/*${PERIOD}*.json; do
    if [ -f "$f" ]; then
        cp "$f" "$REPORTS_ARCHIVE/"
        REPORT_COUNT=$((REPORT_COUNT + 1))
    fi
done
echo "  Archived: ${REPORT_COUNT} usage report(s)"

# Clear transient data files for next period
rm -f data/normalized-usage.json
rm -f data/royalty-ledger.json
rm -f data/payment-batch.json

# Remove processed usage reports
for f in data/usage-reports/*${PERIOD}*.json; do
    if [ -f "$f" ]; then
        rm "$f"
    fi
done

# Write archive manifest
python3 -c "
import json
from datetime import datetime
manifest = {
    'period': '${PERIOD}',
    'archived_at': datetime.utcnow().isoformat() + 'Z',
    'contents': ['royalty-ledger.json', 'normalized-usage.json', 'payment-batch.json',
                 'advance-balances-snapshot.json', 'statements/', 'usage-reports/']
}
with open('${ARCHIVE_DIR}/manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)
print('  Wrote manifest.json')
"

echo ""
echo "Archive complete: ${ARCHIVE_DIR}/"
echo "Transient data files cleared. Ready for next period."
