"""Exercise a selected wheel as an isolated external consumer using only stdlib."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBES = (
    "imports",
    "cli",
    "external-fixture",
    "schemas",
    "templates",
    "source-isolation",
    "sdk-consumer",
    "sdk-version-parity",
    "sdk-operations",
    "compiler-containment",
    "v1.2-schemas",
    "v1.2-compilation",
    "semantic-linkage-v1.5-v1.6",
    "promoted-entity-queries",
    "external-bindings",
    "topology-migration-entrypoint",
)
PROBE = """
from importlib import resources
from pathlib import Path
import adr_kit
from adr_kit.decorators import embodies, enforces, enforces_invariant, implements, implements_adr
from adr_kit.models import NormalizedArchitectureModel
from adr_kit.parser import ADRParser
from adr_kit.repository import ArchitectureRepository

package_path = Path(adr_kit.__file__).resolve()
assert 'site-packages' in package_path.as_posix().lower(), package_path
assert callable(implements) and callable(enforces) and callable(embodies)
assert resources.files('adr_kit.schema.v1_0').joinpath('adr-logical.schema.json').is_file()
assert resources.files('adr_kit.schema.v1_1').joinpath('architecture-index.schema.json').is_file()
assert resources.files('adr_kit.schema.v1_2').joinpath('adr-logical.schema.json').is_file()
assert resources.files('adr_kit.schema.v1_3').joinpath('adr-logical.schema.json').is_file()
assert resources.files('adr_kit.schema.v1_5').joinpath('implementation-attribution-evidence.schema.json').is_file()
assert resources.files('adr_kit.schema.v1_5').joinpath('semantic-attribution-vocabulary.json').is_file()
assert resources.files('adr_kit.schema.v1_6').joinpath('implementation-attribution-evidence.schema.json').is_file()
assert resources.files('adr_kit.schema.v1_6').joinpath('semantic-attribution-vocabulary.json').is_file()
assert resources.files('adr_kit.schema.v2_0').joinpath('normalized-entity.schema.json').is_file()
assert resources.files('adr_kit.templates').joinpath('adr-logical.md.jinja2').is_file()
assert resources.files('adr_kit.templates').joinpath('system-overview-adr-architecture-kit.yaml').is_file()
assert resources.files('adr_kit.templates').joinpath('system-overview-ste-runtime.yaml').is_file()
assert resources.files('adr_kit.templates').joinpath('system-overview.md.jinja2').is_file()
assert resources.files('adr_kit.promotion.rules').joinpath('roadmap_file_rules_v1.json').is_file()
assert resources.files('adr_kit.promotion.schemas').joinpath('promotion_contract_v0_1.json').is_file()
from adr_kit.migrators import TopologyIdentityMigrator
assert TopologyIdentityMigrator.__name__ == 'TopologyIdentityMigrator'
from adr_kit.migrators.identity_v13 import IdentityV13Migrator
assert IdentityV13Migrator.__name__ == 'IdentityV13Migrator'
from adr_kit.promotion.ste_contract import load_promotion_contract_schema
assert isinstance(load_promotion_contract_schema(), dict)
print(adr_kit.__version__)
"""
LINKAGE_PROBE = """
import os
from importlib import resources
from pathlib import Path
from adr_kit.api import (
    EmbodimentIntentLink,
    EmbodimentLinkageRequest,
    EmbodimentLinkageResult,
    LinkageOccurrence,
    LinkageProvenance,
    RejectedEmbodimentClaim,
    build_embodiment_linkage,
    capabilities,
)

