from types import SimpleNamespace

from sentieon_assist.doctor import format_doctor_report, gather_doctor_report
from sentieon_assist.kernel.pack_contract import PackManifestEntry


def test_gather_doctor_report_uses_effective_directories(tmp_path):
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "license.json").write_text("[]")

    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "Sentieon202503.03.pdf").write_text("official")
    (source_dir / "README.md").write_text("PDF 日期显示为 `Mar 30, 2026`")
    (source_dir / "guide.md").write_text("SENTIEON_LICENSE")

    report = gather_doctor_report(
        knowledge_directory=str(knowledge_dir),
        source_directory=str(source_dir),
        api_probe=lambda base_url: {
            "ok": True,
            "version": "0.20.0",
            "load_duration_ms": 1250,
            "eval_duration_ms": 340,
        },
    )

    assert report["ollama"]["ok"] is True
    assert report["ollama"]["version"] == "0.20.0"
    assert report["ollama"]["load_duration_ms"] == 1250
    assert report["ollama"]["eval_duration_ms"] == 340
    assert report["knowledge"]["directory"] == str(knowledge_dir)
    assert report["knowledge"]["file_count"] == 1
    assert report["sources"]["directory"] == str(source_dir)
    assert report["sources"]["file_count"] == 3
    assert report["sources"]["files"] == ["Sentieon202503.03.pdf", "README.md", "guide.md"]
    assert report["sources"]["primary_release"] == "202503.03"
    assert report["sources"]["primary_date"] == "Mar 30, 2026"


def test_gather_doctor_report_handles_ollama_probe_failure(tmp_path):
    report = gather_doctor_report(
        knowledge_directory=str(tmp_path / "missing-knowledge"),
        source_directory=str(tmp_path / "missing-sources"),
        api_probe=lambda base_url: {"ok": False, "error": "connection refused"},
    )

    assert report["ollama"]["ok"] is False
    assert report["ollama"]["error"] == "connection refused"
    assert report["knowledge"]["exists"] is False
    assert report["sources"]["exists"] is False


def test_gather_doctor_report_can_skip_ollama_probe(tmp_path):
    report = gather_doctor_report(
        knowledge_directory=str(tmp_path / "missing-knowledge"),
        source_directory=str(tmp_path / "missing-sources"),
        skip_ollama_probe=True,
        api_probe=lambda base_url: {"ok": True},
    )

    assert report["ollama"]["ok"] is False
    assert report["ollama"]["skipped"] is True
    assert report["ollama"]["error"] == "ollama probe skipped"


def test_format_doctor_report_includes_key_summary_fields():
    text = format_doctor_report(
        {
            "runtime_llm": {
                "provider": "ollama",
                "base_url": "http://127.0.0.1:11434",
                "model": "gemma4:e4b",
                "ok": True,
                "version": "0.20.0",
                "load_duration_ms": 1250,
                "eval_duration_ms": 340,
            },
            "knowledge": {
                "directory": "/tmp/knowledge",
                "exists": True,
                "file_count": 2,
                "files": ["install.json", "license.json"],
            },
            "sources": {
                "directory": "/tmp/sources",
                "exists": True,
                "file_count": 1,
                "files": ["guide.md"],
                "primary_release": "202503.03",
                "primary_date": "Mar 30, 2026",
                "primary_reference": "Sentieon202503.03.pdf",
            },
        }
    )

    assert "【Runtime LLM】" in text
    assert "provider: ollama" in text
    assert "status: ok" in text
    assert "model: gemma4:e4b" in text
    assert "load_duration_ms: 1250" in text
    assert "eval_duration_ms: 340" in text
    assert "【Knowledge】" in text
    assert "file_count: 2" in text
    assert "install.json, license.json" in text
    assert "【Sources】" in text
    assert "guide.md" in text
    assert "primary_release: 202503.03" in text
    assert "primary_date: Mar 30, 2026" in text


def test_gather_doctor_report_includes_build_runtime_and_source_pack_health(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "sentieon-modules.json").write_text('{"version":"","entries":[]}\n')
    (source_dir / "workflow-guides.json").write_text('{"version":"","entries":[]}\n')
    (source_dir / "external-format-guides.json").write_text('{"version":"","entries":[]}\n')

    report = gather_doctor_report(
        knowledge_directory=str(tmp_path / "knowledge"),
        source_directory=str(source_dir),
        api_probe=lambda base_url: {"ok": False, "error": "connection refused"},
    )

    assert "build_runtime" in report
    assert isinstance(report["build_runtime"]["docling_available"], bool)
    assert report["sources"]["managed_pack_complete"] is False
    assert "external-tool-guides.json" in report["sources"]["missing_managed_pack_files"]
    assert "external-error-associations.json" in report["sources"]["missing_managed_pack_files"]
    assert "incident-memory.json" in report["sources"]["missing_managed_pack_files"]


