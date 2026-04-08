import os
import subprocess
import sys

from sentieon_assist.ollama_client import build_generate_payload, generate_stream
from sentieon_assist.answering import answer_query, format_rule_answer, normalize_model_answer
from sentieon_assist.prompts import ANSWER_TEMPLATE, build_support_prompt


def test_build_generate_payload_uses_configured_model():
    payload = build_generate_payload("gemma4:e4b", "hello")
    assert payload["model"] == "gemma4:e4b"
    assert payload["prompt"] == "hello"
    assert payload["stream"] is False


def test_build_generate_payload_can_enable_streaming():
    payload = build_generate_payload("gemma4:e4b", "hello", stream=True)
    assert payload["model"] == "gemma4:e4b"
    assert payload["prompt"] == "hello"
    assert payload["stream"] is True


def test_build_generate_payload_can_include_keep_alive():
    payload = build_generate_payload("gemma4:e4b", "hello", keep_alive="2h")
    assert payload["model"] == "gemma4:e4b"
    assert payload["prompt"] == "hello"
    assert payload["stream"] is False
    assert payload["keep_alive"] == "2h"


def test_generate_stream_reads_chunked_ollama_response(monkeypatch):
    chunks: list[str] = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            lines = [
                b'{"response":"\xe8\xaf\xb7\xe5\x91\x8a\xe8\xaf\x89\xe6\x88\x91","done":false}\n',
                b'{"response":" Sentieon \xe7\x89\x88\xe6\x9c\xac\xe5\x8f\xb7","done":false}\n',
                b'{"response":"\xef\xbc\x8c\xe4\xbe\x8b\xe5\xa6\x82 202503.03\xe3\x80\x82","done":true}\n',
            ]
            return iter(lines)

    def fake_urlopen(request, timeout):
        assert request.full_url == "http://127.0.0.1:11434/api/generate"
        assert timeout == 120
        return FakeResponse()

    monkeypatch.setattr("sentieon_assist.ollama_client.urlopen", fake_urlopen)

    text = generate_stream(
        "gemma4:e4b",
        "hello",
        on_chunk=chunks.append,
    )

    assert chunks == ["请告诉我", " Sentieon 版本号", "，例如 202503.03。"]
    assert text == "请告诉我 Sentieon 版本号，例如 202503.03。"


def test_answer_template_has_required_sections():
    assert "【问题判断】" in ANSWER_TEMPLATE
    assert "【可能原因】" in ANSWER_TEMPLATE
    assert "【建议步骤】" in ANSWER_TEMPLATE
    assert "【需要补充的信息】" in ANSWER_TEMPLATE


def test_format_rule_answer_uses_required_sections():
    text = format_rule_answer(
        {
            "category": "license",
            "summary": "这是一个 license 问题",
            "causes": ["环境变量未设置"],
            "steps": ["检查 SENTIEON_LICENSE"],
            "requires": ["Sentieon 版本"],
        }
    )
    assert "【问题判断】" in text
    assert "【可能原因】" in text
    assert "【建议步骤】" in text
    assert "【需要补充的信息】" in text


def test_answer_query_filters_already_known_required_info(monkeypatch):
    monkeypatch.setattr(
        "sentieon_assist.answering.collect_source_bundle_metadata",
        lambda directory: {
            "primary_release": "202503.03",
            "primary_date": "Mar 30, 2026",
            "primary_reference": "Sentieon202503.03.pdf",
        },
    )

    text = answer_query(
        "license",
        "Sentieon 202503 license 报错，找不到 license 文件",
        {
            "version": "202503",
            "input_type": "",
            "error": "Sentieon 202503 license 报错，找不到 license 文件",
            "error_keywords": "license",
            "step": "",
            "data_type": "",
        },
    )

    assert "【需要补充的信息】" in text
    assert "Sentieon 版本" not in text
    assert "完整报错信息" not in text
    assert "- 无" in text


