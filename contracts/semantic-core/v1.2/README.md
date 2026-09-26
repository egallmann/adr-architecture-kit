# Semantic-core protocol 1.2

Semantic-core protocol 1.2 is an additive transport boundary for the two
Authoring Construction Contract 1.0 operations:

- `validate_authoring`
- `construct_authoring_set`

The envelope routes an exact ACC 1.0 request or result. ACC remains the sole
authority for request DTOs, result DTOs, exact basis qualification, fragment,
reference, composition, relationship, diagnostic, outcome, detached-candidate,
and round-trip semantics. This protocol contract intentionally validates only
the versioned envelope and agreement between its outer and inner operations.

Protocol 1.0 and 1.1 remain separate additive surfaces. Protocol 1.2 executes
both operations through the canonical Rust/WASM dispatcher. Low-level Python
and Node adapters advertise the exact supported version and operation surface;
they do not add author-facing construction APIs or semantic implementations.

The transport conformance vectors reference the frozen ACC C01-C42 corpus
instead of copying its meaning-bearing inputs or expected outputs.
