# contracts/design-journal-promotion-contract — Mirrored STE PC Schema

## What This Is

Schemas and conformance fixtures under this directory are a **local mirror** of
the normative STE Design Journal Promotion Contract v0.1. They do not grant this
repository authority over STE semantics.

## Normative Authority

- **Repository:** `ste`
- **Path:** `docs/product-design/contracts/design-journal-promotion-contract/v0.1/`
- **Version ID:** `ste.design_journal.promotion_contract/v0.1`

## Current Mirror State

- **Last synced:** 2026-08-09
- **Pinned version:** v0.1
- Includes `schema.json` and `conformance/*.json` fixtures
- Installed-package schema copy:
  `src/adr_kit/promotion/schemas/promotion_contract_v0_1.json`
  (must byte-match `v0.1/schema.json`; shipped via package data)

## How to Update

Copy updated schema and conformance fixtures from `ste`, update this date,
refresh the packaged copy under `src/adr_kit/promotion/schemas/`, and commit
together. Advisory sibling drift checks may run when `ste` is present.
