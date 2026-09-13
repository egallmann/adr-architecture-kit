# Authoring schemas

Family-scoped ADR authoring contracts live in versioned directories through
`v1.6/`. The current existing authoring resources include logical,
physical-system, and physical-component contracts for the v1.6 line. The stable
v1.0 compatibility line remains the separate canonical `schema/v1.0/`
exception; it is retained for compatibility and is not replaced by a future
version claim here.

The language-neutral Authoring Domain Contract is a separate family under
`contracts/authoring-domain/`. ADC 1.0 currently provides descriptive discovery
of authoring contracts and types. Its version is independent of these
persistence-schema versions and it does not provide semantic authoring
construction or mutation.

Evidence-attribution versions are another independent family. In particular,
evidence v1.5/v1.6 must not be read as ADR authoring v1.5/v1.6.