def test_answer_query_asks_for_missing_fields_in_chinese():
    text = answer_query(
        "license",
        "许可证激活失败",
        {
            "version": "",
            "input_type": "",
            "error": "许可证激活失败",
            "error_keywords": "license",
            "step": "",
            "data_type": "",
        },
    )

    assert text == "需要补充以下信息：Sentieon 版本"


def test_answer_query_uses_model_fallback_when_rule_misses(monkeypatch):
    monkeypatch.setattr("sentieon_assist.answering.match_rule", lambda query: None)
    monkeypatch.setattr(
        "sentieon_assist.answering.collect_source_evidence",
        lambda directory, issue_type, query, info: [{"name": "notes.md", "snippet": "license note"}],
    )

    def fake_generate(issue_type, query, info, evidence):
        assert issue_type == "install"
        assert info["version"] == "202503"
        assert evidence[0]["name"] == "notes.md"
        return "MODEL_ANSWER"

    text = answer_query(
        "install",
        "Sentieon 202503 install 失败",
        {
            "version": "202503",
            "input_type": "",
            "error": "Sentieon 202503 install 失败",
            "error_keywords": "",
            "step": "install",
            "data_type": "",
        },
        model_fallback=fake_generate,
    )
    assert text.endswith("notes.md")


def test_answer_query_uses_explicit_source_directory(monkeypatch):
    seen: dict[str, str] = {}

    monkeypatch.setattr("sentieon_assist.answering.match_rule", lambda query: None)

    def fake_collect(directory, issue_type, query, info):
        seen["directory"] = directory
        return [{"name": "notes.md", "snippet": "install note"}]

    monkeypatch.setattr("sentieon_assist.answering.collect_source_evidence", fake_collect)

    text = answer_query(
        "install",
        "Sentieon 202503 install 失败",
        {
            "version": "202503",
            "input_type": "",
            "error": "Sentieon 202503 install 失败",
            "error_keywords": "",
            "step": "install",
            "data_type": "",
        },
        model_fallback=lambda issue_type, query, info, evidence: "MODEL_ANSWER",
        source_directory="/tmp/custom-sources",
    )
    assert seen["directory"] == "/tmp/custom-sources"
    assert text.endswith("notes.md")


def test_answer_query_does_not_call_model_when_rule_matches(monkeypatch):
    def fake_generate(issue_type, query, info, evidence):
        raise AssertionError("model fallback should not be called")

    monkeypatch.setattr(
        "sentieon_assist.answering.collect_source_bundle_metadata",
        lambda directory: {
            "primary_release": "202503.03",
            "primary_date": "Mar 30, 2026",
            "primary_reference": "Sentieon202503.03.pdf",
        },
    )

    text = answer_query(
        "license",
        "Sentieon 202503 license 报错，找不到 license 文件",
        {
            "version": "202503",
            "input_type": "",
            "error": "Sentieon 202503 license 报错，找不到 license 文件",
            "error_keywords": "license",
            "step": "",
            "data_type": "",
        },
        model_fallback=fake_generate,
    )
    assert "【问题判断】" in text
    assert "【资料版本】" in text
    assert "202503.03" in text


def test_answer_query_adds_version_warning_when_release_family_differs(monkeypatch):
    monkeypatch.setattr(
        "sentieon_assist.answering.collect_source_bundle_metadata",
        lambda directory: {
            "primary_release": "202503.03",
            "primary_date": "Mar 30, 2026",
            "primary_reference": "Sentieon202503.03.pdf",
        },
    )

    text = answer_query(
        "license",
        "Sentieon 202408 license 报错，找不到 license 文件",
        {
            "version": "202408",
            "input_type": "",
            "error": "Sentieon 202408 license 报错，找不到 license 文件",
            "error_keywords": "license",
            "step": "",
            "data_type": "",
        },
    )

    assert "【版本提示】" in text
    assert "用户问题版本: 202408" in text
    assert "当前资料主版本: 202503.03" in text


