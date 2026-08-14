"""ArchitectureRepository.next_id uses v1.3 alias_id without sequencing UUIDs."""

from __future__ import annotations

from pathlib import Path

import pytest

from adr_kit.repository import ArchitectureRegistryError, ArchitectureRepository
from tests.test_architecture_index_generator import _create_fixture


def _write_logical(
    tmp_path: Path,
    filename: str,
    *,
    declared_id: str,
    alias_id: str | None = None,
    title: str = "Allocation fixture",
) -> Path:
    lines = [
        'schema_version: "1.3"',
        "adr_type: logical",
        f"id: {declared_id}",
        f'title: "{title}"',
        "status: proposed",
        'created_date: "2026-08-13"',
        'authors: ["test.author"]',
        'domains: ["test"]',
        "context: |",
        "  next_id allocation fixture.",
    ]
    if alias_id is not None:
        lines.append(f"alias_id: {alias_id}")
    path = tmp_path / "adrs" / "logical" / filename
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_next_id_uses_legacy_patterned_id_when_alias_id_absent(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    (tmp_path / "adrs" / "logical" / "ADR-L-1099-legacy.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "adr_type: logical",
                "id: ADR-L-1099",
                'title: "Legacy patterned id"',
                "status: proposed",
                'created_date: "2026-04-14"',
                'authors: ["test.author"]',
                'domains: ["test"]',
                "context: |",
                "  Legacy id remains an allocation alias.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    repository = ArchitectureRepository(project_root=tmp_path)

    assert repository.next_id("logical") == "ADR-L-1100"


def test_next_id_uses_v13_alias_id_when_present(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    _write_logical(
        tmp_path,
        "ADR-L-1099-uuid.yaml",
        declared_id="019fee89-e615-7577-8d37-dd0df031bec9",
        alias_id="ADR-L-1099",
    )
    repository = ArchitectureRepository(project_root=tmp_path)

    assert repository.next_id("logical") == "ADR-L-1100"


def test_next_id_mixed_legacy_id_and_v13_alias_uses_highest_effective_alias(
    tmp_path: Path,
) -> None:
    _create_fixture(tmp_path)
    (tmp_path / "adrs" / "logical" / "ADR-L-1200-legacy.yaml").write_text(
        "\n".join(
            [
                'schema_version: "1.0"',
                "adr_type: logical",
                "id: ADR-L-1200",
                'title: "Legacy high water"',
                "status: proposed",
                'created_date: "2026-04-14"',
                'authors: ["test.author"]',
                'domains: ["test"]',
                "context: |",
                "  Mixed corpus.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_logical(
        tmp_path,
        "ADR-L-1300-uuid.yaml",
        declared_id="019fee89-e617-78d9-ba3b-b7e3e6db1b12",
        alias_id="ADR-L-1300",
    )
    repository = ArchitectureRepository(project_root=tmp_path)

    assert repository.next_id("logical") == "ADR-L-1301"


def test_next_id_ignores_uuid_id_without_alias_id(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    _write_logical(
        tmp_path,
        "ADR-L-uuid-only.yaml",
        declared_id="019fee89-e615-7577-8d37-dd0df031bec9",
    )
    repository = ArchitectureRepository(project_root=tmp_path)

    assert repository.next_id("logical") == "ADR-L-1001"


def test_next_id_rejects_duplicate_effective_alias(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    _write_logical(
        tmp_path,
        "ADR-L-1000-uuid.yaml",
        declared_id="019fee89-e615-7577-8d37-dd0df031bec9",
        alias_id="ADR-L-1000",
    )
    repository = ArchitectureRepository(project_root=tmp_path)

    with pytest.raises(ArchitectureRegistryError, match="Duplicate ADR ID"):
        repository.next_id("logical")


def test_next_id_historical_high_water_still_authoritative(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    (tmp_path / ".adr-id-allocation.yaml").write_text(
        "allocation:\n  logical: 1400\n",
        encoding="utf-8",
    )
    _write_logical(
        tmp_path,
        "ADR-L-1099-uuid.yaml",
        declared_id="019fee89-e615-7577-8d37-dd0df031bec9",
        alias_id="ADR-L-1099",
    )
    repository = ArchitectureRepository(project_root=tmp_path)

    assert repository.next_id("logical") == "ADR-L-1401"


def test_next_id_reserved_alias_does_not_advance_normal_allocation(tmp_path: Path) -> None:
    _create_fixture(tmp_path)
    _write_logical(
        tmp_path,
        "ADR-L-9001-reserved.yaml",
        declared_id="019fee89-e616-7066-8d2f-3acc7f469f72",
        alias_id="ADR-L-9001",
    )
    repository = ArchitectureRepository(project_root=tmp_path)

    assert repository.next_id("logical") == "ADR-L-1001"
