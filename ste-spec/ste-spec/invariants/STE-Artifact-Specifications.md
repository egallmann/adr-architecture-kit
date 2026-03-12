# STE Artifact Specifications  
## Canonical Structure and Formatting Rules for All STE Artifacts  
### System of Thought Engineering (STE)

## Publication Notice
This document defines architectural constraints and responsibilities. It does not prescribe implementation.

# 1. Purpose of This Document
This file defines the **artifact-level specifications** required for deterministic interpretation, validation, and synchronization across the STE framework.

Its objectives are to ensure that:

- all STE artifacts follow consistent structure  
- validators can parse and enforce rules deterministically  
- documentation-state is stable and machine-interpretable  
- canonical files do not drift in tone, structure, or semantics  
- artifact types remain well-defined and predictable  

These specifications apply to:

- invariant files  
- documentation-state artifacts  
- framework files  
- validators  
- templates  
- domain and subdomain definitions  

This file resides at the **Artifact Specification Layer** and inherits from:

- Prime Invariant  
- System Invariants  

This file is canonical and must remain synchronized with:

- STE-Invariant-Template
- STE-Framework-Validation-Rules
- STE-Documentation-Validator
- STE-Manifest
- STE-Divergence-Taxonomy

---

# 2. Artifact Categories  
STE defines four primary artifact categories.

## 2.1 AI-DOC  
Authoritative, structured documentation intended for machine consumption and deterministic reasoning.

Characteristics:

- explicit  
- non-narrative  
- declarative  
- deterministic structure  
- validated by Documentation-State Rules  

Examples:

- inventories  
- schemas  
- framework files  
- invariant files  
- validation outputs

Location: `/.ste/state/`

---

## 2.2 Human-DOC  
Documentation intended for human readers, not used as authoritative state.

Characteristics:

- narrative permitted  
- explanatory in nature  
- not authoritative truth unless explicitly promoted to AI-DOC  

Examples:

- guides  
- overview documents  
- blog posts  
- manuals  

Location: `/.ste/human/`

---

## 2.3 Invariant Files  
Documents that define rules governing cognitive behavior.

Characteristics:

- must follow the Invariant Template  
- may not contain narrative or persuasion  
- must be unambiguous  
- must declare placement in the invariant hierarchy  
- must map all divergence triggers to taxonomy  

Examples:

- AWS Domain Invariants  
- IAM Subdomain Invariants  
- Documentation Domain Invariants  
- Meta-Invariants (future)

Location: `/.ste/invariants/`

---

## 2.4 Validators  
Files that define validation logic for:

- structure  
- semantics  
- documentation-state  
- framework alignment  
- divergence classification  

Validators enforce rules; they do not define new constraints.

Location: `/.ste/validation/`

---

# 3. Structural Requirements for All Artifacts

## 3.1 Canonical File Format  
All STE files must:

- be Markdown (*.md*)  
- use H1/H2 for structure predictably  
- avoid embedded styling other than Markdown  
- avoid HTML, unless explicitly declared  
- be free of narrative drift  
- avoid personal pronouns except in Human-DOC  

---

## 3.2 Required Top-Level Structure  
All AI-DOC and invariant files must begin with:

- H1 title  
- H2 purpose statement  
- clear and explicit domain or context  

Validators must begin with:

- purpose  
- scope  
- validation logic  
- divergence integration  

---

## 3.3 Deterministic Ordering  
Sections must appear in stable, predictable order.

Reordering is a divergence unless governed by a structural update to this file.

---

## 3.4 No Narrative Language in AI-DOC  
AI-DOC artifacts must avoid:

- storytelling  
- emotional tone  
- persuasive intent  
- conversational language  

Their purpose is clarity and explicitness.

---

## 3.5 Explicit Dependency Declaration  
Each artifact must list:

- the invariant layers it depends on  
- the validator classes required  
- the taxonomy categories applicable

---

## 3.6 Synchronization Section Requirement

All canonical framework files (files in `/.ste/core/`, `/.ste/protocols/`, `/.ste/validation/`, `/.ste/invariants/`, `/.ste/framework/`) must include a **synchronization section** near the top of the file declaring:

