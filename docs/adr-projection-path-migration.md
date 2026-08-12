# ADR human projection path migration

## Change

Hard cutover:

- from: `adrs/rendered/{id}.md`
- to: `adrs/adr-projection/{logical|physical|physical-system|physical-component}/{alias_id}-{slug}.md`

Authority: ADR-L-0007 (DEC-0108, DEC-0109).

## Preserved public semantics

| Surface | Disposition |
|---------|-------------|
| SDK artifact group | Remains `markdown` |
| `artifact_kind` | Remains `rendered_adr_markdown` |
| Logical `artifact_id` | `rendered-adr:{adr.id}` (canonical machine id; not slug-dependent) |
| CLI | Preferred `generate-adr-projection`; `generate-rendered-docs` retained as alias |
| API contract | Remains `1.0` |
| Package version | Governed independently by the release process |

## Intentional diffs

- Concrete `relative_path` values under the `markdown` group now use `adrs/adr-projection/...`
- Integrity enumeration covers `adrs/adr-projection/**/*.md` (skips `README.md`)
- Human projections include Mermaid 1-hop graphs and peer relation cards from compiler RelGraph
- New `RelationshipType` value: `implements_logical`
- ADR-level `supersedes` / `superseded_by` now derive shared RelGraph edges

## Consumer guidance

- Prefer `artifact_id` over path stems when correlating markdown artifacts
- Treat path values as generated metadata; regenerate after ADR or generator changes
- Do not dual-read `adrs/rendered/` after this cutover (directory removed)
