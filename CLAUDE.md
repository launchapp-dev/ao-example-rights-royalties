# Rights & Royalties Manager — Agent Context

This is a rights and royalties management pipeline. It processes content usage data from streaming platforms, calculates royalties per agreement terms, generates rights holder statements, and conducts periodic audits.

## What This System Does

- **Ingest**: Reads monthly usage reports from Spotify, Apple Music, YouTube (data/usage-reports/)
- **Normalize**: Maps platform-specific IDs to catalog IDs, aggregates by content+platform+territory
- **Calculate**: Applies tiered rates, revenue share, flat fees, splits, and advance recoupment
- **Statement**: Generates per-rights-holder markdown statements in statements/
- **Payment**: Applies thresholds, withholding, and creates payment-batch.json
- **Audit**: Quarterly cross-check of all calculations and data completeness
- **Reconcile**: Adjusts ledger for any discrepancies found, reissues amended statements

## Key Files

| File | Purpose |
|---|---|
| `config/agreements.yaml` | Rights holder agreements with rate structures and payment preferences |
| `config/content-catalog.yaml` | Master content catalog: IDs, titles, rights holder mappings |
| `config/platform-config.yaml` | Platform field mappings, currencies, rate types |
| `config/payment-rules.yaml` | Minimum thresholds, withholding rates by territory, payment methods |
| `data/usage-reports/*.json` | Raw platform usage reports (input) |
| `data/normalized-usage.json` | Aggregated usage (written by usage-tracker, read by royalty-calculator) |
| `data/royalty-ledger.json` | Calculated royalties (written by royalty-calculator) |
| `data/advance-balances.json` | Advance recoupment state (updated by royalty-calculator each period) |
| `data/payment-batch.json` | Payment instructions (written by payment-processor) |
| `data/audit-findings.json` | Audit results (written by auditor) |
| `data/reconciliation-log.json` | Reconciliation history (written by reconciler) |
| `data/history/YYYY-MM/` | Archived period data |
| `statements/` | Per-holder royalty statements |
| `reports/` | Quarterly audit reports |

## Rate Calculation Logic

### Tiered Rates
Tiers are applied incrementally to total plays:
- First N plays at rate_tier_1, next M plays at rate_tier_2, remainder at rate_tier_3
- Total royalty = (min(plays, tier1_threshold) × rate_1) + (min(plays - tier1, tier2_threshold) × rate_2) + ...

### Multi-party Splits
When content has co-rights-holders, the total royalty is split by the percentages in agreements.yaml.
All split percentages for a content item must sum to 1.0 (100%).

### Advance Recoupment
Holders with unrecouped advances receive no net payment until the advance is fully recouped.
Gross royalties are applied to the advance balance first; the remaining gross (if any) becomes net payable.
The balance in data/advance-balances.json is updated each period.

### Revenue Share (YouTube)
For revenue_share agreements, royalty = platform_reported_revenue_usd × revenue_share_pct.
No per-play rate is applied.

## Workflow Routing Notes

- `review-calculations` verdict `recalculate` sends back to `calculate-royalties` (max 2 attempts)
- `process-payments` verdict `hold` is normal — it means all holders are below the $50 threshold
- `process-payments` verdict `disputed` is a critical failure requiring human review
- `assess-findings` verdict `escalate` stops the quarterly audit for manual intervention

## Naming Conventions

- Statement files: `statements/YYYY-MM-<holder-slug>.md`
  - holder-slug = lowercase, hyphens for spaces (e.g., "jane-doe", "bright-wave-media")
- Amended statements: `statements/YYYY-MM-<holder-slug>-amended.md`
- Audit reports: `reports/audit-YYYY-QN.md` (e.g., `reports/audit-2026-Q1.md`)
- History archives: `data/history/YYYY-MM/`

## Data Integrity Rules

1. Never delete original ledger entries — only append adjustment entries
2. Never overwrite original statements — write amended versions as new files
3. Advance balances must never go negative (can reach 0 but not below)
4. Net royalties must never be negative for a period (floor at 0)
5. All split percentages across co-holders must sum to exactly 1.0

## Important Notes for Agents

- The `validate-usage.py` script exits non-zero on CRITICAL errors (unknown IDs in records, negative counts) — if it fails, the workflow stops before calculation
- Usage reports are named `platform-YYYY-MM.json` but check the internal `period` or `month` field for the authoritative period
- Territory codes in platform reports may be ISO country codes, Apple storefront numbers, or "WORLD" — use platform-config.yaml to map them
- YouTube reports use revenue_share model — do NOT apply per-play rates to YouTube plays
