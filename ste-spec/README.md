# System of Thought Engineering (STE)
## Architectural Specification for Governable Cognition

## What This Is

This repository contains the architectural specification for the System of Thought Engineering (STE), a system-of-interest designed to enable deterministic, constraint-governed cognition in artificial intelligence systems.

This specification is structured using concepts from ISO/IEC/IEEE 42010:2022 (Systems and Software Engineering — Architecture Description) and provides:

- System-of-interest definition
- Architectural viewpoints and stakeholder concerns
- Invariant hierarchy and constraint specifications
- Execution semantics and governance protocols
- Converged architectural decisions with rationale

**Intended Audience**: Architectural researchers, governance system designers, standards bodies, and organizations building systems that require transparent, auditable AI reasoning.

## What This Is NOT

This is not:

- A framework, library, or SDK for building AI agents
- A runtime implementation or deployment-ready system
- A tutorial or implementation guide
- An attack system or exploitation toolkit
- A complete system realization (viewpoints are provided, not complete views)
- A deployed product or operational system
- A prescriptive directory structure or file organization scheme

This specification defines architectural constraints, responsibilities, and authority boundaries. It does not prescribe implementation mechanisms, deployment topology, operational procedures, or specific directory structures. Examples showing file paths (e.g., `/.ste/core/`) are illustrative, not normative.

**Important**: This repository contains an architectural specification. Examples and protocols are illustrative and represent design intent, not operational guidance for deployed systems. Implementation maturity may vary and is not guaranteed by this specification.

## Status

See `status.md` for specification maturity, versioning, and evolution stance.

## Scope

### In Scope

- System-of-interest definition (what STE governs)
- Architectural viewpoints (perspectives on system structure)
- Invariant hierarchy (layered constraint specifications)
- Execution semantics (cognitive lifecycle stages and responsibilities)
- Governance protocols (documentation standards and validation requirements)
- Architectural decisions (converged commitments with explicit rationale)

### Out of Scope

- Implementation code, libraries, or runtimes
- Deployment topology and infrastructure choices
- Operational runbooks and procedures
- Runtime optimization strategies
- Complete architectural views (realization details)

See `scope-and-non-goals.md` for detailed boundaries and `NON-GOALS.md` for common misinterpretations to avoid.

## Architecture Overview

STE defines a governance framework for AI cognition through:

1. **Invariant Hierarchy** — Layered constraints that bound reasoning (Prime Invariant → System Invariants → Domain Invariants → Artifact Specifications)

2. **Cognitive Execution Model** — Deterministic lifecycle with explicit stages: Initialization → State Loading → Validation → Divergence Detection → Correction → Reasoning → Post-Validation → Convergence

3. **Documentation-State Protocols** — Standards for maintaining explicit, synchronized truth through AI-DOC (semantic documentation substrate)

4. **Divergence Taxonomy** — Classification system for detecting and resolving drift, inconsistency, and constraint violations

5. **Authority Boundaries** — Clear separation between attestation, enforcement, and execution responsibilities

## Repository Structure

```
ste-spec/
├── README.md                           (this file)
├── status.md                           (maturity and versioning)
├── scope-and-non-goals.md              (explicit boundaries)
├── architecture/                       (system-of-interest + foundations)
│   ├── STE-Architecture.md             (canonical system architecture)
│   ├── STE-Manifest.md                 (reference architecture and governance)
│   └── STE-Foundations.md              (conceptual foundations)
├── execution/                          (cognitive execution viewpoint)
│   └── STE-Cognitive-Execution-Model.md (deterministic lifecycle)
├── invariants/                         (constraint specifications)
│   ├── STE-Invariant-Hierarchy.md      (layered constraint model)
│   ├── STE-Divergence-Taxonomy.md      (fault classification)
│   └── STE-Artifact-Specifications.md  (structural requirements)
├── governance/                         (documentation protocols)
│   ├── STE-Documentation-Checkpoint-Protocol.md
│   └── STE-AI-DOC-Update-Workflow-Protocol.md
├── adr/                                (architectural decisions)
│   ├── README.md                       (ADR taxonomy and curation rationale)
│   └── [architectural ADRs]
├── glossary.md                         (consolidated terminology)
├── SECURITY.md                         (responsible disclosure + dual-use awareness)
└── NON-GOALS.md                        (misinterpretation prevention)
```

