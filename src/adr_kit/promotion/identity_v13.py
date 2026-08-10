"""Deterministic A-N2 candidate projection for DJ-adr-kit-canonical-entity-identity-v13.

Amendment wording is derived from the locked A-N2 mutation map and A-N1 outcome
statements. This module is provider mechanics, not a second design authority.
"""

from __future__ import annotations

import copy
import re
from typing import Any

IDENTITY_V13_JOURNAL_ID = "DJ-adr-kit-canonical-entity-identity-v13"

_SCOPED_CHILDREN: dict[str, dict[str, tuple[str, ...]]] = {
    "M-02": {
        "decisions": ("DEC-0004",),
        "interaction_contracts": ("CONTRACT-0001",),
        "constraints": ("CONST-0002",),
        "invariants": ("INV-0005",),
    },
    "M-03": {
        "decisions": ("DEC-0047", "DEC-0077"),
        "capabilities": ("CAP-0038",),
        "prose": ("context",),
    },
    "M-04": {
        "decisions": ("DEC-0050", "DEC-0051", "DEC-0080"),
        "capabilities": ("CAP-0039", "CAP-0047"),
        "prose": ("notes",),
    },
    "M-05": {
        "decisions": ("DEC-0084", "DEC-0085", "DEC-0086", "DEC-0088"),
        "invariants": ("INV-0079", "INV-0081", "INV-0082"),
        "capabilities": ("CAP-0049", "CAP-0052"),
    },
    "M-07": {
        "decisions": ("DEC-0069", "DEC-0073", "DEC-0075"),
        "capabilities": ("CAP-0045",),
        "invariants": ("INV-0069", "INV-0071"),
    },
}


def _find_child(document: dict[str, Any], section: str, child_id: str) -> dict[str, Any]:
    items = document.get(section)
    if not isinstance(items, list):
        raise KeyError(f"missing section {section} for {child_id}")
    for item in items:
        if isinstance(item, dict) and item.get("id") == child_id:
            return item
    raise KeyError(f"missing scoped child {child_id} in {section}")


def _replace_child(document: dict[str, Any], section: str, child: dict[str, Any]) -> None:
    items = document.get(section)
    if not isinstance(items, list):
        raise KeyError(f"missing section {section}")
    child_id = child["id"]
    for index, item in enumerate(items):
        if isinstance(item, dict) and item.get("id") == child_id:
            items[index] = child
            return
    items.append(child)


def apply_identity_v13_amend(mutation_id: str, document: dict[str, Any]) -> dict[str, Any]:
    """Apply deterministic scoped amendments for an identity-v13 mutation."""
    handlers = {
        "M-02": _amend_m02,
        "M-03": _amend_m03,
        "M-04": _amend_m04,
        "M-05": _amend_m05,
        "M-07": _amend_m07,
    }
    handler = handlers.get(mutation_id)
    if handler is None:
        raise ValueError(f"UNSUPPORTED_MUTATION_INSTRUCTION: {mutation_id}")
    return handler(copy.deepcopy(document))


