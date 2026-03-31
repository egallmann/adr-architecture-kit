"""Shared YAML rendering support for ADR source generators."""

import yaml


class ADRYamlDumper(yaml.SafeDumper):
    """YAML dumper that prefers block literals for multiline strings."""

    def ignore_aliases(self, data):
        return True


def represent_str(dumper: yaml.SafeDumper, value: str):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


ADRYamlDumper.add_representer(str, represent_str)