project_root = Path(os.environ['ADR_LINKAGE_PROJECT_ROOT'])
evidence_path = Path(os.environ['ADR_LINKAGE_EVIDENCE_PATH'])
v15_evidence_path = Path(os.environ['ADR_LINKAGE_V15_EVIDENCE_PATH'])
manifest = capabilities()
assert 'build_embodiment_linkage' in manifest.operations
assert manifest.supported_evidence_attribution_versions == ('1.5', '1.6')
assert manifest.preferred_evidence_attribution_version == '1.6'
canonical = (project_root / 'schema/evidence-attribution/v1.6/implementation-attribution-evidence.schema.json').read_bytes()
packaged = resources.files('adr_kit.schema.v1_6').joinpath('implementation-attribution-evidence.schema.json').read_bytes()
assert canonical == packaged
canonical_vocabulary = (project_root / 'schema/evidence-attribution/v1.6/semantic-attribution-vocabulary.json').read_bytes()
packaged_vocabulary = resources.files('adr_kit.schema.v1_6').joinpath('semantic-attribution-vocabulary.json').read_bytes()
assert canonical_vocabulary == packaged_vocabulary
result = build_embodiment_linkage(EmbodimentLinkageRequest(project_root, evidence_path))
assert isinstance(result, EmbodimentLinkageResult)
assert result.success and len(result.links) == 1
assert isinstance(result.links[0], EmbodimentIntentLink)
assert isinstance(result.links[0].occurrences[0], LinkageOccurrence)
assert isinstance(result.links[0].occurrences[0].provenance, LinkageProvenance)
assert result.links[0].graph_admission_status == 'not_admitted'
v15_result = build_embodiment_linkage(EmbodimentLinkageRequest(project_root, v15_evidence_path))
assert isinstance(v15_result, EmbodimentLinkageResult)
assert v15_result.success and v15_result.evidence_schema_version == '1.5'
assert RejectedEmbodimentClaim is not None
"""
PHASE2_PROBE = """
import os
import yaml
from pathlib import Path
from adr_kit.api import (
    NormalizedArchitectureModelV2,
    ProviderRegistry,
    capabilities,
    open_provider_registry,
    open_repository,
)