def _amend_m02(document: dict[str, Any]) -> dict[str, Any]:
    dec = _find_child(document, "decisions", "DEC-0004")
    dec["summary"] = (
        "Governed type-prefixed human-recognition aliases (ADR-L-XXXX / ADR-P-XXXX) "
        "with 4-digit numbering; UUID is canonical machine identity"
    )
    dec["rationale"] = (
        "**Human recognition aliases:**\n"
        "- Type-prefixed IDs remain project-local governed `alias_id` surfaces\n"
        "- Alias uniqueness and type visibility remain valuable for documentation\n"
        "- Alias allocation never alters immutable UUID canonical machine identity\n\n"
        "**Canonical machine identity:**\n"
        "- Admitted identity-bearing records use lowercase RFC 9562 UUIDv7 in `id`\n"
        "- Graph / machine operations resolve to UUID, not type-prefixed aliases\n"
    )
    alts = dec.get("alternatives_considered")
    if isinstance(alts, list):
        for alt in alts:
            if isinstance(alt, dict) and "UUID" in str(alt.get("name", "")):
                alt["rejected_because"] = (
                    "A UUID-only human authoring surface is not human-readable and is "
                    "poor for documentation conversation. UUID remains required as "
                    "canonical machine identity; type-prefixed values continue as "
                    "governed human-recognition aliases, not as a substitute for UUID."
                )
    _replace_child(document, "decisions", dec)

    contract = _find_child(document, "interaction_contracts", "CONTRACT-0001")
    guarantees = str(contract.get("guarantees", ""))
    guarantees = guarantees.replace(
        "Type-prefixed IDs (ADR-L-XXXX, ADR-P-XXXX)",
        "Type-prefixed human-recognition aliases (ADR-L-XXXX, ADR-P-XXXX) distinct "
        "from canonical UUID machine identity",
    )
    if "canonical UUID" not in guarantees:
        guarantees = (
            guarantees.rstrip()
            + "\n- Canonical machine identity and relationship targets use UUID\n"
        )
    contract["guarantees"] = guarantees
    _replace_child(document, "interaction_contracts", contract)

    const = _find_child(document, "constraints", "CONST-0002")
    const["description"] = (
        "Type-prefixed IDs (ADR-L-XXXX, ADR-P-XXXX) are governed human-recognition "
        "aliases with 4-digit numbering; canonical machine identity is UUID."
    )
    const["rationale"] = (
        "Prevents alias collision between logical and physical ADRs while keeping "
        "type visible in the human alias. Canonical machine operations and graph "
        "node identity resolve to UUID, not the type-prefixed alias."
    )
    _replace_child(document, "constraints", const)

    inv = _find_child(document, "invariants", "INV-0005")
    inv["statement"] = (
        "Project-local ADR alias IDs must be unique across the project while "
        "canonical machine identity remains UUID"
    )
    inv["rationale"] = (
        "Governed type-prefixed aliases require project-local uniqueness for human "
        "recognition and documentation. Alias uniqueness does not make type-prefixed "
        "values graph node identity; machine identity and relationship targets use UUID."
    )
    _replace_child(document, "invariants", inv)
    return document


