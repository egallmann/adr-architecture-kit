# STE Glossary

## Purpose

This glossary defines terminology used throughout the STE architectural specification. Consistent use of these terms ensures precision and prevents ambiguity.

## Core Architectural Concepts

### System of Thought Engineering (STE)

An architectural framework for governing artificial intelligence cognition through explicit constraints, deterministic execution, and validated documentation-state. STE transforms raw LLM execution into bounded, deterministic reasoning through layered invariants, execution lifecycle stages, and divergence detection mechanisms.

### System-of-Interest

The scope of the STE architecture: the governance framework that constrains, validates, and directs AI cognition. Excludes implementation mechanisms, deployment topology, and operational procedures.

### Governance Framework

The complete set of constraints, protocols, validators, and execution semantics that bound AI reasoning. Operates as an AI Operating System, transforming unconstrained token generation into deterministic, validated cognition.

## Invariant Hierarchy

### Prime Invariant

The highest-level constraint governing all STE reasoning. Prohibits implicit assumptions, undeclared state, unbounded reasoning, unvalidated modifications, and non-framework concepts. All other invariants derive from the Prime Invariant.

**Formal Definition**: Five enumerated constraints (PRIME-1 through PRIME-5) in STE-Prime-Invariant.md.

### System Invariants

Global rules governing the entire STE cognitive system. Define system-wide requirements for explicitness, determinism, validator enforcement, divergence resolution, and documentation-state discipline. Apply universally to all reasoning tasks, domains, and artifacts.

**Formal Definition**: Sixteen enumerated constraints (SYS-1 through SYS-16) in STE-System-Invariants.md.

### Domain Invariants

Constraints governing reasoning within a specific domain. Examples include AWS Domain Invariants, Documentation Domain Invariants, and IAM Subdomain Invariants. Must align with System Invariants and define bounded scope.

### Artifact Specifications

Structural and formatting rules for all STE artifacts. Define required sections, naming conventions, placement rules, and conformance requirements. Layer 4 of the Invariant Hierarchy.

### Invariant Layer

One of seven hierarchical constraint levels (Prime → System → Domain → Artifact → Documentation-State → Framework Synchronization → Meta-Invariants). Lower layers may specialize but cannot override higher layers.

## Execution Model

### Cognitive Execution Model (CEM)

The deterministic lifecycle STE uses to ensure constraint-governed cognition. Nine stages executed in sequence: Initialization → State Loading → Pre-Task Validation → Divergence Detection → Divergence Communication → Correction and Reconvergence → Reasoning Execution → Post-Task Validation → Final Convergence.

### Stage

A discrete phase in the Cognitive Execution Model. Each stage has explicit responsibilities, inputs, outputs, and validation requirements. No stage may be skipped.

### Initialization

Stage 1 of CEM. Loads Prime Invariant, System Invariants, establishes invariant hierarchy boundaries, prepares validators, and verifies RECON completion status.

### State Loading

Stage 2 of CEM. Loads only explicit state relevant to the task through Task Analysis, Entry Point Discovery, RSS Graph Traversal, and Context Assembly.

### Validation

Stages 3 and 8 of CEM. Pre-Task Validation ensures reasoning begins from valid, explicit state. Post-Task Validation ensures no divergence was introduced and outputs conform to artifact specifications.

### Divergence Detection

Stage 4 of CEM. Identifies inconsistencies such as stale documentation, missing inventories, implicit assumptions, structural violations, hierarchy conflicts, taxonomy gaps, misplaced artifacts, or semantic drift.

### Reconvergence

Stage 6 of CEM. Correction process ensuring no further divergence exists, validation succeeds, and consistency is restored across artifacts, invariants, and documentation-state.

### Final Convergence

Stage 9 of CEM. The cognitive task is accepted only when all validators pass, all invariants remain satisfied, framework synchronization is preserved, documentation-state is complete, divergence is absent, and all dependencies are satisfied.

## Divergence and Drift

### Divergence

