# Architecture Stabilization Assessment

## Why a boundary is needed now

The compiler direction is now real: ADR-Kit has an explicit pipeline, compiled
contract artifacts, recursive scope handling, and additive graph projection.
That makes this the right moment to lock the in-process consumer seam before
downstream tools multiply.

If the seam is not defined now, drift pressure will come from:

- direct registry reads by CLI and agent tooling
- future kernel loaders reimplementing bundle semantics
- duplicated relationship interpretation logic
- schema migration pain when registry formats evolve
- direct coupling to scope-local file paths
- unresolved and provenance semantics diverging by consumer

## Options

### Option 1: raw registries only

Pros:
- minimal new code
- matches current compiled contract artifacts

Cons:
- highest drift risk
- every consumer must load YAML, resolve paths, and interpret relationships
- registry schema becomes accidental API
- poor multi-repo and migration resilience

Assessment:
- clarity: low
- determinism: medium
- evolvability: low
- multi-repo readiness: low
- schema migration resilience: low
- consumer simplicity: low
- kernel compatibility: medium
- testing simplicity: low
- provenance support: low
- drift prevention: low
- overengineering risk: low
- under-modeling risk: high

### Option 2: repository-only boundary

Pros:
- centralizes load and validation
- hides some path/layout details
- uses an existing seed (`ArchitectureRepository`)

Cons:
- semantics remain bundle-shaped
- consumers still reason in terms of current registry categories
- schema changes still leak through unless a model layer exists

Assessment:
- clarity: medium
- determinism: high
- evolvability: medium
- multi-repo readiness: medium
- schema migration resilience: medium
- consumer simplicity: medium
- kernel compatibility: medium
- testing simplicity: medium
- provenance support: medium
- drift prevention: medium
- overengineering risk: low
- under-modeling risk: medium

### Option 3: normalized semantic model only

Pros:
- strongest semantic contract
- good future handoff to graph compilation

Cons:
- no stable load/validation boundary
- callers still need path, version, and scope logic
- duplicates repository concerns in every consumer

Assessment:
- clarity: medium
- determinism: medium
- evolvability: medium
- multi-repo readiness: medium
- schema migration resilience: medium
- consumer simplicity: low
- kernel compatibility: medium
- testing simplicity: medium
- provenance support: high
- drift prevention: medium
- overengineering risk: medium
- under-modeling risk: low

### Option 4: repository + normalized semantic model

Pros:
- centralizes file and contract handling
- centralizes semantic interpretation
- hides layout and schema details from consumers
- creates a clean landing zone for future graph compilation
- keeps compiler IR separate from consumer API

Cons:
- slightly more code than the other options
- requires discipline to keep the boundary small

Assessment:
- clarity: high
- determinism: high
- evolvability: high
- multi-repo readiness: high
- schema migration resilience: high
- consumer simplicity: high
- kernel compatibility: high
- testing simplicity: high
- provenance support: high
- drift prevention: high
- overengineering risk: medium
- under-modeling risk: low

## Recommendation

Choose Option 4.

It is the smallest move that materially improves long-term stability. It avoids
turning the registry schemas into a permanent in-process API while also
avoiding a premature kernel-grade meta-model.

## Hard pressure points to address

- `ArchitectureRepository` must stop being treated as just a convenience loader
- `ArchModel` must remain compiler-internal
- unresolved records must stay explicit, not inferred from missing edges
- provenance must remain rich enough for later RECON and embodiment joins
- future federation must consume stable normalized semantics, not raw file
  layouts
