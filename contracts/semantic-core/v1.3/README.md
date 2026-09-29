# Semantic-core protocol 1.3

Protocol 1.3 is the closed successor transport boundary for
`materialize_architecture` under `architecture-materialization@1.1`:

`authoring@1.7 -> architecture-interpretation@1.1 -> normalized-model@2.4`

This is a new protocol contract because protocol 1.1 is already the public
transport for the historical authoring 1.5/1.6 materialization tuple and must
not be widened to admit authoring 1.7. Protocol 1.2 remains specific to the
Authoring Construction Contract operations `validate_authoring` and
`construct_authoring_set`; it is not a general materialization transport.

The public operation remains `materialize_architecture`: Architecture
Interpretation is governed semantic machinery inside materialization, not a
second public API operation. The successor profile records AI 1.1, NM 2.4,
and the existing normative-semantics 1.0 contract as one exact tuple.

This slice establishes authority and transport shape only. Protocol 1.3 is
recognized and validated version-first, but execution returns deterministic
`Unavailable`; it does not route to the internal AI 1.1 kernel. The current
semantic-contract selection, the `architecture-materialization@1.0` profile,
and all older protocol contracts remain unchanged.
