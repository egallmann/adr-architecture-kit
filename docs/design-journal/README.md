# Design Journal directory

## Authority model

```text
DESIGN_JOURNAL_DURABLE_AUTHORITY=NO
DESIGN_JOURNAL_VERSIONED_HISTORY=NO
PREPARED_PROMOTION_CONTRACT_DURABLE_AUTHORITY=NO
PROMOTED_SUBSTRATE_DURABLE_AUTHORITY=YES
```

STE Design Journals are **local convergence artifacts**. They support explore →
evaluate → decide → lock readiness → prepare promotion. They are not durable
architecture authority and must not become a second versioned history of intent.

After a successful promotion, current architectural intent is reconstructed from
the promoted substrate (`adrs/**`, `ROADMAP.md`, and related governed artifacts)
and its Git history — not from historical Design Journals.

Prepared Promotion Contracts are **local mechanical handoffs** for review and
human lock. Default persistence is under the existing ignored kit state root
(`.adr-kit/`). They are not repository authority.

## What is tracked here

Only explanatory **process notes** from earlier kit phases (not STE DJ durable
authority):

- `2026-phase-1-public-sdk.md`
- `2026-phase-2-schema-v12.md`
- `2026-production-hardening.md`

Those documents point at ADRs as authority. Keeping them versioned does not make
STE Design Journals durable project memory.

## Local working state (ignored)

Active STE Design Journal / A-N handoff / prepared-PC working files under this
directory are gitignored. Prefer writing new prepared handoffs via the provider
default under `.adr-kit/promotion/`. Do not commit local journals, `_an-handoff/`,
or `_prepared/` as architecture history.