Any inconsistency, drift, or constraint violation detected during reasoning. Must be explicitly classified using the Divergence Taxonomy before correction. Reasoning cannot proceed until divergence is resolved.

### Divergence Taxonomy

Canonical classification system for detecting, routing, and resolving divergence. Categories include documentation-state drift, structural violations, constraint violations, and framework synchronization drift.

### Divergence Type

Specific classification within the taxonomy. Examples: Doc-Missing-Inventory, Doc-State-Staleness, Doc-Implicit-State, Artifact-Structure-Violation, Domain-Constraint-Violation.

### Drift

Gradual divergence from documented truth over time. STE treats drift as detectable and correctable condition, not inevitable failure. Uncorrected drift is prohibited.

### Gate Type

Classification determining how divergence is communicated to users: Auto-Resolvable (agent may proceed), User-Gated (requires user confirmation), or Blocking (requires user guidance).

## Documentation-State

### Documentation-State

The explicit, machine-readable substrate that grounds reasoning. Provides complete, consistent, validated truth for cognition. Must be synchronized before reasoning proceeds.

### AI-DOC

Structured, explicit, machine-interpretable representation of system state. Bidirectional references, sliceability, graph completeness. Stored as YAML files. Generated by RECON, maintained incrementally.

### RECON (Reconciliation Protocol)

The protocol for bootstrapping explicit domain truth from existing artifacts. Extracts project structure, relationships, and semantics into AI-DOC. Prerequisite for reasoning (SYS-6: RECON Completion Prerequisite).

### RSS (Runtime State Slicing)

Graph traversal protocol for deterministic context assembly. Starts at entry points, traverses explicit references with depth bounds, assembles Minimally Viable Context. Includes convergence validation for multi-entry traversals. Deterministic: same entry points → same traversal → same context.

### Convergence Validation

Protocol for validating semantic coherence of multiple RSS entry points. Measures subgraph overlap between independent traversals. Classification: 3 of 3 converge (ideal), 2 of 3 converge (strong), <2 of 3 converge (divergence detected). Enables detection of ambiguous identifiers, stale graph structure, and Task Analysis errors.

### Subgraph Overlap

Measurement of semantic relationship between two RSS traversal results. Calculated as intersection over union of traversed nodes. Threshold: ≥70% overlap indicates convergent (semantically coherent) subgraphs. Used in convergence validation to detect entry points leading to different architectural regions.

### MVC (Minimally Viable Context)

The smallest set of state needed to reason about a task. Bounded (explicit depth limits), minimal (only necessary state), deterministic (reproducible), explicit (every item justified by graph path).

### Task Analysis

Deterministic algorithm mapping natural language tasks to AI-DOC entry points. Decomposes requests, resolves domains, discovers candidates, scores relevance, selects entry points. No probabilistic matching.

### Entry Point

Starting node for RSS traversal, identified by Task Analysis. High-scoring slices matching task intent, type, identifier, and keywords.

### Graph Traversal

Following explicit edges from entry points to discover related state. Deterministic, auditable, depth-bounded. Uses `_slice` metadata for dependencies and dependents.

### Sliceability

Property of AI-DOC enabling graph traversal through explicit `_slice` metadata. Every item declares dependencies (forward edges) and dependents (backward edges). Bidirectional relationships maintained consistently.

## Validation and Enforcement

### Validator

A gate that enforces constraints before operations proceed. Validators detect divergence, enforce artifact specifications, ensure documentation-state integrity, apply domain and system rules, validate cross-file consistency, and prevent implicit reasoning.

### Checkpoint

Mandatory validation gate in the cognitive lifecycle. Pre-Task Checkpoint validates state before reasoning. State-Mutating Checkpoint validates updates after changes.

### Documentation Validator

Checks structure, completeness, explicitness of documentation-state artifacts.

### Framework Validator

Ensures canonical artifacts (schemas, inventories) remain synchronized.

### Domain Validator

Validates domain-specific correctness when reasoning requires specialized constraints.

## Authority and Governance

