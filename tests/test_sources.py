from sentieon_assist.sources import (
    collect_source_bundle_metadata,
    collect_source_evidence,
    extract_source_text,
    list_sources,
    search_sources,
)


def test_list_sources_reads_pdf_and_markdown(tmp_path):
    (tmp_path / "guide.pdf").write_text("fake")
    (tmp_path / "notes.md").write_text("# notes")

    sources = list_sources(tmp_path)

    names = {item["name"] for item in sources}
    types = {item["type"] for item in sources}
    assert "guide.pdf" in names
    assert "notes.md" in names
    assert "pdf" in types
    assert "markdown" in types


def test_list_sources_prefers_official_and_curated_files(tmp_path):
    (tmp_path / "sentieon-chinese-reference.md").write_text("secondary")
    (tmp_path / "thread-019d5249-summary.md").write_text("derived")
    (tmp_path / "sentieon-doc-map.md").write_text("curated official")
    (tmp_path / "Sentieon202503.03.pdf").write_text("official")

    sources = list_sources(tmp_path)

    assert [item["name"] for item in sources] == [
        "Sentieon202503.03.pdf",
        "sentieon-doc-map.md",
        "sentieon-chinese-reference.md",
        "thread-019d5249-summary.md",
    ]
    assert sources[0]["trust"] == "official"
    assert sources[1]["trust"] == "derived"
    assert sources[2]["trust"] == "secondary"
    assert sources[3]["trust"] == "derived"


def test_extract_source_text_reads_markdown(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("SENTIEON_LICENSE is required")
    assert "SENTIEON_LICENSE" in extract_source_text(path)


def test_extract_source_text_uses_pdftotext_for_pdf(monkeypatch, tmp_path):
    path = tmp_path / "guide.pdf"
    path.write_text("fake")

    class Result:
        stdout = "PDF CONTENT"

    def fake_run(cmd, capture_output, text, check):
        assert cmd == ["pdftotext", str(path), "-"]
        assert capture_output is True
        assert text is True
        assert check is True
        return Result()

    monkeypatch.setattr("sentieon_assist.sources.subprocess.run", fake_run)
    assert extract_source_text(path) == "PDF CONTENT"


def test_search_sources_returns_matching_snippets(tmp_path):
    (tmp_path / "notes.md").write_text("prefix SENTIEON_LICENSE suffix")
    matches = search_sources(tmp_path, "SENTIEON_LICENSE")
    assert matches
    assert matches[0]["name"] == "notes.md"
    assert "SENTIEON_LICENSE" in matches[0]["snippet"]
    assert matches[0]["trust"] == "other"


def test_collect_source_evidence_aggregates_multiple_terms(tmp_path):
    (tmp_path / "notes.md").write_text("Sentieon 202503 requires SENTIEON_LICENSE")
    evidence = collect_source_evidence(
        tmp_path,
        issue_type="license",
        query="Sentieon 202503 license 报错",
        info={
            "version": "202503",
            "input_type": "",
            "error": "license 报错",
            "error_keywords": "license",
            "step": "",
            "data_type": "",
        },
    )
    assert evidence
    assert evidence[0]["name"] == "notes.md"


def test_collect_source_evidence_prefers_official_over_secondary(monkeypatch, tmp_path):
    (tmp_path / "sentieon-chinese-reference.md").write_text("SENTIEON_LICENSE should be set")
    (tmp_path / "Sentieon202503.03.pdf").write_text("SENTIEON_LICENSE should be set")
    monkeypatch.setattr("sentieon_assist.sources.extract_source_text", lambda path: "SENTIEON_LICENSE should be set")

    evidence = collect_source_evidence(
        tmp_path,
        issue_type="license",
        query="SENTIEON_LICENSE",
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "SENTIEON_LICENSE",
            "step": "",
            "data_type": "",
        },
    )

    assert evidence[0]["name"] == "Sentieon202503.03.pdf"
    assert evidence[0]["trust"] == "official"


def test_collect_source_bundle_metadata_reads_primary_release_and_date(tmp_path):
    (tmp_path / "Sentieon202503.03.pdf").write_text("official")
    (tmp_path / "README.md").write_text(
        "本地 PDF 文件名是 `Sentieon202503.03.pdf`\n"
        "PDF 日期显示为 `Mar 30, 2026`\n"
    )

    metadata = collect_source_bundle_metadata(tmp_path)

    assert metadata["primary_release"] == "202503.03"
    assert metadata["primary_date"] == "Mar 30, 2026"
    assert metadata["primary_reference"] == "Sentieon202503.03.pdf"


