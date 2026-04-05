from __future__ import annotations

from backend.scripts import check_architecture, check_vocabulary, export_json_schemas


def test_guardrail_scripts_and_generated_schemas_are_current() -> None:
    assert check_architecture.main() == 0
    assert check_vocabulary.main() == 0
    assert export_json_schemas.check_schemas(
        export_json_schemas.AGENT_OUT_DIR,
        export_json_schemas.AGENT_SCHEMAS,
    ) == []
    assert export_json_schemas.check_schemas(
        export_json_schemas.EVENT_OUT_DIR,
        export_json_schemas.EVENT_SCHEMAS,
    ) == []
