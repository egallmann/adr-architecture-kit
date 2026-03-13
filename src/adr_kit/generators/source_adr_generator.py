"""Generic YAML source generator for ADR artifacts."""

from pathlib import Path
from typing import Generic, TypeVar, Union

import yaml

from ..parser import ADRParser
from ..validators import ADRValidator
from ._yaml_support import ADRYamlDumper

T = TypeVar("T")


class SourceADRGenerator(Generic[T]):
    """Generate validated YAML source files for ADR models."""

    model_class = None
    schema_name = None

    def __init__(self, parser: ADRParser = None, validator: ADRValidator = None):
        self.parser = parser or ADRParser()
        self.validator = validator or ADRValidator(parser=self.parser)
        if self.model_class is None or self.schema_name is None:
            raise ValueError("model_class and schema_name must be defined by subclasses")

    def create_adr(self, adr_data: Union[dict, T], mode: str = "complete") -> Union[dict, T]:
        """Create or validate ADR data according to generation mode."""
        if mode == "complete":
            if isinstance(adr_data, self.model_class):
                return adr_data
            return self.model_class(**adr_data)
        if mode == "structural":
            if isinstance(adr_data, self.model_class):
                adr_dict = adr_data.model_dump(mode="json", exclude_none=True, by_alias=True)
            else:
                adr_dict = adr_data
            self.parser.validate_against_schema(adr_dict, self.schema_name, mode="structural")
            return adr_dict
        raise ValueError(f"Unknown generation mode: {mode}")

    def create_adr_from_file(self, input_path: Union[str, Path], mode: str = "complete") -> Union[dict, T]:
        """Load structured YAML input and create an ADR model."""
        data = self.parser.parse_yaml(input_path)
        return self.create_adr(data, mode=mode)

    def _prune_empty(self, value):
        """Remove empty collections so generated ADR YAML stays schema-compatible."""
        if isinstance(value, dict):
            pruned = {
                key: self._prune_empty(item)
                for key, item in value.items()
            }
            return {
                key: item
                for key, item in pruned.items()
                if item is not None and item != [] and item != {}
            }
        if isinstance(value, list):
            return [item for item in (self._prune_empty(item) for item in value) if item is not None and item != {}]
        return value

    def render_yaml(
        self,
        adr_data: Union[dict, T],
        mode: str = "complete",
        preserve_empty_sections: bool = False,
    ) -> str:
        """Render an ADR model to YAML."""
        adr = self.create_adr(adr_data, mode=mode)
        if isinstance(adr, self.model_class):
            adr_dict = adr.model_dump(mode="json", exclude_none=True, by_alias=True)
        else:
            adr_dict = adr
        if not preserve_empty_sections:
            adr_dict = self._prune_empty(adr_dict)
        return yaml.dump(
            adr_dict,
            Dumper=ADRYamlDumper,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=1000,
        )

    def save_adr(
        self,
        adr_data: Union[dict, T],
        output_path: Union[str, Path],
        mode: str = "complete",
        preserve_empty_sections: bool = False,
    ) -> Union[dict, T]:
        """Save an ADR YAML file."""
        adr = self.create_adr(adr_data, mode=mode)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.render_yaml(adr, mode=mode, preserve_empty_sections=preserve_empty_sections))

        return adr
