# Normalized model v2.1

Model v2.1 is an additive successor to v2.0. Existing read paths remain
available. Core normalized entities never gain extension semantics; a
qualified extension entity requires the typed `extension` payload.

Canonical relationship records are identity-bearing entities with persisted
UUIDv7 IDs and UUID endpoints. Hash-derived legacy relationship and assertion
identifiers are mechanically distinct compatibility records. A hash-only
relationship is never admitted as a v2.1 canonical graph edge.