## Getting Started

### For Architectural Researchers

1. Start with `architecture/STE-Foundations.md` to understand core principles
2. Read `architecture/STE-Manifest.md` for reference architecture
3. Review `architecture/STE-Architecture.md` for system structure
4. Examine `execution/STE-Cognitive-Execution-Model.md` for execution semantics
5. Study `invariants/STE-Invariant-Hierarchy.md` for constraint layering

### For Governance System Designers

1. Review `architecture/STE-Foundations.md` for governance philosophy
2. Study `invariants/STE-Divergence-Taxonomy.md` for fault classification
3. Examine `governance/` protocols for documentation standards
4. Review `adr/` for architectural decision rationale
5. Consult `glossary.md` for precise terminology

### For Standards Bodies

1. Review use of ISO/IEC/IEEE 42010 architectural description concepts
2. Examine invariant hierarchy as constraint engineering approach
3. Study divergence taxonomy as determinism mechanism
4. Assess authority boundary model in ADRs
5. Evaluate governance protocols as documentation standards

## Key Concepts

**System of Thought Engineering (STE)**: An architectural framework for governing AI cognition through explicit constraints, deterministic execution, and validated documentation-state.

**Invariant Hierarchy**: Seven-layer constraint model (Prime Invariant → System Invariants → Domain Invariants → Artifact Specifications → Documentation-State → Framework Synchronization → Meta-Invariants).

**Cognitive Execution Model (CEM)**: Deterministic lifecycle that transforms invariants into enforceable behavior through initialization, state loading, validation, divergence detection, correction, reasoning, and convergence stages.

**Divergence**: Any inconsistency, drift, or constraint violation. All divergence must be explicitly classified and resolved before reasoning proceeds.

**Documentation-State**: Explicit, machine-readable substrate (AI-DOC) that provides truth for reasoning. Must be complete, consistent, and validated before cognition.

**Authority Boundaries**: Clear separation between attestation (signing canonical artifacts), enforcement (verifying eligibility), and execution (performing operations).

See `glossary.md` for complete terminology.

## Security and Dual-Use Awareness

This architecture describes capability boundaries and governance constraints. The specification recognizes the tension between capability and safety.

See `SECURITY.md` for responsible disclosure procedures and dual-use considerations.

## Completeness

This specification intentionally publishes viewpoints without complete views. Implementation details, deployment topology, and operational procedures are excluded by design to preserve architectural design freedom while ensuring correctness of published material.

**This is standards-aligned incompleteness, not accidental omission.**

## Versioning

This specification uses semantic versioning (MAJOR.MINOR.PATCH):

- MAJOR: Breaking changes to architectural invariants or system-of-interest definition
- MINOR: New viewpoints, protocols, or non-breaking constraint additions
- PATCH: Clarifications, corrections, and documentation improvements

Current version: See `status.md`

## Relationship to Working Repository

This is a curated, publishable subset of a broader working specification. The working repository contains:

- Operational designs and runtime implementations
- Exploratory decision records (E-ADRs)
- Infrastructure and deployment decisions
- Implementation examples and reference code
- Gap analyses and execution-pressure artifacts

Those materials are intentionally excluded from this publication to maintain clear separation between architectural specification and operational realization.

## Contributing

This specification is currently published for review and feedback. Contributions are not yet accepted as the specification is under governance by the authoring organization.

For questions, clarifications, or feedback, please open an issue describing:

- Which architectural viewpoint or document is unclear
- What clarification would improve understanding
- Whether the concern is architectural or operational

## License

Copyright 2024-2025 Erik Gallmann

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Contact

For questions, clarifications, or architectural feedback:

- **GitHub**: @egallmann
- **Issues**: Open an issue in this repository describing your concern

For security-related matters, see SECURITY.md for responsible disclosure procedures.

---

**STE: Architectural specification for governable cognition through explicit constraints, deterministic execution, and validated documentation-state.**

