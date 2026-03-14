# System Overview

## Purpose

This document describes `adr-architecture-kit` as a compiler-oriented
architecture knowledge system and identifies the missing stabilizing boundary
between canonical ADR authority and future kernel consumers.

## Current Layers

### Canonical authority

- ADRs under `adrs/`
- standalone invariants under `adrs/invariants/`
- accepted governance decisions and invariants embedded in those artifacts

These source artifacts remain the only canonical architecture authority.

### Compiler layer

- explicit compiler pipeline under `src/adr_kit/compiler/`
- compiler IR represented by `ArchModel`
- deterministic passes for parse, normalization, extraction, relationship
  derivation, unresolved detection, and validation

`ArchModel` is compiler-internal. It is the right place for compiler work, but
it is too implementation-shaped to become the public in-process interface for
all consumers.

### Derived contract and discovery layer

- `architecture-index.yaml`
- `entity-registry.yaml`
- `relationship-registry.yaml`
- `unresolved-registry.yaml`
- subset registries
- compatibility registry
- additive `architecture-graph.yaml`
- manifest and rendered ADR markdown

These artifacts are deterministic derived projections. They are contract and
discovery surfaces, not canonical authority.

### Current consumer boundary

`ArchitectureRepository` already exists as a registry bundle loader and
validator. It is the right seed for a stable boundary, but it currently exposes
bundle-shaped state more than a stable semantic consumer model.

## Missing Stabilizing Boundary

The system still lacks one required semantic layer for in-process consumers.
Without it, different tools can drift into:

- loading registries directly
- reinterpreting relationships independently
- binding to current file layout details
- inventing separate scope and unresolved handling logic
- coupling future kernel consumers to current registry schemas

## Recommended Stabilizing Move

Introduce an explicit Architecture Repository Boundary:

- `ArchitectureRepository` becomes the only supported in-process entry point
- it returns a `NormalizedArchitectureModel`
- the normalized model becomes the stable semantic handoff surface for tools,
  validators, agents, and future graph compilation

This keeps canonical authority in ADRs, preserves registries as derived
artifacts, and creates one trusted semantic boundary without implementing the
kernel inside ADR-Kit.
