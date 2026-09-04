# Authoring Domain Contract

`v1.0/contract.json` is the canonical, language-neutral Authoring Domain
Contract (ADC) authority. It is maintained independently of canonical ADR
persistence-schema versions and is not generated from Python models, TypeScript
types, JSON Schema definitions, registries, or compiler IR.

The companion `schema.json` validates the artifact’s structural envelope only;
it does not define or generate the admitted catalog. Bindings may package or
project this artifact, but must not maintain an independent semantic catalog.

ADC 1.0 defines only `authoring.discovery` and the operations
`describe_contract`, `list_types`, and `describe_type`. It does not authorize
construction, composition, mutation, identity allocation, persistence, or
repository writes.

The TypeScript `./authoring` browser-safe subpath is promoted as a planned
binding surface in the compatibility contract, but remains deliberately
unimplemented in this checkpoint. Python discovery callables are likewise
deferred to the implementation-plan phase.
