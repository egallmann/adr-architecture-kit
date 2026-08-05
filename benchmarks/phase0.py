"""Deterministic Phase 0 functional and performance benchmark harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import statistics
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Callable, Sequence, TypeVar

import yaml

from adr_kit.compiler import ArchitectureCompiler, CompilerConfig
from adr_kit.compiler.backend.graph_rendering import build_architecture_graph, render_graph_yaml
from adr_kit.compiler.frontend import CachedADRParser, FrontendBuildResult
from adr_kit.compiler.pipeline import (
    ADRNormalizationPass,
    ADRParsePass,
    CompilerPipelineState,
    InvariantExtractionPass,
    LogicalEntityExtractionPass,
    PhysicalEntityExtractionPass,
    RelationshipInferencePass,
)
from adr_kit.compiler.registry_bundle import assemble_registry_bundle, render_bundle_yaml
from adr_kit.compiler.diagnostics import DiagnosticLog
from adr_kit.parser import ADRParser
from adr_kit.repository import ArchitectureRepository
from adr_kit.scope import ProjectScope, ProjectScopeResolver
from adr_kit.validators import ADRValidator

ROOT = Path(__file__).resolve().parents[1]
FIXED_TIMESTAMP = "2026-01-01T00:00:00Z"
STAGE_NAMES = (
    "schema_validation",
    "parsing",
    "normalization",
    "extraction",
    "relationship_derivation",
    "registry_generation",
    "graph_generation",
    "serialization",
    "filesystem_writes",
    "full_compilation",
    "repository_loading",
    "representative_queries",
)
SOURCE_DIRS = ("logical", "physical", "physical-system", "physical-component", "invariants")
T = TypeVar("T")


@dataclass(frozen=True)
class CorpusCase:
    name: str
    root: Path
    adr_count: int
    identity: str


def _measure(operation: Callable[[], T]) -> tuple[float, T]:
    started = perf_counter_ns()
    value = operation()
    return (perf_counter_ns() - started) / 1_000_000, value


def _write_project(root: Path, name: str) -> None:
    payload = {
        "schema_version": "1.0",
        "type": "project_metadata",
        "project": {"name": name, "description": "Phase 0 benchmark corpus", "type": "library"},
        "ownership": {"team": "benchmark", "tech_lead": "benchmark"},
        "repository": {"url": "local/benchmark", "primary_branch": "main"},
        "architecture_documentation": {
            "adr_directory": "adrs/",
            "manifest_path": "adrs/manifest.yaml",
            "architecture_namespace": name,
        },
    }
    (root / "PROJECT.yaml").write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _synthetic_case(base: Path, size: int) -> CorpusCase:
    root = base / f"synthetic-{size}"
    logical = root / "adrs" / "logical"
    logical.mkdir(parents=True)
    _write_project(root, f"phase0-synthetic-{size}")
    for offset in range(size):
        sequence = 1000 + offset
        payload = {
            "schema_version": "1.0",
            "adr_type": "logical",
            "id": f"ADR-L-{sequence:04d}",
            "title": f"Deterministic synthetic decision {sequence:04d}",
            "status": "proposed",
            "created_date": "2026-01-01",
            "authors": ["phase0-benchmark"],
            "domains": ["benchmark"],
            "context": "Fixed-seed synthetic benchmark input.",
            "decisions": [
                {
                    "id": f"DEC-{sequence:04d}",
                    "summary": f"Synthetic decision {sequence:04d}",
                    "rationale": "Deterministic benchmark rationale.",
                }
            ],
        }
        path = logical / f"ADR-L-{sequence:04d}-synthetic.yaml"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return _case("synthetic", root)


def _copy_case(base: Path, name: str, source: Path) -> CorpusCase:
    root = base / name
    root.mkdir(parents=True)
    _write_project(root, f"phase0-{name}")
    for directory in SOURCE_DIRS:
        source_dir = source / directory
        if source_dir.exists():
            shutil.copytree(source_dir, root / "adrs" / directory)
    return _case(name, root)


def _case(name: str, root: Path) -> CorpusCase:
    sources = sorted((root / "adrs").rglob("*.yaml"))
    digest = hashlib.sha256()
    for path in sources:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return CorpusCase(name=name, root=root, adr_count=len(sources), identity=digest.hexdigest())


def _new_state(scope: ProjectScope) -> CompilerPipelineState:
    return CompilerPipelineState(
        scope=scope,
        parser=CachedADRParser(ADRParser()),
        config=CompilerConfig(pinned_timestamp=FIXED_TIMESTAMP),
        diagnostics=DiagnosticLog(),
    )


def _run_iteration(case: CorpusCase, output: Path) -> tuple[dict[str, float], str]:
    timings: dict[str, float] = {}
    resolver = ProjectScopeResolver(explicit_scope=case.root)
    scope = resolver.resolve()
    validator = ADRValidator(scope_resolver=resolver)

    timings["schema_validation"], validation = _measure(
        lambda: validator.validate_directory(scope.adr_dir, scope)
    )
    if validation.get("errors"):
        raise RuntimeError(f"benchmark corpus validation failed: {validation['errors']}")

    state = _new_state(scope)
    timings["parsing"], _ = _measure(lambda: ADRParsePass().run(state))
    timings["normalization"], _ = _measure(lambda: ADRNormalizationPass().run(state))

    def extract() -> None:
        LogicalEntityExtractionPass().run(state)
        InvariantExtractionPass().run(state)
        PhysicalEntityExtractionPass().run(state)

    timings["extraction"], _ = _measure(extract)
    timings["relationship_derivation"], _ = _measure(lambda: RelationshipInferencePass().run(state))
    build_result = FrontendBuildResult(
        model=state.model, coverage=state.coverage, namespace=state.namespace
    )
    timings["registry_generation"], bundle = _measure(
        lambda: assemble_registry_bundle(
            state.model,
            coverage=state.coverage,
            namespace=state.namespace,
            generated_at=state.model.metadata.generated_at,
            diagnostics=state.diagnostics,
        )
    )
    timings["graph_generation"], graph = _measure(lambda: build_architecture_graph(build_result))
    timings["serialization"], serialized = _measure(
        lambda: (render_bundle_yaml(bundle.entity_registry), render_graph_yaml(graph))
    )

    def write_files() -> None:
        output.mkdir(parents=True, exist_ok=True)
        (output / "bundle.yaml").write_text(serialized[0], encoding="utf-8")
        (output / "graph.yaml").write_text(serialized[1], encoding="utf-8")

    timings["filesystem_writes"], _ = _measure(write_files)
    compiler = ArchitectureCompiler(scope_resolver=resolver)
    timings["full_compilation"], compilation = _measure(
        lambda: compiler.compile(
            scope,
            CompilerConfig(emit={"registries", "manifest"}, pinned_timestamp=FIXED_TIMESTAMP),
        )
    )
    if not compilation.success:
        raise RuntimeError("full benchmark compilation failed")
    repository = ArchitectureRepository(project_root=case.root)
    timings["repository_loading"], model = _measure(repository.get_model)

    def query() -> tuple[int, int, int]:
        return (
            len(repository.get_decisions()),
            len(repository.get_relationships()),
            repository.get_corpus_summary().unresolved_count,
        )

    timings["representative_queries"], _ = _measure(query)
    return timings, model.fingerprint


def _summarize(samples: list[dict[str, float]]) -> dict[str, dict[str, object]]:
    summary: dict[str, dict[str, object]] = {}
    for stage in STAGE_NAMES:
        values = [sample[stage] for sample in samples]
        warm = values[1:]
        summary[stage] = {
            "cold_first_ms": round(values[0], 3),
            "warm_ms": [round(value, 3) for value in warm],
            "warm_median_ms": round(statistics.median(warm), 3) if warm else None,
        }
    return summary


def _parse_sizes(value: str) -> list[int]:
    sizes = [int(item) for item in value.split(",")]
    if not sizes or any(size < 1 or size > 8999 for size in sizes):
        raise argparse.ArgumentTypeError("sizes must be between 1 and 8999")
    return sizes


def run(corpus: str, sizes: list[int], warmups: int, repeats: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="adr-kit-phase0-benchmark-") as temporary:
        base = Path(temporary)
        cases: list[CorpusCase] = []
        if corpus in ("all", "repository"):
            cases.append(_copy_case(base, "repository", ROOT / "adrs"))
        if corpus in ("all", "examples"):
            cases.append(_copy_case(base, "examples", ROOT / "examples" / "public-v1" / "adrs"))
        if corpus in ("all", "synthetic"):
            cases.extend(_synthetic_case(base, size) for size in sizes)

        results: list[dict[str, object]] = []
        fingerprints: dict[str, str] = {}
        deterministic = True
        for case in cases:
            for index in range(warmups):
                _run_iteration(case, base / "outputs" / case.name / f"warmup-{index}")
            samples: list[dict[str, float]] = []
            case_fingerprints: list[str] = []
            for index in range(repeats + 1):
                timings, fingerprint = _run_iteration(
                    case, base / "outputs" / case.name / f"repeat-{index}"
                )
                samples.append(timings)
                case_fingerprints.append(fingerprint)
            deterministic = deterministic and len(set(case_fingerprints)) == 1
            fingerprints[f"{case.name}:{case.adr_count}"] = case_fingerprints[0]
            results.append(
                {
                    "corpus": case.name,
                    "adr_count": case.adr_count,
                    "identity": case.identity,
                    "stages": _summarize(samples),
                }
            )
        return {
            "schema_version": 1,
            "environment": {
                "python": platform.python_version(),
                "implementation": platform.python_implementation(),
                "platform": platform.platform(),
            },
            "configuration": {
                "corpus": corpus,
                "sizes": sizes,
                "warmups": warmups,
                "repeats": repeats,
            },
            "results": results,
            "fingerprints": fingerprints,
            "deterministic": deterministic,
        }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus", choices=("all", "repository", "examples", "synthetic"), default="all"
    )
    parser.add_argument("--sizes", type=_parse_sizes, default=_parse_sizes("10,100,500"))
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--json-out", type=Path, required=True)
    arguments = parser.parse_args(argv)
    if arguments.warmups < 0 or arguments.repeats < 1:
        parser.error("warmups must be >= 0 and repeats must be >= 1")
    try:
        payload = run(arguments.corpus, arguments.sizes, arguments.warmups, arguments.repeats)
        arguments.json_out.parent.mkdir(parents=True, exist_ok=True)
        arguments.json_out.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(arguments.json_out)
        return 0 if payload["deterministic"] else 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"benchmark failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
