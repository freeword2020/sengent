from __future__ import annotations

import json
from pathlib import Path

from sentieon_assist.cli import main


def _write_source_packs(source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "sentieon-modules.json",
        "workflow-guides.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
    ):
        (source_dir / name).write_text('{"version":"","entries":[]}\n', encoding="utf-8")


def _latest_build_dir(build_root: Path) -> Path:
    build_dirs = sorted(path for path in build_root.iterdir() if path.is_dir())
    assert build_dirs
    return build_dirs[-1]


def _write_activation_candidate_build(build_root: Path, build_id: str, *, module_id: str, module_name: str) -> Path:
    build_dir = build_root / build_id
    candidate_dir = build_dir / "candidate-packs"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    (candidate_dir / "sentieon-modules.json").write_text(
        json.dumps({"version": "", "entries": [{"id": module_id, "name": module_name}]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    for name in (
        "workflow-guides.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
    ):
        (candidate_dir / name).write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    (candidate_dir / "manifest.json").write_text('{"status":"candidate_only"}\n', encoding="utf-8")
    (build_dir / "pilot-readiness-report.json").write_text('{"ok": true}\n', encoding="utf-8")
    (build_dir / "pilot-closed-loop-report.json").write_text('{"ok": true}\n', encoding="utf-8")
    return build_dir


def test_knowledge_build_command_writes_artifacts_and_candidate_packs(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "release-note.md").write_text("# Release\n\nDNAscope supports PCR-free.\n", encoding="utf-8")
    (inbox_dir / "example.sh").write_text("sentieon-cli dnascope --help\n", encoding="utf-8")

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"
    outputs: list[str] = []

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=outputs.append,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    assert (build_dir / "inventory.json").exists()
    assert (build_dir / "canonical_doc_record.jsonl").exists()
    assert (build_dir / "canonical_section_record.jsonl").exists()
    assert (build_dir / "exceptions.jsonl").exists()
    assert (build_dir / "report.md").exists()
    assert (build_dir / "candidate-packs" / "sentieon-modules.json").exists()

    doc_records = [
        json.loads(line)
        for line in (build_dir / "canonical_doc_record.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(doc_records) == 2
    assert {record["file_type"] for record in doc_records} == {"markdown", "shell"}
    assert any("knowledge build completed" in item.lower() for item in outputs)


def test_knowledge_build_queues_pdf_when_docling_is_unavailable(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "datasheet.pdf").write_bytes(b"%PDF-1.4\n% fake pdf\n")
    (inbox_dir / "notes.md").write_text("# Notes\n\nCPU guidance\n", encoding="utf-8")

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    exceptions = [
        json.loads(line)
        for line in (build_dir / "exceptions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(item["exception_type"] == "parser_unavailable" for item in exceptions)
    assert any(item["path"].endswith("datasheet.pdf") for item in exceptions)
    report = (build_dir / "report.md").read_text(encoding="utf-8")
    assert "Docling available: no" in report
    assert "parser_unavailable" in report


def test_knowledge_build_queues_unsupported_files_without_crashing(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "table.csv").write_text("sample,depth\nNA12878,35\n", encoding="utf-8")

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    exceptions = [
        json.loads(line)
        for line in (build_dir / "exceptions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(item["exception_type"] == "unsupported_file" for item in exceptions)
    assert any(item["relative_path"] == "table.csv" for item in exceptions)


def test_knowledge_build_keeps_active_packs_unchanged_and_reports_gate_commands(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "release-note.md").write_text("# Release\n\nTNscope update\n", encoding="utf-8")

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    original_modules = (source_dir / "sentieon-modules.json").read_text(encoding="utf-8")
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    assert (source_dir / "sentieon-modules.json").read_text(encoding="utf-8") == original_modules
    build_dir = _latest_build_dir(build_root)
    report = (build_dir / "report.md").read_text(encoding="utf-8")
    assert "python scripts/pilot_readiness_eval.py --source-dir" in report
    assert "python scripts/pilot_closed_loop.py --source-dir" in report
    assert "candidate-packs" in report
    assert "candidate packs are not active runtime packs yet" in report


def test_knowledge_build_compiles_markdown_front_matter_into_candidate_packs(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "fastdedup.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: fastdedup\n"
        "name: FastDedup\n"
        "aliases:\n"
        "  - fastdedup\n"
        "  - fast dedup\n"
        "category: utility\n"
        "summary: Fast duplicate marking helper.\n"
        "scope:\n"
        "  - PCR-free\n"
        "related_modules:\n"
        "  - DNAscope\n"
        "---\n\n"
        "# FastDedup\n\n"
        "Used for accelerated duplicate marking notes.\n",
        encoding="utf-8",
    )
    (inbox_dir / "wes-qc.md").write_text(
        "---\n"
        "pack_target: workflow-guides.json\n"
        "entry_type: workflow\n"
        "id: wes-qc\n"
        "name: WES QC\n"
        "priority: 12\n"
        "summary: WES QC guidance.\n"
        "guidance:\n"
        "  - Check target interval coverage.\n"
        "follow_up:\n"
        "  - Do you already have interval BED files?\n"
        "---\n\n"
        "# WES QC\n\n"
        "Use this after alignment and duplicate marking.\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    modules_payload = json.loads((build_dir / "candidate-packs" / "sentieon-modules.json").read_text(encoding="utf-8"))
    workflow_payload = json.loads((build_dir / "candidate-packs" / "workflow-guides.json").read_text(encoding="utf-8"))

    compiled_module = next(entry for entry in modules_payload["entries"] if entry["id"] == "fastdedup")
    assert compiled_module["name"] == "FastDedup"
    assert compiled_module["summary"] == "Fast duplicate marking helper."
    assert compiled_module["sources"] == ["fastdedup.md"]

    compiled_workflow = next(entry for entry in workflow_payload["entries"] if entry["id"] == "wes-qc")
    assert compiled_workflow["name"] == "WES QC"
    assert compiled_workflow["guidance"] == ["Check target interval coverage."]
    assert compiled_workflow["sources"] == ["wes-qc.md"]


def test_knowledge_build_compiles_sidecar_metadata_without_editing_raw_doc(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "fastdedup.md").write_text(
        "# FastDedup\n\nUsed for accelerated duplicate marking notes.\n",
        encoding="utf-8",
    )
    (inbox_dir / "fastdedup.meta.yaml").write_text(
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: fastdedup\n"
        "name: FastDedup\n"
        "aliases:\n"
        "  - fastdedup\n"
        "category: utility\n"
        "summary: Sidecar-supplied summary.\n"
        "scope:\n"
        "  - PCR-free\n"
        "related_modules:\n"
        "  - DNAscope\n"
        "version: 202503.03\n"
        "date: 2026-04-09\n"
        "origin: notebooklm-export\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    modules_payload = json.loads((build_dir / "candidate-packs" / "sentieon-modules.json").read_text(encoding="utf-8"))
    compiled_module = next(entry for entry in modules_payload["entries"] if entry["id"] == "fastdedup")
    assert compiled_module["name"] == "FastDedup"
    assert compiled_module["summary"] == "Sidecar-supplied summary."

    doc_records = [
        json.loads(line)
        for line in (build_dir / "canonical_doc_record.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    doc_record = next(record for record in doc_records if record["relative_path"] == "fastdedup.md")
    assert doc_record["source_metadata"]["origin"] == "notebooklm-export"
    assert doc_record["metadata_missing"] == []


def test_knowledge_build_prefers_front_matter_over_sidecar_when_both_exist(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "fastdedup.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: fastdedup\n"
        "name: Front Matter Name\n"
        "---\n\n"
        "# FastDedup\n\n"
        "Used for accelerated duplicate marking notes.\n",
        encoding="utf-8",
    )
    (inbox_dir / "fastdedup.meta.yaml").write_text(
        "name: Sidecar Name\n"
        "summary: Sidecar summary.\n"
        "version: 202503.03\n"
        "date: 2026-04-09\n"
        "origin: notebooklm-export\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    modules_payload = json.loads((build_dir / "candidate-packs" / "sentieon-modules.json").read_text(encoding="utf-8"))
    compiled_module = next(entry for entry in modules_payload["entries"] if entry["id"] == "fastdedup")
    assert compiled_module["name"] == "Front Matter Name"
    assert compiled_module["summary"] == "Sidecar summary."


def test_knowledge_build_compiles_external_reference_candidate_packs(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "bgzip-tabix.md").write_text(
        "---\n"
        "pack_target: external-format-guides.json\n"
        "entry_type: external_format\n"
        "id: bgzip-tabix\n"
        "name: bgzip/tabix\n"
        "aliases:\n"
        "  - bgzip\n"
        "  - tabix\n"
        "summary: Generic bgzip and tabix guidance.\n"
        "details:\n"
        "  - Validate bgzip compression before indexing.\n"
        "troubleshooting:\n"
        "  - Rebuild the .tbi index after replacing the file.\n"
        "usage_boundary:\n"
        "  - This is format-layer guidance only.\n"
        "source_notes:\n"
        "  - notebooklm-export\n"
        "official_sources:\n"
        "  - https://example.com/bgzip\n"
        "---\n\n"
        "# bgzip/tabix\n\n"
        "Formatting notes.\n",
        encoding="utf-8",
    )
    (inbox_dir / "samtools.md").write_text(
        "---\n"
        "pack_target: external-tool-guides.json\n"
        "entry_type: external_tool\n"
        "id: samtools\n"
        "name: samtools\n"
        "aliases:\n"
        "  - samtools quickcheck\n"
        "summary: Generic samtools guidance.\n"
        "details:\n"
        "  - Use quickcheck to test BAM readability.\n"
        "troubleshooting:\n"
        "  - Re-run index after sorting.\n"
        "usage_boundary:\n"
        "  - This does not replace Sentieon module guidance.\n"
        "source_notes:\n"
        "  - notebooklm-export\n"
        "official_sources:\n"
        "  - https://example.com/samtools\n"
        "---\n\n"
        "# samtools\n\n"
        "Tool notes.\n",
        encoding="utf-8",
    )
    (inbox_dir / "license-errors.md").write_text(
        "---\n"
        "pack_target: external-error-associations.json\n"
        "entry_type: external_error\n"
        "id: license-connectivity\n"
        "name: License connectivity\n"
        "patterns_any:\n"
        "  - licclnt\n"
        "  - server\n"
        "require_any:\n"
        "  - failed\n"
        "summary: Generic license connectivity checks.\n"
        "checks:\n"
        "  - Confirm the license server is reachable.\n"
        "related_guides:\n"
        "  - FlexNet\n"
        "usage_boundary:\n"
        "  - This is environment-layer guidance only.\n"
        "source_notes:\n"
        "  - notebooklm-export\n"
        "---\n\n"
        "# License connectivity\n\n"
        "Error association notes.\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    format_payload = json.loads((build_dir / "candidate-packs" / "external-format-guides.json").read_text(encoding="utf-8"))
    tool_payload = json.loads((build_dir / "candidate-packs" / "external-tool-guides.json").read_text(encoding="utf-8"))
    error_payload = json.loads((build_dir / "candidate-packs" / "external-error-associations.json").read_text(encoding="utf-8"))

    compiled_format = next(entry for entry in format_payload["entries"] if entry["id"] == "bgzip-tabix")
    assert compiled_format["official_sources"] == ["https://example.com/bgzip"]
    compiled_tool = next(entry for entry in tool_payload["entries"] if entry["id"] == "samtools")
    assert compiled_tool["summary"] == "Generic samtools guidance."
    compiled_error = next(entry for entry in error_payload["entries"] if entry["id"] == "license-connectivity")
    assert compiled_error["checks"] == ["Confirm the license server is reachable."]


def test_knowledge_build_queues_duplicate_candidate_ids_as_exceptions(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    for name, title in (("fastdedup-a.md", "FastDedup A"), ("fastdedup-b.md", "FastDedup B")):
        (inbox_dir / name).write_text(
            "---\n"
            "pack_target: sentieon-modules.json\n"
            "entry_type: module\n"
            "id: fastdedup\n"
            f"name: {title}\n"
            "---\n\n"
            "# FastDedup\n\n"
            "Duplicate candidate.\n",
            encoding="utf-8",
        )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    exceptions = [
        json.loads(line)
        for line in (build_dir / "exceptions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(item["exception_type"] == "duplicate_candidate" for item in exceptions)
    modules_payload = json.loads((build_dir / "candidate-packs" / "sentieon-modules.json").read_text(encoding="utf-8"))
    matching_entries = [entry for entry in modules_payload["entries"] if entry["id"] == "fastdedup"]
    assert len(matching_entries) == 1


def test_knowledge_build_manifest_records_added_and_updated_candidate_ids(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "fastdedup.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: fastdedup\n"
        "name: FastDedup\n"
        "---\n\n"
        "# FastDedup\n\n"
        "Updated module notes.\n",
        encoding="utf-8",
    )
    (inbox_dir / "wes-qc.md").write_text(
        "---\n"
        "pack_target: workflow-guides.json\n"
        "entry_type: workflow\n"
        "id: wes-qc\n"
        "name: WES QC\n"
        "guidance:\n"
        "  - Check target interval coverage.\n"
        "---\n\n"
        "# WES QC\n\n"
        "New workflow notes.\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "sentieon-modules.json").write_text(
        json.dumps({"version": "", "entries": [{"id": "fastdedup", "name": "Old FastDedup"}]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (source_dir / "workflow-guides.json").write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    (source_dir / "external-format-guides.json").write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    (source_dir / "external-tool-guides.json").write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    (source_dir / "external-error-associations.json").write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    manifest = json.loads((build_dir / "candidate-packs" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["pack_diffs"]["sentieon-modules.json"]["updated_ids"] == ["fastdedup"]
    assert manifest["pack_diffs"]["workflow-guides.json"]["added_ids"] == ["wes-qc"]
    assert manifest["pack_diffs"]["external-tool-guides.json"]["unchanged"] is True


def test_knowledge_build_report_surfaces_metadata_gaps_and_changed_ids(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "fastdedup.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: fastdedup\n"
        "name: FastDedup\n"
        "---\n\n"
        "# FastDedup\n\n"
        "Updated module notes.\n",
        encoding="utf-8",
    )
    (inbox_dir / "notes.md").write_text("# Notes\n\nMissing metadata on purpose.\n", encoding="utf-8")

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    report = (build_dir / "report.md").read_text(encoding="utf-8")
    assert "Metadata gaps" in report
    assert "notes.md" in report
    assert "Changed candidate packs" in report
    assert "sentieon-modules.json" in report
    assert "fastdedup" in report


def test_knowledge_build_writes_script_and_parameter_candidate_artifacts(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "dnascope.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: dnascope\n"
        "name: DNAscope\n"
        "summary: Germline variant calling.\n"
        "---\n\n"
        "# DNAscope\n\n"
        "```bash\n"
        "sentieon-cli dnascope -r ref.fa --pcr_free -t 16 -d dbsnp.vcf out.vcf\n"
        "```\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    assert (build_dir / "script_candidate_record.jsonl").exists()
    assert (build_dir / "parameter_candidate_record.jsonl").exists()

    script_candidates = [
        json.loads(line)
        for line in (build_dir / "script_candidate_record.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    parameter_candidates = [
        json.loads(line)
        for line in (build_dir / "parameter_candidate_record.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(script_candidates) == 1
    assert script_candidates[0]["module_hint"] == "dnascope"
    assert script_candidates[0]["confidence"] == "high"
    assert "sentieon-cli dnascope" in script_candidates[0]["command_lines"][0]
    assert {item["parameter_name"] for item in parameter_candidates} >= {"-r", "--pcr_free", "-t", "-d"}


def test_knowledge_build_extracts_script_candidates_from_shell_files(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "joint-call.sh").write_text(
        "sentieon driver -r ref.fa --algo GVCFtyper -t 16 cohort.g.vcf.gz out.vcf.gz\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    script_candidates = [
        json.loads(line)
        for line in (build_dir / "script_candidate_record.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(script_candidates) == 1
    assert script_candidates[0]["relative_path"] == "joint-call.sh"
    assert script_candidates[0]["module_hint"] == "gvcftyper"
    assert script_candidates[0]["source_kind"] == "shell_file"


def test_knowledge_build_deduplicates_parameter_candidates_within_a_script(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "dnascope.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: dnascope\n"
        "name: DNAscope\n"
        "---\n\n"
        "```bash\n"
        "sentieon-cli dnascope -r ref.fa -r ref.fa --pcr_free --pcr_free -t 16 out.vcf\n"
        "```\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    parameter_candidates = [
        json.loads(line)
        for line in (build_dir / "parameter_candidate_record.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    names = [item["parameter_name"] for item in parameter_candidates]
    assert names.count("-r") == 1
    assert names.count("--pcr_free") == 1


def test_knowledge_build_enriches_module_candidate_with_extracted_script_example(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "dnascope.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: dnascope\n"
        "name: DNAscope\n"
        "summary: Germline variant calling.\n"
        "---\n\n"
        "# DNAscope\n\n"
        "```bash\n"
        "sentieon-cli dnascope -r ref.fa --pcr_free -t 16 out.vcf\n"
        "```\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    modules_payload = json.loads((build_dir / "candidate-packs" / "sentieon-modules.json").read_text(encoding="utf-8"))
    compiled_module = next(entry for entry in modules_payload["entries"] if entry["id"] == "dnascope")
    assert compiled_module["script_examples"][0]["command_lines"][0].startswith("sentieon-cli dnascope")


def test_knowledge_build_reports_extraction_ambiguity_and_keeps_low_confidence_out_of_candidate_pack(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "ambiguous.md").write_text(
        "# Ambiguous\n\n"
        "```bash\n"
        "sentieon-cli dnascope -r ref.fa out.vcf\n"
        "sentieon-cli tnscope -r ref.fa tumor.bam out.vcf\n"
        "```\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    script_candidates = [
        json.loads(line)
        for line in (build_dir / "script_candidate_record.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert script_candidates[0]["confidence"] == "low"
    assert script_candidates[0]["module_hint"] is None

    exceptions = [
        json.loads(line)
        for line in (build_dir / "exceptions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(item["exception_type"] == "extraction_ambiguity" for item in exceptions)

    report = (build_dir / "report.md").read_text(encoding="utf-8")
    assert "Extraction ambiguities" in report
    assert "ambiguous.md" in report


def test_knowledge_build_compiles_structured_module_parameters_from_front_matter(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "dnascope-params.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: dnascope\n"
        "name: DNAscope\n"
        "summary: Germline variant calling.\n"
        "parameters:\n"
        "  - name: --pcr_free\n"
        "    aliases:\n"
        "      - pcr_free\n"
        "    summary: PCR-free library mode.\n"
        "    details:\n"
        "      - Use for PCR-free libraries.\n"
        "    values: []\n"
        "  - name: --assay\n"
        "    aliases:\n"
        "      - assay\n"
        "    summary: Metrics assay type.\n"
        "    details:\n"
        "      - Common values are WGS and WES.\n"
        "    values:\n"
        "      - WGS\n"
        "      - WES\n"
        "---\n\n"
        "# DNAscope parameters\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    modules_payload = json.loads((build_dir / "candidate-packs" / "sentieon-modules.json").read_text(encoding="utf-8"))
    compiled_module = next(entry for entry in modules_payload["entries"] if entry["id"] == "dnascope")
    assert compiled_module["parameters"] == [
        {
            "name": "--pcr_free",
            "aliases": ["pcr_free"],
            "summary": "PCR-free library mode.",
            "details": ["Use for PCR-free libraries."],
            "values": [],
        },
        {
            "name": "--assay",
            "aliases": ["assay"],
            "summary": "Metrics assay type.",
            "details": ["Common values are WGS and WES."],
            "values": ["WGS", "WES"],
        },
    ]


def test_knowledge_build_compiles_structured_module_parameters_from_sidecar_metadata(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "dnascope-params.md").write_text("# DNAscope\n", encoding="utf-8")
    (inbox_dir / "dnascope-params.meta.yaml").write_text(
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: dnascope\n"
        "name: DNAscope\n"
        "summary: Germline variant calling.\n"
        "parameters:\n"
        "  - name: --pcr_free\n"
        "    aliases:\n"
        "      - pcr_free\n"
        "    summary: PCR-free library mode.\n"
        "    details:\n"
        "      - Use for PCR-free libraries.\n"
        "    values: []\n"
        "version: 202503.03\n"
        "date: 2026-04-10\n"
        "origin: notebooklm-export\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    modules_payload = json.loads((build_dir / "candidate-packs" / "sentieon-modules.json").read_text(encoding="utf-8"))
    compiled_module = next(entry for entry in modules_payload["entries"] if entry["id"] == "dnascope")
    assert compiled_module["parameters"][0]["name"] == "--pcr_free"
    assert compiled_module["parameters"][0]["summary"] == "PCR-free library mode."


def test_knowledge_build_queues_duplicate_parameter_definitions_as_exceptions(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "dnascope-params.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: dnascope\n"
        "name: DNAscope\n"
        "summary: Germline variant calling.\n"
        "parameters:\n"
        "  - name: --pcr_free\n"
        "    summary: First definition.\n"
        "  - name: --pcr_free\n"
        "    summary: Duplicate definition.\n"
        "---\n\n"
        "# DNAscope\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    exceptions = [
        json.loads(line)
        for line in (build_dir / "exceptions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(item["exception_type"] == "duplicate_parameter_definition" for item in exceptions)

    modules_payload = json.loads((build_dir / "candidate-packs" / "sentieon-modules.json").read_text(encoding="utf-8"))
    compiled_module = next(entry for entry in modules_payload["entries"] if entry["id"] == "dnascope")
    assert compiled_module["parameters"] == [
        {
            "name": "--pcr_free",
            "aliases": [],
            "summary": "First definition.",
            "details": [],
            "values": [],
        }
    ]


def test_knowledge_build_writes_parameter_promotion_review_and_report_sections(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "dnascope-params.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: dnascope\n"
        "name: DNAscope\n"
        "summary: Germline variant calling.\n"
        "parameters:\n"
        "  - name: --pcr_free\n"
        "    aliases:\n"
        "      - pcr_free\n"
        "    summary: PCR-free library mode.\n"
        "    details:\n"
        "      - Use for PCR-free libraries.\n"
        "---\n\n"
        "```bash\n"
        "sentieon-cli dnascope --pcr_free --dry_run out.vcf\n"
        "```\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    review_records = [
        json.loads(line)
        for line in (build_dir / "parameter_promotion_review.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(
        item["status"] == "promoted"
        and item["parameter_name"] == "--pcr_free"
        and item["evidence_status"] == "matched"
        for item in review_records
    )
    assert any(
        item["status"] == "candidate_only"
        and item["parameter_name"] == "--dry_run"
        and item["relative_path"] == "dnascope-params.md"
        for item in review_records
    )

    report = (build_dir / "report.md").read_text(encoding="utf-8")
    assert "Parameter promotion review" in report
    assert "Promoted parameters: 1" in report
    assert "Extracted but unpromoted parameters: 1" in report
    assert "dnascope-params.md" in report


def test_knowledge_build_excludes_low_confidence_parameter_candidates_from_promotion_review(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "ambiguous-params.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: dnascope\n"
        "name: DNAscope\n"
        "summary: Germline variant calling.\n"
        "parameters:\n"
        "  - name: --pcr_free\n"
        "    summary: PCR-free library mode.\n"
        "---\n\n"
        "```bash\n"
        "sentieon-cli dnascope --pcr_free out.vcf\n"
        "sentieon-cli tnscope --trim_soft_clip out.vcf\n"
        "```\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    review_records = [
        json.loads(line)
        for line in (build_dir / "parameter_promotion_review.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(item["status"] == "promoted" and item["parameter_name"] == "--pcr_free" for item in review_records)
    assert not any(item["status"] == "candidate_only" for item in review_records)


def test_knowledge_build_writes_parameter_review_suggestions_for_true_gaps(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "dnascope-gap.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: dnascope\n"
        "name: DNAscope\n"
        "summary: Germline variant calling.\n"
        "parameters:\n"
        "  - name: --pcr_free\n"
        "    summary: PCR-free library mode.\n"
        "---\n\n"
        "```bash\n"
        "sentieon-cli dnascope --pcr_free --dry_run out.vcf\n"
        "```\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    suggestion_records = [
        json.loads(line)
        for line in (build_dir / "parameter_review_suggestion.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert suggestion_records == [
        {
            "build_id": suggestion_records[0]["build_id"],
            "doc_id": suggestion_records[0]["doc_id"],
            "relative_path": "dnascope-gap.md",
            "module_id": "dnascope",
            "parameter_name": "--dry_run",
            "suggested_action": "add_structured_parameter_metadata",
            "template": {
                "name": "--dry_run",
                "aliases": [],
                "summary": "",
                "details": [],
                "values": [],
            },
            "detail": "High-confidence extracted parameter candidate is not yet covered by structured metadata.",
        }
    ]

    report = (build_dir / "report.md").read_text(encoding="utf-8")
    assert "Parameter review suggestions: 1" in report
    assert "parameter_review_suggestion.jsonl" in report


def test_knowledge_build_marks_shared_parameters_as_already_covered(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "dnascope-threads.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: dnascope\n"
        "name: DNAscope\n"
        "summary: Germline variant calling.\n"
        "---\n\n"
        "```bash\n"
        "sentieon-cli dnascope -t 16 out.vcf\n"
        "```\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    (source_dir / "sentieon-modules.json").write_text(
        json.dumps(
            {
                "version": "",
                "entries": [
                    {
                        "id": "sentieon-cli",
                        "name": "sentieon-cli",
                        "parameters": [
                            {
                                "name": "-t",
                                "aliases": ["threads"],
                                "summary": "Thread count.",
                                "details": [],
                                "values": [],
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    review_records = [
        json.loads(line)
        for line in (build_dir / "parameter_promotion_review.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(
        item["parameter_name"] == "-t" and item["status"] == "covered_by_shared_module" for item in review_records
    )

    suggestion_records = [
        json.loads(line)
        for line in (build_dir / "parameter_review_suggestion.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert not suggestion_records

    report = (build_dir / "report.md").read_text(encoding="utf-8")
    assert "Covered by shared module: 1" in report


def test_knowledge_build_delete_action_removes_candidate_entry_and_reports_removed_ids(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "retire-fastdedup.md").write_text("# Retire FastDedup\n", encoding="utf-8")
    (inbox_dir / "retire-fastdedup.meta.yaml").write_text(
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: fastdedup\n"
        "action: delete\n"
        "date: 2026-04-10\n"
        "origin: manual-maintainer\n"
        "version: 202503.03\n",
        encoding="utf-8",
    )

    source_dir = tmp_path / "sentieon-note"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "sentieon-modules.json").write_text(
        json.dumps(
            {
                "version": "",
                "entries": [
                    {"id": "fastdedup", "name": "FastDedup"},
                    {"id": "dnascope", "name": "DNAscope"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    for name in (
        "workflow-guides.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
    ):
        (source_dir / name).write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    modules_payload = json.loads((build_dir / "candidate-packs" / "sentieon-modules.json").read_text(encoding="utf-8"))
    assert [entry["id"] for entry in modules_payload["entries"]] == ["dnascope"]

    manifest = json.loads((build_dir / "candidate-packs" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["pack_diffs"]["sentieon-modules.json"]["removed_ids"] == ["fastdedup"]

    report = (build_dir / "report.md").read_text(encoding="utf-8")
    assert "removed=fastdedup" in report


def test_knowledge_build_reports_compile_skips_for_docs_without_pack_metadata(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "freeform-note.md").write_text("# Freeform\n\nNo structured hints yet.\n", encoding="utf-8")

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    report = (build_dir / "report.md").read_text(encoding="utf-8")
    assert "Compile skips" in report
    assert "freeform-note.md" in report


def test_knowledge_activate_keeps_only_latest_three_backups(tmp_path: Path):
    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    (source_dir / "sentieon-modules.json").write_text(
        json.dumps({"version": "", "entries": [{"id": "module-0", "name": "Module 0"}]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    build_root = tmp_path / "runtime" / "knowledge-build"

    for index in range(1, 5):
        _write_activation_candidate_build(
            build_root,
            f"build-{index}",
            module_id=f"module-{index}",
            module_name=f"Module {index}",
        )
        code = main(
            [
                "--source-dir",
                str(source_dir),
                "knowledge",
                "activate",
                "--build-root",
                str(build_root),
                "--build-id",
                f"build-{index}",
            ],
            output_fn=lambda _message: None,
        )
        assert code == 0

    backup_root = build_root / "activation-backups"
    backup_dirs = sorted(path for path in backup_root.iterdir() if path.is_dir())
    assert len(backup_dirs) == 3
    backed_up_module_ids = []
    for backup_dir in backup_dirs:
        payload = json.loads((backup_dir / "sentieon-modules.json").read_text(encoding="utf-8"))
        backed_up_module_ids.append(payload["entries"][0]["id"])
    assert backed_up_module_ids == ["module-1", "module-2", "module-3"]


def test_knowledge_rollback_exactly_restores_managed_pack_set(tmp_path: Path):
    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    (source_dir / "sentieon-modules.json").write_text(
        json.dumps({"version": "", "entries": [{"id": "baseline", "name": "Baseline"}]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_dir = _write_activation_candidate_build(
        build_root,
        "build-restore",
        module_id="fastdedup",
        module_name="FastDedup",
    )

    assert (
        main(
            [
                "--source-dir",
                str(source_dir),
                "knowledge",
                "activate",
                "--build-root",
                str(build_root),
                "--build-id",
                "build-restore",
            ],
            output_fn=lambda _message: None,
        )
        == 0
    )
    backup_id = json.loads((build_dir / "activation-manifest.json").read_text(encoding="utf-8"))["backup_id"]

    assert (
        main(
            [
                "--source-dir",
                str(source_dir),
                "knowledge",
                "rollback",
                "--build-root",
                str(build_root),
                "--backup-id",
                backup_id,
            ],
            output_fn=lambda _message: None,
        )
        == 0
    )

    managed_files = sorted(path.name for path in source_dir.glob("*.json"))
    assert managed_files == [
        "external-error-associations.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "sentieon-modules.json",
        "workflow-guides.json",
    ]
    restored_modules = json.loads((source_dir / "sentieon-modules.json").read_text(encoding="utf-8"))
    assert restored_modules["entries"][0]["id"] == "baseline"


def test_knowledge_build_queues_malformed_front_matter_instead_of_crashing(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "broken-front-matter.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: [module\n"
        "---\n\n"
        "# Broken\n",
        encoding="utf-8",
    )
    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    exceptions = [
        json.loads(line)
        for line in (build_dir / "exceptions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(item["exception_type"] == "document_parse_error" for item in exceptions)
    assert any(item["relative_path"] == "broken-front-matter.md" for item in exceptions)


def test_knowledge_build_queues_malformed_sidecar_metadata_instead_of_crashing(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "fastdedup.md").write_text("# FastDedup\n", encoding="utf-8")
    (inbox_dir / "fastdedup.meta.yaml").write_text("pack_target: [sentieon-modules.json\n", encoding="utf-8")
    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    build_dir = _latest_build_dir(build_root)
    exceptions = [
        json.loads(line)
        for line in (build_dir / "exceptions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert any(item["exception_type"] == "sidecar_metadata_error" for item in exceptions)
    assert any(item["relative_path"] == "fastdedup.md" for item in exceptions)


def test_knowledge_rollback_rejects_unknown_backup_id_without_changing_active_packs(tmp_path: Path):
    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    (source_dir / "sentieon-modules.json").write_text(
        json.dumps({"version": "", "entries": [{"id": "baseline", "name": "Baseline"}]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    build_root = tmp_path / "runtime" / "knowledge-build"
    original_modules = (source_dir / "sentieon-modules.json").read_text(encoding="utf-8")
    outputs: list[str] = []

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "rollback",
            "--build-root",
            str(build_root),
            "--backup-id",
            "missing-backup",
        ],
        output_fn=outputs.append,
    )

    assert code == 2
    assert (source_dir / "sentieon-modules.json").read_text(encoding="utf-8") == original_modules
    assert any("backup" in item.lower() for item in outputs)


def test_knowledge_build_rejects_incomplete_active_source_pack_set(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "release-note.md").write_text("# Release\n\nTNscope update\n", encoding="utf-8")

    source_dir = tmp_path / "sentieon-note"
    _write_source_packs(source_dir)
    (source_dir / "external-tool-guides.json").unlink()
    build_root = tmp_path / "runtime" / "knowledge-build"
    outputs: list[str] = []

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=outputs.append,
    )

    assert code == 2
    assert not build_root.exists()
    assert any("external-tool-guides.json" in item for item in outputs)
