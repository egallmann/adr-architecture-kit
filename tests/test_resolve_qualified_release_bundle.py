"""Resolver semantics for release-eligible main-push qualification evidence."""

from __future__ import annotations

import json
import urllib.request
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest

from scripts import resolve_qualified_release_bundle as resolver


class _FakeResponse:
    def __init__(self, payload: Any, *, headers: dict[str, str] | None = None) -> None:
        self._payload = payload
        self.headers = headers or {}

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_resolve_success_selects_latest_main_push_with_unique_artifact(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    responses = {
        "/actions/workflows/adr-governance.yml": {"id": 11},
        "/actions/workflows/11/runs": {
            "workflow_runs": [
                {
                    "id": 100,
                    "head_sha": "abc123",
                    "head_branch": "main",
                    "event": "push",
                    "status": "completed",
                    "conclusion": "success",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "html_url": "https://example.test/runs/100",
                },
                {
                    "id": 200,
                    "head_sha": "abc123",
                    "head_branch": "main",
                    "event": "push",
                    "status": "completed",
                    "conclusion": "success",
                    "updated_at": "2026-01-02T00:00:00Z",
                    "html_url": "https://example.test/runs/200",
                },
            ]
        },
        "/actions/runs/200/artifacts": {
            "artifacts": [
                {"name": "release-bundle", "expired": False, "id": 9},
            ]
        },
    }

    captured: list[dict[str, str]] = []

    def fake_urlopen(request: Any, timeout: float = 0) -> _FakeResponse:
        del timeout
        headers = {key.lower(): value for key, value in request.header_items()}
        captured.append(headers)
        path = urlparse(request.full_url).path
        for key, value in responses.items():
            if key in path:
                return _FakeResponse(value)
        raise AssertionError(request.full_url)

    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "egallmann/adr-architecture-kit")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    code = resolver.main(
        [
            "resolve",
            "--sha",
            "abc123",
            "--workflow",
            "adr-governance.yml",
            "--branch",
            "main",
            "--event",
            "push",
            "--artifact-name",
            "release-bundle",
        ]
    )
    out = capsys.readouterr()
    assert code == 0
    assert out.out.strip() == "run_id=200"
    assert "https://example.test/runs/200" in out.err
    for headers in captured:
        assert headers["authorization"] == "Bearer token"
        assert headers["accept"] == "application/vnd.github+json"
        assert headers["x-github-api-version"] == "2026-03-10"
        assert headers["user-agent"] == "adr-architecture-kit-release-resolver"


