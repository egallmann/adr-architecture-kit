"""Generate committed kernel contract JSON Schemas."""

from __future__ import annotations

from pathlib import Path

from adr_kit.schema.kernel_contract import write_kernel_schema_documents


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    output_dir = repo_root / "schema" / "kernel"
    write_kernel_schema_documents(output_dir)
    print(f"Wrote kernel schemas to {output_dir}")


if __name__ == "__main__":
    main()

