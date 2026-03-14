# Implementation Roadmap

## Phase 1: Governance lock

- add a logical ADR for the Architecture Repository Boundary
- add an invariant forbidding ad hoc registry interpretation when the boundary
  exists
- cross-link discovery, contract, and federation ADRs

## Phase 2: Boundary hardening

- refactor `ArchitectureRepository` from bundle loader to bundle loader plus
  semantic adapter
- add `NormalizedArchitectureModel`
- preserve deterministic fingerprinting and scope-safe loading

## Phase 3: Consumer migration

- move CLI entity queries to the repository boundary
- migrate internal validators and agents to repository/model access
- keep raw registry access only for generation, validation internals, and tests
  that explicitly target compiled artifacts

## Phase 4: Compatibility and resilience

- add schema-version adapter tests
- add legacy-to-normalized semantic adaptation tests
- add qualified-identity compatibility seams without implementing federation

## Phase 5: Deferred future work

- federation loader
- graph materialization from normalized model
- richer provenance joins with RECON and embodiment evidence
- kernel graph query surfaces

## Low-risk first steps

- governance artifacts
- normalized model type
- repository semantic export
- CLI migration
- parity tests
