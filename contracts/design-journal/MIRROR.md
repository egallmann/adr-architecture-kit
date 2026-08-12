# contracts/design-journal — Mirrored STE Design Journal Schema

## What This Is

Schemas under this directory are a **local mirror** of the normative STE Design
Journal reference contract. They exist so adr-architecture-kit can validate
standalone without a live `ste` sibling checkout.

## Normative Authority

- **Repository:** `ste`
- **Path:** `docs/product-design/contracts/design-journal/v0.1/`
- **Version ID:** `ste.design_journal/v0.1`

## Current Mirror State

- **Last synced:** 2026-08-09
- **Pinned version:** v0.1

## How to Update

Copy updated `schema.json` from the `ste` repository into `v0.1/`, update this
date, and commit together. When a sibling `ste` checkout is present, CI may
advisory-compare for drift.