def test_collect_source_evidence_matches_mixed_language_reference_query_without_spaces(tmp_path):
    (tmp_path / "notes.md").write_text(
        "Sentieon DNAscope is a pipeline for alignment and germline variant calling."
    )

    evidence = collect_source_evidence(
        tmp_path,
        issue_type="reference",
        query="dnascope是什么",
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )

    assert evidence
    assert evidence[0]["name"] == "notes.md"
    assert "DNAscope" in evidence[0]["snippet"]


def test_collect_source_evidence_does_not_match_generic_reference_term(tmp_path):
    (tmp_path / "noise.md").write_text("This section only discusses generic reference materials.")
    (tmp_path / "notes.md").write_text(
        "Sentieon DNAscope is a pipeline for alignment and germline variant calling."
    )

    evidence = collect_source_evidence(
        tmp_path,
        issue_type="reference",
        query="dnascope是什么",
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )

    assert evidence
    assert all(item["name"] != "noise.md" for item in evidence)


def test_search_sources_prefers_definition_snippet_over_contents_snippet(tmp_path):
    (tmp_path / "notes.md").write_text(
        "Contents\n"
        "DNAscope .... 19\n"
        "\n"
        "Typical usage for DNAscope\n"
        "DNAscope is a pipeline for alignment and germline variant calling from short-read DNA sequence data.\n"
    )

    matches = search_sources(tmp_path, "DNAscope")

    assert matches
    assert matches[0]["name"] == "notes.md"
    assert "pipeline for alignment and germline variant calling" in matches[0]["snippet"]


def test_search_sources_prefers_exact_definition_statement(tmp_path):
    (tmp_path / "notes.md").write_text(
        "Quick start pipeline summary. Variant calling: DNAscope variant calling.\n"
        "Detailed module intro. DNAscope is a pipeline for alignment and germline variant calling from short-read DNA sequence data.\n"
    )

    matches = search_sources(tmp_path, "DNAscope")

    assert matches
    assert matches[0]["name"] == "notes.md"
    assert "DNAscope is a pipeline for alignment and germline variant calling" in matches[0]["snippet"]


def test_search_sources_prefers_curated_reference_index_over_generic_pdf(monkeypatch, tmp_path):
    pdf_path = tmp_path / "Sentieon202503.03.pdf"
    pdf_path.write_text("fake")
    module_path = tmp_path / "sentieon-modules.json"
    module_path.write_text("fake")

    def fake_extract_source_text(path):
        name = path.name if hasattr(path, "name") else str(path)
        if str(name).endswith("sentieon-modules.json"):
            return '{"entries":[{"name":"DNAscope","summary":"DNAscope 是短读长胚系主流程。"}]}'
        return "Reference manual. DNAscope mentioned in a long generic chapter."

    monkeypatch.setattr("sentieon_assist.sources.extract_source_text", fake_extract_source_text)

    matches = search_sources(tmp_path, "DNAscope")

    assert matches
    assert matches[0]["name"] == "sentieon-modules.json"


def test_collect_source_evidence_includes_external_guides_for_external_format_query(tmp_path):
    (tmp_path / "external-format-guides.json").write_text(
        """
        {
          "entries": [
            {
              "name": "VCF/BCF",
              "summary": "VCF/BCF 是变异记录格式。",
              "details": ["INFO 是位点级字段。", "FORMAT 是样本级字段。"]
            }
          ]
        }
        """.strip()
    )
    (tmp_path / "notes.md").write_text("Generic local note.")

    evidence = collect_source_evidence(
        tmp_path,
        issue_type="reference",
        query="VCF 的 INFO 和 FORMAT 有什么区别",
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )

    assert evidence
    assert evidence[0]["name"] == "external-format-guides.json"


def test_collect_source_evidence_includes_external_error_associations_for_external_error_query(tmp_path):
    (tmp_path / "external-format-guides.json").write_text(
        """
        {
          "entries": [
            {
              "name": "VCF/BCF",
              "summary": "VCF/BCF 是变异记录格式。",
              "details": ["VCF 头里会声明 contig 和样本列。"]
            }
          ]
        }
        """.strip()
    )
    (tmp_path / "external-error-associations.json").write_text(
        """
        {
          "entries": [
            {
              "name": "Contig naming / sequence dictionary mismatch",
              "summary": "这更像是 contig 命名或 dictionary 不一致的问题。"
            }
          ]
        }
        """.strip()
    )

    evidence = collect_source_evidence(
        tmp_path,
        issue_type="reference",
        query="VCF 报 contig not found 是什么情况",
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )

    assert evidence
    assert any(item["name"] == "external-error-associations.json" for item in evidence)


