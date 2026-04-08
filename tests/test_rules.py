import json

from sentieon_assist.rules import load_rules, match_rule
from sentieon_assist.rules import package_knowledge_dir


def test_load_rules_reads_base_knowledge_files():
    rules = load_rules()
    assert any(rule["category"] == "license" for rule in rules)
    assert any(rule["category"] == "install" for rule in rules)


def test_package_knowledge_dir_contains_base_json_files():
    base_dir = package_knowledge_dir()
    assert (base_dir / "license.json").exists()
    assert (base_dir / "install.json").exists()


def test_match_rule_finds_license_rule():
    rule = match_rule("license 报错，找不到 license 文件")
    assert rule is not None
    assert rule["category"] == "license"


def test_load_rules_reads_override_directory(tmp_path):
    override_file = tmp_path / "license.json"
    override_file.write_text(
        json.dumps(
            [
                {
                    "category": "license",
                    "summary": "override",
                    "patterns": ["customer-license"],
                    "causes": ["x"],
                    "steps": ["y"],
                    "requires": ["z"],
                }
            ]
        )
    )
    rules = load_rules(tmp_path)
    assert rules[0]["summary"] == "override"