def test_gather_doctor_report_reports_missing_managed_pack_files_from_vendor_profile(tmp_path, monkeypatch):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    for name in (
        "sentieon-modules.json",
        "workflow-guides.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
        "incident-memory.json",
    ):
        (source_dir / name).write_text('{"version":"","entries":[]}\n')

    monkeypatch.setattr(
        "sentieon_assist.kernel.pack_runtime.get_vendor_profile",
        lambda vendor_id: SimpleNamespace(
            pack_manifest={
                "vendor-reference": PackManifestEntry(required=True, file_name="sentieon-modules-v2.json", entry_schema_version="2.0", load_order=10),
                "vendor-decision": PackManifestEntry(required=True, file_name="workflow-guides.json", entry_schema_version="2.0", load_order=20),
                "domain-standard": PackManifestEntry(required=True, file_name="external-format-guides.json", entry_schema_version="2.0", load_order=30),
                "playbook": PackManifestEntry(required=True, file_name="external-tool-guides.json", entry_schema_version="2.0", load_order=40),
                "troubleshooting": PackManifestEntry(required=True, file_name="external-error-associations.json", entry_schema_version="2.0", load_order=50),
                "incident-memory": PackManifestEntry(required=True, file_name="incident-memory.json", entry_schema_version="2.0", load_order=60),
            }
        ),
    )

    report = gather_doctor_report(
        knowledge_directory=str(tmp_path / "knowledge"),
        source_directory=str(source_dir),
        api_probe=lambda base_url: {"ok": False, "error": "connection refused"},
    )

    assert report["sources"]["managed_pack_complete"] is False
    assert "sentieon-modules-v2.json" in report["sources"]["missing_managed_pack_files"]


