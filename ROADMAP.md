# ADR Architecture Kit Roadmap

## Summary

The current roadmap is centered on making `adr-architecture-kit` a clean public STE component for canonical ADR encoding, repository-normalized discovery, and ADR-derived Architecture IR adaptation.

The near-term priority is not a large internal refactor. It is surface stabilization:

- clarify the repository role
- document stable versus draft versus experimental areas
- add standalone onboarding examples
- keep the authority split with `ste-spec`, `ste-runtime`, and `ste-kernel` explicit

## Current Priority Track

### 1. Public surface clarification

- keep `ste-spec` explicit as the owner of the normative Architecture IR contract
- present this repository as the canonical ADR encoding and IR adapter layer
- keep `ArchModel` compiler-internal
- make the repository-normalized discovery bundle a clearly named public surface

### 2. Public documentation cleanup

- maintain a README that explains the repository role without assuming a private workspace
- keep one canonical ADR type model document
- document the authority boundary across handbook, spec, kit, runtime, and kernel
- keep graph integration docs framed as downstream integration notes rather than contract ownership

### 3. Onboarding and examples

- provide a minimal public ADR example set
- include resulting normalized outputs
- include an ADR-derived IR fragment example
- document the end-to-end walkthrough from ADR source to discovery bundle to IR adapter output

### 4. Stability policy

- treat `schema/v1.0/` as stable
- keep `schema/v1.1/` draft
- keep `ADR-V-*`, migrators, and boot publication examples experimental
- separate reference implementation assets from normative surfaces

## Ongoing Engineering Work

The existing compiler and governance work remains important, but it should now be expressed through the public-surface lens:

- authoring-time compiler path remains the repository discovery/compiler surface
- normalized bundle and repository boundary remain the intended Python consumer seam
- ADR-derived IR compilation remains an adapter into `ste-spec`
- workspace-only or boot-specific publication assets remain examples, not core public API

## Completion Markers

This public-readiness phase is in good shape when:

- the top-level docs tell one consistent story
- external readers can tell which surface is normative, stable, draft, or experimental
- the repo can be understood without access to a private sibling workspace
- example assets demonstrate the end-to-end flow without relying on local lore
