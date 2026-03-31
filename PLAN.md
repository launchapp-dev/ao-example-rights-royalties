# Rights & Royalties Manager — Build Plan

## Overview

A rights and royalties management pipeline for content creators, publishers, and distributors. Tracks content usage across platforms, calculates royalties per agreement terms, generates royalty statements, flags discrepancies, and produces reconciliation reports. Runs on autopilot with monthly royalty runs and quarterly audits.

---

## Agents

| Agent | Model | Role |
|---|---|---|
| **usage-tracker** | claude-haiku-4-5 | Ingests and normalizes usage data from multiple platforms (streaming counts, downloads, syndication plays). Aggregates raw logs into structured usage records per content item. |
| **royalty-calculator** | claude-sonnet-4-6 | Applies agreement terms (rate tiers, minimums, advances, splits) to usage data. Calculates gross and net royalties per rights holder. Uses sequential-thinking for complex multi-tier and escalating rate calculations. |
| **statement-generator** | claude-haiku-4-5 | Produces formatted royalty statements per rights holder — itemized usage, rate applied, gross amount, deductions, net payable. Writes statements as markdown files. |
| **payment-processor** | claude-sonnet-4-6 | Reviews calculated royalties against payment thresholds, advance recoupment, and withholding rules. Produces a payment batch file and flags any holds or disputes. Decision phase. |
| **auditor** | claude-opus-4-6 | Conducts periodic audits — cross-references usage data against source reports, validates calculation accuracy, checks for missing content or unreported usage. Produces audit findings. |
| **reconciler** | claude-sonnet-4-6 | Resolves discrepancies found by auditor — traces root causes, proposes adjustments, updates ledger entries, and produces reconciliation summaries. |

## MCP Servers

| Server | Purpose |
|---|---|
| `filesystem` | Read/write all config, data, and output files |
| `sequential-thinking` | Complex royalty calculation reasoning (tiered rates, advance recoupment, multi-party splits) |

---

## Data Model

| File | What It Contains | Who Reads | Who Writes |
|---|---|---|---|
| `config/agreements.yaml` | Rights holder agreements: parties, content catalog, rate structures (per-stream, per-download, flat fee), advance amounts, split percentages, payment thresholds, withholding rates | royalty-calculator, payment-processor, auditor | Static config (updated when agreements change) |
| `config/content-catalog.yaml` | Master catalog of all content: IDs, titles, type (song, episode, article, book), rights holders, territory restrictions, active/inactive status | usage-tracker, royalty-calculator, auditor | Static config (updated when new content added) |
| `config/platform-config.yaml` | Platform definitions: name, report format expectations, rate type, currency, reporting frequency | usage-tracker | Static config |
| `config/payment-rules.yaml` | Payment thresholds (minimum payout), advance recoupment schedule, withholding tax rates by territory, payment methods per rights holder | payment-processor | Static config |
| `data/usage-reports/` | Raw usage reports per platform per period (CSV/JSON) — platform name, content ID, play/download/view count, territory, date range | usage-tracker | External import (simulated via sample data) |
| `data/normalized-usage.json` | Aggregated usage records: content ID, total plays per platform, territory breakdown, period | royalty-calculator, auditor | usage-tracker |
| `data/royalty-ledger.json` | Calculated royalties per rights holder per period: content, usage count, rate applied, gross amount, deductions, net amount, running balance | statement-generator, payment-processor, auditor, reconciler | royalty-calculator |
| `data/advance-balances.json` | Current advance recoupment status per rights holder: original advance, recouped to date, remaining | royalty-calculator, payment-processor | royalty-calculator (updated each run) |
| `data/payment-batch.json` | Payment instructions: rights holder, net payable, payment method, currency, hold/release status, notes | External (payment system) | payment-processor |
| `data/audit-findings.json` | Audit results: discrepancies found, severity, affected content/periods, recommended actions | reconciler | auditor |
| `data/reconciliation-log.json` | Adjustments made: original amount, corrected amount, reason, affected statement, date | auditor (next cycle), statement-generator (reissue) | reconciler |
| `data/history/` | Archived royalty ledgers, payment batches, and audit reports by period | auditor, reconciler | Archive scripts |
| `statements/` | Per-rights-holder royalty statements (markdown) — one per holder per period | Rights holders (reference) | statement-generator |
| `reports/` | Audit reports, reconciliation summaries, annual royalty summaries (markdown) | Management reference | auditor, reconciler |

---

## Phases

### Monthly Royalty Run (scheduled monthly)

| Phase | Mode | Agent | What It Does |
|---|---|---|---|
| `ingest-usage` | agent | usage-tracker | Reads raw usage reports from data/usage-reports/, normalizes across platforms (maps platform-specific content IDs to catalog IDs, converts currencies, aggregates by content+territory), writes data/normalized-usage.json |
| `validate-usage` | command | — | Runs validation script: checks all content IDs exist in catalog, flags unknown IDs, verifies no negative counts, checks date range matches expected period. Exits non-zero on critical errors. |
| `calculate-royalties` | agent | royalty-calculator | Reads normalized-usage.json and agreements.yaml. For each content item: looks up applicable rate structure, applies tiered rates (e.g., first 100K streams at $0.004, next 500K at $0.003), calculates per-holder splits, applies advance recoupment. Uses sequential-thinking for multi-tier calculations. Writes royalty-ledger.json and updates advance-balances.json. |
| `review-calculations` | agent | auditor | Spot-checks royalty calculations: verifies rate application matches agreement terms, checks split percentages sum to 100%, validates advance recoupment doesn't exceed earnings. Decision: `approved` / `recalculate` |
| `generate-statements` | agent | statement-generator | Reads royalty-ledger.json, generates per-rights-holder statements to statements/YYYY-MM-holder-name.md. Each statement: period, itemized usage per content, rate applied, gross, deductions (advance recoup, withholding), net payable. |
| `process-payments` | agent | payment-processor | Reads royalty-ledger.json and payment-rules.yaml. Checks each holder's net against minimum payout threshold. Applies withholding tax by territory. Creates payment-batch.json with pay/hold decisions. Decision: `approved` / `disputed` / `hold` |
| `archive-period` | command | — | Copies current period's ledger, statements, and payment batch to data/history/YYYY-MM/. Resets usage-reports/ for next period. |

