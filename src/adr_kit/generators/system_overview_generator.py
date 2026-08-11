"""Generator for the AI-first repository system overview."""

from __future__ import annotations

import json
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader

from ..decorators import enforces_invariant, implements_adr
from ..integrity import (
    GENERATED_MARKER,
    HASH_ALGORITHM,
    INTEGRITY_SCHEMA_VERSION,
    ArtifactKind,
    GeneratorIdentity,
    HashInput,
    build_markdown_header,
    compute_rendered_hash,
    compute_source_hash,
)
from .system_overview_model import (
    AuthorityAnchor,
    LinkCategory,
    OverviewLink,
    ProfileOverview,
    ProjectOverview,
    ProviderOverview,
    ResponsibilityBoundary,
    SystemOverviewModel,
    SystemOverviewSourceError,
    TaskRoute,
)

CapabilitiesProvider = Callable[[], Any]

KIT_PROFILE_NAME = "system-overview-adr-architecture-kit.yaml"
RUNTIME_PROFILE_NAME = "system-overview-ste-runtime.yaml"
TEMPLATE_NAME = "system-overview.md.jinja2"


def _default_capabilities() -> Any:
    from ..api import capabilities

    return capabilities()


@implements_adr("ADR-L-0007")
@enforces_invariant("INV-0099", "INV-0100", "INV-0101", "INV-0102")
class SystemOverviewGenerator:
    """Generate the repo-level AI-first SYSTEM-OVERVIEW.md artifact."""

    generator_identity = GeneratorIdentity("adr-system-overview", 2)

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        template_dir: Path | None = None,
        capabilities_provider: CapabilitiesProvider | None = None,
    ):
        if template_dir is None:
            template_dir = Path(__file__).parent.parent / "templates"

        self.template_dir = Path(template_dir)
        self.repo_root = Path(repo_root) if repo_root is not None else Path.cwd()
        self.capabilities_provider = capabilities_provider or _default_capabilities
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._model_cache: SystemOverviewModel | None = None
        self._profile_path_cache: Path | None = None

    def _project_metadata(self) -> dict[str, Any]:
        path = self.repo_root / "PROJECT.yaml"
        if not path.is_file():
            return {}
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
            return loaded if isinstance(loaded, dict) else {}
        except (OSError, yaml.YAMLError):
            return {}

    def _project_name_and_description(self) -> tuple[str, str]:
        meta = self._project_metadata()
        project_raw = meta.get("project")
        project_block = project_raw if isinstance(project_raw, dict) else {}
        name = str(project_block.get("name") or "adr-architecture-kit")
        description = str(project_block.get("description") or "")
        return name, description

    def _load_profile_yaml(self, profile_name: str) -> tuple[dict[str, Any], Path]:
        path = self.template_dir / profile_name
        if not path.is_file():
            raise SystemOverviewSourceError(f"Missing overview profile: {profile_name}")
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise SystemOverviewSourceError(
                f"Invalid overview profile YAML: {profile_name}"
            ) from exc
        if not isinstance(data, dict):
            raise SystemOverviewSourceError(f"Overview profile must be a mapping: {profile_name}")
        return data, path

    def _manifest_records(self) -> dict[str, dict[str, Any]]:
        manifest = self.repo_root / "adrs" / "manifest.yaml"
        if not manifest.is_file():
            return {}
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return {}
        records: dict[str, dict[str, Any]] = {}
        for adr in data.get("adrs", []):
            if isinstance(adr, dict) and isinstance(adr.get("id"), str):
                records[adr["id"]] = adr
        return records

    def _resolve_authority_anchors(
        self, anchor_ids: list[str], records: dict[str, dict[str, Any]]
    ) -> tuple[AuthorityAnchor, ...]:
        anchors: list[AuthorityAnchor] = []
        for adr_id in anchor_ids:
            record = records.get(adr_id)
            if record is None:
                raise SystemOverviewSourceError(
                    f"Authority anchor {adr_id} is missing from adrs/manifest.yaml"
                )
            status = str(record.get("status") or "")
            if status != "accepted":
                raise SystemOverviewSourceError(
                    f"Authority anchor {adr_id} must be accepted; found status={status!r}"
                )
            path = str(record.get("file_path") or "")
            if not path:
                raise SystemOverviewSourceError(f"Authority anchor {adr_id} is missing file_path")
            anchors.append(
                AuthorityAnchor(
                    id=adr_id,
                    title=str(record.get("title") or adr_id),
                    status=status,
                    path=path,
                )
            )
        return tuple(anchors)

    def _parse_boundaries(self, raw: list[Any]) -> tuple[ResponsibilityBoundary, ...]:
        items: list[ResponsibilityBoundary] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            subject = str(entry.get("subject") or "").strip()
            detail = str(entry.get("detail") or "").strip()
            if not subject or not detail:
                continue
            link = entry.get("link")
            items.append(
                ResponsibilityBoundary(
                    subject=subject,
                    detail=detail,
                    link=str(link) if link else None,
                )
            )
        return tuple(items)

    def _parse_task_routes(self, raw: list[Any]) -> tuple[TaskRoute, ...]:
        items: list[TaskRoute] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            task = str(entry.get("task") or "").strip()
            entry_point = str(entry.get("entry") or "").strip()
            surface = str(entry.get("surface") or "").strip()
            if not task or not entry_point:
                continue
            items.append(TaskRoute(task=task, entry=entry_point, surface=surface or "other"))
        return tuple(items)

    def _parse_links(self, raw: list[Any]) -> tuple[OverviewLink, ...]:
        items: list[OverviewLink] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            label = str(entry.get("label") or "").strip()
            target = str(entry.get("target") or "").strip()
            if not label or not target:
                continue
            category_raw = entry.get("category") or "related"
            category: LinkCategory = (
                "authority_anchor" if category_raw == "authority_anchor" else "related"
            )
            items.append(OverviewLink(label=label, target=target, category=category))
        return tuple(items)

    def _string_tuple(self, raw: Any) -> tuple[str, ...]:
        if not isinstance(raw, list):
            return ()
        return tuple(str(item).strip() for item in raw if str(item).strip())

    def _packaged_adr_schema_versions(self) -> set[str]:
        versions: set[str] = set()
        schema_root = Path(__file__).resolve().parent.parent / "schema"
        if schema_root.is_dir():
            for child in schema_root.iterdir():
                if child.is_dir() and child.name.startswith("v") and "_" in child.name:
                    # packaged module style v1_0
                    dotted = child.name[1:].replace("_", ".")
                    versions.add(dotted)
                elif child.is_dir() and child.name.startswith("v") and "." in child.name:
                    versions.add(child.name[1:])
        # Also discover importable package namespaces used by the wheel.
        try:
            schema_pkg = resources.files("adr_kit.schema")
        except (ModuleNotFoundError, TypeError, AttributeError):
            return versions
        for entry in schema_pkg.iterdir():
            name = getattr(entry, "name", "")
            if name.startswith("v") and "_" in name and entry.is_dir():
                versions.add(name[1:].replace("_", "."))
        return versions

    def _cli_surface_command_names(self) -> set[str]:
        candidates = [
            self.repo_root / "contracts" / "compatibility" / "cli-surface.json",
            Path(__file__).resolve().parents[3]
            / "contracts"
            / "compatibility"
            / "cli-surface.json",
        ]
        for path in candidates:
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            commands = data.get("commands")
            if isinstance(commands, dict):
                return {str(name) for name in commands}
        raise SystemOverviewSourceError(
            "Unable to load CLI surface snapshot for overview consistency"
        )

    def _assert_kit_provider_consistency(self, caps: Any) -> None:
        from .. import api as api_module
        from ..models.normalized_architecture_model import NormalizedArchitectureModel

        model_declared = NormalizedArchitectureModel.model_fields["schema_version"].default
        if str(caps.normalized_model_schema_version) != str(model_declared):
            raise SystemOverviewSourceError(
                "capabilities().normalized_model_schema_version disagrees with "
                "NormalizedArchitectureModel schema_version declaration"
            )

        packaged = self._packaged_adr_schema_versions()
        advertised = set(caps.supported_adr_schema_versions)
        # ADR schema packages use v1_0..v1_3; ignore normalized v2_0 for this comparison.
        packaged_adr = {version for version in packaged if version.startswith("1.")}
        if not advertised.issubset(packaged_adr):
            missing = sorted(advertised - packaged_adr)
            raise SystemOverviewSourceError(
                "capabilities().supported_adr_schema_versions include unpackaged versions: "
                + ", ".join(missing)
            )

        exported = set(api_module.__all__)
        for operation in caps.operations:
            if operation not in exported:
                raise SystemOverviewSourceError(
                    f"capabilities() advertises operation {operation!r} missing from adr_kit.api.__all__"
                )

    def _build_provider_overview(self, caps: Any) -> ProviderOverview:
        self._assert_kit_provider_consistency(caps)
        return ProviderOverview(
            primary_module="adr_kit.api",
            package_version=caps.package_version,
            api_contract_version=caps.api_contract_version,
            operations=tuple(caps.operations),
            validation_modes=tuple(caps.validation_modes),
            artifact_groups=tuple(caps.artifact_groups),
            supported_adr_schema_versions=tuple(caps.supported_adr_schema_versions),
            stable_adr_schema_versions=tuple(caps.stable_adr_schema_versions),
            provisional_adr_schema_versions=tuple(caps.provisional_adr_schema_versions),
            normalized_model_schema_version=str(caps.normalized_model_schema_version),
            supported_normalized_model_schema_versions=tuple(
                caps.supported_normalized_model_schema_versions
            ),
        )

    def _assert_required_cli_commands(self, required: tuple[str, ...]) -> None:
        available = self._cli_surface_command_names()
        missing = [name for name in required if name not in available]
        if missing:
            raise SystemOverviewSourceError(
                "Overview required CLI commands missing from cli-surface snapshot: "
                + ", ".join(missing)
            )

    def _build_kit_model(self, project: ProjectOverview) -> tuple[SystemOverviewModel, Path]:
        raw, profile_path = self._load_profile_yaml(KIT_PROFILE_NAME)
        records = self._manifest_records()
        anchors = self._resolve_authority_anchors(
            [str(item) for item in raw.get("authority_anchor_ids", [])],
            records,
        )
        required_cli = self._string_tuple(raw.get("required_cli_commands"))
        self._assert_required_cli_commands(required_cli)
        caps = self.capabilities_provider()
        provider = self._build_provider_overview(caps)
        profile = ProfileOverview(
            profile_kind="adr-architecture-kit",
            purpose=str(raw.get("purpose") or "").strip(),
            system_identity=str(raw.get("system_identity") or "").strip(),
            purpose_bullets=self._string_tuple(raw.get("purpose_bullets")),
            purpose_footer=str(raw.get("purpose_footer") or "").strip(),
            one_line_orientation=str(raw.get("one_line_orientation") or "").strip(),
        )
        model = SystemOverviewModel(
            project=project,
            profile=profile,
            responsibility_boundaries=self._parse_boundaries(
                list(raw.get("responsibility_boundaries") or [])
            ),
            authority_anchors=anchors,
            related_links=(),
            task_routes=self._parse_task_routes(list(raw.get("task_routes") or [])),
            safe_extension_rules=self._string_tuple(raw.get("safe_extension_rules")),
            category_errors=self._string_tuple(raw.get("category_errors")),
            validation_gates=self._string_tuple(raw.get("validation_gates")),
            read_next=self._parse_links(list(raw.get("read_next") or [])),
            provider=provider,
            required_cli_commands=required_cli,
            source_basis_labels=(
                "PROJECT.yaml",
                "adrs/manifest.yaml (selected anchors)",
                "adr_kit.api.capabilities()",
                "contracts/compatibility/cli-surface.json",
                KIT_PROFILE_NAME,
            ),
        )
        return model, profile_path

    def _workspace_highlights_from_profile(
        self, raw: dict[str, Any], records: dict[str, dict[str, Any]]
    ) -> tuple[str, ...]:
        lines: list[str] = []
        for adr_id in raw.get("workspace_highlight_ids") or []:
            record = records.get(str(adr_id))
            if record is None:
                continue
            title = record.get("title") or adr_id
            lines.append(f"**{adr_id}**: {title}")
        lines.extend(self._string_tuple(raw.get("workspace_highlight_extras")))
        return tuple(lines)

    def _build_runtime_model(self, project: ProjectOverview) -> tuple[SystemOverviewModel, Path]:
        raw, profile_path = self._load_profile_yaml(RUNTIME_PROFILE_NAME)
        records = self._manifest_records()
        profile = ProfileOverview(
            profile_kind="ste-runtime",
            purpose=str(raw.get("purpose") or "").strip(),
            system_identity=str(raw.get("system_identity") or "").strip(),
            purpose_bullets=self._string_tuple(raw.get("purpose_bullets")),
            purpose_footer=str(raw.get("purpose_footer") or "").strip(),
            one_line_orientation=str(raw.get("one_line_orientation") or "").strip(),
        )
        model = SystemOverviewModel(
            project=project,
            profile=profile,
            responsibility_boundaries=self._parse_boundaries(
                list(raw.get("responsibility_boundaries") or [])
            ),
            task_routes=self._parse_task_routes(list(raw.get("task_routes") or [])),
            safe_extension_rules=self._string_tuple(raw.get("safe_extension_rules")),
            category_errors=self._string_tuple(raw.get("category_errors")),
            validation_gates=self._string_tuple(raw.get("validation_gates")),
            read_next=self._parse_links(list(raw.get("read_next") or [])),
            workspace_highlights=self._workspace_highlights_from_profile(raw, records),
            source_basis_labels=(
                "PROJECT.yaml",
                "adrs/manifest.yaml (selected highlights)",
                RUNTIME_PROFILE_NAME,
            ),
        )
        return model, profile_path

    def _build_legacy_generic_model(
        self, project: ProjectOverview
    ) -> tuple[SystemOverviewModel, Path | None]:
        """Case B compatibility path: emit minimal orientation without kit provider IA."""

        description = project.description or (
            f"`{project.name}` is an ADR-managed repository. "
            "This generated overview is a compatibility orientation surface only."
        )
        profile = ProfileOverview(
            profile_kind="legacy-generic",
            purpose=(
                "Compatibility-only SYSTEM-OVERVIEW for repositories without a dedicated "
                "authored overview profile. Not normative architecture authority."
            ),
            system_identity=description,
            purpose_bullets=(
                "Accepted ADRs under adrs/ are canonical project intent for their declared scope",
                "Regenerate this file with `adr generate-system-overview`; do not hand-edit it",
                "Do not treat this overview as ADR Kit provider documentation",
            ),
            purpose_footer=(
                "Rich generic consumer overview assembly is deferred; this path preserves "
                "legacy generation success without inheriting ADR Kit provider semantics."
            ),
            one_line_orientation=(
                f"`{project.name}` uses ADR tooling for authored architecture artifacts; "
                "this overview is compatibility orientation, not provider documentation."
            ),
        )
        model = SystemOverviewModel(
            project=project,
            profile=profile,
            responsibility_boundaries=(
                ResponsibilityBoundary(
                    subject="Project ADR authority",
                    detail="Accepted ADRs under adrs/ are canonical project intent for their declared scope.",
                    link="adrs/",
                ),
                ResponsibilityBoundary(
                    subject="Derived outputs",
                    detail="Generated docs and registries are derived unless a governing contract says otherwise.",
                ),
            ),
            task_routes=(
                TaskRoute(task="Validate ADRs", entry="adr validate", surface="cli"),
                TaskRoute(
                    task="Regenerate this overview",
                    entry="adr generate-system-overview",
                    surface="cli",
                ),
                TaskRoute(
                    task="Validate this overview",
                    entry="adr validate-system-overview",
                    surface="cli",
                ),
            ),
            safe_extension_rules=(
                "Do not hand-edit generated SYSTEM-OVERVIEW.md.",
                "Do not treat this overview as ADR Kit provider documentation.",
                "Prefer accepted ADRs and PROJECT.yaml over this orientation surface.",
            ),
            category_errors=(
                "Hand-editing generated SYSTEM-OVERVIEW.md",
                "Treating this compatibility overview as ADR Kit provider documentation",
                "Treating generated registries as canonical ADR authority",
            ),
            validation_gates=(
                "adr validate",
                "adr generate-system-overview",
                "adr validate-system-overview",
            ),
            read_next=(
                OverviewLink(label="PROJECT.yaml", target="PROJECT.yaml"),
                OverviewLink(label="ADRs", target="adrs/"),
            ),
            source_basis_labels=("PROJECT.yaml", "legacy-generic compatibility path"),
        )
        return model, None

    def build_model(self) -> SystemOverviewModel:
        """Assemble the complete semantic overview model for the current repository."""

        name, description = self._project_name_and_description()
        project = ProjectOverview(name=name, description=description)
        profile_path: Path | None
        if name == "adr-architecture-kit":
            model, profile_path = self._build_kit_model(project)
        elif name == "ste-runtime":
            model, profile_path = self._build_runtime_model(project)
        else:
            model, profile_path = self._build_legacy_generic_model(project)
        self._model_cache = model
        self._profile_path_cache = profile_path
        return model

    def build_context(self) -> dict[str, object]:
        """Build structured context for the generated overview."""

        return self.build_model().to_template_context()

    def render(self) -> str:
        """Render the system overview markdown."""

        template = self.env.get_template(TEMPLATE_NAME)
        return template.render(**self.build_context())

    def declared_source_inputs(self, output_path: Path) -> list[Path | HashInput]:
        """Return the explicit v2 semantic + projection-rule inputs for SYSTEM-OVERVIEW."""

        model = self._model_cache or self.build_model()
        inputs: list[Path | HashInput] = [
            HashInput(
                "__semantic__/system-overview-model.json",
                model.to_canonical_json(),
            ),
            HashInput(
                "__projection__/src/adr_kit/generators/system_overview_generator.py",
                Path(__file__).resolve().read_bytes(),
            ),
            HashInput(
                "__projection__/src/adr_kit/generators/system_overview_model.py",
                (Path(__file__).resolve().parent / "system_overview_model.py").read_bytes(),
            ),
            HashInput(
                f"__projection__/src/adr_kit/templates/{TEMPLATE_NAME}",
                (self.template_dir / TEMPLATE_NAME).resolve().read_bytes(),
            ),
        ]
        if self._profile_path_cache is not None and self._profile_path_cache.is_file():
            relative = self._profile_path_cache.name
            inputs.append(
                HashInput(
                    f"__projection__/src/adr_kit/templates/{relative}",
                    self._profile_path_cache.read_bytes(),
                )
            )
        # Include selected semantic source files that feed the model when present.
        project_yaml = self.repo_root / "PROJECT.yaml"
        if project_yaml.is_file():
            inputs.append(HashInput("PROJECT.yaml", project_yaml.read_bytes()))
        if model.authority_anchors or model.workspace_highlights:
            manifest_yaml = self.repo_root / "adrs" / "manifest.yaml"
            if manifest_yaml.is_file():
                # Only selected records affect semantics; hash a deterministic selection digest.
                records = self._manifest_records()
                selected_ids = [anchor.id for anchor in model.authority_anchors]
                if model.profile.profile_kind == "ste-runtime":
                    selected_ids.extend(["ADR-L-0009", "ADR-L-0010"])
                selected = {
                    adr_id: {
                        "id": records[adr_id].get("id"),
                        "title": records[adr_id].get("title"),
                        "status": records[adr_id].get("status"),
                        "file_path": records[adr_id].get("file_path"),
                    }
                    for adr_id in selected_ids
                    if adr_id in records
                }
                inputs.append(
                    HashInput(
                        "adrs/manifest.yaml#selected",
                        json.dumps(selected, sort_keys=True, separators=(",", ":")).encode("utf-8"),
                    )
                )
        return inputs

    def render_with_inputs(self, output_path: Path) -> tuple[str, list[Path | HashInput]]:
        """Render SYSTEM-OVERVIEW body with explicit source basis."""

        body = self.render()
        return body, self.declared_source_inputs(output_path)

    def build_integrity_header(
        self, output_path: Path, body: str, source_inputs: list[Path | HashInput]
    ) -> str:
        """Build integrity header for SYSTEM-OVERVIEW."""

        header_fields = {
            "integrity_schema_version": str(INTEGRITY_SCHEMA_VERSION),
            "generated": GENERATED_MARKER,
            "artifact_kind": ArtifactKind.SYSTEM_OVERVIEW.value,
            "generator_id": self.generator_identity.generator_id,
            "generator_version": str(self.generator_identity.generator_version),
            "hash_algorithm": HASH_ALGORITHM,
            "source_hash": compute_source_hash(
                self.repo_root, source_inputs, self.generator_identity
            ),
            "rendered_hash": compute_rendered_hash(body),
        }
        return build_markdown_header(header_fields)

    def save(self, output_path: Path) -> Path:
        """Render and save the system overview."""

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        body, source_inputs = self.render_with_inputs(output_path)
        output_path.write_text(
            self.build_integrity_header(output_path, body, source_inputs) + body,
            encoding="utf-8",
            newline="\n",
        )
        return output_path
