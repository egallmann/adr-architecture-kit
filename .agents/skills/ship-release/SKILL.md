---
name: ship-release
description: >
  Ship an ADR Architecture Kit release from admitted develop through main
  qualification, exact v* tagging, and promotion-only PyPI/npm publish. Use when
  the user asks to cut/ship/release a version, prepare release/X.Y.Z, promote a
  release candidate to main, tag vX.Y.Z after main-push ADR Governance, or close
  the release-protocol skill issue with a validated execution trace.
disable-model-invocation: true
---

# Ship release (`develop` → `release/<ver>` → `main` → `v*` → publish → `develop`)

Repository-owned release procedure for `adr-architecture-kit`. Authority lives in
[`CONTRIBUTING.md`](../../../CONTRIBUTING.md) (“Ship a version” / “Publishing to
npm”). This skill does not invent a second policy: discover and follow that
document; fail closed when it and CI disagree with improvisation.

Recipe shape follows ste-runtime-private `promote-checkpoint` (explicit human
authorization, ordered gates, no silent repair), adapted for ADR-Kit’s release
branch + changelog + dual-distribution promote model.

## Authorization

Do **not** merge to `main`, create/push release tags, or publish without explicit
user approval for that step.

User approval authorizes running the governed protocol. It does **not** bypass
failed gates.

## Parameters

| Parameter | Source |
|---|---|
| `VERSION` | `pyproject.toml` `[project].version` (sole manually edited authority) |
| `TAG` | `v$VERSION` (exact; no other tag shape) |
| `RELEASE_BRANCH` | `release/$VERSION` |
| Distributions | PyPI `adr-architecture-kit` + npm `@system-of-thought/adr-kit` |

Confirm Node metadata with:

```bash
python scripts/sync_node_package_version.py --check
# only if drifting:
python scripts/sync_node_package_version.py --write
```

## Procedure

Execute in order. Stop and report on any failure.

### 1. Admit develop

1. Ensure the intended tip is on `origin/develop`.
2. Wait for successful **develop `push`** ADR Governance on that exact SHA.
3. Confirm no `v$VERSION` tag exists yet; confirm PyPI/npm do not already hold a
   conflicting different artifact for `$VERSION` (exact same version no-op is OK
   only after intentional prior publish).

### 2. Cut release branch

```bash
git fetch origin
git checkout -B release/$VERSION origin/develop
```

Version bump: edit **only** `pyproject.toml` when the version is not already set.
Do not hand-edit `packages/node/package.json` version fields.

### 3. Sectionize changelog

1. Move `CHANGELOG.md` `## [Unreleased]` body into `## [$VERSION] — YYYY-MM-DD`.
2. Restore an empty `## [Unreleased]` heading above it.
3. Commit on `release/$VERSION` (changelog-only commits are expected).

**Local hook note (0.8.0 lesson):** pre-push may run long ADR/docs/pytest bundles
even for a three-line changelog. Prefer letting **PR CI** be the quality gate for
changelog-only release commits; do not invent a second local protocol. If the
user authorizes skipping the local hook for that narrow case, say so explicitly
(`git push --no-verify`) and still require green PR + main-push CI.

### 4. Open release PR → main

```bash
git push -u origin release/$VERSION
gh pr create --base main --head release/$VERSION --title "release: $VERSION" ...
```

Wait for green PR checks. Merge with **merge commit** (not squash/rebase) after
explicit user approval:

```bash
gh pr merge <n> --merge
```

### 5. Main-push qualification (release-eligible)

PR and develop runs are **not** publication admission.

Wait for successful **main `push`** ADR Governance on the merge commit SHA.
Retain the `release-bundle` artifact from that run.

### 6. Tag exactly

On the admitted main SHA only:

```bash
git fetch origin main
git tag -a v$VERSION <main-sha> -m "v$VERSION"
git push origin v$VERSION
```

Tag push triggers promotion-only workflows (no rebuild / no re-pytest).

### 7. Confirm publish

1. `Publish to PyPI` success → `pip index versions adr-architecture-kit` shows `$VERSION`.
2. `Publish to npm` success → `npm view @system-of-thought/adr-kit version` shows `$VERSION`.

If npm fails because a bare `dir/file.tgz` was passed to `npm publish`, that is a
known footgun (npm treats it as a GitHub locator). The workflow must pass an
explicit `./`-prefixed or absolute tarball path. Recover by:

- fixing/publishing via `workflow_dispatch` on `Publish to npm` with input tag
  `v$VERSION` after the path fix is on the default branch used by the workflow, or
- human-authenticated publish of the **exact** retained `node-dist/*.tgz` from the
  qualifying main `release-bundle` (never rebuild).

### 8. Post-release synchronization → develop

Publication does not complete the branch lifecycle. After PyPI and npm both expose
`$VERSION`, synchronize the exact released `main` state back into `develop`:

1. Fetch `origin/main` and `origin/develop`.
2. Create `post-release/$VERSION` from `origin/develop`.
3. Merge `origin/main` into that branch with `--no-ff`; do not copy release files
   manually or squash the synchronization merge.
4. Open a reviewed PR from `post-release/$VERSION` to `develop` and wait for its
   PR checks.
5. Merge the synchronization PR with a merge commit, then wait for successful
   **develop `push`** Develop Assurance on the resulting merge SHA.
6. Run the executable ancestry/version check:

   ```bash
   python scripts/verify_release_branch_sync.py \
     --main-ref origin/main \
     --release-ref v$VERSION \
     --develop-ref origin/develop \
     --expected-version $VERSION
   ```

The synchronization is incomplete if the released `main` commit or current
`main` tip is not an ancestor of `develop`. This is a required post-release gate,
not an optional cleanup step.

### 9. Verify

Record evidence for the skill/issue trail:

- develop tip SHA admitted
- release PR URL + merge commit on `main`
- main ADR Governance run URL (release-eligible)
- tag `v$VERSION` → annotated tag object / target SHA
- PyPI + npm publish run URLs
- installed/version probes
- post-release synchronization PR URL + merge commit on `develop`
- successful develop `push` Develop Assurance run URL
- branch-sync ancestry/version check output

## Fail closed

Do not:

- tag from develop or from a PR head
- publish from a rebuilt local dist when a retained bundle exists
- force-push release branches or tags
- bump past `$VERSION` merely to retry publish
- treat develop/PR green as release-eligible
- declare a release complete while `main` is ahead of `develop`
- auto-merge or auto-tag without explicit human approval

Content repairs belong on `feature/*` → `develop`, then a fresh release cut.

## Evidence anchors

| Release | Notes |
|---|---|
| 0.3.0 | Original issue evidence ([#33](https://github.com/egallmann/adr-architecture-kit/issues/33)) |
| 0.8.0 | Main `c08c83ca6975c9b1e401e499c19cea78585783c6`; tag `v0.8.0`; PyPI published; npm initially failed on bare tarball path then recovered via path fix + dispatch |

## STE reuse posture

This skill is the ADR-Kit **reference implementation**, not an automatic STE-wide
standard. Other STE repos may reference/adapt it and must record deviations.
Extract shared STE invariants only after multi-repo evidence exists.

## Related

- [`CONTRIBUTING.md`](../../../CONTRIBUTING.md)
- ste-runtime-private `.agents/skills/promote-checkpoint` (checkpoint promotion recipe)
