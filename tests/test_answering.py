import os
import json
from pathlib import Path
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


def test_answer_reference_query_returns_boundary_for_benchmark_claim_without_model():
    text = answer_reference_query(
        "为什么在 AWS 上运行一次标准的 Sentieon 30X 全基因组流程的计算成本可被压缩至 1~5 美元左右？",
        model_fallback=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert "【资料边界】" in text
    assert "benchmark" in text or "竞品" in text or "精确数值" in text


def test_answer_reference_query_returns_boundary_for_competitive_claim_without_model():
    text = answer_reference_query(
        "针对 ONT R10.4.1+ 数据中长同聚物区域的 Indel 错误率，Sentieon 模型是如何与 Clair3 拉开差距的？",
        model_fallback=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert "【资料边界】" in text
    assert "Clair3" not in text or "不能直接给出确定性结论" in text


def test_notebooklm_adversarial_corpus_is_committed_and_complete():
    path = Path(__file__).resolve().parent / "data" / "notebooklm_adversarial_cases.json"
    payload = json.loads(path.read_text())

    assert len(payload) == 50
    assert payload[0]["id"] == 1
    assert payload[-1]["id"] == 50
    assert len([item for item in payload if item["expected_mode"] == "boundary"]) >= 40


def test_answer_reference_query_supports_bwa_interleaved_parameter():
    text = answer_reference_query("当 FASTQ 是 interleaved 时，Sentieon BWA 的 -p 参数有什么作用？")

    assert "【常用参数】" in text
    assert "Sentieon BWA 的 -p" in text


def test_answer_reference_query_prefers_dnascope_pcr_free_alias_over_model_substring():
    text = answer_reference_query("对于 PCR-free 建库样本，在运行 DNAscope 时，如何通过 --pcr_indel_model none 来关闭过滤？")

    assert "DNAscope" in text
    assert "CNVscope" not in text
    assert "--pcr_free" in text or "--pcr_indel_model" in text


def test_answer_reference_query_supports_gvcftyper_emit_mode_parameter():
    text = answer_reference_query("在 GVCFtyper 中，参数 --emit_mode 设置为 variant、confident 或 all 时有什么区别？")

    assert "【常用参数】" in text
    assert "GVCFtyper 的 --emit_mode" in text


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


def test_answer_reference_query_marks_placeholder_module_as_unverified(tmp_path):
    (tmp_path / "sentieon-modules.json").write_text(
        """
        {
          "version": "202503.03",
          "entries": [
            {
              "id": "python-api",
              "name": "Python API",
              "aliases": ["python api"],
              "category": "architecture",
              "summary": "当前本地官方 PDF 未见 Python API 的详细章节；该名称暂按待核验占位保留。",
              "scope": [],
              "inputs": [],
              "outputs": [],
              "common_questions": ["Python API 在本地官方资料里是否有详细章节"],
              "related_modules": [],
              "source_priority_notes": [],
              "sources": []
            }
          ]
        }
        """.strip()
    )

    text = answer_reference_query("python api是什么", source_directory=str(tmp_path))

    assert "Python API：当前本地官方 PDF 未见 Python API 的详细章节；该名称暂按待核验占位保留。" in text
    assert "当前本地官方资料未提供可用于确定性回答的详细章节。" in text
    assert "常见输入" not in text


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


def test_answer_reference_query_uses_semantic_intent_for_module_overview(tmp_path, monkeypatch):
    (tmp_path / "sentieon-modules.json").write_text(
        """
        {
          "version": "202503.03",
          "entries": [
            {
              "id": "alignment",
              "name": "Alignment",
              "aliases": ["alignment"],
              "category": "family",
              "summary": "比对模块家族。",
              "scope": [],
              "inputs": [],
              "outputs": [],
              "common_questions": [],
              "related_modules": []
            },
            {
              "id": "bwa",
              "name": "Sentieon BWA",
              "aliases": ["bwa"],
              "category": "alignment",
              "summary": "短读长比对器。",
              "scope": [],
              "inputs": [],
              "outputs": [],
              "common_questions": [],
              "related_modules": []
            },
            {
              "id": "dnascope",
              "name": "DNAscope",
              "aliases": ["dnascope"],
              "category": "germline-variant-calling",
              "summary": "短读长胚系主流程。",
              "scope": [],
              "inputs": [],
              "outputs": [],
              "common_questions": [],
              "related_modules": []
            },
            {
              "id": "tnscope",
              "name": "TNscope",
              "aliases": ["tnscope"],
              "category": "somatic-variant-calling",
              "summary": "体细胞主力 caller。",
              "scope": [],
              "inputs": [],
              "outputs": [],
              "common_questions": [],
              "related_modules": []
            },
            {
              "id": "rnaseq",
              "name": "RNAseq",
              "aliases": ["rnaseq"],
              "category": "rna-variant-calling",
              "summary": "RNA 变异调用流程。",
              "scope": [],
              "inputs": [],
              "outputs": [],
              "common_questions": [],
              "related_modules": []
            },
            {
              "id": "dedup",
              "name": "Dedup",
              "aliases": ["dedup"],
              "category": "bam-processing",
              "summary": "去重模块。",
              "scope": [],
              "inputs": [],
              "outputs": [],
              "common_questions": [],
              "related_modules": []
            },
            {
              "id": "qc",
              "name": "QC",
              "aliases": ["qc"],
              "category": "family",
              "summary": "QC 模块总览。",
              "scope": [],
              "inputs": [],
              "outputs": [],
              "common_questions": [],
              "related_modules": []
            },
            {
              "id": "python-api",
              "name": "Python API",
              "aliases": ["python api"],
              "category": "architecture",
              "summary": "二次开发入口。",
              "scope": [],
              "inputs": [],
              "outputs": [],
              "common_questions": [],
              "related_modules": []
            }
          ]
        }
        """.strip()
    )

    from sentieon_assist.reference_intents import ReferenceIntent

    monkeypatch.setattr(
        "sentieon_assist.answering.parse_reference_intent",
        lambda query, **kwargs: ReferenceIntent(intent="module_overview", confidence=0.93),
    )

    text = answer_reference_query("sentieon都有哪些模块", source_directory=str(tmp_path))

    assert "【模块介绍】" in text
    assert "Sentieon 主要模块可以先按" in text
    assert "Alignment" in text
    assert "DNAscope" in text
    assert "TNscope" in text
    assert "RNAseq" in text
    assert "Alignment：Alignment；Sentieon BWA" not in text
    assert "Preprocess / QC / Support：Alignment" not in text
    assert "Preprocess / QC / Support：QC；Dedup；Python API" in text
    assert "【资料查询】" not in text
    assert "【资料版本】" not in text
    assert "【参考资料】" not in text


def test_answer_reference_query_uses_script_index_for_rnaseq(tmp_path):
    (tmp_path / "sentieon-modules.json").write_text(
        """
        {
          "version": "202503.03",
          "entries": [
            {
              "id": "rnaseq",
              "name": "RNAseq",
              "aliases": ["rnaseq"],
              "category": "rna-variant-calling",
              "summary": "RNA 变异调用流程。",
              "scope": ["RNA short-variant calling"],
              "inputs": ["FASTQ", "STAR reference"],
              "outputs": ["VCF", "RNA BAM/CRAM"],
              "common_questions": [],
              "related_modules": ["Sentieon STAR", "RNASplitReadsAtJunction", "Haplotyper"],
              "script_examples": [
                {
                  "title": "RNA short-variant calling skeleton",
                  "summary": "典型 RNA 小变异流程骨架，包含 STAR、Dedup、split junction 和 variant calling。",
                  "when_to_use": ["RNA 小变异调用", "short-read RNA"],
                  "command_lines": [
                    "sentieon STAR --runThreadN NUMBER_THREADS --genomeDir STAR_REFERENCE --readFilesIn SAMPLE SAMPLE2 --readFilesCommand zcat --outStd BAM_Unsorted --outSAMtype BAM Unsorted --outBAMcompression 0 --outSAMattrRGline ID:GROUP_NAME SM:SAMPLE_NAME PL:PLATFORM --twopassMode Basic --twopass1readsN -1 --sjdbOverhang READ_LENGTH_MINUS_1 | sentieon util sort -r REFERENCE -o SORTED_BAM -t NUMBER_THREADS -i -",
                    "sentieon driver -t NUMBER_THREADS -i SORTED_BAM --algo LocusCollector --rna --fun score_info SCORE.gz",
                    "sentieon driver -t NUMBER_THREADS -i SORTED_BAM --algo Dedup --score_info SCORE.gz DEDUPED_BAM",
                    "sentieon driver -t NUMBER_THREADS -r REFERENCE -i DEDUPED_BAM --algo RNASplitReadsAtJunction --reassign_mapq 255:60 SPLIT_BAM",
                    "sentieon driver -t NUMBER_THREADS -r REFERENCE -i SPLIT_BAM [-q RECAL_DATA.TABLE] --algo Haplotyper --trim_soft_clip --call_conf 20 --emit_conf 20 [-d dbSNP] VARIANT_VCF"
                  ],
                  "notes": [
                    "这不是 sentieon-cli 单命令流程，而是 manual 里的 step-by-step workflow。",
                    "如果想用 DNAscope 做 RNA calling，可把最后一步的 Haplotyper 换成 DNAscope。"
                  ],
                  "sources": ["Sentieon202503.03.pdf", "sentieon-doc-map.md", "sentieon-github-map.md"]
                }
              ],
              "source_priority_notes": [],
              "sources": ["Sentieon202503.03.pdf"]
            }
          ]
        }
        """.strip()
    )

    from sentieon_assist.reference_intents import ReferenceIntent

    text = answer_reference_query(
        "能给个 rnaseq 的参考脚本吗",
        source_directory=str(tmp_path),
        parsed_intent=ReferenceIntent(intent="script_example", module="RNAseq", confidence=0.91),
    )

    assert "【模块介绍】" in text
    assert "【参考命令】" in text
    assert "RNAseq：RNA 变异调用流程。" in text
    assert "sentieon STAR --runThreadN NUMBER_THREADS" in text
    assert "RNASplitReadsAtJunction" in text
    assert "Haplotyper --trim_soft_clip" in text
    assert "这不是 sentieon-cli 单命令流程" in text
    assert "【资料查询】" not in text
    assert "【资料版本】" not in text
    assert "【参考资料】" not in text


def test_answer_reference_query_parses_script_intent_before_module_intro(tmp_path, monkeypatch):
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
              "summary": "DNAscope 是 short-read DNA 的 alignment and germline variant calling pipeline。",
              "scope": ["短读长 DNA", "WGS"],
              "inputs": ["FASTQ", "参考基因组", "model bundle"],
              "outputs": ["VCF", "deduped BAM/CRAM"],
              "common_questions": [],
              "related_modules": ["DNAseq"],
              "script_examples": [
                {
                  "title": "sentieon-cli DNAscope FASTQ skeleton",
                  "summary": "官方 sentieon-cli 的 DNAscope 单命令骨架。",
                  "when_to_use": ["短读长 DNA", "WGS"],
                  "command_lines": [
                    "sentieon-cli dnascope -r REFERENCE --r1_fastq R1_FASTQ --r2_fastq R2_FASTQ --readgroups READGROUPS -m MODEL_BUNDLE SAMPLE_VCF"
                  ],
                  "notes": [
                    "这是 sentieon-cli 的命令行入口。"
                  ],
                  "sources": ["Sentieon202503.03.pdf", "sentieon-doc-map.md"]
                }
              ],
              "source_priority_notes": [],
              "sources": ["Sentieon202503.03.pdf", "sentieon-doc-map.md"]
            }
          ]
        }
        """.strip()
    )

    from sentieon_assist.reference_intents import ReferenceIntent

    monkeypatch.setattr(
        "sentieon_assist.answering.parse_reference_intent",
        lambda query, **kwargs: ReferenceIntent(intent="script_example", module="DNAscope", confidence=0.92),
    )

    text = answer_reference_query("能给个 dnascope 做 wgs 分析的示例脚本吗", source_directory=str(tmp_path))

    assert "【参考命令】" in text
    assert "sentieon-cli dnascope -r REFERENCE" in text
    assert "【使用前提】" in text


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


def test_normalize_model_answer_hides_secondary_and_thread_summary_sources():
    text = normalize_model_answer(
        "【问题判断】\nA",
        source_context={
            "primary_release": "202503.03",
            "primary_date": "Mar 30, 2026",
            "primary_reference": "Sentieon202503.03.pdf",
        },
        sources=[
            "sentieon-modules.json",
            "Sentieon202503.03.pdf",
            "sentieon-chinese-reference.md",
            "thread-019d5249-summary.md",
        ],
    )

    assert "【参考资料】" in text
    assert "sentieon-modules.json" in text
    assert "Sentieon202503.03.pdf" in text
    assert "sentieon-chinese-reference.md" not in text
    assert "thread-019d5249-summary.md" not in text


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


def test_normalize_model_answer_removes_inline_markdown_artifacts():
    raw = (
        "**1. 比对模块（Alignment）**\n"
        "*   **Sentieon BWA:** 适用于短读长 DNA 比对。\n"
        "*   **使用流程：** 常见路径包括 `sentieon-cli`。"
    )
    text = normalize_model_answer(raw)
    assert "**" not in text
    assert "`" not in text
    assert "*   " not in text
    assert "1. 比对模块（Alignment）" in text
    assert "- Sentieon BWA: 适用于短读长 DNA 比对。" in text
    assert "- 使用流程： 常见路径包括 sentieon-cli。" in text


def test_normalize_model_answer_standardizes_bioinformatics_terminology():
    raw = (
        "这是没有 matched normal 的 tumor-only 流程，"
        "会包含 germline variants，"
        "并覆盖 somatic variant 和 structural variant detection。"
        "该流程适用于 long-read sequence data，"
        "仅推荐 diploid organism。"
    )
    text = normalize_model_answer(raw)

    assert "配对正常样本（matched normal）" in text
    assert "单肿瘤（tumor-only）" in text
    assert "胚系变异（germline variants）" in text
    assert "体细胞变异" in text
    assert "结构变异检测" in text
    assert "长读长测序数据（long-read sequence data）" in text
    assert "二倍体生物（diploid organism）" in text


def test_checked_in_source_directory_exposes_dnaseq_script_example():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "DNAseq 的参考脚本",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="script_example", module="DNAseq", confidence=0.91),
    )

    assert "【参考命令】" in text
    assert "sentieon bwa mem" in text
    assert "LocusCollector" in text
    assert "QualCal" in text
    assert "Haplotyper" in text


def test_checked_in_source_directory_exposes_dnascope_hybrid_script_example():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "DNAscope Hybrid 的参考命令",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="script_example", module="DNAscope Hybrid", confidence=0.92),
    )

    assert "【参考命令】" in text
    assert "sentieon-cli dnascope-hybrid" in text
    assert "--sr_aln SR_ALN" in text
    assert "--lr_aln LR_ALN" in text


def test_checked_in_source_directory_exposes_pangenome_script_example():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "Pangenome 的参考命令",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="script_example", module="Sentieon Pangenome", confidence=0.92),
    )

    assert "【参考命令】" in text
    assert "sentieon-cli sentieon-pangenome" in text
    assert "--hapl HAPL" in text
    assert "--gbz GBZ" in text
    assert "--pop_vcf POP_VCF" in text


def test_checked_in_source_directory_exposes_cnvscope_script_example():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "CNVscope 的参考脚本",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="script_example", module="CNVscope", confidence=0.92),
    )

    assert "【参考命令】" in text
    assert "--algo CNVscope" in text
    assert "--algo CNVModelApply" in text
    assert "DEDUPED_BAM" in text
    assert "ML_MODEL/cnv.model" in text


def test_checked_in_source_directory_exposes_pangenome_parameter_example():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "Sentieon Pangenome 的 --pop_vcf 是什么",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="parameter_lookup", module="Sentieon Pangenome", confidence=0.92),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【模块介绍】" not in text
    assert "Sentieon Pangenome 的 --pop_vcf" in text
    assert "population VCF" in text
    assert "Pangenome" in text


def test_checked_in_source_directory_exposes_cnvscope_parameter_example():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "CNVscope 的 --model 是什么",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="parameter_lookup", module="CNVscope", confidence=0.92),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【模块介绍】" not in text
    assert "CNVscope 的 --model" in text
    assert "machine learning model" in text
    assert "CNVModelApply" in text


def test_checked_in_source_directory_exposes_ambiguous_wgs_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "如果我要做wgs分析，能不能给个指导",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.92),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "短读长胚系 WGS" in text
    assert "体细胞 WGS" in text
    assert "长读长胚系 WGS" in text
    assert "Sentieon BWA" not in text
    assert "WgsMetricsAlgo" not in text


def test_checked_in_source_directory_exposes_ambiguous_wgs_script_request_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做wgs分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "短读长胚系 WGS" in text
    assert "体细胞 WGS" in text
    assert "长读长胚系 WGS" in text
    assert "【需要确认的信息】" in text
    assert "**" not in text
    assert "`" not in text


def test_checked_in_source_directory_exposes_short_read_germline_wgs_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "short-read germline WGS 应该看哪个流程",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "DNAscope" in text
    assert "DNAseq" in text
    assert "diploid" in text


def test_checked_in_source_directory_exposes_somatic_wgs_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "somatic WGS 应该看哪个流程",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.94),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "TNseq" in text
    assert "TNscope" in text
    assert "tumor-normal" in text or "tumor only" in text


def test_checked_in_source_directory_exposes_long_read_wgs_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "PacBio HiFi WGS 应该看哪个流程",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.95),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "DNAscope LongRead" in text
    assert "PacBio HiFi" in text
    assert "ONT" in text


def test_checked_in_source_directory_exposes_wes_script_request_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做wes分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "DNAscope" in text
    assert "WES" in text
    assert "【需要确认的信息】" in text


def test_checked_in_source_directory_exposes_tumor_only_script_request_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做tumor-only分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "TNscope" in text
    assert "tumor-only" in text or "tumor only" in text
    assert "【需要确认的信息】" in text


def test_checked_in_source_directory_uses_standard_bioinformatics_terms_for_tumor_only_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做tumor-only分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "单肿瘤（tumor-only）" in text
    assert "配对正常样本（matched normal）" in text
    assert "体细胞变异" in text
    assert "结构变异检测" in text
    assert "胚系变异" in text


def test_checked_in_source_directory_exposes_long_read_script_request_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做long-read分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "DNAscope LongRead" in text
    assert "DNAscope Hybrid" in text
    assert "【需要确认的信息】" in text


def test_checked_in_source_directory_uses_standard_bioinformatics_terms_for_long_read_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做long-read分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "长读长测序数据（long-read sequence data）" in text
    assert "长读长胚系（long-read germline）" in text
    assert "胚系变异检测流程（germline variant calling pipeline）" in text


def test_checked_in_source_directory_exposes_pangenome_script_request_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做pangenome分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "Sentieon Pangenome" in text
    assert "GRCh38" in text
    assert "【需要确认的信息】" in text


def test_checked_in_source_directory_exposes_panel_script_request_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做panel分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "DNAscope" in text
    assert "panel" in text.lower()
    assert "【需要确认的信息】" in text


def test_checked_in_source_directory_exposes_rna_script_request_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做rna分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "RNAseq" in text
    assert "Sentieon STAR" in text
    assert "【需要确认的信息】" in text


def test_checked_in_source_directory_exposes_tumor_normal_script_request_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做tumor-normal分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "TNseq" in text
    assert "TNscope" in text
    assert "tumor-normal" in text or "tumor normal" in text


def test_checked_in_source_directory_exposes_short_read_germline_script_request_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做短读长胚系分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "DNAscope" in text
    assert "DNAseq" in text
    assert "diploid" in text

def test_checked_in_source_directory_escalates_terse_example_followup_to_script_skeleton_for_short_read_germline_wgs():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "short-read germline WGS diploid organism 我就要个示例",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【参考命令】" in text
    assert "sentieon-cli dnascope" in text
    assert "【流程指导】" not in text


def test_checked_in_source_directory_exposes_hybrid_script_request_as_script_example():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"
    text = answer_reference_query(
        "我要做hybrid分析，能给个示例脚本吗",
        source_directory=str(source_directory),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【参考命令】" in text
    assert "sentieon-cli dnascope-hybrid" in text


def test_checked_in_source_directory_exposes_global_option_t_answer():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "sentieon-cli 的 -t 是什么",
        source_directory=str(source_directory),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【常用参数】" in text
    assert "-t" in text
    assert "线程" in text
    assert "【资料查询】" not in text
    assert "**" not in text
    assert "`" not in text


def test_checked_in_source_directory_exposes_global_option_r_answer():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "sentieon-cli 的 -r 是什么",
        source_directory=str(source_directory),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【常用参数】" in text
    assert "-r" in text
    assert "参考" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_gene_edit_intro_as_release_note_only():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "GeneEditEvaluator 是做什么的",
        source_directory=str(source_directory),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【模块介绍】" in text
    assert "GeneEditEvaluator" in text
    assert "当前本地官方资料仅见 release notes 级提及" in text
    assert "当前模块索引优先覆盖" not in text


def test_checked_in_source_directory_exposes_gene_edit_parameter_status():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "GeneEditEvaluator 的参数有哪些",
        source_directory=str(source_directory),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【常用参数】" in text
    assert "GeneEditEvaluator" in text
    assert "未提供可确定性索引的参数列表" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_gene_edit_script_status():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "能给个 GeneEditEvaluator 的参考脚本吗",
        source_directory=str(source_directory),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【参考命令】" in text
    assert "GeneEditEvaluator" in text
    assert "未提供可确定性复用的参考脚本或 CLI 骨架" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_vcf_external_guide_answer():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "VCF 的 INFO 和 FORMAT 有什么区别",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.88),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【资料说明】" in text
    assert "VCF/BCF" in text
    assert "INFO" in text
    assert "FORMAT" in text
    assert "【使用边界】" in text


def test_checked_in_source_directory_exposes_fastqc_external_guide_answer():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "FastQC 是做什么的",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.86),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【资料说明】" in text
    assert "FastQC" in text
    assert "质量控制" in text
    assert "【关联排查】" in text


def test_checked_in_source_directory_exposes_read_group_external_guide_answer():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "read group 是什么，为什么会影响 BAM",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.86),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【资料说明】" in text
    assert "Read Group" in text
    assert "@RG" in text
    assert "【关联排查】" in text


def test_checked_in_source_directory_exposes_bgzip_tabix_external_guide_answer():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "为什么 VCF 需要 bgzip 和 tabix",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.86),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【资料说明】" in text
    assert "bgzip/tabix" in text
    assert "VCF" in text
    assert "索引" in text


def test_checked_in_source_directory_exposes_shell_external_guide_answer():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "bash 的引号和管道怎么用",
        source_directory=str(source_directory),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【资料说明】" in text
    assert "shell quoting / pipeline basics" in text
    assert "单引号" in text
    assert "管道" in text


def test_checked_in_source_directory_exposes_vcf_index_error_association():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "普通 gzip 的 VCF 为什么 tabix 建不了索引",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.9),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "bgzip/tabix" in text
    assert "普通 gzip" in text
    assert "【优先检查】" in text


def test_checked_in_source_directory_exposes_shell_error_association():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "bash 报 unexpected EOF while looking for matching quote",
        source_directory=str(source_directory),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "shell 引号、变量展开、转义或管道连接写错" in text
    assert "【优先检查】" in text


def test_checked_in_source_directory_exposes_read_group_error_association():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "BAM 报错说 read group 不一致怎么办",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.9),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "Read Group" in text
    assert "@RG" in text
    assert "【优先检查】" in text


def test_checked_in_source_directory_exposes_cram_reference_error_association():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "CRAM 解码时报 reference mismatch 怎么看",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.9),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "FASTA/FAI" in text
    assert "CRAM" in text
    assert "【关联资料】" in text


def test_checked_in_source_directory_exposes_contig_naming_error_association():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "VCF 报 contig not found 是什么情况",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.91),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "contig" in text.lower()
    assert "命名" in text or "dictionary" in text.lower()
    assert "【优先检查】" in text


def test_checked_in_source_directory_exposes_sequence_dictionary_error_association():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "sequence dictionary mismatch 报错怎么办",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.91),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "dictionary" in text.lower()
    assert "【优先检查】" in text


def test_checked_in_source_directory_exposes_bed_coordinate_error_association():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "BED 区间总是差一位是为什么",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.91),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "BED" in text
    assert "坐标" in text
    assert "【优先检查】" in text


def test_checked_in_source_directory_exposes_reference_companion_file_error_association():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "reference FASTA 的 fai 和 dict 对不上怎么办",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.91),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "FASTA/FAI" in text
    assert "dict" in text.lower()
    assert "【优先检查】" in text


def test_checked_in_source_directory_exposes_cram_crai_random_access_error_association():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "CRAM 没有 crai 不能随机访问怎么办",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.91),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "CRAM" in text
    assert "crai" in text.lower()
    assert "随机访问" in text
    assert "【优先检查】" in text


def test_checked_in_source_directory_exposes_bam_sort_index_error_association():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "BAM 不能随机访问，是不是没排序或者没索引",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.91),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【关联判断】" in text
    assert "BAM" in text
    assert "排序" in text
    assert "索引" in text
    assert "【优先检查】" in text


def test_checked_in_source_directory_keeps_bam_format_explanation_on_external_guide_path():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "BAM 是什么格式",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="reference_other", confidence=0.88),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【资料说明】" in text
    assert "SAM/BAM/CRAM" in text
    assert "【关联判断】" not in text


def test_answer_reference_query_prefers_module_answer_over_generic_external_guide_when_module_is_explicit(tmp_path):
    from sentieon_assist.reference_intents import ReferenceIntent

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
              "sources": []
            }
          ]
        }
        """.strip()
    )
    (tmp_path / "external-format-guides.json").write_text(
        """
        {
          "entries": [
            {
              "name": "Read Group",
              "aliases": ["read group", "@rg"],
              "summary": "Read Group 通常通过 @RG header 行和记录里的 RG:Z tag 关联。",
              "details": ["常见字段包括 ID、SM、LB、PL。"]
            }
          ]
        }
        """.strip()
    )

    text = answer_reference_query(
        "DNAscope 的 read group 有什么要求",
        source_directory=str(tmp_path),
        parsed_intent=ReferenceIntent(intent="reference_other", module="DNAscope", confidence=0.91),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【模块介绍】" in text
    assert "DNAscope：DNAscope 是短读长胚系主流程。" in text
    assert "Read Group：" not in text


def test_checked_in_source_directory_prompts_for_specific_dnascope_parameter_on_deictic_followup():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "介绍下 dnascope 这个参数呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="parameter_lookup", module="DNAscope", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【常用参数】" in text
    assert "DNAscope" in text
    assert "还没给出具体参数名" in text
    assert "--pcr_free" in text
    assert "--duplicate_marking" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_prompts_for_specific_sentieon_cli_parameter_on_deictic_followup():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "介绍下 sentieon-cli 这个参数呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="parameter_lookup", module="sentieon-cli", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【常用参数】" in text
    assert "sentieon-cli" in text
    assert "还没给出具体参数名" in text
    assert "-t" in text
    assert "-r" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_germline_wgs_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wgs分析，能给个示例脚本吗 那胚系呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是胚系 WGS 的流程分流问题" in text
    assert "短读长胚系" in text
    assert "长读长胚系" in text
    assert "体细胞 WGS" not in text


def test_checked_in_source_directory_exposes_short_read_wgs_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wgs分析，能给个示例脚本吗 那 short-read 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是短读长 WGS 的流程分流问题" in text
    assert "DNAscope" in text
    assert "TNseq" in text
    assert "长读长 WGS" not in text
    assert "Sentieon Pangenome" not in text


def test_checked_in_source_directory_exposes_short_read_wes_panel_fragment_followup_for_wes():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wes分析，能给个示例脚本吗 那 short-read 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是短读长 WES 的流程分流问题" in text
    assert "DNAscope" in text
    assert "TNscope" in text
    assert "长读长" not in text


def test_checked_in_source_directory_exposes_short_read_wes_panel_fragment_followup_for_panel():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做panel分析，能给个示例脚本吗 那 short-read 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是短读长 panel 的流程分流问题" in text
    assert "DNAscope" in text
    assert "TNscope" in text
    assert "长读长" not in text


def test_checked_in_source_directory_exposes_hybrid_followup_under_wgs_context_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wgs分析，能给个示例脚本吗 那 hybrid 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "hybrid" in text.lower()
    assert "DNAscope Hybrid" in text
    assert "【参考命令】" not in text


def test_checked_in_source_directory_exposes_hybrid_followup_under_long_read_context_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做long-read分析，能给个示例脚本吗 那 hybrid 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "hybrid" in text.lower()
    assert "DNAscope Hybrid" in text
    assert "【参考命令】" not in text


def test_checked_in_source_directory_exposes_tumor_normal_wgs_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wgs分析，能给个示例脚本吗 那 tumor-normal 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是有配对正常样本（matched normal）的体细胞 WGS 流程分流问题" in text
    assert "TNseq" in text
    assert "TNscope" in text
    assert "WGS、WES 还是 panel" not in text


def test_checked_in_source_directory_exposes_tumor_only_wgs_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wgs分析，能给个示例脚本吗 那 tumor-only 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是没有配对正常样本（matched normal）的体细胞 WGS 流程分流问题" in text
    assert "TNscope" in text
    assert "SV" in text
    assert "WGS、WES 还是 panel" not in text


def test_checked_in_source_directory_exposes_tumor_normal_wes_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wes分析，能给个示例脚本吗 那 tumor-normal 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是有配对正常样本（matched normal）的体细胞 WES 流程分流问题" in text
    assert "TNseq" in text
    assert "TNscope" in text
    assert "WGS、WES 还是 panel" not in text


def test_checked_in_source_directory_exposes_tumor_only_wes_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wes分析，能给个示例脚本吗 那 tumor-only 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是没有配对正常样本（matched normal）的体细胞 WES 流程分流问题" in text
    assert "TNscope" in text
    assert "SV" in text
    assert "WGS、WES 还是 panel" not in text


def test_checked_in_source_directory_exposes_tumor_normal_panel_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做panel分析，能给个示例脚本吗 那 tumor-normal 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是有配对正常样本（matched normal）的体细胞 panel 流程分流问题" in text
    assert "TNseq" in text
    assert "TNscope" in text
    assert "WGS、WES 还是 panel" not in text


def test_checked_in_source_directory_exposes_tumor_only_panel_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做panel分析，能给个示例脚本吗 那 tumor-only 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是没有配对正常样本（matched normal）的体细胞 panel 流程分流问题" in text
    assert "TNscope" in text
    assert "SV" in text
    assert "WGS、WES 还是 panel" not in text


def test_checked_in_source_directory_exposes_semantic_fragment_followup_for_somatic_wes_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wes分析，能给个示例脚本吗 那 somatic 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是体细胞 WES 的流程分流问题" in text
    assert "TNseq" in text
    assert "TNscope" in text
    assert "matched normal" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_semantic_fragment_followup_for_somatic_panel_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做panel分析，能给个示例脚本吗 那 somatic 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是体细胞 panel 的流程分流问题" in text
    assert "TNscope" in text
    assert "TNseq" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_semantic_fragment_followup_for_germline_panel_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做panel分析，能给个示例脚本吗 那 germline 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "这是胚系 panel 的流程分流问题" in text
    assert "DNAscope" in text
    assert "TNscope" not in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_wgs_fastq_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wgs分析，能给个示例脚本吗 那 FASTQ 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "WGS" in text
    assert "FASTQ" in text
    assert "uBAM/uCRAM" not in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_wgs_bam_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wgs分析，能给个示例脚本吗 那 BAM 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "WGS" in text
    assert "BAM/CRAM" in text
    assert "已对齐" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_wes_fastq_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做wes分析，能给个示例脚本吗 那 FASTQ 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "WES" in text
    assert "FASTQ" in text
    assert "target intervals" in text or "assay" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_panel_bam_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做panel分析，能给个示例脚本吗 那 BAM 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "panel" in text.lower()
    assert "BAM/CRAM" in text
    assert "capture" in text or "target intervals" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_long_read_ont_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做long-read分析，能给个示例脚本吗 那 ONT 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "ONT" in text
    assert "long-read" in text or "长读长" in text
    assert "如果你明确是 ONT 数据" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_exposes_long_read_hifi_fragment_followup_as_workflow_guidance():
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    text = answer_reference_query(
        "我要做long-read分析，能给个示例脚本吗 那 HiFi 呢",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
        model_fallback=lambda *args: (_ for _ in ()).throw(AssertionError("should not fall back to model")),
    )

    assert "【流程指导】" in text
    assert "HiFi" in text
    assert "long-read" in text or "长读长" in text
    assert "如果你明确是 PacBio HiFi 数据" in text
    assert "【资料查询】" not in text


def test_checked_in_source_directory_does_not_collapse_alignmentstat_into_alignment_family(monkeypatch):
    from sentieon_assist.reference_intents import ReferenceIntent

    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    monkeypatch.setattr(
        "sentieon_assist.answering.generate_reference_fallback",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not fall back to generic reference synthesis")),
    )

    text = answer_reference_query(
        "介绍下AlignmentStat",
        source_directory=str(source_directory),
        parsed_intent=ReferenceIntent(intent="module_intro", module="AlignmentStat", confidence=0.91),
    )

    assert "Alignment：" not in text
    assert "AlignmentStat" in text
