"""Physical-System ADR YAML generator."""

from pathlib import Path
from typing import Union

import yaml

from ..models import PhysicalSystemADR
from ..parser import ADRParser
from ..validators import ADRValidator


class _ADRYamlDumper(yaml.SafeDumper):
    """YAML dumper that prefers block literals for multiline strings."""

    def ignore_aliases(self, data):
        return True


def _represent_str(dumper: yaml.SafeDumper, value: str):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_ADRYamlDumper.add_representer(str, _represent_str)


class PhysicalSystemADRGenerator:
    """Generate YAML source files for Physical-System ADRs."""

    def __init__(self, parser: ADRParser = None, validator: ADRValidator = None):
        self.parser = parser or ADRParser()
        self.validator = validator or ADRValidator(parser=self.parser)

    def create_adr(self, adr_data: Union[dict, PhysicalSystemADR]) -> PhysicalSystemADR:
        """Create a validated Physical-System ADR model."""
        if isinstance(adr_data, PhysicalSystemADR):
            return adr_data
        return PhysicalSystemADR(**adr_data)

    def create_adr_from_file(self, input_path: Union[str, Path]) -> PhysicalSystemADR:
        """Load structured YAML input and create a Physical-System ADR model."""
        data = self.parser.parse_yaml(input_path)
        return self.create_adr(data)

    def render_yaml(self, adr_data: Union[dict, PhysicalSystemADR]) -> str:
        """Render a Physical-System ADR to YAML."""
        adr = self.create_adr(adr_data)
        adr_dict = adr.model_dump(mode="json", exclude_none=True, by_alias=True)
        return yaml.dump(
            adr_dict,
            Dumper=_ADRYamlDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        )

    def save_adr(self, adr_data: Union[dict, PhysicalSystemADR], output_path: Union[str, Path]) -> PhysicalSystemADR:
        """Save a Physical-System ADR YAML file."""
        adr = self.create_adr(adr_data)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.render_yaml(adr))

        return adr
