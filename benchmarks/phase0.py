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
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import TypeVar

import yaml

from adr_kit.compiler import ArchitectureCompiler, CompilerConfig
from adr_kit.api import (
    CompilationRequest,
    ValidationRequest,
    compile_architecture,
    open_repository,
    validate_architecture,
)
from adr_kit.compiler.backend.graph_rendering import build_architecture_graph, render_graph_yaml
from adr_kit.compiler.diagnostics import DiagnosticLog
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
from adr_kit.generators import ArchitectureIndexGenerator
from adr_kit.identity import derive_assertion_id
from adr_kit.migrators import TopologyIdentityMigrator
from adr_kit.migrators.identity_v13 import IdentityV13Migrator
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
SDK_STAGE_NAMES = ("sdk_validate", "sdk_compile_preview", "sdk_open_repository")
PHASE2_STAGE_NAMES = (
    "v12_parsing",
    "semantic_compilation",
    "assertion_derivation_1000",
    "topology_migration_plan",
    "v13_identity_preflight",
    "v13_identity_plan",
    "v13_model2_compile",
    "v13_model2_repository_load",
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


def _phase2_case(base: Path) -> CorpusCase:
    root = base / "phase2-semantic"
    root.mkdir(parents=True)
    _write_project(root, "phase2-semantic")
    fixture_root = ROOT / "tests" / "fixtures" / "v1_2"
    fixtures = (
        ("logical-bindings.yaml", "logical", "ADR-L-9801-bindings.yaml"),
        (
            "physical-component-semantics.yaml",
            "physical-component",
            "ADR-PC-9801-semantics.yaml",
        ),
        ("physical-system-topology.yaml", "physical-system", "ADR-PS-9801-topology.yaml"),
    )
    for source_name, directory, destination_name in fixtures:
        destination = root / "adrs" / directory / destination_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fixture_root / source_name, destination)
    return _case("phase2-semantic", root)


def _v13_model2_case(base: Path) -> CorpusCase:
    """Tiny authored v1.3 corpus for model 2.0 compile/load timing."""
    root = base / "phase2-v13-model2"
    logical = root / "adrs" / "logical"
    logical.mkdir(parents=True)
    _write_project(root, "phase2-v13-model2")
    payload = {
        "schema_version": "1.3",
        "adr_type": "logical",
        "id": "019fee89-e615-70a5-861b-b2dde147e5af",
        "alias_id": "ADR-L-7001",
        "alias_name": "benchmark-v13",
        "title": "Benchmark v1.3 logical ADR",
        "status": "accepted",
        "created_date": "2026-01-01",
        "authors": ["phase0-benchmark"],
        "domains": ["benchmark"],
        "context": "Deterministic v1.3 model 2.0 benchmark input.",
        "capabilities": [
            {
                "id": "019fee89-e614-7c68-be36-2c84d4579279",
                "alias_id": "CAP-7001",
                "alias_name": "benchmark-capability",
                "name": "Benchmark capability",
                "description": "Deterministic capability for model 2.0 timing.",
            }
        ],
        "decisions": [
            {
                "id": "019fee89-e615-7bb9-ad3b-93d12b0f65b6",
                "alias_id": "DEC-7001",
                "alias_name": "benchmark-decision",
                "summary": "Benchmark decision",
                "rationale": "Deterministic decision for model 2.0 timing.",
                "enables_capabilities": ["019fee89-e614-7c68-be36-2c84d4579279"],
            }
        ],
        "architectural_boundaries": [],
        "interaction_contracts": [],
        "constraints": [],
        "non_functional_requirements": [],
        "invariants": [],
        "gaps": [],
    }
    path = logical / "ADR-L-7001-benchmark-v13.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return _case("phase2-v13-model2", root)


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


def _run_iteration(
    case: CorpusCase, output: Path
) -> tuple[dict[str, float], str, dict[str, float], dict[str, object]]:
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
    sdk_timings: dict[str, float] = {}
    sdk_timings["sdk_validate"], sdk_validation = _measure(
        lambda: validate_architecture(ValidationRequest(case.root))
    )
    sdk_timings["sdk_compile_preview"], sdk_compilation = _measure(
        lambda: compile_architecture(CompilationRequest(case.root, timestamp=FIXED_TIMESTAMP))
    )
    sdk_timings["sdk_open_repository"], sdk_repository = _measure(
        lambda: open_repository(case.root)
    )
    if not sdk_validation.success or not sdk_compilation.success:
        raise RuntimeError("SDK benchmark operation failed")
    evidence: dict[str, object] = {
        "validation_diagnostics": [
            (item.severity, item.code, item.message, item.path)
            for item in sdk_validation.diagnostics
        ],
        "artifact_hashes": {item.artifact_id: item.sha256 for item in sdk_compilation.artifacts},
        "preview_fingerprint": sdk_compilation.fingerprint,
        "repository_fingerprint": sdk_repository.fingerprint(),
    }
    return timings, model.fingerprint, sdk_timings, evidence