### Authority Boundary

Clear separation between attestation (signing canonical artifacts), enforcement (verifying eligibility), and execution (performing operations). Prevents single entities from signing their own eligibility or executing without verification.

### Attestation Authority

Responsibility for signing canonical artifacts and producing non-repudiable truth claims. Example: Organizational (ORG) authority signs AI-DOC slices.

### Enforcement Authority

Responsibility for verifying prerequisites and eligibility. Example: Gateway verifies signatures and queries trust registry but does not sign canonical artifacts.

### Execution Authority

Responsibility for performing operations based on verified eligibility. Acts only after enforcement authority confirms prerequisites are satisfied.

### Gateway

Component with ORG-scoped enforcement authority. Verifies artifacts signed by ORG authority, enforces execution eligibility based on ORG-signed invariants, queries trust registry, produces ephemeral unsigned eligibility decisions.

## Protocols and Workflows

### Protocol

A canonical workflow defining how operations must be performed. Examples: Documentation Checkpoint Protocol, AI-DOC Update Workflow Protocol, RECON Protocol, Divergence Communication Protocol.

### Documentation Checkpoint Protocol

Standard for documentation-state validation before and after tasks. Defines Pre-Task Checkpoint and State-Mutating Checkpoint requirements.

### AI-DOC Update Workflow Protocol

Standard for mutating documentation-state artifacts. Eight-step workflow: Identify Update Type → Load Artifacts → Apply Update → Synchronize Inventory → Execute Checkpoint → Validate → Reconverge → Finalize.

### Divergence Communication Protocol

Standard for how divergence is communicated to users. Defines gate type determination, communication flow, consent requirements, and decline handling.

## Architectural Decisions

### ADR (Architectural Decision Record)

Converged, binding architectural commitment where alternatives have been explicitly rejected and reversal would be expensive or destabilizing. Governs future work and enforcement behavior.

### E-ADR (Exploratory Architectural Decision Record)

Provisional, explicitly reversible decision existing to force execution and generate learning. Operationally binding but architecturally non-binding. Does not define system truth. Not published in this specification.

### Execution-Pressure

The use of E-ADRs to force implementation and surface friction, conflicts, and learning. Drives experimentation without establishing architectural truth.

## Determinism and Explicitness

### Determinism

Property where identical inputs always produce identical outputs. STE achieves determinism through constraint engineering, layered invariants, validated documentation-state, divergence detection, and structural rules.

### Explicitness

Requirement that all assumptions, boundaries, state, and reasoning be declared. Implicit knowledge is treated as drift (PRIME-1: No Implicit Assumptions, PRIME-2: No Undeclared State).

### Boundedness

Requirement that reasoning remain within declared scopes and domains. Unbounded reasoning is prohibited (PRIME-3: No Unbounded Reasoning).

## Framework and Synchronization

### Framework

The complete set of STE artifacts defining the governance system: core architecture, invariants, validators, protocols, divergence taxonomy, and canonical references.

### Framework Synchronization

Requirement that modifications to any canonical artifact trigger synchronization updates to dependent artifacts (SYS-16: Cascade Update Requirement).

### Canon Status

Declaration that a file is canonical and modifications require Framework Validator approval, inventory updates, directory verification, and reconvergence.

### Inventory

Authoritative list of all artifacts within a category. Ensures completeness and prevents undeclared artifacts (Doc-Missing-Inventory divergence if inventory is stale).

## Operating System Analogy

### AI Operating System

Conceptual framing of STE as an OS for AI cognition. Invariant Hierarchy acts as kernel, AI-DOC as filesystem, Validators as system calls, Divergence Taxonomy as error handling, CEM as runtime.

### Kernel

The invariant layers (Prime and System) that provide foundational governance rules analogous to OS kernel.

### Filesystem

AI-DOC, providing explicit structured machine-interpretable truth analogous to OS filesystem.

### System Calls

Validators, enforcing constraints before operations proceed analogous to OS system calls.

