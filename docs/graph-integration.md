# Graph Integration Guide

## Purpose

This document describes how `adr-architecture-kit` relates to graph-oriented downstream consumers such as `ste-runtime`.

It is an integration note, not the normative Architecture IR contract.

## Boundary

`adr-architecture-kit` owns:

- ADR encoding and validation
- repository-normalized discovery outputs
- ADR-derived IR adapter outputs

`ste-runtime` owns:

- runtime observation and evidence extraction
- graph composition and query behavior
- consumption of upstream architecture surfaces without redefining them

## Recommended Consumption Posture

For cross-language or out-of-process consumers, start from the repository-normalized discovery bundle:

- `adrs/index/architecture-index.yaml`
- `adrs/index/entity-registry.yaml`
- `adrs/index/relationship-registry.yaml`
- `adrs/index/unresolved-registry.yaml`
- `adrs/manifest.yaml`

Treat that bundle as the repository-owned discovery surface.

Do not treat it as a replacement for the public Architecture IR contract owned by `ste-spec`.

## Relation To Public Architecture IR

This repository has two downstream-facing machine surfaces:

- repository-normalized discovery bundle
- ADR-derived Architecture IR adapter outputs

The first is for repository discovery and semantic loading. The second targets the public cross-repo IR contract.

## Practical Rule

- use `adrs/index/*` and `adrs/manifest.yaml` for repository-local architecture discovery
- use `ste-spec` for the normative Architecture IR schema
- do not recreate architecture authority by treating downstream graph projections as the source of truth

## Related

- [architecture-ir-overview.md](architecture-ir-overview.md)
- [authority-boundary.md](authority-boundary.md)