def _run_phase2_iteration(
    case: CorpusCase, v13_case: CorpusCase
) -> tuple[dict[str, float], dict[str, object]]:
    timings: dict[str, float] = {}
    resolver = ProjectScopeResolver(explicit_scope=case.root)
    scope = resolver.resolve()
    parser = ADRParser()
    source_files = sorted((case.root / "adrs").rglob("*.yaml"))

    timings["v12_parsing"], parsed = _measure(
        lambda: [parser.parse_adr(path) for path in source_files]
    )
    generator = ArchitectureIndexGenerator(scope_resolver=resolver)
    timings["semantic_compilation"], bundle = _measure(lambda: generator.generate_from_scope(scope))

    def assertions() -> list[str]:
        return [
            derive_assertion_id(
                "binds_rule",
                "ADR-L-9801",
                "ste-rules:RULE-0001",
                "ADR-L-9801",
                f"/rule_bindings/{index}",
            )
            for index in range(1000)
        ]

    timings["assertion_derivation_1000"], assertion_ids = _measure(assertions)
    migrator = TopologyIdentityMigrator()
    timings["topology_migration_plan"], migration_plan = _measure(lambda: migrator.plan(scope))

    identity_migrator = IdentityV13Migrator()
    timings["v13_identity_preflight"], preflight = _measure(
        lambda: identity_migrator.preflight(scope)
    )
    timings["v13_identity_plan"], identity_plan = _measure(lambda: identity_migrator.plan(scope))

    v13_resolver = ProjectScopeResolver(explicit_scope=v13_case.root)
    v13_scope = v13_resolver.resolve()
    v13_compiler = ArchitectureCompiler(scope_resolver=v13_resolver)
    timings["v13_model2_compile"], v13_compilation = _measure(
        lambda: v13_compiler.compile(
            v13_scope,
            CompilerConfig(emit={"registries", "manifest"}, pinned_timestamp=FIXED_TIMESTAMP),
        )
    )
    if not v13_compilation.success:
        raise RuntimeError(
            "v1.3 model 2.0 benchmark compile failed: "
            + "; ".join(item.message for item in v13_compilation.diagnostics)
        )

    def load_v13_repository() -> ArchitectureRepository:
        repository = ArchitectureRepository(project_root=v13_case.root)
        repository.load()
        return repository

    timings["v13_model2_repository_load"], v13_repository = _measure(load_v13_repository)

    relationships = bundle.relationship_registry.relationships
    evidence = {
        "parsed_types": [type(item).__name__ for item in parsed],
        "entity_counts": {
            entity_type: sum(
                item.entity_type == entity_type for item in bundle.entity_registry.entities
            )
            for entity_type in (
                "boundary",
                "contract",
                "interface",
                "implementation_decision",
            )
        },
        "binding_relationships": sum(
            item.relationship_type in {"binds_substrate", "binds_rule", "expects_evidence"}
            for item in relationships
        ),
        "assertion_digest": hashlib.sha256("\n".join(assertion_ids).encode()).hexdigest(),
        "migration_changes": [
            (item.pointer, item.before, item.after) for item in migration_plan.changes
        ],
        "migration_diagnostics": [item.message for item in migration_plan.diagnostics],
        "v13_preflight_ok": preflight.ok,
        "v13_plan_ok": identity_plan.ok,
        "v13_plan_entry_count": len(identity_plan.identity_map.entries),
        "v13_compile_success": v13_compilation.success,
        "v13_repository_model_version": v13_repository.model_version,
        "v13_entity_count": len(v13_repository.get_entities()),
    }
    return timings, evidence


def _summarize(
    samples: list[dict[str, float]], stage_names: tuple[str, ...] = STAGE_NAMES
) -> dict[str, dict[str, object]]:
    summary: dict[str, dict[str, object]] = {}
    for stage in stage_names:
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
        phase2_case = _phase2_case(base)
        v13_case = _v13_model2_case(base)
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
        sdk_deterministic = True
        sdk_evidence: dict[str, object] = {}
        for case in cases:
            for index in range(warmups):
                _run_iteration(case, base / "outputs" / case.name / f"warmup-{index}")
            samples: list[dict[str, float]] = []
            sdk_samples: list[dict[str, float]] = []
            case_fingerprints: list[str] = []
            case_sdk_evidence: list[dict[str, object]] = []
            for index in range(repeats + 1):
                timings, fingerprint, sdk_timings, evidence = _run_iteration(
                    case, base / "outputs" / case.name / f"repeat-{index}"
                )
                samples.append(timings)
                sdk_samples.append(sdk_timings)
                case_fingerprints.append(fingerprint)
                case_sdk_evidence.append(evidence)
            deterministic = deterministic and len(set(case_fingerprints)) == 1
            sdk_deterministic = sdk_deterministic and all(
                item == case_sdk_evidence[0] for item in case_sdk_evidence
            )
            fingerprints[f"{case.name}:{case.adr_count}"] = case_fingerprints[0]
            sdk_evidence[f"{case.name}:{case.adr_count}"] = case_sdk_evidence[0]
            results.append(
                {
                    "corpus": case.name,
                    "adr_count": case.adr_count,
                    "identity": case.identity,
                    "stages": _summarize(samples),
                    "sdk_stages": _summarize(sdk_samples, SDK_STAGE_NAMES),
                }
            )
        for _ in range(warmups):
            _run_phase2_iteration(phase2_case, v13_case)
        phase2_samples: list[dict[str, float]] = []
        phase2_evidence_samples: list[dict[str, object]] = []
        for _ in range(repeats + 1):
            timings, evidence = _run_phase2_iteration(phase2_case, v13_case)
            phase2_samples.append(timings)
            phase2_evidence_samples.append(evidence)
        phase2_deterministic = all(
            item == phase2_evidence_samples[0] for item in phase2_evidence_samples
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
            "sdk_deterministic": sdk_deterministic,
            "sdk_evidence": sdk_evidence,
            "phase2_stages": _summarize(phase2_samples, PHASE2_STAGE_NAMES),
            "phase2_deterministic": phase2_deterministic,
            "phase2_evidence": phase2_evidence_samples[0],
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
        return 0 if payload["deterministic"] and payload["phase2_deterministic"] else 1
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"benchmark failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
