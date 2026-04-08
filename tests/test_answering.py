import os
import subprocess
import sys

from sentieon_assist.ollama_client import build_generate_payload, generate_stream
from sentieon_assist.answering import answer_query, answer_reference_query, format_rule_answer, normalize_model_answer
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


def test_answer_reference_query_uses_module_index_for_intro_question(tmp_path):
    (tmp_path / "sentieon-modules.json").write_text(
        """
        {
          "version": "202503.03",
          "entries": [
            {
              "id": "dnascope",
              "name": "DNAscope",
              "aliases": ["dnascope"],
              "category": "germline-variant-calling",
              "summary": "DNAscope 是短读长胚系主流程。",
              "scope": ["短读长 DNA", "diploid organism"],
              "inputs": ["FASTQ", "BAM/CRAM"],
              "outputs": ["VCF", "gVCF"],
              "common_questions": ["DNAscope 支持什么输入"],
              "related_modules": ["DNAseq"],
              "source_priority_notes": [],
              "sources": ["Sentieon202503.03.pdf"]
            }
          ]
        }
        """.strip()
    )

    text = answer_reference_query("dnascope是什么", source_directory=str(tmp_path))

    assert "【模块介绍】" in text
    assert "DNAscope：DNAscope 是短读长胚系主流程。" in text
    assert "常见输入：FASTQ；BAM/CRAM" in text
    assert "【资料查询】" not in text
    assert "【资料版本】" not in text
    assert "【参考资料】" not in text
    assert "命中模块索引" not in text


def test_answer_reference_query_uses_module_index_for_input_question(tmp_path):
    (tmp_path / "sentieon-modules.json").write_text(
        """
        {
          "version": "202503.03",
          "entries": [
            {
              "id": "cnvscope",
              "name": "CNVscope",
              "aliases": ["cnvscope"],
              "category": "copy-number",
              "summary": "CNVscope 是胚系 CNV 模块。",
              "scope": ["WGS germline CNV"],
              "inputs": ["deduped BAM", "参考基因组", "CNV model"],
              "outputs": ["CNV VCF"],
              "common_questions": ["CNVscope 需要什么输入"],
              "related_modules": ["CNVModelApply"],
              "source_priority_notes": [],
              "sources": ["Sentieon202503.03.pdf"]
            }
          ]
        }
        """.strip()
    )

    text = answer_reference_query("CNVscope 支持什么输入", source_directory=str(tmp_path))

    assert "CNVscope：CNVscope 是胚系 CNV 模块。" in text
    assert "常见输入：deduped BAM；参考基因组；CNV model" in text
    assert "常见输出" not in text


def test_answer_reference_query_uses_parameter_index_for_dnascope_flag(tmp_path):
    (tmp_path / "sentieon-modules.json").write_text(
        """
        {
          "version": "202503.03",
          "entries": [
            {
              "id": "dnascope",
              "name": "DNAscope",
              "aliases": ["dnascope"],
              "category": "germline-variant-calling",
              "summary": "DNAscope 是短读长胚系主流程。",
              "scope": ["短读长 DNA"],
              "inputs": ["FASTQ", "BAM/CRAM"],
              "outputs": ["VCF", "gVCF"],
              "common_questions": ["DNAscope 支持什么输入"],
              "related_modules": ["DNAseq"],
              "parameters": [
                {
                  "name": "--pcr_free",
                  "aliases": ["pcr_free"],
                  "summary": "按 PCR-free 文库模式调用，适合 PCR-free library prep。",
                  "details": ["内部对应使用适合 PCR-free 的 indel 模型。", "Dedup 仍会执行，用于识别 optical duplicates。"],
                  "values": []
                }
              ],
              "source_priority_notes": [],
              "sources": ["Sentieon202503.03.pdf"]
            }
          ]
        }
        """.strip()
    )

    text = answer_reference_query("sentieon-cli dnascope 的 --pcr_free 是什么", source_directory=str(tmp_path))

    assert "【资料查询】" not in text
    assert "命中模块索引：DNAscope" not in text
    assert "命中参数：--pcr_free" not in text
    assert "【模块介绍】" not in text
    assert "DNAscope 的 --pcr_free" in text
    assert "按 PCR-free 文库模式调用" in text
    assert "Dedup 仍会执行" in text
    assert "【资料版本】" not in text
    assert "【参考资料】" not in text


