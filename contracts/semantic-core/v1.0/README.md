# ADR-Kit semantic core contract v1.0

Protocol `1.0` is immutable compatibility surface. The additive protocol
successor for exact retained-set resolution and sealed architecture
materialization is documented in `../v1.1/README.md`; no v1.0 operation or
observable v1.0 envelope is redefined by that successor.

This directory defines the first portable semantic execution boundary for
ADR-Kit. It is intentionally a normalized JSON contract: host SDKs load
host-owned resources, normalize them, and submit equivalent operation requests
to one semantic authority.

The request and result shape is the public boundary. The operation-discriminated
JSON Schema in `contract.json` governs transport structure, required fields,
diagnostics, and result envelopes; ADRs and canonical schemas continue to own
domain meaning. Python and Node must consume the same implementation artifact
and must not recreate these rules independently.

The packaged semantic core is a self-contained WASM artifact. Its Rust build
dependencies, including `serde` and `serde_json`, are compiled into that
artifact; the Python host additionally depends on `wasmtime` to load it. The
Python package is therefore not dependency-free.

The vectors are conformance evidence, not a second authority. The normative
meaning remains the ADR corpus and the canonical normalized-model schemas.

Version `1.0` currently covers these extracted operation slices:

- contract profiles and allowed completeness states;
- required metadata keys;
- profile-specific sentinel rules;
- deterministic issue ordering;
- sentinel and non-complete counts;
- threshold diagnostics; and
- remediation-ledger references for sentinel-capable fields.
- project-metadata required fields, types, and constrained enumerations.
- provider-registry routing uniqueness and deterministic ordering.
- normalized repository identity fields, namespace/model-version checks, and
  duplicate identity detection.
- generated-artifact integrity status classification from normalized header and
  hash facts.
- non-authoritative embodiment-linkage diagnostics, grouping, and ordering.
- architecture source-validation business rules, cross-reference, and
  topology-membership validation from host-normalized ADR facts.

Repository filesystem discovery, source parsing, projection, and compilation
are not part of this slice. The normalized repository identity check is shared;
the remaining source validation, projection, compilation, and promotion
operations will use the same execution-boundary pattern when their semantic
dependencies are extracted.