def _amend_m03(document: dict[str, Any]) -> dict[str, Any]:
    context = str(document.get("context") or "")
    context = context.replace(
        "bare local IDs must evolve into an unambiguous multi-repository identity model",
        "pre-v1.3 bare local IDs were an authoring convenience that must evolve into "
        "an unambiguous multi-repository identity model",
        1,
    )
    if "pre-v1.3" not in context.lower():
        context = (
            "Pre-v1.3 authoring treated bare local references as the default local rule. " + context
        )
    # Numbered list form used by ADR-L-0012 (may span lines).
    context = re.sub(
        r"(?is)4\.\s*Bare local references remaining valid by default,\s*"
        r"with qualification only\s*when cross-repo references are intended",
        (
            "4. Pre-v1.3 bare local references remained valid by default as historical "
            "authoring ergonomics; v1.3 canonical authored entity references use UUIDs; "
            "provider-authoritative machine identity is (architecture_namespace, UUID); "
            "aliases and legacy IDs remain human-recognition or compatibility surfaces; "
            "and a workspace repository key is registration/routing/attribution only"
        ),
        context,
        count=1,
    )
    # Non-numbered prose form.
    context = re.sub(
        r"(?is)Bare local references remaining valid by default,\s*"
        r"with qualification only\s*when cross-repo references are intended\.?",
        (
            "Pre-v1.3 bare local references remained valid by default as historical "
            "authoring ergonomics; v1.3 canonical authored entity references use UUIDs, "
            "while human alias qualification remains derived"
        ),
        context,
        count=1,
    )
    context = context.replace(
        "workspaceRepoKey:ADR-L-XXXX is treated as qualified identity.",
        (
            "A workspace repository key is registration/routing/attribution only; "
            "canonical external identity is (architecture_namespace, UUID)."
        ),
    )
    if "architecture_namespace" not in context:
        context = (
            context.rstrip() + "\n\nCanonical external identity is (architecture_namespace, UUID); "
            "workspace repository keys do not supply provider namespace identity authority.\n"
        )
    document["context"] = context

    dec47 = _find_child(document, "decisions", "DEC-0047")
    dec47["summary"] = (
        "Qualify machine identity as (architecture_namespace, UUID); keep human "
        "alias qualification derived"
    )
    dec47["rationale"] = (
        "V1.3 canonical external identity is the pair (architecture_namespace, UUID). "
        "Local v1.3 authored references use UUIDs. Human-recognition aliases may be "
        "namespace-qualified for display, but alias qualification remains derived and "
        "is not provider namespace identity authority."
    )
    _replace_child(document, "decisions", dec47)

    dec77 = _find_child(document, "decisions", "DEC-0077")
    dec77["summary"] = (
        "Emit workspace-attribution-federation.yaml as read-only cross-repo attribution "
        "index keyed by workspace routing identity that resolves to architecture_namespace"
    )
    dec77["rationale"] = (
        "Workspace repository keys remain local registration/routing/attribution handles. "
        "They resolve to the provider's architecture_namespace and must not be treated as "
        "the provider identity namespace. Canonical external identity remains "
        "(architecture_namespace, UUID), not a workspace-key-qualified local ADR alias."
    )
    consequences = dec77.get("consequences")
    if isinstance(consequences, dict):
        negative = consequences.get("negative")
        if isinstance(negative, list):
            consequences["negative"] = [
                (
                    (
                        "Workspace manifest repo keys remain stable for routing/attribution "
                        "resolution to architecture_namespace, not as UUID identity namespaces"
                    )
                    if "qualified_id namespaces" in str(item)
                    else item
                )
                for item in negative
            ]
    _replace_child(document, "decisions", dec77)

    cap = _find_child(document, "capabilities", "CAP-0038")
    cap["description"] = (
        "Support unambiguous multi-repository entity references using "
        "architecture_namespace and UUID identity while retaining read-only provider "
        "authority and derived human alias qualification."
    )
    cap["acceptance_criteria"] = [
        "Canonical machine identity resolves as (architecture_namespace, UUID)",
        "Local v1.3 authored references use UUID identity",
        "Human alias qualification remains derived and non-canonical",
        "Provider repositories remain authoritative for their own entity definitions",
        "Federation reads and merges per-repo registries without rewriting them",
        "Workspace repository keys provide routing/attribution only",
    ]
    _replace_child(document, "capabilities", cap)
    return document


