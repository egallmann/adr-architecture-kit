# contracts/architecture-ir — Mirrored Architecture IR Schema

## What This Is

`architecture-ir.schema.json` in this directory is a **local mirror** of the
normative Architecture IR JSON Schema governed by **ste-spec**.

This mirror exists so the repository can be tested and validated as a standalone
checkout without requiring a live `ste-spec` sibling checkout. It does not grant
this repository any authority over the schema's content or evolution.

## Normative Authority

The authoritative source is:

- **Repository:** `ste-spec`
- **Path:** `contracts/architecture-ir/architecture-ir.schema.json`
- **Schema `$id`:** `https://github.com/egallmann/ste-spec/contracts/architecture-ir/architecture-ir.schema.json`

## Current Mirror State

- **Mirrored from:** `ste-spec` `contracts/architecture-ir/architecture-ir.schema.json`
- **Last synced:** 2026-04-11
- **Schema title:** STE Architecture IR (Compiled\_IR\_Document)

## How to Update

When `ste-spec` publishes a new version of the Architecture IR schema:

1. Copy the updated `architecture-ir.schema.json` from the `ste-spec` repository
   into this directory.
2. Update the "Last synced" date above.
3. Commit both the schema update and the MIRROR.md update together.
4. CI will validate that the mirror is internally consistent.

## CI Validation

CI includes an advisory mirror check that compares this file against the sibling
`ste-spec` checkout when one is present. If the sibling is absent, the check is
skipped gracefully (it does not fail the build).

The check is advisory — a drift warning does not block the build, but it is
surfaced in the CI log for review.
