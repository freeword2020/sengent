import json

from sentieon_assist.workflow_index import (
    match_workflow_entry,
    workflow_allows_direct_script_handoff,
)


def test_workflow_allows_direct_script_handoff_normalizes_string_false():
    assert workflow_allows_direct_script_handoff({"direct_script_handoff": "false"}) is False
    assert workflow_allows_direct_script_handoff({"direct_script_handoff": "true"}) is True


def test_match_workflow_entry_tolerates_malformed_runtime_hints(tmp_path):
    source_directory = tmp_path
    payload = {
        "version": "test",
        "entries": [
            {
                "id": "malformed",
                "name": "Malformed",
                "priority": "high",
                "require_any_groups": [["wgs"]],
                "prefer_any": "脚本",
                "summary": "malformed runtime hints",
            },
            {
                "id": "valid",
                "name": "Valid",
                "priority": 1,
                "require_any_groups": [["wgs"]],
                "prefer_any": ["脚本"],
                "summary": "valid runtime hints",
            },
        ],
    }
    (source_directory / "workflow-guides.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    matched = match_workflow_entry("wgs 脚本", source_directory)

    assert matched is not None
    assert matched["id"] == "valid"