def test_resolve_rejects_wrong_sha_pr_develop_failed_incomplete_and_artifact_problems(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = [
        (
            [
                {
                    "id": 1,
                    "head_sha": "other",
                    "head_branch": "main",
                    "event": "push",
                    "status": "completed",
                    "conclusion": "success",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "html_url": "u",
                }
            ],
            {"artifacts": [{"name": "release-bundle", "expired": False}]},
        ),
        (
            [
                {
                    "id": 1,
                    "head_sha": "abc123",
                    "head_branch": "main",
                    "event": "pull_request",
                    "status": "completed",
                    "conclusion": "success",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "html_url": "u",
                }
            ],
            {"artifacts": [{"name": "release-bundle", "expired": False}]},
        ),
        (
            [
                {
                    "id": 1,
                    "head_sha": "abc123",
                    "head_branch": "develop",
                    "event": "push",
                    "status": "completed",
                    "conclusion": "success",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "html_url": "u",
                }
            ],
            {"artifacts": [{"name": "release-bundle", "expired": False}]},
        ),
        (
            [
                {
                    "id": 1,
                    "head_sha": "abc123",
                    "head_branch": "main",
                    "event": "push",
                    "status": "completed",
                    "conclusion": "failure",
                    "updated_at": "2026-01-01T00:00:00Z",
                    "html_url": "u",
                }
            ],
            {"artifacts": [{"name": "release-bundle", "expired": False}]},
        ),
        (
            [
                {
                    "id": 1,
                    "head_sha": "abc123",
                    "head_branch": "main",
                    "event": "push",
                    "status": "in_progress",
                    "conclusion": None,
                    "updated_at": "2026-01-01T00:00:00Z",
                    "html_url": "u",
                }
            ],
            {"artifacts": [{"name": "release-bundle", "expired": False}]},
        ),
    ]
    artifact_cases: list[dict[str, Any]] = [
        {"artifacts": []},
        {"artifacts": [{"name": "release-bundle", "expired": True}]},
        {
            "artifacts": [
                {"name": "release-bundle", "expired": False},
                {"name": "release-bundle", "expired": False},
            ]
        },
    ]

    for run_list, artifact_payload in cases:
        responses: dict[str, Any] = {
            "/actions/workflows/adr-governance.yml": {"id": 11},
            "/actions/workflows/11/runs": {"workflow_runs": run_list},
            "/actions/runs/1/artifacts": artifact_payload,
        }

        def fake_urlopen(
            request: Any, timeout: float = 0, _responses: dict[str, Any] = responses
        ) -> _FakeResponse:
            del timeout
            path = urlparse(request.full_url).path
            for key, value in _responses.items():
                if key in path:
                    return _FakeResponse(value)
            raise AssertionError(request.full_url)

        monkeypatch.setenv("GITHUB_TOKEN", "token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "egallmann/adr-architecture-kit")
        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        assert (
            resolver.main(
                [
                    "resolve",
                    "--sha",
                    "abc123",
                    "--workflow",
                    "adr-governance.yml",
                    "--branch",
                    "main",
                    "--event",
                    "push",
                    "--artifact-name",
                    "release-bundle",
                ]
            )
            != 0
        )

    for artifact_payload in artifact_cases:
        artifact_responses: dict[str, Any] = {
            "/actions/workflows/adr-governance.yml": {"id": 11},
            "/actions/workflows/11/runs": {
                "workflow_runs": [
                    {
                        "id": 1,
                        "head_sha": "abc123",
                        "head_branch": "main",
                        "event": "push",
                        "status": "completed",
                        "conclusion": "success",
                        "updated_at": "2026-01-01T00:00:00Z",
                        "html_url": "u",
                    }
                ]
            },
            "/actions/runs/1/artifacts": artifact_payload,
        }

        def fake_urlopen_artifacts(
            request: Any,
            timeout: float = 0,
            _responses: dict[str, Any] = artifact_responses,
        ) -> _FakeResponse:
            del timeout
            path = urlparse(request.full_url).path
            for key, value in _responses.items():
                if key in path:
                    return _FakeResponse(value)
            raise AssertionError(request.full_url)

        monkeypatch.setenv("GITHUB_TOKEN", "token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "egallmann/adr-architecture-kit")
        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen_artifacts)
        assert (
            resolver.main(
                [
                    "resolve",
                    "--sha",
                    "abc123",
                    "--workflow",
                    "adr-governance.yml",
                    "--branch",
                    "main",
                    "--event",
                    "push",
                    "--artifact-name",
                    "release-bundle",
                ]
            )
            != 0
        )


def test_resolve_paginates_and_fails_closed_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    page_one = {
        "workflow_runs": [
            {
                "id": 1,
                "head_sha": "nope",
                "head_branch": "main",
                "event": "push",
                "status": "completed",
                "conclusion": "success",
                "updated_at": "2026-01-01T00:00:00Z",
                "html_url": "u1",
            }
        ]
    }
    page_two = {
        "workflow_runs": [
            {
                "id": 2,
                "head_sha": "abc123",
                "head_branch": "main",
                "event": "push",
                "status": "completed",
                "conclusion": "success",
                "updated_at": "2026-01-03T00:00:00Z",
                "html_url": "u2",
            }
        ]
    }

    def fake_urlopen(request: Any, timeout: float = 0) -> _FakeResponse:
        del timeout
        path = urlparse(request.full_url).path
        query = parse_qs(urlparse(request.full_url).query)
        if path.endswith("/actions/workflows/adr-governance.yml"):
            return _FakeResponse({"id": 11})
        if path.endswith("/actions/workflows/11/runs"):
            page = int(query.get("page", ["1"])[0])
            if page == 1:
                return _FakeResponse(
                    page_one,
                    headers={
                        "Link": '<https://api.github.com/repos/egallmann/adr-architecture-kit/actions/workflows/11/runs?page=2>; rel="next"'
                    },
                )
            return _FakeResponse(page_two)
        if path.endswith("/actions/runs/2/artifacts"):
            return _FakeResponse({"artifacts": [{"name": "release-bundle", "expired": False}]})
        raise AssertionError(request.full_url)

    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_REPOSITORY", "egallmann/adr-architecture-kit")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert (
        resolver.main(
            [
                "resolve",
                "--sha",
                "abc123",
                "--workflow",
                "adr-governance.yml",
                "--branch",
                "main",
                "--event",
                "push",
                "--artifact-name",
                "release-bundle",
            ]
        )
        == 0
    )

    def boom(request: Any, timeout: float = 0) -> _FakeResponse:
        del request, timeout
        raise HTTPError("https://api.github.com", 500, "boom", hdrs=None, fp=None)  # type: ignore[arg-type]

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert (
        resolver.main(
            [
                "resolve",
                "--sha",
                "abc123",
                "--workflow",
                "adr-governance.yml",
                "--branch",
                "main",
                "--event",
                "push",
                "--artifact-name",
                "release-bundle",
            ]
        )
        != 0
    )
