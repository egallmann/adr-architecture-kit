# Schema v1.1 — Package-Bundled Copy

These JSON Schema files are **package-bundled copies** of the authoring schemas
from the family-scoped v1.1 schemas at the repository root.

## Canonical Source

The repository root `schema/` family directories are the canonical source of truth.
Do not edit the files in this directory directly.

## Purpose

These copies exist so that the `adr_kit` Python package can locate its schemas
via `importlib.resources` when installed as a wheel (i.e. outside the source
tree). They are kept in sync with the repository root copies by CI.

## Sync Rule

When any mirrored v1.1 file in `schema/` is updated, the corresponding file in
`src/adr_kit/schema/v1_1/` must be updated in the same commit. CI validates
byte-for-byte parity through the explicit inventory mappings.
