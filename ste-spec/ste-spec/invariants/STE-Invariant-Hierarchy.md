# STE Invariant Hierarchy  
## Canonical Ordering, Precedence, and Constraint Model for All STE Invariants

## Publication Notice

This specification references several detailed invariant and protocol documents that exist in the working repository but are not included in the v1.0.0 public release:

- `STE-Prime-Invariant.md` — Formal definition of PRIME-1 through PRIME-5
- `STE-System-Invariants.md` — Formal definition of SYS-1 through SYS-16
- `STE-Framework-Inventory.md` — Framework-specific constraint inventory
- `STE-Framework-Directory-Structure.md` — Required directory structure by framework
- `STE-Framework-Validation-Rules.md` — Framework configuration validation

The architectural principles and constraints defined in these documents are enumerated within this specification's published files. Formal standalone documents may be published in future releases.

For the current release, constraint definitions are found in:
- Prime and System Invariants: Enumerated in this document (sections 3.1 and 3.2)
- Framework Invariants: Described in STE-Architecture.md (section on Framework Synchronization Layer)

---

# 1. Purpose of This Document
This file defines the **hierarchical structure**, **precedence rules**, and **interactions** between all invariant layers within the System of Thought Engineering (STE).

Its objectives are to ensure:

- correct ordering of invariant evaluation  
- consistent specialization of constraints  
- prevention of conflict or override violations  
- predictable cognitive behavior  
- deterministic reasoning paths  
- clear separation of responsibilities between layers  

This file is canonical and must be synchronized with:

- STE-Manifest  
- STE-Foundations  
- STE-Prime-Invariant  
- STE-System-Invariants  
- STE-Divergence-Taxonomy  
- STE-Artifact-Specifications  
- STE-RECON-Protocol  
- Framework Synchronization Layer

---

# 2. The Seven Invariant Layers  
STE's invariants are organized into seven strictly ordered layers.  
Each layer inherits from higher layers and may specialize rules but cannot override them.

### **Layer 1 — Prime Invariant**  
The highest-level constraint governing all STE reasoning.  
It prohibits:
- implicit assumptions  
- undeclared state  
- unbounded reasoning  
- unvalidated modifications  

All other rules derive from the Prime Invariant.

**Formal Definition:** See `/.ste/core/STE-Prime-Invariant.md`

The Prime Invariant contains five formally enumerated constraints:
- PRIME-1: No Implicit Assumptions  
- PRIME-2: No Undeclared State  
- PRIME-3: No Unbounded Reasoning  
- PRIME-4: No Unvalidated Modifications  
- PRIME-5: Framework-Defined Concepts Only

---

### **Layer 2 — System Invariants**  
Global rules that govern the entire STE cognitive system.  
They define system-wide requirements for:

- explicitness  
- determinism  
- validator enforcement  
- divergence resolution  
- documentation-state discipline  
- RECON completion before reasoning (see STE-RECON-Protocol)

These invariants apply universally to all reasoning tasks, domains, artifacts, and validators.

**Formal Definition:** See `/.ste/core/STE-System-Invariants.md`

System Invariants contain sixteen formally enumerated constraints:
- SYS-1: Explicitness Enforcement  
- SYS-2: Determinism Requirement  
- SYS-3: Validator Enforcement  
- SYS-4: Divergence Resolution Mandate  
- SYS-5: Documentation-State Precedence  
- SYS-6: RECON Completion Prerequisite  
- SYS-7: Checkpoint Enforcement  
- SYS-8: Framework Coherence
- SYS-9: Invariant Lifecycle Compliance
- SYS-10: Architecture Currency
- SYS-11: Communication Protocol Compliance
- SYS-12: AI-DOC Sliceability
- SYS-13: Graph Completeness
- SYS-14: Index Currency
- SYS-15: Framework Reference Resolution
- SYS-16: Cascade Update Requirement

---

### **Layer 3 — Domain Invariants**  
Constraints governing reasoning within a specific domain.  
Examples include:

- AWS Domain Invariants  
- IAM Subdomain Invariants  
- Documentation Domain Invariants  

Domain invariants must:

- align with System Invariants  
- define bounded scope  
- prevent context bleed  
- ensure domain-correct reasoning  

They may not contradict higher layers.

---

### **Layer 4 — Artifact Specifications**  
Rules defining the structure, semantic constraints, naming, and formatting for:

- AI-DOC  
- Human-DOC  
- templates  
- generated outputs  
- invariant files  
- validators  

These rules ensure consistency and machine-interpretability across the corpus.

Artifact Specifications apply to **all files**.

---

### **Layer 5 — Documentation-State Layer**  
Defines how authoritative state is structured, maintained, validated, and consumed.

It governs:

- inventories  
- schemas  
- API definitions  
- infrastructure state  
- ADR  
- RCA  
- runbooks  
- boundary definitions  