def test_gather_doctor_report_reports_invalid_required_runtime_pack(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    for name in (
        "sentieon-modules.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
        "incident-memory.json",
    ):
        (source_dir / name).write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    (source_dir / "workflow-guides.json").write_text('{"version":""}\n', encoding="utf-8")

    report = gather_doctor_report(
        knowledge_directory=str(tmp_path / "knowledge"),
        source_directory=str(source_dir),
        api_probe=lambda base_url: {"ok": False, "error": "connection refused"},
    )

    assert report["sources"]["managed_pack_complete"] is False
    assert report["sources"]["invalid_managed_pack_files"] == ["workflow-guides.json"]


def test_missing_managed_pack_files_uses_resolved_default_vendor(tmp_path, monkeypatch):
    import sentieon_assist.doctor as doctor

    seen: dict[str, object] = {}
    monkeypatch.setattr(
        doctor,
        "resolve_vendor_id",
        lambda vendor_id=None: seen.setdefault("resolved", vendor_id) or "sentieon",
        raising=False,
    )

    def fake_required_pack_status(directory, vendor_id):
        seen["pack_vendor_id"] = vendor_id
        return ()

    monkeypatch.setattr(doctor, "required_pack_status", fake_required_pack_status)

    assert doctor._missing_managed_pack_files(tmp_path) == []
    assert seen["resolved"] is None
    assert seen["pack_vendor_id"] == "sentieon"


def test_format_doctor_report_includes_build_runtime_and_managed_pack_health():
    text = format_doctor_report(
        {
            "ollama": {
                "base_url": "http://127.0.0.1:11434",
                "model": "gemma4:e4b",
                "ok": False,
                "error": "connection refused",
            },
            "build_runtime": {
                "docling_available": False,
                "docling_mode": "optional-pdf-parser-missing",
            },
            "knowledge": {
                "directory": "/tmp/knowledge",
                "exists": True,
                "file_count": 2,
                "files": ["install.json", "license.json"],
            },
            "sources": {
                "directory": "/tmp/sources",
                "exists": True,
                "file_count": 1,
                "files": ["guide.md"],
                "primary_release": "202503.03",
                "primary_date": "Mar 30, 2026",
                "primary_reference": "Sentieon202503.03.pdf",
                "managed_pack_complete": False,
                "missing_managed_pack_files": ["external-tool-guides.json"],
                "invalid_managed_pack_files": ["workflow-guides.json"],
            },
        }
    )

    assert "【Build Runtime】" in text
    assert "docling_available: no" in text
    assert "managed_pack_complete: no" in text
    assert "external-tool-guides.json" in text
    assert "workflow-guides.json" in text


def test_format_doctor_report_includes_actionable_ollama_guidance_for_error_state():
    text = format_doctor_report(
        {
            "runtime_llm": {
                "provider": "ollama",
                "base_url": "http://127.0.0.1:11434",
                "model": "gemma4:e4b",
                "ok": False,
                "error": "connection refused",
            },
            "build_runtime": {
                "pyyaml_available": True,
                "pyyaml_mode": "mandatory-installed",
                "docling_available": False,
                "docling_mode": "optional-pdf-parser-missing",
            },
            "knowledge": {
                "directory": "/tmp/knowledge",
                "exists": True,
                "file_count": 2,
                "files": ["install.json", "license.json"],
            },
            "sources": {
                "directory": "/tmp/sources",
                "exists": True,
                "file_count": 5,
                "files": [
                    "sentieon-modules.json",
                    "workflow-guides.json",
                    "external-format-guides.json",
                    "external-tool-guides.json",
                    "external-error-associations.json",
                ],
                "primary_release": "202503.03",
                "primary_date": "Mar 30, 2026",
                "primary_reference": "workflow-guides.json",
                "managed_pack_complete": True,
                "missing_managed_pack_files": [],
            },
        }
    )

    assert "【建议下一步】" in text
    assert "sengent doctor --skip-ollama" in text
    assert "ollama pull gemma4:e4b" in text


def test_format_doctor_report_includes_actionable_ollama_guidance_for_missing_model():
    text = format_doctor_report(
        {
            "runtime_llm": {
                "provider": "ollama",
                "base_url": "http://127.0.0.1:11434",
                "model": "gemma4:e4b",
                "ok": True,
                "version": "0.20.0",
                "model_available": False,
            },
            "build_runtime": {
                "pyyaml_available": True,
                "pyyaml_mode": "mandatory-installed",
                "docling_available": False,
                "docling_mode": "optional-pdf-parser-missing",
            },
            "knowledge": {
                "directory": "/tmp/knowledge",
                "exists": True,
                "file_count": 2,
                "files": ["install.json", "license.json"],
            },
            "sources": {
                "directory": "/tmp/sources",
                "exists": True,
                "file_count": 5,
                "files": [
                    "sentieon-modules.json",
                    "workflow-guides.json",
                    "external-format-guides.json",
                    "external-tool-guides.json",
                    "external-error-associations.json",
                ],
                "primary_release": "202503.03",
                "primary_date": "Mar 30, 2026",
                "primary_reference": "workflow-guides.json",
                "managed_pack_complete": True,
                "missing_managed_pack_files": [],
            },
        }
    )

    assert "model_available: no" in text
    assert "ollama pull gemma4:e4b" in text


def test_format_doctor_report_includes_hosted_provider_guidance():
    text = format_doctor_report(
        {
            "runtime_llm": {
                "provider": "openai_compatible",
                "base_url": "https://api.example.com/v1",
                "model": "gpt-4.1",
                "ok": False,
                "error": "openai-compatible request failed: connection refused",
            },
            "build_runtime": {
                "pyyaml_available": True,
                "pyyaml_mode": "mandatory-installed",
                "docling_available": False,
                "docling_mode": "optional-pdf-parser-missing",
            },
            "knowledge": {
                "directory": "/tmp/knowledge",
                "exists": True,
                "file_count": 2,
                "files": ["install.json", "license.json"],
            },
            "sources": {
                "directory": "/tmp/sources",
                "exists": True,
                "file_count": 5,
                "files": [
                    "sentieon-modules.json",
                    "workflow-guides.json",
                    "external-format-guides.json",
                    "external-tool-guides.json",
                    "external-error-associations.json",
                ],
                "primary_release": "202503.03",
                "primary_date": "Mar 30, 2026",
                "primary_reference": "workflow-guides.json",
                "managed_pack_complete": True,
                "missing_managed_pack_files": [],
            },
        }
    )

    assert "provider: openai_compatible" in text
    assert "https://api.example.com/v1" in text
    assert "gpt-4.1" in text
    assert "ollama pull" not in text
    assert "API key" in text or "api_key" in text
