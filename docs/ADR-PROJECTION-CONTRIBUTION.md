# ADR Projection Frontmatter - ste-rules-library Contribution

**Date**: 2026-03-08  
**Authority**: ste-rules-library ADR-L-0002, adr-architecture-kit ADR-L-0006  
**Purpose**: Document schema extensions contributed by ste-rules-library to adr-architecture-kit

---

## Summary

ste-rules-library contributes optional ADR frontmatter fields that enable:

1. **Projection signals** - ADRs declare which context signals activate their derived rules
2. **AI-first hints** - ADRs declare minimal sections for AI context projection

These extensions are **optional** - existing ADRs remain valid. New ADRs can adopt them for ste-rules-library integration.

---

## Schema Extensions (adr-common.schema.json)

### projection_signals

```yaml
projection_signals:
  - python
  - scope-resolution
  - traceability
```

**Description**: Context signals that activate rules derived from this ADR. Consumed by ste-rules-library for rule projection.

**Examples**:
- `python` - Rule activates when editing Python files
- `scope-resolution` - Rule activates for scope-related work
- `traceability` - Rule activates for decorator/traceability work
- `security` - Rule activates for security-related context

**Flow**:
```
ADR (projection_signals: [python, traceability])
    |
    v
Rules & Signal Service or ste-rules-library
    |
    v
Rule (signals: [python, traceability], source_adr: ADR-L-0004)
    |
    v
Runtime: Context matches -> Rule projected to AI
```

### ai_projectable

```yaml
ai_projectable:
  minimal_sections:
    - invariants
    - decisions
  primary_domains:
    - governance
    - traceability
```

**Description**: AI-first projection hints. When context is constrained, these guide which sections to project.

**Use cases**:
- Prompt translator: Include minimal_sections in implementation prompts
- ste-rules-library: Prioritize rules by primary_domains
- RECON: Extract minimal context for AI-DOC slices

---

## Rule Schema Alignment (ste-rules-library)

When rules are derived from ADRs:

| ADR field | Rule field |
|-----------|------------|
| projection_signals | signals |
| id | source_adr |
| ai_projectable.minimal_sections | ai_projectable.minimal_context |
| domains | (scope hints) |

---

## Example: ADR with Projection

```yaml
# adrs/logical/ADR-L-0004-adr-to-code-traceability-via-decorators.yaml

schema_version: "1.0"
adr_type: logical
id: ADR-L-0004
title: ADR-to-Code Traceability via Decorators
# ... existing fields ...

projection_signals:
  - python
  - traceability
  - decorators
  - governance

ai_projectable:
  minimal_sections:
    - invariants
    - decisions
  primary_domains:
    - traceability
    - governance
```

---

## Contribution Status

- [x] adr-common.schema.json: projection_signals, ai_projectable added
- [x] ste-rules-library rule.schema.json: ai_projectable, source_adr linkage
- [x] ste-rules-library ADR-L-0002: Contribution documented
- [ ] ADRs in adr-architecture-kit: Add projection_signals where relevant (optional)
- [ ] Prompt translator: Consume ai_projectable for minimal prompts (future)

---

## References

- adr-architecture-kit: schema/v1.0/adr-common.schema.json
- ste-rules-library: adrs/logical/ADR-L-0002-adr-projection-frontmatter-contribution.yaml
- ste-rules-library: schema/rule.schema.json
