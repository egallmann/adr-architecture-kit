# STE AI-DOC Update Workflow Protocol  
## Canonical Workflow for Mutating Documentation-State Artifacts  
### System of Thought Engineering (STE)

## Purpose & Scope

This standard defines the workflow requirements for modifying documentation-state (AI-DOC) artifacts. It establishes the sequence of steps, preconditions, and validation requirements that shall be satisfied when documentation-state is mutated.

**Scope**: Applies to all modifications of AI-DOC artifacts, regardless of size or scope.

**Relationship to Implementation**: This standard prescribes the workflow stages and validation gates, not the mechanisms by which updates are performed.

## Publication Notice

This protocol references several AI-DOC technical specifications that exist in the working repository but are not included in the v1.0.0 public release:

- `STE-AI-DOC-Schema.md` — Schema definition for AI-DOC artifacts
- `STE-AI-DOC-Sliceability-Protocol.md` — Slice boundary and mergeability rules
- `STE-AI-DOC-Invariants.md` — Documentation-state invariant definitions

The architectural principles governing AI-DOC are described in STE-Architecture.md (AI-DOC Fabric section). Formal technical specifications may be published in future releases.

---

# 1. Purpose of This Document
This file defines the **AI-DOC Update Workflow Protocol**, which governs how documentation-state (AI-DOC) may be modified.

Its objectives are to ensure that:

- all AI-DOC updates are explicit  
- updates follow deterministic workflow steps  
- validators enforce correctness before and after mutation  
- documentation-state remains synchronized  
- no implicit updates occur  
- divergence is detected and corrected immediately  

This protocol is mandatory for every documentation-state change, regardless of size or scope.

This file is canonical and must remain synchronized with:

- STE-Documentation-Checkpoint-Protocol
- STE-Documentation-Validator
- STE-Cognitive-Execution-Model
- STE-Divergence-Taxonomy
- STE-AI-DOC-Schema

---

# 2. Preconditions for AI-DOC Updates  
Before modifying any AI-DOC artifact, the following shall be true:

1. **Pre-Task Documentation Checkpoint** has passed.  
2. All relevant documentation-state artifacts are loaded.  
3. Dependencies are explicitly declared.  
4. No divergence is present.  
5. Framework is in synchronized state.  

If any precondition fails, the update shall not proceed.

---

# 3. Workflow Overview  
The AI-DOC Update Workflow consists of:

1. **Identify Update Type**  
2. **Load Relevant Artifacts & Dependencies**  
3. **Apply Explicit Update**  
4. **Synchronize Inventories & References**  
5. **Run State-Mutating Checkpoint**  
6. **Validate & Detect Divergence**  
7. **Reconverge**  
8. **Finalize Update**  

All steps shall be completed in order.

---

# 4. Step 1 — Identify Update Type  
Every AI-DOC update shall be categorized explicitly:

- **New Artifact Creation**  
- **Artifact Modification**  
- **Artifact Removal**  
- **Schema Update**  
- **Inventory Update**  
- **Cross-Artifact Consistency Update**  
- **Incremental RECON Update** (source code change → AI-DOC regeneration)

Ambiguous updates shall be rejected.

## 4.1 Full Workflow vs. Incremental RECON

**Use Full Workflow (this protocol) when:**
- Manual AI-DOC authoring (documented items)
- Schema changes
- Framework modifications
- Inventory updates
- Cross-artifact consistency fixes

**Use Incremental RECON (see STE-Incremental-RECON-Protocol) when:**
- Source code changes detected (file watcher, git hook)
- AI-DOC item's source file modified
- Automatic AI-DOC regeneration from current source
- O(changed files) update required

Both workflows shall pass the same validators and maintain the same invariants.

---

# 5. Step 2 — Load Relevant Artifacts  
The system shall load:

- the artifact being updated  
- referenced inventories  
- schemas  
- dependent documentation-state files  

