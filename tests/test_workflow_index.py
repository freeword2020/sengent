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


def test_match_workflow_entry_defaults_generic_wgs_to_short_read_when_long_read_is_unspecified(tmp_path):
    source_directory = tmp_path
    payload = {
        "version": "test",
        "entries": [
            {
                "id": "wgs-ambiguous",
                "name": "WGS routing",
                "priority": 20,
                "require_any_groups": [["wgs"]],
                "prefer_any": ["脚本", "分析"],
                "summary": "generic wgs",
            },
            {
                "id": "short-read-wgs",
                "name": "Short-read WGS",
                "priority": 53,
                "require_any_groups": [["wgs"], ["short-read", "短读长"]],
                "prefer_any": ["脚本", "分析"],
                "summary": "default short-read wgs",
            },
            {
                "id": "long-read-wgs",
                "name": "Long-read WGS",
                "priority": 60,
                "require_any_groups": [["wgs"], ["long-read", "长读长", "ont"]],
                "prefer_any": ["脚本", "分析"],
                "summary": "explicit long-read wgs",
            },
        ],
    }
    (source_directory / "workflow-guides.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    matched = match_workflow_entry("我要做wgs分析，能给个示例脚本吗", source_directory)

    assert matched is not None
    assert matched["id"] == "short-read-wgs"
