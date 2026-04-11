# Schema v1.0 — Package-Bundled Copy

These JSON Schema files are **package-bundled copies** of the authoring schemas
from `schema/v1.0/` at the repository root.

## Canonical Source

The repository root `schema/v1.0/` directory is the canonical source of truth.
Do not edit the files in this directory directly.

## Purpose

These copies exist so that the `adr_kit` Python package can locate its schemas
via `importlib.resources` when installed as a wheel (i.e. outside the source
tree). They are kept in sync with the repository root copies by CI.

## Sync Rule

When any file in `schema/v1.0/` is updated, the corresponding file in
`src/adr_kit/schema/v1.0/` must be updated in the same commit. CI validates
byte-for-byte parity between the two directories.
