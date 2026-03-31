# Schema Guide

## Overview

ADR Kit v1.0 uses JSON Schema for validation with YAML as the document format. This guide provides a complete reference for all schema types.

## Schema Files

Located in `schema/v1.0/`:

- `types.schema.json` - Shared type definitions (IDs, dates, enums)
- `adr-common.schema.json` - Common frontmatter for all ADR types
- `adr-logical.schema.json` - Logical ADR schema
- `adr-physical.schema.json` - Physical ADR schema
- `invariant.schema.json` - Standalone invariant schema
- `project-metadata.schema.json` - PROJECT.yaml schema
- `manifest.schema.json` - Generated manifest schema

## ID Patterns

All entity IDs follow strict patterns:

| Entity | Pattern | Example | Description |
|--------|---------|---------|-------------|
| Logical ADR | `ADR-L-\d{4}` | `ADR-L-0001` | Conceptual design |
| Physical ADR | `ADR-P-\d{4}` | `ADR-P-0001` | Implementation spec |
| Decision ADR | `ADR-D-\d{4}` | `ADR-D-0001` | Autonomous agent decision |
| Invariant | `INV-\d{4}` | `INV-0001` | Must-hold constraint |
| Capability | `CAP-\d{4}` | `CAP-0001` | System capability |
| Component | `COMP-\d{4}` | `COMP-0001` | Implementation component |
| Interface | `IFACE-\d{4}` | `IFACE-0001` | Component interface |
| Decision | `DEC-\d{4}` | `DEC-0001` | Logical decision |
| Implementation | `IMPL-\d{4}` | `IMPL-0001` | Physical decision |
| Constraint | `CONST-\d{4}` | `CONST-0001` | Architectural constraint |
| Boundary | `BOUND-\d{4}` | `BOUND-0001` | Architectural boundary |
| Contract | `CONTRACT-\d{4}` | `CONTRACT-0001` | Interaction contract |
| Integration | `INTEG-\d{4}` | `INTEG-0001` | Integration point |
| NFR | `NFR-\d{4}` | `NFR-0001` | Non-functional requirement |
| Gap | `GAP-\d{4}` | `GAP-0001` | Unresolved question |

## Common Frontmatter

All ADR types share common frontmatter:

```yaml
schema_version: "1.0"
adr_type: logical | physical | decision
id: ADR-L-0001 | ADR-P-0001 | ADR-D-0001
title: "Human-readable title"
status: proposed | accepted | deprecated | superseded
created_date: "2026-03-07"
modified_date: "2026-03-08"  # Optional
authors: ["github.handle"]

domains: ["api", "infrastructure"]  # Required, min 1
tags: ["gateway", "security"]  # Optional

related_adrs: ["ADR-L-0002"]  # Optional
supersedes: ["ADR-L-0001"]  # Optional
superseded_by: "ADR-L-0003"  # Optional (null if current)

ownership:  # Optional
  architecture_authority: "platform-architecture"
  implementation_owners: ["team-api", "team-infra"]
```

## Logical ADR Schema

### Required Fields

- `schema_version`: "1.0"
- `adr_type`: "logical"
- `id`: Pattern `ADR-L-\d{4}`
- `title`: 5-200 characters
- `status`: proposed | accepted | deprecated | superseded
- `created_date`: ISO date (YYYY-MM-DD)
- `authors`: Array, min 1
- `domains`: Array, min 1
- `context`: Markdown text
- `decisions`: Array, min 1

### Optional Sections

- `capabilities` - System capabilities
- `architectural_boundaries` - Boundaries and separation
- `interaction_contracts` - Component contracts
- `constraints` - Architectural constraints
- `invariants` - Must-hold statements
- `non_functional_requirements` - NFRs
- `gaps` - Unresolved questions

### Decision Structure

```yaml
decisions:
  - id: DEC-0001
    summary: "Decision statement"
    rationale: |
      Why this decision was made (markdown)
    alternatives_considered:  # Optional
      - name: "Alternative approach"
        rejected_because: "Reasoning"
    consequences:  # Optional
      positive: ["Benefit 1", "Benefit 2"]
      negative: ["Trade-off 1", "Trade-off 2"]
    related_invariants: ["INV-0001"]  # Optional
```

### Invariant Structure

```yaml
invariants:
  - id: INV-0001
    statement: "What must always be true"
    scope: global | domain_name | component_name
    enforcement_level: must | should | may
    enforcement_mechanism: design | runtime | test | policy
    verification_method: automated | manual | audit
    rationale: |
      Why this invariant exists
    policy_reference: "POL-0001"  # Optional
    compliance_frameworks: ["SOC2", "GDPR"]  # Optional
    exceptions: ["EXC-0001"]  # Optional
```

## Physical ADR Schema

### Required Fields

- All common frontmatter fields
- `adr_type`: "physical"
- `id`: Pattern `ADR-P-\d{4}`
- `implements_logical`: Array of logical ADR IDs, min 1
- `technologies`: Array of technology names
- `context`: Markdown text
- `technology_stack`: Array, min 1
- `component_specifications`: Array, min 1

### Technology Stack

```yaml
technology_stack:
  - category: language | framework | library | database | messaging | infrastructure | tooling
    name: "PostgreSQL"
    version: "15.x"
    rationale: |
      Why this technology was chosen
```

### Component Specification

