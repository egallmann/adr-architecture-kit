# System of Thought Engineering (STE) — Manifest  
## Canonical Reference Architecture and Governance of the STE Discipline

# 1. Purpose of This Document
This manifest defines the **reference architecture**, **governance constraints**, **invariant layers**, and **synchronization rules** of the System of Thought Engineering (STE).  
It establishes the authoritative structure that ensures deterministic cognition, drift resistance, and stable evolution of the STE framework.

This file is canonical and must remain aligned with:

- STE-Framework-Inventory  
- STE-Framework-Directory-Structure  
- STE-Invariant-Hierarchy  
- STE-Divergence-Taxonomy  
- STE-Framework-Validation-Rules  
- STE-RECON-Protocol  
- STE-Architecture
- STE-AI-DOC-Schema
- STE-AI-DOC-Sliceability-Protocol
- STE-AI-DOC-Invariants  

Any modification triggers Framework Synchronization requirements.

---

# 2. Core Thesis of STE
STE asserts that deterministic cognition can be engineered by:

1. Explicitly defining the boundaries within which reasoning occurs.  
2. Governing these boundaries through layered invariants.  
3. Using documentation-state and validators to eliminate implicit or contradictory reasoning.  
4. Enforcing synchronization rules that guarantee consistency across the corpus.  
5. Using the RECON lifecycle to bootstrap explicit domain truth from existing artifacts.  
6. Ensuring all reasoning operates from validated, explicit state.  

STE does **not** rely on prompt engineering.  
It relies on **structured constraint engineering**.

---

# 3. The Seven Invariant Layers
STE reasoning is bounded by seven hierarchical invariant layers:

1. **Prime Invariant**  
2. **System Invariants**  
3. **Domain Invariants**  
4. **Artifact Specifications**  
5. **Documentation-State Layer**  
6. **Framework Synchronization Layer**  
7. **Meta-Invariants (future)**

These layers are defined in the Invariant Hierarchy and must be applied in this order.  
Lower layers may specialize but never override higher layers.

---

# 4. Required System Artifacts
The STE framework requires the following system artifacts:

**Core (Kernel):**
- STE-Manifest  
- STE-Foundations  
- STE-Prime-Invariant  
- STE-System-Invariants (SYS-1 through SYS-16)
- STE-Invariant-Hierarchy  
- STE-Divergence-Taxonomy  
- STE-Cognitive-Execution-Model  
- STE-Architecture  
- STE-AI-DOC-Schema  

**Invariants:**
- STE-Invariant-Template  
- STE-Artifact-Specifications  
- STE-Output-Invariants  
- STE-Meta-Invariants  
- STE-RECON-Invariants  
- STE-Agent-Boundary-Invariants  
- STE-AI-DOC-Invariants (DOC-1 through DOC-15)

**Validation:**
- STE-Validator-Template  
- STE-Domain-Invariant-Validation  
- STE-Framework-Validation-Rules  
- STE-Documentation-Validator  
- STE-AI-DOC-Graph-Validator  

**Protocols:**
- STE-RECON-Protocol  
- STE-AI-DOC-Sliceability-Protocol  
- STE-Plan-Validation-Protocol  
- STE-Invariant-Lifecycle-Protocol  
- STE-AI-DOC-Update-Workflow-Protocol  
- STE-Documentation-Checkpoint-Protocol  
- STE-Divergence-Communication-Protocol  
- STE-Contributor-Workflow  

**Framework:**
- STE-Framework-Directory-Structure  
- STE-Framework-Inventory  

No STE deployment may proceed without these artifacts.

---

# 5. Governance Model

## 5.1 Deterministic Reasoning Requirements
STE enforces:

- explicit boundaries  
- explicit assumptions  
- high-fidelity documentation-state  
- validator enforcement  
- divergence classification and correction  
- reconvergence before execution proceeds  
- RECON completion before domain reasoning  

No reasoning may occur with:

- stale documentation-state  
- implicit state  
- incomplete inventories  
- unclassified divergence  
- unsynchronized artifacts  
- incomplete RECON (RECON-Incomplete divergence active)  