def _amend_m04(document: dict[str, Any]) -> dict[str, Any]:
    dec50 = _find_child(document, "decisions", "DEC-0050")
    dec50["summary"] = (
        "Use ArchitectureRepository as the supported in-process semantic entry point "
        "with UUID, governed alias, and logical URI lookup"
    )
    rationale50 = str(dec50.get("rationale") or "")
    dec50["rationale"] = (
        rationale50.rstrip()
        + "\n\nRepository lookup/resolution supports UUID, governed aliases, and logical "
        "URI forms while canonical machine operations resolve to UUID.\n"
    )
    _replace_child(document, "decisions", dec50)

    dec51 = _find_child(document, "decisions", "DEC-0051")
    dec51["summary"] = (
        "Expose NormalizedArchitectureModel 2.0 as the repository semantic payload "
        "carrying UUID/alias/type/URI/time/fingerprint semantics"
    )
    rationale51 = str(dec51.get("rationale") or "")
    dec51["rationale"] = (
        rationale51.rstrip()
        + "\n\nV1.3 advances the normalized semantic model to model 2.0 with UUID IDs/"
        "endpoints, explicit UUID/alias lookups, and versioned compatibility adapters.\n"
    )
    _replace_child(document, "decisions", dec51)

    dec80 = _find_child(document, "decisions", "DEC-0080")
    rationale80 = str(dec80.get("rationale") or "")
    dec80["rationale"] = (
        rationale80.rstrip()
        + "\n\nThe supported facade evolves repository/model consumption for model 2.0 "
        "compatibility adapters without exposing compiler internals or ArchModel.\n"
    )
    _replace_child(document, "decisions", dec80)

    cap39 = _find_child(document, "capabilities", "CAP-0039")
    cap39["description"] = (
        "Provide one scope-safe, deterministic in-process interface that loads compiled "
        "architecture bundles and returns NormalizedArchitectureModel 2.0 with UUID, "
        "alias, and logical URI resolution."
    )
    criteria39 = list(cap39.get("acceptance_criteria") or [])
    criteria39.append(
        "Model 2.0 UUID/alias/URI resolution is available through the repository seam"
    )
    cap39["acceptance_criteria"] = criteria39
    _replace_child(document, "capabilities", cap39)

    cap47 = _find_child(document, "capabilities", "CAP-0047")
    desc47 = str(cap47.get("description") or "")
    if "promotion-provider" not in desc47.lower() and "promotion provider" not in desc47.lower():
        cap47["description"] = (
            desc47.rstrip()
            + " The facade remains a narrow supported authoring SDK and admits only "
            "explicitly authorized public symbols for the current API contract, including "
            "additive promotion-provider operations once separately authorized. Bounded "
            "model 2.0 compatibility adapters may be exposed without exposing compiler "
            "internals and without advertising schema/model embodiment as complete."
        )
    criteria47: list[Any] = []
    replaced_phase1 = False
    for item in list(cap47.get("acceptance_criteria") or []):
        text = str(item)
        if "Phase 1 symbol inventory" in text:
            criteria47.append(
                "the facade exposes only explicitly authorized supported public symbols "
                "for the current API contract, including additive promotion-provider "
                "operations once separately authorized"
            )
            replaced_phase1 = True
        else:
            criteria47.append(item)
    if not replaced_phase1 and not any(
        "promotion-provider" in str(item).lower() or "promotion provider" in str(item).lower()
        for item in criteria47
    ):
        criteria47.append(
            "the facade exposes only explicitly authorized supported public symbols "
            "for the current API contract, including additive promotion-provider "
            "operations once separately authorized"
        )
    if not any("model 2.0" in str(item).lower() for item in criteria47):
        criteria47.append("Bounded model 2.0 compatibility adapters remain on the supported facade")
    cap47["acceptance_criteria"] = criteria47
    _replace_child(document, "capabilities", cap47)

    notes = str(document.get("notes") or "")
    # Remove Phase-2-completed deferrals; retain Phase-3 and structural topology deferral.
    notes = (
        "Explicitly deferred beyond Phase 2 / into Phase 3 or later: graph bundles, "
        "transactional authoring, Assembler implementation, MCP, runtime extraction, "
        "rules, substrate, and admission capability. Topology remains structural-ID-only; "
        "intrinsic UUID identity for topology records remains deferred (D-09). "
        "Phase 2 completed deferrals no longer listed here: assertion identity, "
        "entity/schema expansion, bindings, and normalized-model expansion (now model 2.0).\n"
    )
    document["notes"] = notes
    return document


