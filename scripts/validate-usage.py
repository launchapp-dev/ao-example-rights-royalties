#!/usr/bin/env python3
"""
validate-usage.py — Validates normalized usage data after ingestion.

Checks:
1. All content IDs in normalized-usage.json exist in the content catalog
2. No negative play counts
3. Date range / period is present and valid
4. At least one platform was processed
5. Flags UNKNOWN content IDs as warnings (not errors)

Exits with code 0 on success (warnings OK), code 1 on critical errors.
"""

import json
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NORMALIZED_FILE = os.path.join(PROJECT_ROOT, "data", "normalized-usage.json")
CATALOG_FILE = os.path.join(PROJECT_ROOT, "config", "content-catalog.yaml")


def load_json(path):
    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path) as f:
        return json.load(f)


def load_catalog_ids(catalog_path):
    """Extract all content IDs from catalog YAML (simple parse without yaml lib)."""
    ids = set()
    if not os.path.exists(catalog_path):
        print(f"ERROR: Catalog file not found: {catalog_path}", file=sys.stderr)
        sys.exit(1)
    with open(catalog_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("- id:"):
                catalog_id = line.split("- id:")[-1].strip()
                if catalog_id:
                    ids.add(catalog_id)
    return ids


def main():
    print("=== Usage Data Validation ===")
    errors = []
    warnings = []

    # Load data
    data = load_json(NORMALIZED_FILE)
    catalog_ids = load_catalog_ids(CATALOG_FILE)

    # Check period field
    period = data.get("period")
    if not period:
        errors.append("CRITICAL: 'period' field missing from normalized-usage.json")
    else:
        print(f"  Period: {period}")

    # Check platforms processed
    platforms = data.get("platforms_processed", [])
    if not platforms:
        warnings.append("WARNING: No platforms listed in 'platforms_processed'")
    else:
        print(f"  Platforms processed: {', '.join(platforms)}")

    # Check records
    records = data.get("records", [])
    if not records:
        errors.append("CRITICAL: No records found in normalized-usage.json")
    else:
        print(f"  Total records: {len(records)}")

    unknown_in_records = set()
    negative_counts = []

    for i, record in enumerate(records):
        content_id = record.get("content_id", "")
        plays = record.get("plays", 0)
        downloads = record.get("downloads", 0)

        # Check catalog membership
        if content_id and content_id not in catalog_ids:
            unknown_in_records.add(content_id)

        # Check for negative counts
        if plays < 0:
            negative_counts.append(f"  Record {i}: content_id={content_id} has negative plays={plays}")
        if downloads < 0:
            negative_counts.append(f"  Record {i}: content_id={content_id} has negative downloads={downloads}")

    # Report unknown IDs in records
    if unknown_in_records:
        errors.append(
            f"CRITICAL: {len(unknown_in_records)} content IDs in records not found in catalog: "
            + ", ".join(sorted(unknown_in_records))
        )

    # Report unknown IDs in the declared unknown_ids field (these are expected to be flagged)
    declared_unknowns = data.get("unknown_ids", [])
    if declared_unknowns:
        warnings.append(
            f"WARNING: {len(declared_unknowns)} unknown platform IDs flagged during ingestion: "
            + ", ".join(declared_unknowns)
        )

    # Report negative counts
    if negative_counts:
        for msg in negative_counts:
            errors.append(f"CRITICAL: {msg}")

    # Check total_play_events consistency
    reported_total = data.get("total_play_events")
    if reported_total is not None:
        actual_total = sum(r.get("plays", 0) for r in records)
        if abs(reported_total - actual_total) > 10:
            warnings.append(
                f"WARNING: total_play_events mismatch — reported={reported_total}, "
                f"sum_of_records={actual_total}"
            )

    # Print results
    print()
    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  {w}")

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        print(f"\nValidation FAILED: {len(errors)} error(s), {len(warnings)} warning(s)")
        sys.exit(1)
    else:
        print(f"\nValidation PASSED: 0 errors, {len(warnings)} warning(s)")
        sys.exit(0)


if __name__ == "__main__":
    main()