## 5.2 Prohibited Behaviors
STE prohibits:

- implicit reasoning  
- ungoverned creation of artifacts  
- narrative drift in canonical files  
- introducing new concepts outside invariant boundaries  
- modifying documentation-state without checkpoint validation  
- bypassing RECON for new deployments  

Any violation must trigger divergence handling.

---

# 6. RECON Requirement
The **RECON Protocol** (Reconstruction Phase) is a mandatory system-level protocol.

It ensures:

- domain invariants can be reconstructed from existing artifacts  
- AI-DOC is complete and explicit  
- RECON divergence is resolved  
- system invariants operate from real project data  

All reasoning must occur **after** RECON is validated complete.

RECON failure triggers **RECON-Incomplete** divergence, which blocks execution.

See: `/.ste/protocols/STE-RECON-Protocol.md`

---

# 7. Documentation-State Layer (Cognitive Substrate)
STE uses **AI-DOC** as its authoritative state layer.

AI-DOC must be:

- explicit  
- complete  
- machine-interpretable  
- cross-linked  
- governed by Documentation-State invariants  

AI-DOC defines:

- project inventories  
- schemas  
- API catalogs  
- infrastructure definitions  
- IAM/KMS state  
- ADR and RCA documentation  
- operational definitions  

AI-DOC is validated by:

- Documentation-State Validator  
- Documentation Checkpoint Protocol  
- AI-DOC Update Workflow Protocol  

No reasoning that depends on state may occur without passing the required checkpoint.

---

# 8. Framework Synchronization Layer
This layer ensures that the STE framework itself remains synchronized.

It consists of:

- **STE-Framework-Directory-Structure**  
- **STE-Framework-Inventory**  
- **STE-Framework-Validation-Rules**  
- **STE-Invariant-Template**  
- **STE-Contributor-Workflow**  

This layer prevents framework drift by verifying:

- file placement correctness  
- inventory completeness  
- cross-file alignment  
- taxonomy integration  
- hierarchy consistency  

No canonical file may exist outside the structure declared in the Framework Directory Specification.

---

# 9. Divergence Governance

## 9.1 Divergence Detection
All inconsistencies must be classified using the Layered Divergence Taxonomy before correction.

Divergence types include:

- System-level (including RECON-Incomplete)  
- Domain-level  
- Artifact-level  
- Documentation-state-level  
- Framework-level  

Examples include:

- System-Hierarchy-Violation  
- RECON-Incomplete  
- Domain-Constraint-Violation  
- Artifact-Type-Mismatch  
- Doc-Implicit-State  
- Framework-Structure-Violation  

## 9.2 Reconvergence Loop
All divergences must pass through:

1. **Detection**  
2. **Classification**  
3. **Correction**  
4. **Revalidation**  
5. **Convergence confirmation**

No reasoning may continue while divergence remains unresolved.

---

# 10. Cognitive Execution Model
All STE-guided reasoning must follow the Cognitive Execution Model:

1. Load invariants and documentation-state  
2. Validate state and structure  
3. Detect and classify divergence  
4. Correct and reconverge  
5. Produce deterministic output  
6. Post-task validation  

This ensures that every output reflects accurate, validated, synchronized state.

---

# 11. Canonical Corpus Definition
The STE corpus consists **exclusively** of files listed in:

**STE-Framework-Inventory.md**

All files must be placed according to:

**STE-Framework-Directory-Structure.md**

Any file outside these rules is non-canonical and must trigger divergence.

---

# 12. Governance of Updates
All updates to the STE framework must:

1. Follow the Contributor Workflow  
2. Update the Inventory  
3. Update the Directory Structure (if required)  
4. Trigger Pre-Task and State-Mutating Checkpoints  
5. Pass Framework Validator checks  
6. Revalidate for reconvergence  
7. Maintain alignment with the Manifest and Hierarchy  

Updates performed outside this workflow are invalid.

---

# 13. Canon Status
This Manifest is canonical and authoritative.

Any modification requires:

- Framework-level validation  
- Inventory update  
- Directory verification  
- Reconvergence  
- Alignment with all invariant layers  

No reasoning may assume changes not recorded in this manifest.

