# Authoring Domain Contract

`v1.0/contract.json` is the canonical, language-neutral Authoring Domain
Contract (ADC) semantic authority. It is maintained independently of canonical
ADR persistence-schema versions and is not generated from Python models,
TypeScript types, JSON Schema definitions, registries, or compiler IR.

The authority boundary is:

```text
contract.json
    = language-neutral ADC semantic authority

schema.json
    = structural validation only

compatibility contracts
    = Python/TypeScript implementation and package support state

runtime capabilities()
    = installed binding capability truth
```

The companion `schema.json` validates the artifact’s structural envelope only;
it does not define or generate the admitted catalog. Bindings may package or
project this artifact, but must not maintain an independent semantic catalog.

ADC 1.0 defines only `authoring.discovery` and the operations
`describe_contract`, `list_types`, and `describe_type`. The exact observable
projections of those three operations are canonical ADC semantics in
`discovery_projections`; they are not inferred from binding conformance
evidence.

It does not authorize construction, composition, mutation, identity
allocation, persistence, or repository writes.

The TypeScript `./authoring` browser-safe subpath remains the intended binding
surface. Its implementation status, like Python discovery support, is governed
by compatibility contracts and executable runtime capability manifests rather
than canonical ADC semantic content; both remain planned/not implemented in
this checkpoint.

