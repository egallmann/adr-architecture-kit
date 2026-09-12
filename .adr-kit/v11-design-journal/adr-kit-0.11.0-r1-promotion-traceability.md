# ADR-Kit 0.11.0 R1 Promotion Traceability

This document is repository-local promotion evidence for the approved design
lock at
`.adr-kit/v11-design-journal/adr-kit-0.11.0-semantic-design-lock-approved.md`.
It is not normative authority, an executable contract, a release certification,
or a second source of semantic meaning. After promotion, accepted ADRs govern.

## Baseline and bounded scope

- Base: `origin/develop` at `2b4bfeb8ece639ecaa8026a0f68e354c07157165`.
- New authority owner: `ADR-L-0028`.
- Current authoring representation: supported authoring schema v1.5.
- This slice promotes architectural meaning only; it does not implement
  successor schemas, registries, fingerprints, SDK operations, Runtime
  behavior, or release packaging.

## Locked decisions

| Lock | Promoted authority | Realization slice |
| --- | --- | --- |
| LD-01 | ADR-L-0028 DEC-0211; architecture-interpretation 1.0 is a future distinct semantic family in the initial set | Contract-definition |
| LD-02 | ADR-L-0028 DEC-0214 and INV-0221; existing attribution evaluates an explicit pinned materialization | Contract-definition / implementation / Runtime integration |
| LD-03 | ADR-L-0028 DEC-0214 and INV-0221; released evidence-attribution 1.5/1.6 target and verb semantics remain unchanged | Contract-definition |
| LD-04 | ADR-L-0028 DEC-0213 and INV-0220; source, interpretation, result, and binding remain distinct and recovery exposes mismatch | Runtime integration |

## R1 obligation ownership

The owner column points to accepted ADR authority or to an explicit deferred
realization recorded by ADR-L-0028. A slice is not evidence that the behavior
is already implemented.

| Obligation | Owning authority | Realization / evidence slice |
| --- | --- | --- |
| R1-AUTH-01 | ADR-L-0028 DEC-0207, INV-0208; STE-SPEC doctrine where assigned | Contract-definition / Runtime integration |
| R1-NP-01 | ADR-L-0028 DEC-0209, INV-0209; ADR-L-0019 identity authority | Contract-definition |
| R1-NP-02 | ADR-L-0028 DEC-0210, INV-0211; ADR-PC-0002 validation boundary | Contract-definition / semantic review |
| R1-NP-03 | ADR-L-0028 INV-0213; ADR-L-0013 repository boundary | Contract-definition |
| R1-NP-04 | ADR-L-0028 INV-0209, INV-0210, INV-0211; ADR-PC-0004 | Contract-definition / implementation |
| R1-INT-01 | ADR-L-0028 DEC-0211, INV-0214; ADR-L-0025 succession authority | Contract-definition |
| R1-INT-02 | ADR-L-0028 INV-0214; ADR-L-0025 and ADR-PC-0003 | Contract-definition / implementation |
| R1-SCV-01 | ADR-L-0028 DEC-0213, INV-0215; ADR-L-0025 | Contract-definition |
| R1-SCV-02 | ADR-L-0028 INV-0215; ADR-L-0025 and ADR-PC-0002/0005 | Contract-definition |
| R1-SCS-01 | ADR-L-0028 INV-0216; ADR-L-0025 and ADR-PC-0003 | Contract-definition |
| R1-SCS-02 | ADR-L-0028 DEC-0213, INV-0216; ADR-L-0025 and ADR-PC-0003 | Contract-definition |
| R1-SCS-03 | ADR-L-0028 DEC-0213, INV-0215; ADR-L-0025 and ADR-PC-0005 | Contract-definition / Runtime integration |
| R1-SCS-04 | ADR-L-0028 INV-0216; ADR-L-0013 and existing Runtime authority | Implementation / Runtime integration |
| R1-SRC-01 | ADR-L-0028 DEC-0212, INV-0217; ADR-L-0013 and ADR-PC-0004/0008 | Contract-definition / implementation |
| R1-SRC-02 | ADR-L-0028 INV-0217; ADR-L-0013 and ADR-PC-0004 | Contract-definition |
| R1-SRC-03 | ADR-L-0028 DEC-0212, INV-0218; ADR-L-0019/0022 and ADR-PC-0006 | Contract-definition / implementation |
| R1-RES-01 | ADR-L-0028 INV-0219; ADR-L-0013 | Contract-definition / implementation |
| R1-RES-02 | ADR-L-0028 INV-0219; ADR-L-0013 | Contract-definition / implementation |
| R1-RES-03 | ADR-L-0028 INV-0213, INV-0219 | Contract-definition / semantic review |
| R1-FP-01 | ADR-L-0028 DEC-0213, INV-0220; ADR-L-0013/0019 and ADR-PC-0004 | Contract-definition |
| R1-FP-02 | ADR-L-0028 DEC-0213, INV-0220; ADR-L-0013 and Runtime authority | Contract-definition / Runtime integration |
| R1-HIST-01 | ADR-L-0028 DEC-0213, INV-0220; ADR-L-0025/0027 and Runtime authority | Runtime integration |
| R1-HIST-02 | ADR-L-0028 DEC-0213, INV-0220; ADR-L-0013 and Runtime authority | Runtime integration |
| R1-LINK-01 | ADR-L-0028 DEC-0214, INV-0221; ADR-L-0020 and ADR-PC-0007 | Contract-definition / implementation / Runtime integration |
| R1-LINK-02 | ADR-L-0028 DEC-0214, INV-0221; ADR-L-0020 and ADR-PC-0007 | Contract-definition |
| R1-HOST-01 | ADR-L-0028 DEC-0215, INV-0222; ADR-L-0027 | Implementation / release-certification |
| R1-PUB-01 | ADR-L-0028 DEC-0215, INV-0222; ADR-L-0027 | Implementation / release-certification |
| R1-RUN-01 | ADR-L-0028 DEC-0207, DEC-0213; external Runtime authority | Runtime integration |

## STE-SPEC sequencing exception

ADR-L-0044 at feature commit
`e21b8409f09d01be419db09d979ce924a92e3777` is qualified directional design
evidence only. It is not admitted STE-SPEC develop authority. ADR-Kit may
refine concrete authoring, normalization, materialization, registry,
fingerprint, and SDK mechanics, but may not redefine STE-wide normative force,
authority, competence, effectivity, applicability, epistemic boundaries,
bounded-outcome semantics, or the NP/Invariant peer distinction. STE-SPEC is
not modified in this slice, and CE-01 is not a hidden prerequisite.

## Deferred realization boundary

The contract-definition slice must define authoring 1.6, normalized 2.3,
normative-semantics 1.0, architecture-interpretation 1.0,
architecture-materialization envelopes, exact qualification and fingerprint
domains, and project metadata support for `project.type: specification`. Later
slices realize shared-core/public host operations, Runtime retention and
recovery, and release qualification. Direct NP-target attribution and general
Requirements semantics remain explicitly outside the initial release unless
separately promoted.