def _amend_m05(document: dict[str, Any]) -> dict[str, Any]:
    dec84 = _find_child(document, "decisions", "DEC-0084")
    dec84["summary"] = (
        "Represent external bindings as provider-namespace + UUID references with "
        "canonical fingerprint comparability"
    )
    dec84["rationale"] = (
        "External v1.3 references use provider-authoritative architecture_namespace, UUID, "
        "kind, and sha256:<64 lowercase hexadecimal> fingerprint. The fingerprint is "
        "SHA-256 over the provider's complete schema-normalized canonical identity-bearing "
        "entity record serialized with RFC 8785 JCS. Local human aliases remain "
        "non-canonical recognition surfaces."
    )
    _replace_child(document, "decisions", dec84)

    dec85 = _find_child(document, "decisions", "DEC-0085")
    dec85["summary"] = (
        "Retain Phase-2 normalized model 1.1 promotion history and admit model 2.0 as "
        "the v1.3 compatibility event"
    )
    rationale85 = str(dec85.get("rationale") or "")
    dec85["rationale"] = (
        rationale85.rstrip()
        + "\n\nModel 1.1 remains the Phase-2/pre-v1.3 contract. V1.3 UUID identity advances "
        "normalized semantics to model 2.0 without erasing the Phase-2 promotion history.\n"
    )
    _replace_child(document, "decisions", dec85)

    dec86 = _find_child(document, "decisions", "DEC-0086")
    dec86["rationale"] = (
        "V1.3 relationship endpoints are UUIDs. relationship_id is recomputed from "
        "relationship type, source UUID, and target UUID. Content-derived assertion_id "
        "hashes those UUID endpoint values plus exactly one canonical source-owner UUID "
        "and source_pointer_or_empty. Validation and migration preflight fail closed on "
        "ambiguous ownership."
    )
    _replace_child(document, "decisions", dec86)

    dec88 = _find_child(document, "decisions", "DEC-0088")
    dec88["summary"] = (
        "Split UUID integrity corruption (fail closed) from governed alias collision repair"
    )
    dec88["rationale"] = (
        "Distinct entities claiming one UUID fail closed as integrity corruption and are "
        "never auto-repaired. Distinct UUIDs contesting one local alias preserve an "
        "admitted incumbent or otherwise fail pending explicit reviewed alias allocation. "
        "Automatic repair is limited to governed alias allocation/history and never "
        "changes UUIDs or UUID relationship endpoints."
    )
    _replace_child(document, "decisions", dec88)

    inv79 = _find_child(document, "invariants", "INV-0079")
    inv79["statement"] = (
        "Every newly projected relationship assertion MUST receive an assertion_id using "
        "UUID endpoint and single source-owner inputs from DEC-0086, while compatibility "
        "relationship_id semantics remain endpoint-derived from UUIDs."
    )
    _replace_child(document, "invariants", inv79)

    inv81 = _find_child(document, "invariants", "INV-0081")
    rationale81 = str(inv81.get("rationale") or "")
    inv81["rationale"] = (
        rationale81.rstrip()
        + "\n\nThis Phase-2 vocabulary statement remains historical truth for model 1.1; "
        "v1.3 admission and UUID identity evolve under ADR-L-0019 and model 2.0 without "
        "erasing that history.\n"
    )
    _replace_child(document, "invariants", inv81)

    inv82 = _find_child(document, "invariants", "INV-0082")
    inv82["statement"] = (
        "ADR Kit MUST fail closed on duplicate UUID identity and MUST limit automatic "
        "repair to governed alias allocation/history; alias repair MUST NOT rewrite UUID "
        "references or mint replacement UUIDs."
    )
    _replace_child(document, "invariants", inv82)

    cap49 = _find_child(document, "capabilities", "CAP-0049")
    cap49["description"] = (
        "Expose the Phase-2/pre-v1.3 expanded normalized model 1.1 contract and admit "
        "model 2.0 as the v1.3 UUID/alias compatibility event."
    )
    cap49["acceptance_criteria"] = [
        "Model 1.1 remains readable as the Phase-2 contract",
        "Model 2.0 is the v1.3 compatibility event for UUID/alias semantics",
        "Phase-2 promoted types remain queryable through repository APIs",
    ]
    _replace_child(document, "capabilities", cap49)

    cap52 = _find_child(document, "capabilities", "CAP-0052")
    cap52["name"] = "Governed Alias Allocation and UUID Integrity"
    cap52["description"] = (
        "Detect UUID identity collisions and fail closed; limit automatic repair to "
        "governed alias allocation/history."
    )
    cap52["acceptance_criteria"] = [
        "Duplicate UUID identity fails closed and is never auto-repaired",
        "Automatic repair applies only to governed alias allocation/history",
        "Alias repair never rewrites UUID references or UUID relationship endpoints",
    ]
    _replace_child(document, "capabilities", cap52)
    return document


