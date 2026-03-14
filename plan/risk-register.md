# Risk Register

| Risk | Severity | Leading Indicator | Mitigation | Containment |
|---|---|---|---|---|
| Consumers bypass the repository boundary | High | New code loads registry YAML directly | Add invariant, migrate CLI/tests, review for raw loaders | Keep raw loader helpers internal to generation/validation code |
| Compiler `ArchModel` leaks as public API | High | New callers import compiler IR for consumer workflows | ADR explicitly marks `ArchModel` internal | Restrict public guidance and route callers to repository/model |
| Registry schema lock-in | High | Consumers depend on concrete registry paths or fields | Hide layout behind repository/model adapters | Version adapters separately from compiled schema |
| Duplicated relationship interpretation | High | Different tools disagree on edge meaning or filtering | Centralize semantic interpretation in repository/model | Add parity tests between bundle and normalized model |
| Unresolved state gets dropped | High | Missing targets represented as absent edges only | Keep unresolved records first-class in model | Add tests asserting non-lossy unresolved preservation |
| Provenance too weak for RECON / EDR joins | Medium | Future embodiment work needs fields not present in boundary | Preserve canonical source refs and derived provenance now | Extend provenance fields in model, not in scattered consumers |
| Multi-repo identity conflation | High | Bare local IDs used as future global IDs | Keep local IDs canonical and treat global IDs as overlays | Add qualified-ID seams without changing local IDs |
| ADR-Kit grows into a proto-kernel | High | Boundary starts absorbing graph execution or federation logic | Keep explicit non-goals in ADR and roadmap | Defer runtime graph features to kernel-specific ADRs |

