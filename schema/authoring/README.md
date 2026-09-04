# Authoring schemas

Family-scoped ADR authoring contracts live in versioned directories through
`v1.5/`; v1.5 is the current forward authoring substrate for logical,
physical-system, and physical-component ADRs. The stable compatibility line
remains the separate canonical `schema/v1.0/` exception.

The language-neutral Authoring Domain Contract is a separate contract family
under `contracts/authoring-domain/`. Its ADC version is independent of these
persistence-schema versions.