def _amend_m07(document: dict[str, Any]) -> dict[str, Any]:
    dec69 = _find_child(document, "decisions", "DEC-0069")
    dec69["summary"] = (
        "Extend ArchitectureRepository with deterministic orientation helpers for UUID, "
        "alias_id, alias_ref, and URI lookup"
    )
    dec69["rationale"] = (
        "Repository consumers use one in-process boundary for manifest/index/summary "
        "access, entity-reference lookup whose canonical result is UUID, explicit "
        "UUID/alias_id/alias_ref/URI resolve paths, alias inventory, and governed "
        "alias_id allocation for forward authoring."
    )
    _replace_child(document, "decisions", dec69)

    dec73 = _find_child(document, "decisions", "DEC-0073")
    dec73["summary"] = (
        "Make forward-authoring type-prefixed ADR alias_id allocation monotonic and " "non-reusable"
    )
    dec73["rationale"] = (
        "Forward type-prefixed ADR IDs are governed alias_id allocation handles for "
        "human recognition, not canonical machine identity. UUID remains canonical "
        "entity identity. Alias allocation stays monotonic and non-reusable and must "
        "never replace UUIDs or rewrite UUID references."
    )
    _replace_child(document, "decisions", dec73)

    dec75 = _find_child(document, "decisions", "DEC-0075")
    dec75["summary"] = (
        "Exclude reserved ADR alias IDs 9000-9999 from standard forward alias allocation"
    )
    dec75["rationale"] = (
        "The reserved 9000-9999 range preserves governed alias allocation history for "
        "exceptional records. It is not a UUID identity range and must not be treated "
        "as canonical machine-identity allocation."
    )
    _replace_child(document, "decisions", dec75)

    cap = _find_child(document, "capabilities", "CAP-0045")
    cap["description"] = (
        "Provide one supported API and CLI surface for manifest/index/summary access, "
        "UUID and alias lookup/resolve paths, alias inventory, and scope-local governed "
        "alias_id allocation."
    )
    cap["acceptance_criteria"] = [
        "Entity-reference lookup returns UUID as the canonical result",
        "Explicit UUID, alias_id, alias_ref, and URI resolve paths are available",
        "Normal-band alias_id values allocate monotonically and are never reused",
        "Alias allocation never replaces UUIDs or rewrites UUID references",
    ]
    _replace_child(document, "capabilities", cap)

    inv69 = _find_child(document, "invariants", "INV-0069")
    inv69["statement"] = (
        "Forward-authoring governed alias_id allocation MUST be monotonic and "
        "non-reusable. Previously allocated aliases and historical gaps remain consumed "
        "history and MUST NOT be reissued or used to replace UUID identity."
    )
    _replace_child(document, "invariants", inv69)

    inv71 = _find_child(document, "invariants", "INV-0071")
    inv71["statement"] = (
        "Reserved ADR alias IDs `9000-9999` MUST NOT participate in standard forward "
        "alias allocation and MUST NOT be treated as UUID machine-identity allocation."
    )
    _replace_child(document, "invariants", inv71)
    return document


def build_identity_v13_create_context(
    *,
    journal_id: str,
    outcomes: list[dict[str, Any]],
) -> str:
    """Deterministic ADR context for M-01 from Design Journal identity outcomes.

    Logical schema requires ``context``. Content is framed from the journal id and
    the accepted/deferred outcome statements already bound by the promotion contract.
    """

    lines = [
        "Canonical entity identity for schema v1.3 is recorded from Design Journal "
        f"`{journal_id}` after Phase 1 federation, repository-boundary, and schema "
        "v1.2 normalized-semantic foundations.",
        "",
        "Problem drivers captured by promotion-required outcomes:",
    ]
    for outcome in sorted(outcomes, key=lambda item: str(item.get("id", ""))):
        if not outcome.get("promotion_required"):
            continue
        oid = str(outcome.get("id") or "")
        if not (oid.startswith("D-") or oid.startswith("I-")):
            continue
        statement = str(outcome.get("statement") or oid).strip()
        disposition = str(outcome.get("disposition") or "accepted")
        lines.append(f"- {oid} ({disposition}): {statement}")
    return "\n".join(lines)


