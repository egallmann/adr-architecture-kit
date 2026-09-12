# ADR-Kit semantic core contract v1.1

Semantic-core protocol `1.1` is an additive successor to protocol `1.0`.
Protocol `1.0` remains the compatibility contract for every existing
operation. Protocol `1.1` adds only the canonical core operations
`resolve_semantic_contract_set` and `materialize_architecture`.

`resolve_semantic_contract_set` is exact and retained-corpus based. The caller
must provide the requested SCS identity, the complete retained definitions,
sets, qualifications, catalog, and policy. The operation never consults a
current pointer, package default, nearest set, or pairwise compatibility.

`materialize_architecture` interprets a sealed, provider-qualified, host-parsed
source basis under the exact resolved SCS. Hosts own filesystem access and
parsing. The core owns source-contract validation, interpretation,
normalization, identity qualification, deterministic ordering, capability
limitations, and outcome semantics. Wire outcomes are exactly
`Materialized`, `Rejected`, and `Unavailable`; no Runtime materialization
identity is emitted.

The `authorityStateFingerprint` wire value uses the prefix
`asf:v1:sha256:`. Its JCS preimage is:

```json
{"scheme":"adr-kit.authority-state/v1","provider":<canonical qualified provider>,"state":<closed canonical normalized semantic projection>}
```

The projection excludes source revision, provider source identity, SCS
identity, package version, host binding, diagnostics, Runtime identity, and
all fingerprint fields. Source-only revision changes therefore do not change
the fingerprint, while semantic payload or provider qualification changes do.

The source contract closure is the sorted unique set of authoring contracts
actually encountered in the supplied artifacts. It is not the SCS and is not
expanded to every version supported by the package. A source contract that
cannot express a selected semantic capability produces the typed limitation
`not_expressible_by_source_contract`; it does not become an inferred absence.
