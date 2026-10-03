"""Gap impact must survive human projection for typed and open gap models.

Authoring 1.3 logical gaps are typed ``Gap`` values whose impact is an enum
with ``.value``. Authoring 1.5 and 1.6 leave ``gaps`` structurally open, so a
logical gap is a plain mapping and ``impact`` is a scalar. Physical-system
1.6 stores the same open list as untyped mappings. Physical-component 1.6
keeps authored gaps as extra mappings. The production templates selected for
those versions must render the authored impact without tightening either
authoring contract or mutating canonical YAML.
"""

from enum import Enum
from pathlib import Path

from adr_kit.compiler.backend.markdown_rendering import render_adr_markdown, template_path_for_adr
from adr_kit.integrity import compute_rendered_hash
from adr_kit.models.common import Gap, ImpactLevel
from adr_kit.models.v1_6.logical_adr import LogicalADRv16
from adr_kit.models.v1_6.physical_adr import PhysicalComponentADRv16
from adr_kit.models.v1_6.physical_system_adr import PhysicalSystemADRv16
from adr_kit.parser import ADRParser

_GAP = """
gaps:
  - id: GAP-0001
    question: Example unresolved question
    impact: low
    blocking: false
"""

_LOGICAL_V13 = """
schema_version: "1.3"
adr_type: logical
id: "019109a0-b1c2-7def-8a00-112233445566"
alias_id: ADR-L-9990
alias_name: minimal-v13-logical
title: "Minimal Valid v1.3 Logical ADR"
status: proposed
created_date: "2026-08-10"
authors: ["test.author"]
domains: ["test"]
context: |
  This is a minimal valid v1.3 logical ADR with UUIDv7 identity.
decisions:
  - id: "019109a0-b1c2-7def-8a00-aabbccddeef0"
    alias_id: DEC-9990
    alias_name: test-decision-one
    summary: "Test decision with UUID identity"
    rationale: |
      This is a test decision rationale for v1.3 identity.
""" + _GAP

_LOGICAL_V16 = """
schema_version: "1.6"
adr_type: logical
id: "019109a0-b1c2-7def-8a00-112233445566"
alias_id: ADR-L-9991
alias_name: minimal-v16-logical
title: "Minimal authoring 1.6 logical ADR"
status: proposed
created_date: "2026-08-10"
authors: ["test.author"]
domains: ["test"]
context: |
  Open authoring 1.6 gap projected through the generic logical template.
decisions:
  - id: "019109a0-b1c2-7def-8a00-aabbccddeef0"
    alias_id: DEC-9991
    alias_name: test-decision-one
    summary: "Test decision with UUID identity"
    rationale: |
      This is a test decision rationale for authoring 1.6.
""" + _GAP

_PHYSICAL_SYSTEM_V16 = """
schema_version: "1.6"
adr_type: physical-system
id: "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
alias_id: ADR-PS-9991
alias_name: test-physical-system
title: "Authoring 1.6 physical-system gap projection"
status: accepted
created_date: "2026-08-10"
authors: ["test.author"]
domains: ["test-system"]
implements_logical: ["019109a0-b1c2-7def-8a00-112233445566"]
technologies: ["python"]
context: |
  Physical-system ADR with an open gap mapping.
technology_stack:
  - category: language
    name: "Python"
    version: "3.14"
    rationale: "Standard runtime for architecture tooling"
system:
  id: "019109a0-d5e6-7f78-8c00-aabb00112233"
  alias_id: SYS-0001
  alias_name: test-system-boundary
""" + _GAP

_PHYSICAL_COMPONENT_V16 = """
schema_version: "1.6"
adr_type: physical-component
id: "019109a0-b1c2-7def-8a00-000000000004"
alias_id: ADR-PC-9991
alias_name: gap-projection-component
title: "Authoring 1.6 physical-component gap projection"
status: accepted
created_date: "2026-08-10"
authors: ["test.author"]
domains: ["projection"]
implements_system:
  - "019109a0-c3d4-7e56-8b00-ffeeddccbbaa"
implements_logical:
  - "019109a0-b1c2-7def-8a00-112233445566"
technologies:
  - python
context: |
  Physical-component ADR with an open gap mapping.
technology_stack:
  - category: language
    name: Python
    version: "3.14"
    rationale: Fixture language choice.
component_specifications:
  - id: "019109a0-b1c2-7def-8a00-000000000010"
    alias_id: COMP-9991
    alias_name: alpha-component
    name: Alpha Component
    type: service
    responsibilities: |
      Own projection of authored gaps.
    generation_context:
      purpose: Expose the authored component.
      key_responsibilities:
        - Keep the authored gap available to projection.
""" + _GAP


def _write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body.lstrip(), encoding="utf-8")
    return path


def _project(path: Path) -> tuple[object, str]:
    original = path.read_bytes()
    adr = ADRParser().parse_adr(path)
    rendered = render_adr_markdown(adr)
    assert path.read_bytes() == original
    again = render_adr_markdown(adr)
    assert again == rendered
    assert compute_rendered_hash(again) == compute_rendered_hash(rendered)
    return adr, rendered


def test_authoring_13_logical_gap_impact_renders(tmp_path: Path) -> None:
    adr, rendered = _project(_write(tmp_path, "logical-v13.yaml", _LOGICAL_V13))

    assert template_path_for_adr(adr).name == "adr-logical.md.jinja2"
    gap = adr.gaps[0]
    assert isinstance(gap, Gap)
    assert isinstance(gap.impact, ImpactLevel)
    assert isinstance(gap.impact, Enum)
    assert gap.impact.value == "low"
    assert "**Impact:** low<br>" in rendered
    assert "### GAP-0001: Example unresolved question" in rendered
    assert "**Blocking:** No" in rendered


def test_authoring_16_logical_gap_impact_renders(tmp_path: Path) -> None:
    adr, rendered = _project(_write(tmp_path, "logical-v16.yaml", _LOGICAL_V16))

    assert isinstance(adr, LogicalADRv16)
    assert template_path_for_adr(adr).name == "adr-logical.md.jinja2"
    gap = adr.gaps[0]
    assert isinstance(gap, dict)
    assert gap["impact"] == "low"
    assert not isinstance(gap["impact"], Enum)
    assert "**Impact:** low<br>" in rendered
    assert "### GAP-0001: Example unresolved question" in rendered
    assert "**Blocking:** No" in rendered


def test_authoring_16_physical_gap_impact_renders(tmp_path: Path) -> None:
    system, system_rendered = _project(
        _write(tmp_path, "physical-system-v16.yaml", _PHYSICAL_SYSTEM_V16)
    )
    component, component_rendered = _project(
        _write(tmp_path, "physical-component-v16.yaml", _PHYSICAL_COMPONENT_V16)
    )

    assert isinstance(system, PhysicalSystemADRv16)
    assert isinstance(component, PhysicalComponentADRv16)
    assert template_path_for_adr(system).name == "adr-physical.md.jinja2"
    assert template_path_for_adr(component).name == "adr-physical.md.jinja2"
    assert isinstance(system.gaps[0], dict)
    assert system.gaps[0]["impact"] == "low"
    component_gaps = component.model_extra["gaps"] if component.model_extra else None
    assert isinstance(component_gaps, list)
    assert component_gaps[0]["impact"] == "low"
    for rendered in (system_rendered, component_rendered):
        assert "**Impact:** low<br>" in rendered
        assert "### GAP-0001: Example unresolved question" in rendered
        assert "**Blocking:** No" in rendered
