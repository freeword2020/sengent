from sentieon_assist.doctor import format_doctor_report, gather_doctor_report


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


def test_format_doctor_report_includes_key_summary_fields():
    text = format_doctor_report(
        {
            "ollama": {
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

    assert "【Ollama】" in text
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
