from pathlib import Path

from src.adr_kit.compiler.frontend import CachedADRParser


class StubParser:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def parse_yaml(self, file_path):
        self.calls.append(("parse_yaml", str(file_path)))
        return {"path": str(file_path), "call": len(self.calls), "items": []}


def test_cached_parser_avoids_duplicate_parses_for_unchanged_file(tmp_path):
    source = tmp_path / "sample.yaml"
    source.write_text("value: 1\n", encoding="utf-8")
    parser = StubParser()
    cached = CachedADRParser(parser=parser)

    first = cached.parse_yaml(source)
    second = cached.parse_yaml(source)

    assert len(parser.calls) == 1
    assert first == second
    assert first is not second


def test_cached_parser_invalidates_when_file_fingerprint_changes(tmp_path):
    source = tmp_path / "sample.yaml"
    source.write_text("value: 1\n", encoding="utf-8")
    parser = StubParser()
    cached = CachedADRParser(parser=parser)

    cached.parse_yaml(source)
    source.write_text("value: 22\n", encoding="utf-8")
    cached.parse_yaml(source)

    assert len(parser.calls) == 2
    assert parser.calls == [
        ("parse_yaml", str(source.resolve())),
        ("parse_yaml", str(source.resolve())),
    ]