```yaml
component_specifications:
  - id: COMP-0001
    name: "Payment Service"
    type: service | library | database | queue | cache | gateway | proxy | worker | scheduler
    responsibilities: |
      What this component does
    
    interfaces:  # Optional
      - id: IFACE-0001
        type: REST | gRPC | GraphQL | message | event | stream | batch
        specification: |
          API contract details
        contract_reference: "docs/api/payments.yaml"  # Optional
    
    dependencies: ["COMP-0002", "external-service"]  # Optional
    upstream_services: ["billing-service"]  # Optional
    downstream_services: ["notification-service"]  # Optional
    
    implementation_identifiers:  # Optional but recommended
      service_name: "payment-service"
      repository: "github.com/org/payments"
      module_path: "src/services/payment"
      deployment_name: "payment-service"
```

### Implementation Decision

```yaml
implementation_decisions:
  - id: IMPL-0001
    summary: "Implementation choice"
    rationale: |
      Technical reasoning
    implements_invariants: ["INV-0001"]  # Optional
    alternatives_considered:  # Optional
      - name: "Alternative"
        rejected_because: "Why not chosen"
```

## PROJECT.yaml Schema

Project-level metadata (one per repository):

```yaml
schema_version: "1.0"
type: project_metadata

project:
  name: "payment-service"  # Pattern: ^[a-z0-9-]+$
  description: "Payment processing microservice"
  type: service | library | platform | system | tool

ownership:
  team: "team-payments"
  tech_lead: "@alice"  # Optional
  on_call:  # Optional
    schedule: "payments-oncall"
    rotation: daily | weekly | biweekly | monthly
    members: ["@alice", "@bob"]
    backup: "@tech-lead"

repository:
  url: "github.com/org/payment-service"
  primary_branch: "main"

implementation_identifiers:  # Optional
  service_name: "payment-service"
  namespace: "payments"
  deployment_name: "payment-service"

automation:  # Optional
  auto_merge_allowed: false
  auto_deploy_staging: true
  auto_deploy_production: false
  requires_human_review: true
  comfort_level: conservative | moderate | aggressive

integrations:  # Optional
  scm:
    type: github | gitlab | bitbucket
    app_installation_id: "12345678"
    required_approvers: ["@alice"]
  
  ci:
    type: github_actions | jenkins | circleci | gitlab_ci
    workflow_path: ".github/workflows/ci.yml"
    required_checks: ["test", "lint"]
  
  observability:
    metrics:
      provider: datadog | prometheus | cloudwatch | newrelic
      dashboards: ["service-health"]
    logs:
      provider: cloudwatch | datadog | splunk | elasticsearch
      log_groups: ["/aws/ecs/payment-service"]
    alerts:
      provider: pagerduty | opsgenie | victorops
      escalation_policy: "payments-oncall"

compliance:  # Optional
  security_level: high | medium | low
  data_classification: public | internal | confidential | restricted
  regulatory_requirements: ["PCI-DSS", "SOC2"]
  license: "Apache-2.0"
  required_controls:
    encryption_at_rest: true
    encryption_in_transit: true
    mfa_required: true
    audit_logging: true

architecture_documentation:
  adr_directory: "adrs/"
  manifest_path: "adrs/manifest.yaml"
```

## Manifest Schema

Generated manifest (never manually edited):

```yaml
schema_version: "1.0"
type: manifest
generated_date: "2026-03-07T19:45:00Z"
generated_from: "adrs/**/*.yaml"

adrs:
  - id: ADR-L-0001
    type: logical
    title: "..."
    status: accepted
    file_path: "adrs/logical/ADR-L-0001.yaml"
    domains: [...]
    tags: [...]
    decision_count: 3
    invariant_count: 2

by_domain:
  api: [ADR-L-0001, ADR-P-0001]

by_status:
  accepted: [ADR-L-0001]

logical_to_physical_map:
  ADR-L-0001: [ADR-P-0001, ADR-P-0002]

statistics:
  total_adrs: 5
  logical_adrs: 2
  physical_adrs: 3
```

## Validation

### Schema Validation

```python
from adr_kit.parser import ADRParser

parser = ADRParser()

# Validates against JSON Schema
adr = parser.parse_logical_adr("adrs/logical/ADR-L-0001.yaml")
```

### Validation Errors

Schema validation provides clear error messages:

```
Schema validation failed: 'decisions' is a required property
Path: 

Schema validation failed: 'local' is not one of ['cloud', 'on-premise', 'hybrid', 'edge']
Path: deployment_model.hosting
```

## Schema Evolution

### Backward Compatibility

Schema v1.0 is designed for evolution:

```yaml
# v1.0 (minimal)
owned_by: "team-api"

# v1.1 (expanded - backward compatible)
ownership:
  team: "team-api"
  tech_lead: "@alice"
```

### Version Signaling

```yaml
schema_version: "1.0"  # Explicit version
```

Tools adapt behavior based on schema version.

### Future Fields

Schema v1.0 includes hooks for future use cases:

- `policy_reference` - Links to policy system
- `compliance_frameworks` - Compliance tracking
- `implementation_identifiers` - EDR matching
- `automation` flags - Correction agent permissions
- `validation_query` - Automated compliance checks

## STE Compliance

Schema design follows STE invariants:

- **PRIME-1**: No implicit assumptions (all fields explicit)
- **PRIME-2**: No undeclared state (all metadata in frontmatter)
- **SYS-2**: Deterministic cognition (schema validation)
- **SYS-4**: Drift prevention (violations = divergence)
- **SYS-5**: Documentation-state precedence (ADRs authoritative)
- **SYS-13**: Graph completeness (explicit relationships)
- **SYS-14**: Index currency (manifest generated)

## Further Reading

- `docs/logical-adr-guide.md` - Writing logical ADRs
- `docs/physical-adr-guide.md` - Writing physical ADRs
- `docs/graph-integration.md` - ste-runtime integration
- `schema/v1.0/README.md` - Schema documentation
