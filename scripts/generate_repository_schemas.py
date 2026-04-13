"""Generate committed repository schema JSON Schemas.

Writes Pydantic-derived JSON Schema documents for the repository-normalized
discovery models into schema/kernel/. These schemas describe the shape of
artifacts this repository produces for the kernel-compatibility boundary.
They are not the normative cross-repo Architecture IR schemas; that authority
belongs to ste-spec.
"""

from __future__ import annotations

from pathlib import Path

from adr_kit.schema.repository_schema_generator import write_repository_schema_documents


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "schema" / "kernel"
    write_repository_schema_documents(output_dir)
    print(f"Wrote repository schemas to {output_dir}")


if __name__ == "__main__":
    main()
