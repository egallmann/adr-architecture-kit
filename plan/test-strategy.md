# Test Strategy

## Boundary behavior

- repository fingerprint remains deterministic across repeated loads
- reload reflects on-disk changes only after explicit refresh
- normalized model contents match the compiled bundle semantics

## Semantic parity

- entities, relationships, and unresolved records are preserved without loss
- relationship interpretation is centralized in one place
- legacy compatibility bundles adapt into the normalized model deterministically

## Scope and safety

- scope resolution remains isolated per scope
- recursive workflows do not merge scope-local models implicitly
- index path traversal and malformed bundle failures still stop load

## Evolution safety

- schema changes can be absorbed behind repository/model adapters
- local IDs remain stable while future qualified IDs can be layered on top
- provenance fields survive adaptation paths needed for RECON and embodiment
  evidence joins

## Regression coverage

- CLI entity queries use the repository boundary
- kernel contract validation behavior is unchanged
- generated artifact validation still passes after ADR and invariant updates