### Quarterly Audit (scheduled quarterly)

| Phase | Mode | Agent | What It Does |
|---|---|---|---|
| `run-audit` | agent | auditor | Comprehensive audit of last 3 months: cross-references normalized usage against raw source reports, validates all content in catalog was reported, checks for duplicate entries, verifies royalty calculations against agreement terms, compares payment totals against ledger totals. Writes audit-findings.json. |
| `assess-findings` | agent | auditor | Reviews findings severity. Decision: `clean` (no issues) / `discrepancy` (needs reconciliation) / `escalate` (potential fraud or systemic error) |
| `reconcile` | agent | reconciler | For each discrepancy: traces root cause (missing report, rate error, split error, duplicate), calculates adjustment amount, updates reconciliation-log.json, flags affected statements for reissue. |
| `reissue-statements` | agent | statement-generator | Regenerates corrected statements for any rights holders affected by reconciliation adjustments. Marks as "Amended" with correction details. |
| `compile-audit-report` | agent | auditor | Produces quarterly audit report to reports/audit-YYYY-QN.md: summary of findings, adjustments made, systemic issues identified, recommendations. |

---

## Workflow Routing

### Monthly Royalty Run

```
ingest-usage → validate-usage → calculate-royalties → review-calculations
                                                            │
                                              ┌─────────────┴──────────────┐
                                          approved                    recalculate
                                              │                           │
                                    generate-statements          (back to calculate-royalties)
                                              │                     max 2 rework attempts
                                    process-payments
                                         │
                          ┌──────────────┼──────────────┐
                      approved       disputed          hold
                          │              │               │
                    archive-period   (logged, manual)  (logged, next cycle)
```

- `review-calculations` rework → loops back to `calculate-royalties` (max 2 attempts)
- `process-payments` verdicts:
  - `approved` → advance to `archive-period`
  - `disputed` → workflow fails with dispute details for manual review
  - `hold` → advance to `archive-period` (holds are normal for under-threshold balances)

### Quarterly Audit

```
run-audit → assess-findings
                │
       ┌────────┼────────────┐
     clean   discrepancy   escalate
       │         │            │
    compile   reconcile    (workflow fails,
    audit     → reissue     manual escalation)
    report    → compile
                audit
                report
```

- `assess-findings` on `clean` → skip reconciliation, go to `compile-audit-report`
- `assess-findings` on `discrepancy` → reconcile → reissue-statements → compile-audit-report
- `assess-findings` on `escalate` → workflow fails with escalation notice

---

## Supporting Files

### Scripts

| Script | Purpose |
|---|---|
| `scripts/validate-usage.py` | Validates normalized usage data against content catalog, checks for anomalies |
| `scripts/archive-period.sh` | Moves current period data to history/, clears usage-reports/ for next period |

### Sample Data

| File | Contents |
|---|---|
| `data/usage-reports/spotify-2026-03.json` | Sample Spotify streaming report (~20 tracks, play counts by territory) |
| `data/usage-reports/apple-music-2026-03.json` | Sample Apple Music report (same catalog, different counts) |
| `data/usage-reports/youtube-2026-03.json` | Sample YouTube report (video plays, ad revenue share) |

### Config Templates

| File | Contents |
|---|---|
| `config/agreements.yaml` | 4 sample agreements: 2 artists (different rate tiers), 1 publisher (flat fee + per-use), 1 distributor (revenue share) |
| `config/content-catalog.yaml` | ~30 content items across music, podcast, video — mapped to rights holders |
| `config/platform-config.yaml` | 3 platforms: Spotify, Apple Music, YouTube — with rate types and currencies |
| `config/payment-rules.yaml` | Min payout $50, withholding rates by territory (US 0%, EU 15%, RoW 20%), payment methods |

---

## README Outline

1. **Header** — Rights & Royalties Manager badge/title
2. **What It Does** — One paragraph: tracks content usage, calculates royalties, generates statements, audits
3. **Architecture Diagram** — ASCII flow showing agents and data movement
4. **Quick Start** — Clone, configure agreements, add usage reports, `ao daemon start`
5. **Configuration** — How to set up agreements, content catalog, platform config, payment rules
6. **Workflows** — Monthly royalty run, quarterly audit (with routing diagrams)
7. **Output Examples** — Sample royalty statement, audit report excerpts
8. **Customization** — Adding platforms, rate structures, rights holders
9. **AO Features Demonstrated** — List of features with explanations

---

## AO Features Demonstrated

- **Multi-agent pipeline** — 6 specialized agents with distinct roles (tracker, calculator, generator, processor, auditor, reconciler)
- **Scheduled workflows** — Monthly royalty run + quarterly audit on cron
- **Decision contracts** — review-calculations (approved/recalculate), process-payments (approved/disputed/hold), assess-findings (clean/discrepancy/escalate)
- **Phase routing with rework loops** — Calculation rework on review failure, reconciliation loop on audit discrepancy
- **Command phases** — Usage validation script, period archival script
- **Model variety** — Opus for audit (needs deep reasoning), Sonnet for calculation/reconciliation, Haiku for ingestion/statement generation
- **Sequential-thinking MCP** — Complex multi-tier royalty calculations
- **Output contracts** — Structured royalty ledger, payment batch, audit findings
