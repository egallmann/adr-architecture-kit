"""Resolve a release-eligible ADR Governance main-push run for a tagged SHA."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

GITHUB_API_VERSION = "2026-03-10"
USER_AGENT = "adr-architecture-kit-release-resolver"


class ResolverError(RuntimeError):
    """Fail-closed resolver failure."""


def _api_base() -> str:
    return os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")


def _token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise ResolverError("GITHUB_TOKEN is required")
    return token


def _repository() -> str:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not repository or "/" not in repository:
        raise ResolverError("GITHUB_REPOSITORY must be owner/repo")
    return repository


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": USER_AGENT,
    }


def _request_json(url: str, token: str) -> tuple[Any, Mapping[str, str]]:
    request = urllib.request.Request(url, headers=_headers(token), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
            headers = {key: value for key, value in response.headers.items()}
            return payload, headers
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ResolverError(f"GitHub API HTTP {exc.code} for {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise ResolverError(f"GitHub API transport error for {url}: {exc}") from exc


def _next_link(headers: Mapping[str, str]) -> str | None:
    link = headers.get("Link") or headers.get("link")
    if not link:
        return None
    for part in link.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        start = section.find("<")
        end = section.find(">")
        if start >= 0 and end > start:
            return section[start + 1 : end]
    return None


def _paginate(url: str, token: str, collection_key: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    next_url: str | None = url
    while next_url:
        payload, headers = _request_json(next_url, token)
        if not isinstance(payload, dict):
            raise ResolverError(f"expected object payload from {next_url}")
        batch = payload.get(collection_key)
        if not isinstance(batch, list):
            raise ResolverError(f"expected list '{collection_key}' from {next_url}")
        for entry in batch:
            if isinstance(entry, dict):
                items.append(entry)
        next_url = _next_link(headers)
    return items


def _workflow_id(owner_repo: str, workflow_file: str, token: str) -> int:
    url = f"{_api_base()}/repos/{owner_repo}/actions/workflows/{urllib.parse.quote(workflow_file)}"
    payload, _ = _request_json(url, token)
    if not isinstance(payload, dict) or "id" not in payload:
        raise ResolverError(f"workflow {workflow_file} not found")
    return int(payload["id"])


def _is_qualifying_run(
    run: Mapping[str, Any],
    *,
    sha: str,
    branch: str,
    event: str,
) -> bool:
    return (
        str(run.get("head_sha", "")) == sha
        and str(run.get("head_branch", "")) == branch
        and str(run.get("event", "")) == event
        and str(run.get("status", "")) == "completed"
        and str(run.get("conclusion", "")) == "success"
    )


def _select_latest(runs: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    ranked = sorted(
        runs,
        key=lambda run: (str(run.get("updated_at", "")), int(run.get("id", 0))),
        reverse=True,
    )
    if not ranked:
        raise ResolverError("no qualifying workflow runs")
    return ranked[0]


def _require_unique_artifact(
    run_id: int,
    owner_repo: str,
    artifact_name: str,
    token: str,
) -> None:
    url = f"{_api_base()}/repos/{owner_repo}/actions/runs/{run_id}/artifacts?per_page=100"
    artifacts = _paginate(url, token, "artifacts")
    matches = [item for item in artifacts if str(item.get("name", "")) == artifact_name]
    if not matches:
        raise ResolverError(f"missing artifact {artifact_name!r} on run {run_id}")
    if len(matches) > 1:
        raise ResolverError(f"ambiguous artifact {artifact_name!r} on run {run_id}")
    if bool(matches[0].get("expired")):
        raise ResolverError(f"expired artifact {artifact_name!r} on run {run_id}")


def resolve_run_id(
    *,
    sha: str,
    workflow: str,
    branch: str,
    event: str,
    artifact_name: str,
) -> tuple[int, str]:
    token = _token()
    owner_repo = _repository()
    workflow_id = _workflow_id(owner_repo, workflow, token)
    query = urllib.parse.urlencode(
        {
            "per_page": "100",
            "status": "completed",
            "branch": branch,
            "event": event,
            "head_sha": sha,
        }
    )
    url = f"{_api_base()}/repos/{owner_repo}/actions/workflows/{workflow_id}/runs?{query}"
    runs = _paginate(url, token, "workflow_runs")
    qualifying = [
        run for run in runs if _is_qualifying_run(run, sha=sha, branch=branch, event=event)
    ]
    selected = _select_latest(qualifying)
    run_id = int(selected["id"])
    _require_unique_artifact(run_id, owner_repo, artifact_name, token)
    html_url = str(selected.get("html_url", ""))
    return run_id, html_url


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    resolve = sub.add_parser("resolve")
    resolve.add_argument("--sha", required=True)
    resolve.add_argument("--workflow", required=True)
    resolve.add_argument("--branch", default="main")
    resolve.add_argument("--event", default="push")
    resolve.add_argument("--artifact-name", default="release-bundle")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command != "resolve":
            raise ResolverError(f"unsupported command {arguments.command}")
        run_id, html_url = resolve_run_id(
            sha=arguments.sha,
            workflow=arguments.workflow,
            branch=arguments.branch,
            event=arguments.event,
            artifact_name=arguments.artifact_name,
        )
    except ResolverError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if html_url:
        print(html_url, file=sys.stderr)
    print(f"run_id={run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
