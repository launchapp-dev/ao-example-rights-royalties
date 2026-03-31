# Rights & Royalties Manager

Automates end-to-end royalty management for content creators, publishers, and distributors — ingesting usage data from streaming platforms, calculating royalties against agreement terms, generating statements, processing payments, and conducting periodic audits with full reconciliation.

---

## Architecture

```
MONTHLY ROYALTY RUN
─────────────────────────────────────────────────────────────────────────

  [Spotify / Apple Music / YouTube reports]
               │
               ▼
    ┌──────────────────┐
    │  usage-tracker   │  Normalize and aggregate usage data
    │  (haiku)         │  → data/normalized-usage.json
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │ validate-usage   │  Python validation: catalog IDs, no negatives
    │ (command)        │  Exits non-zero on critical errors
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │royalty-calculator│  Apply tiered rates, splits, advance recoupment
    │(sonnet + seq-    │  → data/royalty-ledger.json
    │ thinking)        │  → data/advance-balances.json (updated)
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │    auditor       │  Spot-check rates, splits, advance math
    │    (opus)        │  verdict: approved / recalculate ──────────┐
    └────────┬─────────┘                                            │
             │ approved                                             │
             ▼                                             (max 2 rework attempts)
    ┌──────────────────┐                                            │
    │statement-generator│  Per-holder statements → statements/      │
    │    (haiku)        │  YYYY-MM-holder-name.md                   │
    └────────┬──────────┘                                           │
             │                                                      │
             ▼                                                      │
    ┌──────────────────┐         ┌──────────────────────────────────┘
    │payment-processor │         │
    │    (sonnet)      │─────────┘
    │                  │
    │ approved ──────► archive-period (command: copy to history/, clear)
    │ hold     ──────► archive-period (holds accumulate to next period)
    │ disputed ──────► FAIL (manual review required)
    └──────────────────┘


QUARTERLY AUDIT
─────────────────────────────────────────────────────────────────────────

    ┌──────────────────┐
    │    auditor       │  Cross-reference 3 months of data, validate
    │    (opus)        │  → data/audit-findings.json
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐
    │    auditor       │  Assess severity
    │ assess-findings  │
    └─────┬──────┬─────┘
          │      │           │
        clean  discrepancy  escalate
          │      │           │
          │      ▼           └──► FAIL (manual escalation)
          │  ┌─────────┐
          │  │reconciler│  Adjust ledger, log changes
          │  │(sonnet)  │  → data/reconciliation-log.json
          │  └────┬─────┘
          │       │
          │       ▼
          │  ┌─────────────────┐
          │  │statement-generator│  Regenerate amended statements
          │  │    (haiku)        │  YYYY-MM-holder-amended.md
          │  └────────┬─────────┘
          │           │
          └─────┬─────┘
                ▼
    ┌──────────────────┐
    │    auditor       │  Quarterly audit report
    │compile-audit-    │  → reports/audit-YYYY-QN.md
    │   report (opus)  │
    └──────────────────┘
```

---

## Quick Start

```bash
cd examples/rights-royalties
ao daemon start

# Run the monthly royalty run immediately
ao workflow run monthly-royalty-run

# Run the quarterly audit
ao workflow run quarterly-audit

# Or let schedules handle it automatically
# Monthly run: 1st of each month at 6am
# Quarterly audit: Jan/Apr/Jul/Oct 1st at 8am
```

---

## Agents

| Agent | Model | Role |
|---|---|---|
| **usage-tracker** | claude-haiku-4-5 | Reads platform reports, maps content IDs, aggregates to normalized-usage.json |
| **royalty-calculator** | claude-sonnet-4-6 | Applies tiered rates and splits from agreements, handles advance recoupment |
| **statement-generator** | claude-haiku-4-5 | Produces itemized royalty statements per rights holder, handles amendments |
| **payment-processor** | claude-sonnet-4-6 | Applies payment thresholds and withholding, creates payment batch |
| **auditor** | claude-opus-4-6 | Spot-checks calculations, runs quarterly audits, assesses finding severity |
| **reconciler** | claude-sonnet-4-6 | Resolves discrepancies, adjusts ledger, maintains reconciliation log |

---

## Workflows

### `monthly-royalty-run` (scheduled: 1st of each month, 6am)

Processes one month of usage data end-to-end:
- **Rework loop**: If auditor finds calculation errors, routes back to royalty-calculator (max 2 retries)
- **Payment routing**: `approved` → archive; `hold` → archive (balance accumulates); `disputed` → manual review

### `quarterly-audit` (scheduled: Jan/Apr/Jul/Oct 1st, 8am)

Audits last 3 months of data:
- **Decision routing**: `clean` skips reconciliation; `discrepancy` triggers reconcile + reissue; `escalate` fails for manual intervention

---

## Configuration

### Adding a Rights Holder

Add an entry to `config/agreements.yaml` with rate structure, payment preferences, and advance balance. Add corresponding content to `config/content-catalog.yaml`.

### Adding a Platform

Add platform definition to `config/platform-config.yaml` including field mappings and currency. The usage-tracker agent reads this config to normalize reports.

### Rate Structures

Three types supported in `config/agreements.yaml`:
- `tiered` — per-play rates with thresholds (e.g., first 100K @ $0.004, next 500K @ $0.003)
- `flat` — fixed per-download rate plus optional minimum guarantee
- `revenue_share` — percentage of platform-reported revenue

---

## Data Flow

```
data/usage-reports/    → (usage-tracker)   → data/normalized-usage.json
config/agreements.yaml → (royalty-calc)    → data/royalty-ledger.json
data/royalty-ledger    → (stmt-generator)  → statements/YYYY-MM-*.md
data/royalty-ledger    → (payment-proc)    → data/payment-batch.json
data/audit-findings    → (reconciler)      → data/reconciliation-log.json
all of the above       → (archive-period)  → data/history/YYYY-MM/
```

---

## AO Features Demonstrated

| Feature | Where |
|---|---|
| **Multi-agent pipeline** | 6 agents with distinct specialized roles |
| **Scheduled workflows** | Monthly royalty run + quarterly audit on cron |
| **Decision contracts** | `review-calculations` (approved/recalculate), `process-payments` (approved/disputed/hold), `assess-findings` (clean/discrepancy/escalate) |
| **Phase routing with rework loops** | `review-calculations` → loops back to `calculate-royalties` on recalculate |
| **Conditional routing** | `assess-findings` verdict routes to reconcile, compile, or fail |
| **Command phases** | `validate-usage` (Python), `archive-period` (Bash) |
| **Model variety** | Opus for deep audit reasoning, Sonnet for calculation/payment, Haiku for ingestion/statements |
| **Sequential-thinking MCP** | Complex multi-tier royalty calculations |
| **Output contracts** | Structured ledger, payment batch, audit findings |

---

## Requirements

- **AO CLI** installed and running
- **Node.js** (for MCP servers via npx)
- **Python 3** (for validation and archive scripts)
- No external API keys required — all processing is local file-based

Human configuration required before first run:
1. Update `config/agreements.yaml` with real rights holder agreements
2. Populate `config/content-catalog.yaml` with your content catalog
3. Place platform usage reports in `data/usage-reports/` (JSON format per platform config)
4. Review `config/payment-rules.yaml` for correct payment thresholds and withholding rates
