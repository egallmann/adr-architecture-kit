from pathlib import Path

from src.adr_kit.compiler.backend.manifest_rendering import build_manifest_from_directory
from src.adr_kit.parser import ADRParser


def test_parse_objection_override(tmp_path):
    parser = ADRParser()
    override_path = tmp_path / "OVERRIDE-0001.yaml"
    override_path.write_text(
        "\n".join(
            [
                'schema_version: "1.1"',
                "type: objection_override",
                "id: OVERRIDE-0001",
                "related_adr: ADR-L-9990",
                "related_review: REVIEW-0001",
                'related_adr_version: "2026-03-14"',
                'objection_summary: "Bounded exception needed for rollout"',
                'override_rationale: "Implementation must proceed before full compliance closes"',
                'accepted_risk: "Short-lived governance variance is accepted"',
                'approving_authority: "erik"',
                'approved_date: "2026-03-18T12:00:00Z"',
                "implementation_effect: exception",
            ]
        ),
        encoding="utf-8",
    )

    override = parser.parse_objection_override(override_path)

    assert override.id == "OVERRIDE-0001"
    assert override.related_review == "REVIEW-0001"
    assert override.approving_authority == "erik"
    assert override.implementation_effect.value == "exception"


def test_parse_steelman_review(tmp_path):
    parser = ADRParser()
    review_path = tmp_path / "REVIEW-0001.yaml"
    review_path.write_text(
        "\n".join(
            [
                'schema_version: "1.1"',
                "type: steelman_review",
                "id: REVIEW-0001",
                "target_adr: ADR-L-9990",
                "review_kind: steelman",
                'review_date: "2026-03-18"',
                'reviewed_by: "erik"',
                'overall_recommendation: "ready with explicit deferred authority"',
                "objections:",
                '  - statement: "Lifecycle status may be too coarse for governance nuance"',
                '    why_it_matters: "Approval and lifecycle remain distinct concepts"',
                '    gap_type: "classification_gap"',
                '    evidence_needed: "Operational examples showing status ambiguity"',
                '    downstream_failure_if_unanswered: "Implementers may misread approval posture"',
                "    disposition: deferred_with_authority",
            ]
        ),
        encoding="utf-8",
    )

    review = parser.parse_steelman_review(review_path)

    assert review.id == "REVIEW-0001"
    assert review.target_adr == "ADR-L-9990"
    assert review.review_kind == "steelman"
    assert review.objections[0].disposition.value == "deferred_with_authority"


def test_manifest_projects_governance_and_override_summary(tmp_path):
    adr_dir = tmp_path / "adrs"
    logical_dir = adr_dir / "logical"
    override_dir = adr_dir / "decisions" / "overrides"
    review_dir = adr_dir / "decisions" / "reviews"
    logical_dir.mkdir(parents=True, exist_ok=True)
    override_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    (logical_dir / "ADR-L-9990-logical.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "adr_type: logical",
                "id: ADR-L-9990",
                'title: "Logical ADR With Override"',
                "status: proposed",
                'created_date: "2026-03-13"',
                "authors: [test.author]",
                "domains: [governance]",
                "context: |",
                "  Manifest projection test ADR.",
                "governance:",
                "  implementation_authority: advisory",
                "  related_reviews: [REVIEW-0001]",
                "  related_overrides: [OVERRIDE-0001]",
                "decisions:",
                "  - id: DEC-0001",
                '    summary: "Test decision"',
                "    rationale: |",
                "      Required for validation.",
            ]
        ),
        encoding="utf-8",
    )
    (override_dir / "OVERRIDE-0001.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.1"',
                "type: objection_override",
                "id: OVERRIDE-0001",
                "related_adr: ADR-L-9990",
                'objection_summary: "Bounded exception needed for rollout"',
                'override_rationale: "Implementation must proceed before full compliance closes"',
                'accepted_risk: "Short-lived governance variance is accepted"',
                'approving_authority: "erik"',
                'approved_date: "2026-03-18T12:00:00Z"',
                "implementation_effect: exception",
            ]
        ),
        encoding="utf-8",
    )
    (review_dir / "REVIEW-0001.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.1"',
                "type: steelman_review",
                "id: REVIEW-0001",
                "target_adr: ADR-L-9990",
                "review_kind: steelman",
                'review_date: "2026-03-18"',
                'reviewed_by: "erik"',
                'overall_recommendation: "ready with explicit deferred authority"',
                "objections:",
                '  - statement: "Lifecycle status may be too coarse for governance nuance"',
                '    why_it_matters: "Approval and lifecycle remain distinct concepts"',
                '    gap_type: "classification_gap"',
                '    evidence_needed: "Operational examples showing status ambiguity"',
                '    downstream_failure_if_unanswered: "Implementers may misread approval posture"',
                "    disposition: deferred_with_authority",
            ]
        ),
        encoding="utf-8",
    )

    manifest = build_manifest_from_directory(adr_dir, parser=ADRParser())

    assert manifest.adrs[0].implementation_authority == "advisory"
    assert manifest.adrs[0].related_reviews == ["REVIEW-0001"]
    assert manifest.adrs[0].related_overrides == ["OVERRIDE-0001"]
    assert manifest.objection_overrides[0].id == "OVERRIDE-0001"
    assert manifest.objection_overrides[0].implementation_effect == "exception"
    assert manifest.steelman_reviews[0].id == "REVIEW-0001"
    assert manifest.steelman_reviews[0].target_adr == "ADR-L-9990"
