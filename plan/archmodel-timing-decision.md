# ArchModel Timing Decision

## Decision

Defer kernel-grade `ArchModel` work.

Keep the current `ArchModel` as the compiler IR and build the stable landing
zone now through:

- `ArchitectureRepository`
- `NormalizedArchitectureModel`

## Why

The current compiler IR is already useful and correct for pipeline work, but it
is not yet the right public contract because:

- it reflects compiler staging concerns
- it is mutable and pass-oriented
- it may evolve as extraction logic and graph preparation change
- exposing it now would freeze the wrong abstraction too early

## What is deferred

- supergraph semantics
- runtime merge semantics
- graph-native query behavior
- federation load and merge behavior
- kernel execution semantics
- rich embodiment/provenance joins beyond preserving compatibility hooks

## What must exist now

- stable model types for consumer semantics
- repository loader and validation boundary
- schema and path hiding adapters
- explicit unresolved representation
- provenance-preserving semantics
- local identity rules that can later compose into qualified IDs

## Landing-zone rule

When kernel-grade graph work begins later, it should land on the normalized
model boundary rather than re-reading compiled registries directly.