def test_answer_reference_query_uses_parameter_index_for_gvcftyper_option(tmp_path):
    (tmp_path / "sentieon-modules.json").write_text(
        """
        {
          "version": "202503.03",
          "entries": [
            {
              "id": "gvcftyper",
              "name": "GVCFtyper",
              "aliases": ["gvcftyper"],
              "category": "germline-variant-calling",
              "summary": "GVCFtyper 是 joint call 核心算法。",
              "scope": ["joint call"],
              "inputs": ["多个 gVCF"],
              "outputs": ["联合分型 VCF"],
              "common_questions": ["什么时候用 multinomial model"],
              "related_modules": ["Joint Call"],
              "parameters": [
                {
                  "name": "--genotype_model",
                  "aliases": ["genotype_model"],
                  "summary": "控制 GVCFtyper 的分型模型。",
                  "details": ["大 cohort 场景可考虑 multinomial。", "multinomial 在大规模 joint call 时扩展性更好。"],
                  "values": ["multinomial"]
                }
              ],
              "source_priority_notes": [],
              "sources": ["Sentieon202503.03.pdf"]
            }
          ]
        }
        """.strip()
    )

    text = answer_reference_query("GVCFtyper 的 --genotype_model multinomial 是什么", source_directory=str(tmp_path))

    assert "命中模块索引：GVCFtyper" not in text
    assert "命中参数：--genotype_model" not in text
    assert "【模块介绍】" not in text
    assert "GVCFtyper 的 --genotype_model" in text
    assert "大 cohort 场景可考虑 multinomial" in text
    assert "可选值/关键值：multinomial" in text
    assert "【资料版本】" not in text
    assert "【参考资料】" not in text


def test_answer_reference_query_can_use_global_parameter_lookup_without_module_name(tmp_path):
    (tmp_path / "sentieon-modules.json").write_text(
        """
        {
          "version": "202503.03",
          "entries": [
            {
              "id": "dnascope-longread",
              "name": "DNAscope LongRead",
              "aliases": ["dnascope longread", "dnascope long read"],
              "category": "germline-variant-calling",
              "summary": "DNAscope LongRead 是长读长胚系流程。",
              "scope": ["long-read germline"],
              "inputs": ["HiFi/ONT BAM/CRAM", "参考基因组"],
              "outputs": ["VCF", "SV VCF"],
              "common_questions": ["DNAscope LongRead 支持什么平台"],
              "related_modules": ["DNAscope", "LongReadSV"],
              "parameters": [
                {
                  "name": "--haploid_bed",
                  "aliases": ["haploid_bed"],
                  "summary": "指定 haploid region BED。",
                  "details": ["这些区域会按 haploid 模式解释基因型。", "常见于 chrX/chrY 或特定单倍体区域。"],
                  "values": []
                }
              ],
              "source_priority_notes": [],
              "sources": ["Sentieon202503.03.pdf"]
            }
          ]
        }
        """.strip()
    )

    text = answer_reference_query("参数 --haploid_bed 是什么", source_directory=str(tmp_path))

    assert "命中模块索引：DNAscope LongRead" not in text
    assert "命中参数：--haploid_bed" not in text
    assert "【模块介绍】" not in text
    assert "DNAscope LongRead 的 --haploid_bed" in text
    assert "指定 haploid region BED" in text
    assert "【资料版本】" not in text
    assert "【参考资料】" not in text


def test_answer_reference_query_asks_to_disambiguate_parameter_when_multiple_modules_match(tmp_path):
    (tmp_path / "sentieon-modules.json").write_text(
        """
        {
          "version": "202503.03",
          "entries": [
            {
              "id": "joint-call",
              "name": "Joint Call",
              "aliases": ["joint call"],
              "category": "workflow",
              "summary": "Joint Call 是多样本联合分型流程。",
              "scope": ["cohort analysis"],
              "inputs": ["多个 gVCF"],
              "outputs": ["多样本 VCF"],
              "parameters": [
                {
                  "name": "--genotype_model",
                  "aliases": ["genotype_model"],
                  "summary": "控制 joint genotyping 使用的分型模型。",
                  "details": ["大 cohort 可考虑 multinomial。"],
                  "values": ["multinomial"]
                }
              ],
              "common_questions": [],
              "related_modules": ["GVCFtyper"],
              "source_priority_notes": [],
              "sources": ["Sentieon202503.03.pdf"]
            },
            {
              "id": "gvcftyper",
              "name": "GVCFtyper",
              "aliases": ["gvcftyper"],
              "category": "germline-variant-calling",
              "summary": "GVCFtyper 是联合分型核心算法。",
              "scope": ["joint call"],
              "inputs": ["多个 gVCF"],
              "outputs": ["联合分型 VCF"],
              "parameters": [
                {
                  "name": "--genotype_model",
                  "aliases": ["genotype_model"],
                  "summary": "控制 GVCFtyper 的分型模型。",
                  "details": ["大 cohort 场景可考虑 multinomial。"],
                  "values": ["multinomial"]
                }
              ],
              "common_questions": [],
              "related_modules": ["Joint Call"],
              "source_priority_notes": [],
              "sources": ["Sentieon202503.03.pdf"]
            }
          ]
        }
        """.strip()
    )

    text = answer_reference_query("参数 --genotype_model 是什么", source_directory=str(tmp_path))

    assert "需要确认模块" in text
    assert "--genotype_model" in text
    assert "Joint Call" in text
    assert "GVCFtyper" in text


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
