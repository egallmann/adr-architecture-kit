from pathlib import Path

from src.adr_kit.compiler import DiagnosticLevel, DiagnosticLog


def test_diagnostic_log_orders_by_level_path_source_and_code():
    diagnostics = DiagnosticLog()
    diagnostics.warning("W-200", "late warning", path="z/file.yaml")
    diagnostics.error("E-100", "first error", path="b/file.yaml", source_ref="ADR-L-0002")
    diagnostics.info("I-100", "info", path="a/file.yaml")
    diagnostics.error("E-090", "earlier error", path="a/file.yaml", source_ref="ADR-L-0001")

    ordered = diagnostics.as_list()

    assert [(item.level, item.code, item.path, item.source_ref) for item in ordered] == [
        (DiagnosticLevel.INFO, "I-100", "a/file.yaml", None),
        (DiagnosticLevel.WARNING, "W-200", "z/file.yaml", None),
        (DiagnosticLevel.ERROR, "E-090", "a/file.yaml", "ADR-L-0001"),
        (DiagnosticLevel.ERROR, "E-100", "b/file.yaml", "ADR-L-0002"),
    ]


def test_diagnostic_log_normalizes_paths_and_tracks_errors():
    diagnostics = DiagnosticLog()

    diagnostics.info("I-100", "ok", path=Path("nested\\file.yaml"))
    assert diagnostics.has_errors is False

    diagnostics.error("E-100", "broken", path=Path("nested\\file.yaml"))
    assert diagnostics.has_errors is True
    assert diagnostics.as_list()[0].path == "nested/file.yaml"
