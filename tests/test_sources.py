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
        "thread-019d5249-summary.md",
        "sentieon-chinese-reference.md",
    ]
    assert sources[0]["trust"] == "official"
    assert sources[1]["trust"] == "derived"
    assert sources[3]["trust"] == "secondary"


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