def build_identity_v13_create_children(
    outcomes: list[dict[str, Any]],
    *,
    dec_ids: list[str],
    inv_ids: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Build DEC/INV/gap children for M-01, including non-active deferred D-12/I-13."""
    d_outcomes = sorted(
        [item for item in outcomes if str(item.get("id", "")).startswith("D-")],
        key=lambda item: item["id"],
    )
    i_outcomes = sorted(
        [item for item in outcomes if str(item.get("id", "")).startswith("I-")],
        key=lambda item: item["id"],
    )
    if len(dec_ids) < len(d_outcomes) or len(inv_ids) < len(i_outcomes):
        raise ValueError("INCOMPLETE_MUTATION_SPECIFICATION: child ID allocation too small")

    decisions: list[dict[str, Any]] = []
    for index, outcome in enumerate(d_outcomes):
        statement = str(outcome.get("statement") or outcome["id"])
        deferred = outcome.get("disposition") == "deferred" or outcome.get("id") == "D-12"
        summary = statement.split(";")[0][:160]
        if deferred:
            summary = "Defer canonical entity-level updated_at to transactional authoring"
        decisions.append(
            {
                "id": dec_ids[index],
                "summary": summary,
                "rationale": statement
                + (
                    "\n\nThis decision records deferral only; it does not activate "
                    "updated_at freshness constraints in v1.3."
                    if deferred
                    else ""
                ),
            }
        )

    invariants: list[dict[str, Any]] = []
    for index, outcome in enumerate(i_outcomes):
        statement = str(outcome.get("statement") or outcome["id"])
        deferred = outcome.get("disposition") == "deferred" or outcome.get("id") == "I-13"
        invariants.append(
            {
                "id": inv_ids[index],
                "statement": statement,
                "scope": "global",
                "enforcement_level": "may" if deferred else "must",
                "enforcement_mechanism": "design",
                "verification_method": "manual" if deferred else "automated",
                "rationale": (
                    "Disposition: deferred. This child records that the updated_at "
                    "ordering constraint is not an active v1.3 identity invariant."
                    if deferred
                    else "Promoted from Design Journal outcome."
                ),
            }
        )

    # CASE B: corpus-governed deferred gap pattern is machine-recognized as non-active.
    gaps = [
        {
            "id": "GAP-0019",
            "question": (
                "Canonical entity-level updated_at and updated_at>=created_at invariant "
                "remain deferred with transactional authoring"
            ),
            "context": (
                "Classification: deferred gap. D-12/I-13 are recorded as deferred children "
                "and must not be treated as active v1.3 identity constraints."
            ),
            "impact": "medium",
            "blocking": False,
        }
    ]
    return decisions, invariants, gaps


def deferred_children_are_non_active(
    decisions: list[dict[str, Any]],
    invariants: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> bool:
    """Evidence helper: deferred encoding must not look like active must-authority."""
    for decision in decisions:
        rationale = str(decision.get("rationale") or "").lower()
        if "updated_at" in rationale and "defer" in rationale:
            if (
                decision.get("status") == "accepted"
                and "[deferred v1.3]" in str(decision.get("details", "")).lower()
            ):
                return False
    for invariant in invariants:
        statement = str(invariant.get("statement") or "").lower()
        if "updated_at" in statement and "defer" in statement:
            if invariant.get("enforcement_level") == "must":
                return False
            if invariant.get("severity") == "must":
                return False
    if not gaps:
        return False
    return any("classification: deferred" in str(gap.get("context") or "").lower() for gap in gaps)


def scoped_child_ids(mutation_id: str) -> dict[str, tuple[str, ...]]:
    return _SCOPED_CHILDREN.get(mutation_id, {})
