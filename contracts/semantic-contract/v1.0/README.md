# ADR-Kit semantic contract definitions v1.0

This directory contains the immutable semantic-definition contract used by the
0.11.0 Slice B boundary. The definition files are content-addressed manifests;
the `semanticContractFingerprint` is calculated over the definition with that
field removed. Resource contents are supplied separately to closure validation.

The two promoted definitions are deliberately narrow:

- `normative-semantics@1.0` records ADR-Kit's faithful NP/Invariant and force
  representation without adding inference or an NP lifecycle.
- `architecture-interpretation@1.0` records the source-to-normalized
  interpretation recipe, including qualification, coverage, ordering, and
  fail-closed behavior.

`scf:v1:sha256` identifies one immutable definition. `scs:v1:sha256` is a
separate composition identity and is not implemented by embedding policy,
catalog state, or current selection in an SCF definition.