def test_answer_query_adds_version_warning_when_patch_release_differs(monkeypatch):
    monkeypatch.setattr(
        "sentieon_assist.answering.collect_source_bundle_metadata",
        lambda directory: {
            "primary_release": "202503.03",
            "primary_date": "Mar 30, 2026",
            "primary_reference": "Sentieon202503.03.pdf",
        },
    )

    text = answer_query(
        "license",
        "Sentieon 202503.01 license 报错，找不到 license 文件",
        {
            "version": "202503.01",
            "input_type": "",
            "error": "Sentieon 202503.01 license 报错，找不到 license 文件",
            "error_keywords": "license",
            "step": "",
            "data_type": "",
        },
    )

    assert "【版本提示】" in text
    assert "用户问题版本: 202503.01" in text
    assert "当前资料主版本: 202503.03" in text


def test_answer_query_skips_version_warning_when_release_family_matches(monkeypatch):
    monkeypatch.setattr(
        "sentieon_assist.answering.collect_source_bundle_metadata",
        lambda directory: {
            "primary_release": "202503.03",
            "primary_date": "Mar 30, 2026",
            "primary_reference": "Sentieon202503.03.pdf",
        },
    )

    text = answer_query(
        "license",
        "Sentieon 202503 license 报错，找不到 license 文件",
        {
            "version": "202503",
            "input_type": "",
            "error": "Sentieon 202503 license 报错，找不到 license 文件",
            "error_keywords": "license",
            "step": "",
            "data_type": "",
        },
    )

    assert "【版本提示】" not in text


def test_build_support_prompt_includes_evidence():
    prompt = build_support_prompt(
        "license",
        "Sentieon 202503 license 报错",
        {"version": "202503"},
        source_context={
            "primary_release": "202503.03",
            "primary_date": "Mar 30, 2026",
            "primary_reference": "Sentieon202503.03.pdf",
        },
        evidence=[{"name": "notes.md", "trust": "official", "snippet": "SENTIEON_LICENSE is required"}],
    )
    assert "资料版本上下文" in prompt
    assert "202503.03" in prompt
    assert "Mar 30, 2026" in prompt
    assert "参考资料片段" in prompt
    assert "notes.md" in prompt
    assert "official" in prompt
    assert "SENTIEON_LICENSE is required" in prompt


def test_normalize_model_answer_can_append_sources_and_source_context():
    text = normalize_model_answer(
        "【问题判断】\nA",
        source_context={
            "primary_release": "202503.03",
            "primary_date": "Mar 30, 2026",
            "primary_reference": "Sentieon202503.03.pdf",
        },
        sources=["notes.md", "guide.pdf"],
    )
    assert "【资料版本】" in text
    assert "202503.03" in text
    assert "【参考资料】" in text
    assert "notes.md" in text
    assert "guide.pdf" in text


def test_normalize_model_answer_does_not_duplicate_reference_section():
    text = normalize_model_answer(
        "【资料查询】\nA\n\n【参考资料】\n- existing.md",
        source_context={
            "primary_release": "202503.03",
            "primary_date": "Mar 30, 2026",
            "primary_reference": "Sentieon202503.03.pdf",
        },
        sources=["notes.md"],
    )
    assert text.count("【参考资料】") == 1
    assert "existing.md" in text


def test_ollama_client_imports_without_site_packages():
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    result = subprocess.run(
        [sys.executable, "-S", "-c", "import sentieon_assist.ollama_client"],
        cwd=str((__import__('pathlib').Path(__file__).resolve().parent.parent)),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_normalize_model_answer_restores_plain_section_headers():
    raw = "**【问题判断】**\nA\n\n**【可能原因】**\nB\n\n**【建议步骤】**\nC\n\n**【需要补充的信息】**\nD"
    text = normalize_model_answer(raw)
    assert "**【问题判断】**" not in text
    assert "【问题判断】" in text
    assert "【可能原因】" in text
    assert "【建议步骤】" in text
    assert "【需要补充的信息】" in text


def test_normalize_model_answer_removes_code_blocks():
    raw = "【建议步骤】\n```bash\n./setup.sh\n```"
    text = normalize_model_answer(raw)
    assert "```" not in text
    assert "命令细节需要结合官方文档确认" in text
