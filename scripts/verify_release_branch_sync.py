"""Verify that the released main state has been synchronized into develop."""

from __future__ import annotations

import argparse
import subprocess
import tomllib


def _commit(ref: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"cannot resolve commit ref {ref!r}: {result.stderr.strip()}")
    return result.stdout.strip()


def _is_ancestor(ancestor: str, descendant: str, *, label: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"{label} is not contained in develop")


def _develop_version(develop_ref: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{develop_ref}:pyproject.toml"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"cannot read pyproject.toml from {develop_ref!r}")
    try:
        payload = tomllib.loads(result.stdout)
        return str(payload["project"]["version"])
    except (KeyError, TypeError, tomllib.TOMLDecodeError) as exc:
        raise SystemExit(f"invalid project version in {develop_ref!r}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify that main and the released tag are ancestors of develop."
    )
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--develop-ref", default="origin/develop")
    parser.add_argument("--expected-version", required=True)
    args = parser.parse_args()

    main_commit = _commit(args.main_ref)
    release_commit = _commit(args.release_ref)
    develop_commit = _commit(args.develop_ref)
    _is_ancestor(main_commit, develop_commit, label=f"main ref {args.main_ref!r}")
    _is_ancestor(release_commit, develop_commit, label=f"release ref {args.release_ref!r}")

    version = _develop_version(args.develop_ref)
    if version != args.expected_version:
        raise SystemExit(
            f"develop package version {version!r} does not match expected release "
            f"{args.expected_version!r}"
        )

    print(f"main ref {args.main_ref}: {main_commit}")
    print(f"release ref {args.release_ref}: {release_commit}")
    print(f"develop ref {args.develop_ref}: {develop_commit}")
    print(f"develop package version: {version}")
    print("post-release branch synchronization verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