def test_collect_source_evidence_includes_external_error_associations_for_sequence_dictionary_query(tmp_path):
    (tmp_path / "external-error-associations.json").write_text(
        """
        {
          "entries": [
            {
              "name": "Contig naming / sequence dictionary mismatch",
              "summary": "这更像是 sequence dictionary 组织不一致的问题。"
            }
          ]
        }
        """.strip()
    )

    evidence = collect_source_evidence(
        tmp_path,
        issue_type="reference",
        query="sequence dictionary mismatch 报错怎么办",
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )

    assert evidence
    assert any(item["name"] == "external-error-associations.json" for item in evidence)


def test_collect_source_evidence_excludes_external_error_associations_for_external_explanatory_query(tmp_path):
    (tmp_path / "external-format-guides.json").write_text(
        """
        {
          "entries": [
            {
              "name": "VCF/BCF",
              "summary": "VCF/BCF 是变异记录格式。",
              "details": ["INFO 是位点级字段。", "FORMAT 是样本级字段。"]
            }
          ]
        }
        """.strip()
    )
    (tmp_path / "external-error-associations.json").write_text(
        """
        {
          "entries": [
            {
              "name": "VCF indexing / bgzip-tabix mismatch",
              "summary": "这更像是 VCF 索引和 bgzip/tabix 前提不满足的问题。"
            }
          ]
        }
        """.strip()
    )

    evidence = collect_source_evidence(
        tmp_path,
        issue_type="reference",
        query="VCF 的 INFO 和 FORMAT 有什么区别",
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )

    assert evidence
    assert all(item["name"] != "external-error-associations.json" for item in evidence)


def test_collect_source_evidence_excludes_external_guides_for_sentieon_module_query(tmp_path):
    (tmp_path / "external-format-guides.json").write_text(
        """
        {
          "entries": [
            {
              "name": "VCF/BCF",
              "summary": "VCF/BCF 是变异记录格式。",
              "details": ["INFO 是位点级字段。", "FORMAT 是样本级字段。"]
            }
          ]
        }
        """.strip()
    )
    (tmp_path / "notes.md").write_text("DNAscope is a pipeline for alignment and germline variant calling.")

    evidence = collect_source_evidence(
        tmp_path,
        issue_type="reference",
        query="DNAscope 是做什么的",
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )

    assert evidence
    assert all(item["name"] != "external-format-guides.json" for item in evidence)


def test_match_external_guide_entry_does_not_match_sam_inside_sample(tmp_path):
    from sentieon_assist.external_guides import match_external_guide_entry

    (tmp_path / "external-format-guides.json").write_text(
        """
        {
          "entries": [
            {
              "name": "SAM/BAM/CRAM",
              "aliases": ["sam", "bam", "cram"],
              "summary": "SAM 是文本对齐格式。"
            }
          ]
        }
        """.strip()
    )

    assert match_external_guide_entry("sample column 是什么", tmp_path) is None


def test_match_external_guide_entry_does_not_match_bare_format_without_vcf_context(tmp_path):
    from sentieon_assist.external_guides import match_external_guide_entry

    (tmp_path / "external-format-guides.json").write_text(
        """
        {
          "entries": [
            {
              "name": "VCF/BCF",
              "aliases": ["vcf", "info", "format"],
              "summary": "VCF/BCF 是变异记录格式。"
            }
          ]
        }
        """.strip()
    )

    assert match_external_guide_entry("format 是什么意思", tmp_path) is None


def test_collect_source_evidence_includes_external_guides_for_shell_query(tmp_path):
    (tmp_path / "external-tool-guides.json").write_text(
        """
        {
          "entries": [
            {
              "name": "shell quoting / pipeline basics",
              "summary": "Shell 里最常见的是引号和管道的解析问题。",
              "details": ["单引号适合保留字面量。", "管道会把前一个命令的标准输出接到后一个命令的标准输入。"]
            }
          ]
        }
        """.strip()
    )
    (tmp_path / "notes.md").write_text("Generic local note.")

    evidence = collect_source_evidence(
        tmp_path,
        issue_type="reference",
        query="shell 的引号和管道怎么用",
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )

    assert evidence
    assert any(item["name"] == "external-tool-guides.json" for item in evidence)


def test_collect_source_evidence_includes_external_error_associations_for_shell_error_query(tmp_path):
    (tmp_path / "external-error-associations.json").write_text(
        """
        {
          "entries": [
            {
              "name": "Shell quoting / pipeline syntax error",
              "summary": "这更像是 shell 引号、变量展开或管道语义写错的问题。"
            }
          ]
        }
        """.strip()
    )

    evidence = collect_source_evidence(
        tmp_path,
        issue_type="reference",
        query="shell 报 unexpected EOF while looking for matching quote",
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )

    assert evidence
    assert any(item["name"] == "external-error-associations.json" for item in evidence)