## ISO/IEC/IEEE 42010 Concepts

### Viewpoint

Perspective on system structure addressing specific stakeholder concerns. Examples: Invariant Hierarchy (constraint layering viewpoint), Cognitive Execution Model (lifecycle viewpoint), Authority Boundary Model (responsibility separation viewpoint).

### Stakeholder Concern

What different audiences need to understand. Examples: Governance system designers need to know how to bound AI reasoning; Implementation teams need to know normative requirements for conformance.

### Architectural View

Complete realization of a viewpoint with exhaustive detail. This specification intentionally provides viewpoints without complete views to preserve design freedom.

## Common Abbreviations

- **ADR**: Architectural Decision Record
- **AI-DOC**: Artificial Intelligence Documentation (semantic index)
- **CEM**: Cognitive Execution Model
- **E-ADR**: Exploratory Architectural Decision Record
- **MVC**: Minimally Viable Context
- **RECON**: Reconciliation Protocol
- **RSS**: Runtime State Slicing
- **STE**: System of Thought Engineering

## State Transition and Environment Management

### Canonization

The process by which provisional workspace state becomes canonical state through version control, CI/CD security gates, and merge approval. Only canonical state is eligible for RECON extraction.

### Canonical State

Security-vetted artifacts in target branches (develop, master) that serve as organizational source of truth. RECON operates exclusively on canonical state. Security validation occurs via CI/CD gates before artifacts reach canonical state.

### Environment

Deployment context for reasoning (nonprod, production, staging, etc.). Attestations are scoped to specific environments. Gateway enforces environment matching during verification. Organizations may use separate signing keys per environment for cryptographic isolation.

### Trust Registry

Service that distributes public keys, maintains authorized signing authorities, and maps signing identities to authorized environments. Enables Gateway to verify Fabric attestation signatures and authority-environment matches. May be implemented using cloud IAM systems, certificate authorities, or dedicated services.

### Key Management Service

Enterprise service for cryptographic key lifecycle management, typically with hardware security module (HSM) backing. Examples: AWS KMS, Azure Key Vault, GCP Cloud KMS, Thales HSM. Used by Fabric to sign attestations with keys that never leave hardware security boundary.

### Multi-Key Architecture

Deployment pattern where single Fabric control plane coordinates multiple data planes, each with environment-specific signing key (managed by key service), authorization scope, and storage. Provides cryptographic environment isolation while maintaining operational simplicity. Nonprod key compromise cannot affect production.

### Authorization Scope

Set of permissions granted to a signing authority. Typically managed by identity and access management (IAM) systems or policy engines. Examples: AWS IAM role with kms:Sign permission, Azure Managed Identity with key signing permission, service account with signing capability.

## Usage Guidelines

### Preferred Terminology

Use these terms consistently:

- Say **"invariant"**, not "rule", "constraint", or "requirement" for hierarchical constraints
- Say **"divergence"**, not "error", "violation", or "inconsistency" for detected drift
- Say **"validator"**, not "checker", "gate", or "enforcer" for constraint enforcement mechanisms
- Say **"documentation-state"**, not "docs", "state", or "context" for AI-DOC substrate
- Say **"cognitive execution"**, not "reasoning", "thinking", or "processing" for governed lifecycle
- Say **"reconvergence"**, not "fixing", "correction", or "repair" for divergence resolution
- Say **"authority boundary"**, not "separation of concerns" or "responsibility model" for attestation/enforcement/execution separation

### Capitalization

- Capitalize proper names: System of Thought Engineering, Prime Invariant, Cognitive Execution Model
- Lowercase common terms: invariant, divergence, validator, protocol, documentation-state
- Capitalize layer names: Prime Invariant, System Invariants, Domain Invariants, Artifact Specifications

### Acronyms

Spell out acronyms on first use in each document, then use acronym consistently.

**First use**: "Cognitive Execution Model (CEM)"  
**Subsequent uses**: "CEM"

---

**This glossary defines STE architectural terminology for precision and consistency across the specification.**