```markdown
This file is canonical and must remain synchronized with:

- [list of files that must stay consistent with this file]
```

**Purpose:**
- Makes cross-file dependencies explicit
- Enables Plan Validation to detect cascade requirements
- Prevents drift between interdependent files
- Supports SYS-16 (Cascade Update Requirement) enforcement

**Requirements:**
- Section must appear after Purpose, before main content
- List must include all files whose content must change when this file changes
- List must include all files that define concepts this file references

**Violation:** Missing synchronization section triggers `Artifact-Structure-Violation`  

Missing dependencies trigger divergence.

---

## 3.6 Canonical Naming  
Each file name must:

- begin with `STE-`  
- use hyphens, not spaces  
- match exact purpose  
- avoid abbreviations, unless defined in STE  

Misnamed artifacts trigger:

- Framework-Structure-Violation  
- Artifact-Type-Mismatch  

---

# 4. Content Requirements for AI-DOC

AI-DOC must be:

- explicit  
- complete  
- declarative  
- unambiguous  
- cross-linked correctly  
- validated before use  

It must not:

- imply state  
- contain opinions  
- include external references as authoritative truth  
- contradict existing documentation-state  

Examples of banned implicit phrases:

- "obviously"  
- "typically"  
- "usually"  
- "you can assume"  

---

# 5. Documentation-State Artifact Requirements

Documentation-state artifacts must:

- reflect authoritative truth  
- be updated before dependent reasoning  
- pass the Documentation Checkpoint Protocol  
- map all changes through the AI-DOC Update Workflow  
- avoid incomplete or partial data  

Documentation-state must remain:

- internally consistent  
- cross-artifact consistent  
- aligned with inventories  
- validated through validators  

Failure triggers:

- Doc-State-Staleness  
- Doc-Missing-Inventory  
- Doc-Linkage-Inconsistency  

---

# 6. Invariant File Requirements  
All invariant files must follow the structure defined in:

**`/.ste/invariants/STE-Invariant-Template.md`**

Requirements include:

- clear scope  
- explicit out-of-scope declaration  
- categorized invariants  
- explicit taxonomy mapping  
- required validator obligations  
- dependency declarations  
- hierarchy placement  

Narrative explanation must be minimal and never persuasive.

---

# 7. Validator Artifact Requirements  
Validator files must:

- define purpose explicitly  
- specify validation logic  
- classify divergence  
- not introduce new rules or constraints  
- follow deterministic parsing rules  

Validators ensure correctness; they do not define new behavior.

---

# 8. Formatting Requirements

## 8.1 Section Headings  
Use:

- H1 for file title  
- H2 for section headers  
- H3+ for subsections  

## 8.2 Lists  
Use bullet or numbered lists consistently.  
Nested lists must be indented using Markdown rules.

## 8.3 Code Blocks  
Use fenced code blocks for:

- schemas  
- directory structures  
- template examples  
- multi-line constraints  

## 8.4 Forbidden Patterns  
The following are prohibited:

- embedded HTML styling  
- unstructured text walls  
- inconsistent Markdown  
- ambiguous headings  

---

# 9. Artifact Lifecycle Requirements

## 9.1 Creation  
All new artifacts require:

- adherence to this file  
- Framework Validator approval  
- addition to Inventory  
- placement under correct directory  

## 9.2 Modification  
All changes must pass:

- Documentation Checkpoint Protocol  
- AI-DOC Update Workflow  
- full validator suite  
- reconvergence  

## 9.3 Removal  
Artifacts may only be removed through:

- Contributor Workflow  
- Inventory update  
- Directory synchronization  
- Framework Validator approval  

---

# 10. Dependencies
This file depends on:

- Prime Invariant  
- System Invariants  
- STE-Invariant-Hierarchy  
- STE-Framework-Directory-Structure  
- STE-Divergence-Taxonomy  

---

# 11. Hierarchy Placement  
This file resides in the:

**Artifact Specification Layer**

It governs structure for all STE artifacts.

---

# 12. Canon Status  
This file is canonical.  
Changes require:

- Framework Validator execution  
- Inventory update  
- Directory verification  
- reconvergence under divergence rules  

All STE artifacts must conform to these specifications.