If a dependency is missing → **Doc-Missing-Inventory**

---

# 6. Step 3 — Apply Explicit Update  
The update shall be:

- precise  
- declarative  
- non-narrative  
- conformant with Artifact Specifications  
- fully replacing (not partially changing) any impacted sections  

Implicit or partial updates are prohibited.

Violations → **Doc-Implicit-State**

---

# 7. Step 4 — Synchronize Inventory and Cross-References  
After applying the update, the following shall be synchronized:

- inventory entries  
- cross-artifact references  
- directory placement  
- naming conventions  

Any inconsistencies → **Doc-Linkage-Inconsistency**

---

# 8. Step 5 — Execute State-Mutating Checkpoint  
This validates the **post-update** documentation-state:

- completeness  
- freshness  
- explicitness  
- structure  
- cross-file consistency  
- dependency coherence  

If the checkpoint fails → divergence shall be corrected.

---

# 9. Step 6 — Validate & Detect Divergence  
Validators shall check:

- artifact structure  
- state integrity  
- domain-specific constraints  
- cross-artifact references  

Any violation shall be classified using the Divergence Taxonomy.

Examples:

- Doc-State-Staleness  
- Artifact-Structure-Violation  
- Doc-Constraint-Drift  
- Domain-Constraint-Violation  

No update may be accepted until all divergence is resolved.

---

# 10. Step 7 — Reconvergence  
Reconvergence occurs when:

- no divergence remains  
- validators pass  
- all structural and semantic checks succeed  
- documentation-state is internally consistent  

Without reconvergence, the update is invalid.

---

# 11. Step 8 — Finalization  
An AI-DOC update is finalized only when:

- state is fully synchronized  
- inventories and references are consistent  
- Documentation Validator passes  
- Framework Validator (if applicable) passes  
- no stale or partial change remains  

Updated artifacts now become the authoritative truth.

---

# 12. Prohibited Update Behaviors  
The following are strictly prohibited:

- modifying documentation-state without running checkpoints  
- updating only part of an artifact  
- assuming state without declaring it  
- relying on external sources as truth  
- bypassing inventory synchronization  
- performing updates without validator passes  

Violations →  
- **Framework-Update-Protocol-Violation**  
- **Doc-Implicit-State**  
- **Doc-State-Staleness**

---

# 13. Validator Integration  
The workflow integrates:

### Documentation Validator  
Checks structure, completeness, explicitness.

### Artifact Validator  
Checks formatting, section ordering, deterministic structure.

### Domain Validator (if applicable)  
Validates domain-specific correctness.

### Framework Validator  
Ensures canonical artifacts (schemas, inventories) remain in sync.

The workflow itself does not modify rules—it enforces them.

---

# 14. Divergence Types Detected  
This workflow may identify:

- Doc-Missing-Inventory  
- Doc-State-Staleness  
- Doc-Linkage-Inconsistency  
- Doc-Implicit-State  
- Artifact-Structure-Violation  
- Artifact-Type-Mismatch  
- Doc-Constraint-Drift  
- Framework-Update-Protocol-Violation  

All divergence shall be resolved before finalization.

---

# 15. Dependencies  
This protocol depends on:

- Prime Invariant  
- System Invariants  
- STE-Documentation-Checkpoint-Protocol  
- STE-Artifact-Specifications  
- STE-Divergence-Taxonomy  

**Related Protocols:**
- STE-Incremental-RECON-Protocol (alternative update workflow for source code changes)
- STE-AI-DOC-Merge-Protocol (merge conflict resolution)

---

# 16. Hierarchy Placement  
This file resides in the:

**Documentation-State Layer**

Location: `/.ste/protocols/`

It governs how documentation-state is mutated.

---

# 17. Canon Status  
This file is canonical.  
Modifications require:

- Framework Validator execution  
- Inventory update  
- Directory verification  
- full reconvergence  

All documentation-state updates shall follow this workflow.