Documentation-state must be:

- explicit  
- complete  
- cross-linked  
- validated through checkpoints  
- updated before reasoning depends on it  

This layer ensures deterministic execution for all projects using STE.

---

### **Layer 6 — Framework Synchronization Layer**  
Ensures the STE framework itself remains consistent and drift-free.

It governs:

- directory structure  
- inventory completeness  
- naming rules  
- placement of canonical files  
- validator integration  
- contributor workflow  

This layer ensures that the framework is self-consistent and scalable.

---

### **Layer 7 — Meta-Invariants (Future Layer)**  
Reserved for invariants that govern:

- meta-level correctness  
- framework completeness  
- invariant evolution  
- stability of the discipline over time  

Meta-Invariants do not yet exist, but the layer is acknowledged to prevent implicit assumptions.

---

# 3. RECON and the Invariant Hierarchy

The **RECON Protocol** (Reconstruction Phase) is not an invariant layer but a **system-level protocol** that must execute before STE reasoning begins.

RECON ensures:
- domain invariants can be extracted from existing artifacts  
- AI-DOC is populated with explicit, validated state  
- implicit assumptions are surfaced and resolved  
- the Documentation-State Layer has valid content to load  

RECON failure triggers **RECON-Incomplete** divergence, which blocks all reasoning until resolved.

See: `/.ste/protocols/STE-RECON-Protocol.md`

---

# 4. Rules of Precedence  
The invariant hierarchy must obey the following precedence rules:

## 4.1 Higher Layers Override Lower Layers  
If a conflict exists:

1. Prime Invariant takes absolute precedence  
2. System Invariants control Domain Invariants  
3. Domain Invariants constrain Artifact Specifications  
4. Artifact Specifications govern how all artifacts must be created  
5. Documentation-State expresses the truth but cannot contradict higher invariants  
6. Framework Synchronization controls structure but not conceptual rules  
7. Meta-Invariants (future) may influence framework evolution but cannot override Prime Invariant  

---

## 4.2 Lower Layers May Specialize Higher Layers  
Specialization is allowed when:

- the higher layer permits refinement  
- specialization reduces ambiguity  
- specialization does not contradict or negate higher rules  

Examples:

- IAM Subdomain specializing the AWS Domain  
- Documentation Domain specializing Artifact Specs for documentation-type artifacts  

---

## 4.3 No Circular Dependencies  
Invariant layers must not:

- depend on each other cyclically  
- reference lower layers for rule justification  
- assume rules not explicitly declared  

---

## 4.4 No Implicit Layer Creation  
New invariant layers cannot be created outside the governance of:

- Contributor Workflow  
- Framework Synchronization Layer  
- Manifest update  
- Inventory update  
- Validation and reconvergence  

---

# 5. Inheritance and Boundary Rules

## 5.1 Upward Inheritance  
A lower layer inherits **all constraints** of higher layers.

Domain Invariants inherit from:

- Prime  
- System  

Artifact Specifications inherit from:

- Prime  
- System  
- Domain invariants (when applicable)

Documentation-State invariants inherit from:

- Prime  
- System  
- Artifact Specifications  

---

## 5.2 Boundary Enforcement  
Each layer must:

- define its scope explicitly  
- declare out-of-scope areas  
- avoid context bleed  
- avoid introducing contradictory rules  

---

## 5.3 Redundancy Avoidance  
Invariants may not restate higher-layer rules unless:

- explicit specialization is required  
- an operational expression is necessary at a lower layer  

---

# 6. Divergence Routing Rules  
Divergence classifications must respect the hierarchy.  
Examples:

- Violations of Prime Invariant → System-Level Divergence  
- Violations of System Invariants → System-Constraint-Violation  
- Misplaced or invalid domain constraints → Domain-Constraint-Violation  
- Artifact structural failures → Artifact-Type-Mismatch  
- Documentation-state issues → Doc-Implicit-State, Doc-State-Staleness  
- Framework inconsistencies → Framework-Structure-Violation  
- Incomplete bootstrap → RECON-Incomplete  

All divergence must pass through the reconvergence loop before reasoning continues.

---

# 7. Placement Rules  
This file governs where invariant files must be placed:

- System Invariants → `/.ste/core/` (embedded in Foundations and Manifest)  
- Domain Invariants → `/.ste/invariants/domain/`  
- Subdomain Invariants → nested under domain  
- Artifact Specifications → `/.ste/invariants/artifact/`  
- Meta-Invariants → `/.ste/invariants/meta/`  

Incorrect placement triggers framework-level divergence.

---

# 8. Canon Status  
This file is canonical.  
Changes require:

- Framework Validator approval  
- Manifest alignment  
- Inventory update  
- Directory verification  
- Reconvergence  

All invariants across all STE files must adhere to this hierarchy.

