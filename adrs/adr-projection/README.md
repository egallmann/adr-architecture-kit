# ADR human projections

These markdown files are **disposable, non-authoritative** human-readable projections of canonical ADR YAML.

- Authority remains in `adrs/logical/`, `adrs/physical/`, `adrs/physical-system/`, and `adrs/physical-component/`.
- Relationship verbs and Mermaid edges come from compiler-derived semantics (not a second ontology).
- Regenerate with `adr generate-adr-projection` (compatibility alias: `adr generate-rendered-docs`).
- Do not hand-edit these files; change canonical ADRs or generators, then regenerate.
- Validate with `adr validate-generated-docs`.

Layout: `{logical|physical|physical-system|physical-component}/{alias_id}-{slug}.md`
