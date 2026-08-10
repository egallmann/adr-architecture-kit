#!/usr/bin/env python3
"""Leg A: prepare the real v1.3 Promotion Contract via public SDK and stop for human lock."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from adr_kit.api import PromotionPrepareRequest, prepare_promotion
from adr_kit.promotion.ste_contract import locked_intent_fingerprint, mechanical_ready

REPO_ROOT = Path(__file__).resolve().parents[1]
PC_PATH = (
    REPO_ROOT
    / "docs"
    / "design-journal"
    / "2026-canonical-entity-identity-v13.promotion-contract.json"
)
# Local transient handoff under existing ignored kit state (not Git authority).
OUT_DIR = REPO_ROOT / ".adr-kit" / "promotion"
PREPARED_PATH = OUT_DIR / "2026-canonical-entity-identity-v13.prepared.promotion-contract.json"
REVIEW_PATH = OUT_DIR / "2026-canonical-entity-identity-v13.promotion-review.md"


def main() -> int:
    if not PC_PATH.is_file():
        print(f"missing promotion contract: {PC_PATH}", file=sys.stderr)
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Invalidate any prior invalid prepared handoff before writing a fresh one.
    for stale in OUT_DIR.glob("2026-canonical-entity-identity-v13*"):
        if stale.is_file():
            stale.unlink()
    store = REPO_ROOT / ".adr-kit" / "promotion"
    payloads = store / "payloads"
    if payloads.is_dir():
        for stale in payloads.glob("M-0*.bin"):
            stale.unlink()
        for stale in payloads.glob("M-0*.review.yaml"):
            stale.unlink()
        for stale in payloads.glob("M-0*.review.md"):
            stale.unlink()

    result = prepare_promotion(
        PromotionPrepareRequest(
            project_root=REPO_ROOT,
            promotion_contract_path=PC_PATH,
            prepared_contract_output_path=PREPARED_PATH,
        )
    )
    prepared = result.prepared_contract
    ready, ready_errors = mechanical_ready(prepared)
    fingerprint = locked_intent_fingerprint(prepared)

    # Human-review representations derived from exact bound payload bytes (not authority).
    reviewable_paths: list[str] = []
    for mutation in prepared.get("mutations", []):
        mutation_id = mutation["id"]
        binding = mutation.get("payload_binding") or {}
        ref = str(binding.get("ref") or "")
        if not ref.startswith("payloads/"):
            continue
        bin_path = store / ref
        if not bin_path.is_file():
            continue
        raw = bin_path.read_bytes()
        # Prove review bytes == bound bytes by writing the exact UTF-8 payload.
        review_path = payloads / f"{mutation_id}.review.yaml"
        if mutation["provider_target_ref"].startswith("file:"):
            review_path = payloads / f"{mutation_id}.review.md"
        review_path.write_bytes(raw)
        if review_path.read_bytes() != raw:
            raise SystemExit(f"review representation drift for {mutation_id}")
        reviewable_paths.append(review_path.as_posix())

    review = [
        "# v1.3 Promotion Review Projection",
        "",
        f"- prepared_contract: `{PREPARED_PATH.as_posix()}`",
        f"- locked_intent_fingerprint: `{fingerprint}`",
        f"- design_lock_ready: {result.design_lock_ready}",
        f"- mechanical_promotion_ready: {result.mechanical_promotion_ready and ready}",
        f"- baseline_equivalent: {result.baseline.equivalent}",
        f"- authority_mutated: {result.authority_mutated}",
        f"- blockers: {len(result.blockers)}",
        f"- reviewable_payloads: {len(reviewable_paths)}",
        "",
        "## Reviewable post-images (exact bound bytes)",
        "",
    ]
    for path in reviewable_paths:
        review.append(f"- `{path}`")
    review.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    if result.blockers:
        for blocker in result.blockers:
            review.append(f"- `{blocker.id}` `{blocker.code}`: {blocker.message}")
    else:
        review.append("- none")
    if ready_errors:
        review.extend(["", "## Mechanical readiness errors", ""])
        for item in ready_errors:
            review.append(f"- {item}")
    review.extend(
        [
            "",
            "## Mutations",
            "",
        ]
    )
    for mutation in result.mutations:
        review.append(
            f"- `{mutation.mutation_id}` `{mutation.operation}` "
            f"`{mutation.provider_target_ref}` → `{mutation.relative_path}`"
        )
    review.extend(
        [
            "",
            "## Mandatory stop",
            "",
            "```text",
            "HUMAN_PROMOTION_LOCK_REQUIRED",
            "```",
            "",
            "Do not fabricate `human_lock`. Do not apply authority promotion in this Leg A step.",
            "",
        ]
    )
    REVIEW_PATH.write_text("\n".join(review), encoding="utf-8")
    print(
        json.dumps(
            {
                "success": result.success,
                "mechanical_promotion_ready": bool(result.mechanical_promotion_ready and ready),
                "baseline_equivalent": result.baseline.equivalent,
                "authority_mutated": result.authority_mutated,
                "prepared_contract_path": str(PREPARED_PATH),
                "review_path": str(REVIEW_PATH),
                "locked_intent_fingerprint": fingerprint,
                "blocker_count": len(result.blockers),
                "reviewable_payloads": reviewable_paths,
                "HUMAN_PROMOTION_LOCK_REQUIRED": True,
            },
            indent=2,
        )
    )
    return 0 if result.authority_mutated is False else 1


if __name__ == "__main__":
    raise SystemExit(main())