root = Path(os.environ['ADR_PHASE2_FIXTURE'])
manifest = capabilities()
assert manifest.supported_adr_schema_versions == ('1.0', '1.1', '1.2', '1.3')
assert manifest.normalized_model_schema_version == '1.1'
assert manifest.supported_normalized_model_schema_versions == ('1.1', '2.0')
assert NormalizedArchitectureModelV2 is not None
assert ProviderRegistry is not None
assert callable(open_provider_registry)
repository = open_repository(root)
assert [item.id for item in repository.get_boundaries()] == ['BOUND-9801']
assert [item.id for item in repository.get_contracts()] == ['CONTRACT-9801']
assert [item.id for item in repository.get_interfaces()] == ['IFACE-9801']
assert [item.id for item in repository.get_implementation_decisions()] == ['IMPL-9801']
entities = yaml.safe_load((root / 'adrs/index/entity-registry.yaml').read_text(encoding='utf-8'))
relationships = yaml.safe_load((root / 'adrs/index/relationship-registry.yaml').read_text(encoding='utf-8'))
entity_ids = {item['id'] for item in entities['entities']}
assert 'ste-substrate:SUBSTRATE-0001' not in entity_ids
assert 'ste-rules:RULE-0001' not in entity_ids
verbs = {item['relationship_type'] for item in relationships['relationships']}
assert {'binds_substrate', 'binds_rule', 'expects_evidence'} <= verbs
assert all(item['assertion_id'].startswith('asrt-') for item in relationships['relationships'])
"""


def _venv_paths(environment: Path) -> tuple[Path, Path, Path]:
    if os.name == "nt":
        scripts = environment / "Scripts"
        return scripts / "python.exe", scripts / "pip.exe", scripts / "adr.exe"
    scripts = environment / "bin"
    return scripts / "python", scripts / "pip", scripts / "adr"


def _run(command: list[str], cwd: Path, environment: dict[str, str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def run_harness(wheel: Path, python: Path) -> None:
    wheel = wheel.resolve()
    if not wheel.is_file() or wheel.suffix != ".whl":
        raise ValueError(f"wheel not found: {wheel}")
    with tempfile.TemporaryDirectory(prefix="adr-kit-wheel-") as temporary:
        root = Path(temporary)
        environment_path = root / "venv"
        isolated_environment = os.environ.copy()
        isolated_environment.pop("PYTHONPATH", None)
        isolated_environment["PYTHONNOUSERSITE"] = "1"
        _run([str(python), "-m", "venv", str(environment_path)], root, isolated_environment)
        venv_python, pip, adr = _venv_paths(environment_path)

        _run([str(pip), "install", str(wheel)], root, isolated_environment)
        consumer = root / "consumer"
        fixture = consumer / "fixture"
        (fixture / "adrs" / "logical").mkdir(parents=True)
        shutil.copy2(ROOT / "PROJECT.yaml", fixture / "PROJECT.yaml")
        shutil.copy2(
            ROOT / "tests" / "fixtures" / "valid" / "logical-minimal.yaml",
            fixture / "adrs" / "logical" / "ADR-L-9999-minimal.yaml",
        )
        fixture_sources = (
            ("logical-bindings.yaml", "logical", "ADR-L-9801-bindings.yaml"),
            (
                "physical-component-semantics.yaml",
                "physical-component",
                "ADR-PC-9801-semantics.yaml",
            ),
            (
                "physical-system-topology.yaml",
                "physical-system",
                "ADR-PS-9801-topology.yaml",
            ),
        )
        for source_name, directory, destination_name in fixture_sources:
            destination = fixture / "adrs" / directory / destination_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "tests" / "fixtures" / "v1_2" / source_name, destination)
        consumer_script = consumer / "test_sdk_consumer.py"
        shutil.copy2(ROOT / "scripts" / "test_sdk_consumer.py", consumer_script)
        _run([str(venv_python), "-c", PROBE], consumer, isolated_environment)
        _run(
            [
                str(venv_python),
                str(consumer_script),
                "--project-root",
                str(fixture),
                "--version-source",
                "metadata",
            ],
            consumer,
            isolated_environment,
        )
        _run([str(adr), "--version"], consumer, isolated_environment)
        _run([str(adr), "validate", "--scope", str(fixture)], consumer, isolated_environment)
        _run(
            [
                str(adr),
                "compile",
                "--scope",
                str(fixture),
                "--emit",
                "registries,manifest",
                "--timestamp",
                "2026-01-01T00:00:00Z",
            ],
            consumer,
            isolated_environment,
        )
        isolated_environment["ADR_PHASE2_FIXTURE"] = str(fixture)
        _run([str(venv_python), "-c", PHASE2_PROBE], consumer, isolated_environment)
        linkage_evidence = consumer / "external-linkage-evidence.yaml"
        linkage_evidence.write_text(
            json.dumps(
                {
                    "schema_version": "1.6",
                    "type": "implementation_attribution_evidence",
                    "records": [
                        {
                            "implementation_entity_id": "wheel.consumer:run",
                            "implementation_entity_type": "function",
                            "provenance": {
                                "source_file": "consumer.py",
                                "extractor": "wheel-smoke",
                                "source_pointer": "wheel.consumer:run",
                            },
                            "claims": [
                                {
                                    "relationship": "implements",
                                    "target_entity_id": "019ffdba-3c42-7c4a-a737-f6751a265d60",
                                    "confidence": "declared",
                                }
                            ],
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        linkage_evidence_v15 = consumer / "external-linkage-evidence-v15.yaml"
        linkage_evidence_v15.write_text(
            json.dumps(
                {
                    "schema_version": "1.5",
                    "type": "implementation_attribution_evidence",
                    "records": [
                        {
                            "implementation_entity_id": "wheel.consumer:v15",
                            "implementation_entity_type": "function",
                            "provenance": {
                                "source_file": "consumer-v15.py",
                                "extractor": "wheel-smoke",
                            },
                            "claims": [
                                {
                                    "relationship": "implements",
                                    "target_entity_id": "019ffdba-3c42-7c4a-a737-f6751a265d60",
                                    "confidence": "inferred",
                                }
                            ],
                        }
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        isolated_environment["ADR_LINKAGE_PROJECT_ROOT"] = str(ROOT)
        isolated_environment["ADR_LINKAGE_EVIDENCE_PATH"] = str(linkage_evidence)
        isolated_environment["ADR_LINKAGE_V15_EVIDENCE_PATH"] = str(linkage_evidence_v15)
        _run([str(venv_python), "-c", LINKAGE_PROBE], consumer, isolated_environment)
        _run([str(adr), "attribution", "linkage-report", "--help"], consumer, isolated_environment)
        _run([str(adr), "migrate-topology-ids", "--help"], consumer, isolated_environment)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument("--describe", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.describe:
        print("\n".join(PROBES))
        return 0
    if arguments.wheel is None:
        parser.error("--wheel is required unless --describe is used")
    try:
        run_harness(arguments.wheel, arguments.python)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"installed-wheel harness failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
