import json
import sys
from pathlib import Path
from types import SimpleNamespace

from sentieon_assist.cli import _build_input_prompt
from sentieon_assist.cli import main
from sentieon_assist.cli import render_chat_response
from sentieon_assist.cli import run_query


class FakeTTY:
    def __init__(self, is_tty: bool) -> None:
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


def _write_activation_source_packs(source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    for name in (
        "sentieon-modules.json",
        "workflow-guides.json",
        "external-format-guides.json",
        "external-tool-guides.json",
        "external-error-associations.json",
    ):
        (source_dir / name).write_text('{"version":"","entries":[]}\n', encoding="utf-8")


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


def test_cli_requires_query(capsys):
    code = main([])
    out = capsys.readouterr().out
    assert code == 0
    assert "Usage: sengent" in out
    assert "sengent chat" in out


def test_cli_help_flag_prints_usage(capsys):
    code = main(["--help"])
    out = capsys.readouterr().out
    assert code == 0
    assert "Usage: sengent" in out
    assert "sengent knowledge build" in out


def test_cli_chat_help_prints_usage_without_entering_runtime(monkeypatch):
    def fail_chat_loop(**kwargs):
        raise AssertionError("chat_loop should not run for chat --help")

    monkeypatch.setattr("sentieon_assist.cli.chat_loop", fail_chat_loop)
    outputs: list[str] = []

    code = main(["chat", "--help"], output_fn=outputs.append)

    assert code == 0
    joined = "\n".join(outputs)
    assert "Usage: sengent chat" in joined
    assert "/feedback" in joined


def test_cli_query_runtime_error_is_reported_with_user_guidance(monkeypatch):
    def fail_run_query(*args, **kwargs):
        raise RuntimeError("local ollama request failed: <urlopen error [Errno 61] Connection refused>")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fail_run_query)
    outputs: list[str] = []

    code = main(["DNAscope", "是做什么的"], output_fn=outputs.append)

    assert code == 2
    joined = "\n".join(outputs)
    assert "Ollama" in joined
    assert "sengent doctor" in joined
    assert "ollama pull" in joined


def test_cli_chat_runtime_error_is_reported_with_user_guidance(monkeypatch):
    def fail_chat_loop(**kwargs):
        raise RuntimeError("local ollama request failed: <urlopen error [Errno 61] Connection refused>")

    monkeypatch.setattr("sentieon_assist.cli.chat_loop", fail_chat_loop)
    outputs: list[str] = []

    code = main(["chat"], output_fn=outputs.append)

    assert code == 2
    joined = "\n".join(outputs)
    assert "Ollama" in joined
    assert "sengent doctor" in joined
    assert "ollama pull" in joined


def test_cli_prints_answer_for_query(capsys):
    code = main(["Sentieon", "202503", "license", "报错"])
    out = capsys.readouterr().out
    assert code == 0
    assert out.strip()
    assert out == f"{run_query('Sentieon 202503 license 报错')}\n"


def test_cli_reads_sys_argv_when_no_argv_argument(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["sentieon-assist", "Sentieon", "202503", "license", "报错"])
    code = main()
    out = capsys.readouterr().out
    assert code == 0
    assert out == f"{run_query('Sentieon 202503 license 报错')}\n"


def test_cli_doctor_forwards_skip_ollama(monkeypatch):
    captured: dict[str, object] = {}

    def fake_gather_doctor_report(**kwargs):
        captured.update(kwargs)
        return {
            "ollama": {"base_url": "http://127.0.0.1:11434", "model": "gemma4:e4b", "ok": False, "skipped": True},
            "build_runtime": {},
            "knowledge": {"directory": "/tmp/knowledge", "exists": True, "file_count": 0, "files": []},
            "sources": {
                "directory": "/tmp/sources",
                "exists": True,
                "file_count": 0,
                "files": [],
                "primary_release": "",
                "primary_date": "",
                "primary_reference": "",
                "managed_pack_complete": True,
                "missing_managed_pack_files": [],
            },
        }

    monkeypatch.setattr("sentieon_assist.cli.gather_doctor_report", fake_gather_doctor_report)
    monkeypatch.setattr("sentieon_assist.cli.format_doctor_report", lambda report: "doctor-ok")
    outputs: list[str] = []

    code = main(["doctor", "--skip-ollama"], output_fn=outputs.append)

    assert code == 0
    assert captured["skip_ollama_probe"] is True
    assert outputs == ["doctor-ok"]


def test_cli_knowledge_activate_promotes_candidate_packs_when_gate_reports_pass(tmp_path: Path):
    source_dir = tmp_path / "sentieon-note"
    _write_activation_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_id = "build-001"
    build_dir = _write_activation_candidate_build(
        build_root,
        build_id,
        module_id="fastdedup",
        module_name="FastDedup",
    )

    outputs: list[str] = []
    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "activate",
            "--build-root",
            str(build_root),
            "--build-id",
            build_id,
        ],
        output_fn=outputs.append,
    )

    assert code == 0
    activated_modules = json.loads((source_dir / "sentieon-modules.json").read_text(encoding="utf-8"))
    assert activated_modules["entries"][0]["id"] == "fastdedup"
    activation_manifest = json.loads((build_dir / "activation-manifest.json").read_text(encoding="utf-8"))
    assert activation_manifest["build_id"] == build_id
    assert "sentieon-modules.json" in activation_manifest["activated_files"]
    assert any("Knowledge activation completed" in item for item in outputs)


def test_cli_knowledge_activate_refuses_when_gate_reports_fail(tmp_path: Path):
    source_dir = tmp_path / "sentieon-note"
    _write_activation_source_packs(source_dir)
    original_modules = (source_dir / "sentieon-modules.json").read_text(encoding="utf-8")
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_id = "build-002"
    build_dir = build_root / build_id
    candidate_dir = build_dir / "candidate-packs"
    candidate_dir.mkdir(parents=True)
    (candidate_dir / "sentieon-modules.json").write_text(
        json.dumps({"version": "", "entries": [{"id": "fastdedup", "name": "FastDedup"}]}, ensure_ascii=False) + "\n",
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
    (build_dir / "pilot-readiness-report.json").write_text('{"ok": false}\n', encoding="utf-8")
    outputs: list[str] = []

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "activate",
            "--build-root",
            str(build_root),
            "--build-id",
            build_id,
        ],
        output_fn=outputs.append,
    )

    assert code == 2
    assert (source_dir / "sentieon-modules.json").read_text(encoding="utf-8") == original_modules
    assert any("gate" in item.lower() for item in outputs)


def test_cli_knowledge_activate_records_backup_id_and_preserves_previous_modules_pack(tmp_path: Path):
    source_dir = tmp_path / "sentieon-note"
    _write_activation_source_packs(source_dir)
    (source_dir / "sentieon-modules.json").write_text(
        json.dumps({"version": "", "entries": [{"id": "old-fastdedup", "name": "Old FastDedup"}]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_id = "build-003"
    build_dir = _write_activation_candidate_build(
        build_root,
        build_id,
        module_id="fastdedup",
        module_name="FastDedup",
    )

    outputs: list[str] = []
    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "activate",
            "--build-root",
            str(build_root),
            "--build-id",
            build_id,
        ],
        output_fn=outputs.append,
    )

    assert code == 0
    activation_manifest = json.loads((build_dir / "activation-manifest.json").read_text(encoding="utf-8"))
    backup_id = activation_manifest["backup_id"]
    backup_dir = build_root / "activation-backups" / backup_id
    backup_modules = json.loads((backup_dir / "sentieon-modules.json").read_text(encoding="utf-8"))
    assert backup_modules["entries"][0]["id"] == "old-fastdedup"
    assert any(backup_id in item for item in outputs)


def test_cli_knowledge_rollback_restores_backup_into_active_source_directory(tmp_path: Path):
    source_dir = tmp_path / "sentieon-note"
    _write_activation_source_packs(source_dir)
    (source_dir / "sentieon-modules.json").write_text(
        json.dumps({"version": "", "entries": [{"id": "baseline", "name": "Baseline"}]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_a = _write_activation_candidate_build(build_root, "build-a", module_id="alpha", module_name="Alpha")
    build_b = _write_activation_candidate_build(build_root, "build-b", module_id="beta", module_name="Beta")

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
                "build-a",
            ],
            output_fn=lambda _message: None,
        )
        == 0
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
                "build-b",
            ],
            output_fn=lambda _message: None,
        )
        == 0
    )
    backup_id = json.loads((build_b / "activation-manifest.json").read_text(encoding="utf-8"))["backup_id"]

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
            backup_id,
        ],
        output_fn=outputs.append,
    )

    assert code == 0
    restored_modules = json.loads((source_dir / "sentieon-modules.json").read_text(encoding="utf-8"))
    assert restored_modules["entries"][0]["id"] == "alpha"
    assert any("Knowledge rollback completed" in item for item in outputs)
    assert any(backup_id in item for item in outputs)


def test_cli_knowledge_activate_restores_previous_state_when_apply_copy_fails(tmp_path: Path, monkeypatch):
    source_dir = tmp_path / "sentieon-note"
    _write_activation_source_packs(source_dir)
    (source_dir / "sentieon-modules.json").write_text(
        json.dumps({"version": "", "entries": [{"id": "baseline", "name": "Baseline"}]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    build_root = tmp_path / "runtime" / "knowledge-build"
    _write_activation_candidate_build(build_root, "build-copy-fail", module_id="fastdedup", module_name="FastDedup")

    import sentieon_assist.knowledge_build as knowledge_build

    real_copy2 = knowledge_build.shutil.copy2

    def flaky_copy2(src, dst, *args, **kwargs):
        src_path = Path(src)
        dst_path = Path(dst)
        if src_path.parent.name == "candidate-packs" and dst_path.parent == source_dir and src_path.name == "workflow-guides.json":
            raise OSError("simulated copy failure")
        return real_copy2(src, dst, *args, **kwargs)

    monkeypatch.setattr(knowledge_build.shutil, "copy2", flaky_copy2)
    outputs: list[str] = []

    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "activate",
            "--build-root",
            str(build_root),
            "--build-id",
            "build-copy-fail",
        ],
        output_fn=outputs.append,
    )

    assert code == 2
    restored_modules = json.loads((source_dir / "sentieon-modules.json").read_text(encoding="utf-8"))
    assert restored_modules["entries"][0]["id"] == "baseline"
    assert any("activation failed" in item.lower() for item in outputs)


def test_cli_knowledge_scaffold_creates_module_source_templates(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    outputs: list[str] = []

    code = main(
        [
            "knowledge",
            "scaffold",
            "--inbox-dir",
            str(inbox_dir),
            "--kind",
            "module",
            "--id",
            "fastdedup",
            "--name",
            "FastDedup",
        ],
        output_fn=outputs.append,
    )

    assert code == 0
    markdown_path = inbox_dir / "fastdedup.md"
    metadata_path = inbox_dir / "fastdedup.meta.yaml"
    assert markdown_path.exists()
    assert metadata_path.exists()
    assert "# FastDedup" in markdown_path.read_text(encoding="utf-8")
    metadata = metadata_path.read_text(encoding="utf-8")
    assert "pack_target: sentieon-modules.json" in metadata
    assert "entry_type: module" in metadata
    assert "id: fastdedup" in metadata
    assert "name: FastDedup" in metadata
    assert any("Knowledge scaffold completed" in item for item in outputs)


def test_cli_knowledge_scaffold_preserves_existing_markdown_and_backfills_metadata(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    markdown_path = inbox_dir / "fastdedup.md"
    metadata_path = inbox_dir / "fastdedup.meta.yaml"
    markdown_path.write_text("# Existing FastDedup\n\nDo not overwrite.\n", encoding="utf-8")
    metadata_path.write_text("summary: Existing summary.\n", encoding="utf-8")

    code = main(
        [
            "knowledge",
            "scaffold",
            "--inbox-dir",
            str(inbox_dir),
            "--kind",
            "module",
            "--id",
            "fastdedup",
            "--name",
            "FastDedup",
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    assert markdown_path.read_text(encoding="utf-8") == "# Existing FastDedup\n\nDo not overwrite.\n"
    metadata = metadata_path.read_text(encoding="utf-8")
    assert "summary: Existing summary." in metadata
    assert "pack_target: sentieon-modules.json" in metadata
    assert "entry_type: module" in metadata
    assert "id: fastdedup" in metadata


def test_cli_knowledge_scaffold_creates_delete_retirement_stub(tmp_path: Path):
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"

    code = main(
        [
            "knowledge",
            "scaffold",
            "--inbox-dir",
            str(inbox_dir),
            "--kind",
            "module",
            "--id",
            "fastdedup",
            "--action",
            "delete",
        ],
        output_fn=lambda _message: None,
    )

    assert code == 0
    markdown_path = inbox_dir / "retire-fastdedup.md"
    metadata_path = inbox_dir / "retire-fastdedup.meta.yaml"
    assert markdown_path.exists()
    assert metadata_path.exists()
    metadata = metadata_path.read_text(encoding="utf-8")
    assert "action: delete" in metadata
    assert "pack_target: sentieon-modules.json" in metadata
    assert "id: fastdedup" in metadata


def test_cli_knowledge_review_prints_latest_build_report(tmp_path: Path):
    build_root = tmp_path / "runtime" / "knowledge-build"
    older_dir = build_root / "20260410T000000Z-aaaa1111"
    latest_dir = build_root / "20260410T000100Z-bbbb2222"
    older_dir.mkdir(parents=True)
    latest_dir.mkdir(parents=True)
    (older_dir / "report.md").write_text("# Older Report\n", encoding="utf-8")
    (latest_dir / "report.md").write_text("# Latest Report\n\nAll good.\n", encoding="utf-8")
    outputs: list[str] = []

    code = main(
        [
            "knowledge",
            "review",
            "--build-root",
            str(build_root),
        ],
        output_fn=outputs.append,
    )

    assert code == 0
    combined = "\n".join(outputs)
    assert "Knowledge review" in combined
    assert str(latest_dir) in combined
    assert "# Latest Report" in combined


def test_cli_knowledge_review_ignores_activation_backups_when_selecting_latest_build(tmp_path: Path):
    build_root = tmp_path / "runtime" / "knowledge-build"
    latest_dir = build_root / "20260410T000100Z-bbbb2222"
    backup_dir = build_root / "activation-backups" / "20260410T000200000000Z-cccc3333"
    latest_dir.mkdir(parents=True)
    backup_dir.mkdir(parents=True)
    (latest_dir / "report.md").write_text("# Latest Report\n", encoding="utf-8")
    outputs: list[str] = []

    code = main(
        [
            "knowledge",
            "review",
            "--build-root",
            str(build_root),
        ],
        output_fn=outputs.append,
    )

    assert code == 0
    combined = "\n".join(outputs)
    assert str(latest_dir) in combined
    assert "Latest Report" in combined


def test_cli_knowledge_commands_use_default_config_source_dir(tmp_path: Path, monkeypatch):
    source_dir = tmp_path / "sentieon-note"
    _write_activation_source_packs(source_dir)
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"
    inbox_dir.mkdir(parents=True)
    (inbox_dir / "fastdedup.md").write_text(
        "---\n"
        "pack_target: sentieon-modules.json\n"
        "entry_type: module\n"
        "id: fastdedup\n"
        "name: FastDedup\n"
        "---\n\n# FastDedup\n",
        encoding="utf-8",
    )
    build_root = tmp_path / "runtime" / "knowledge-build"
    monkeypatch.setattr(
        "sentieon_assist.cli.load_config",
        lambda: SimpleNamespace(knowledge_dir="", source_dir=str(source_dir)),
    )

    build_outputs: list[str] = []
    build_code = main(
        [
            "knowledge",
            "build",
            "--inbox-dir",
            str(inbox_dir),
            "--build-root",
            str(build_root),
        ],
        output_fn=build_outputs.append,
    )
    assert build_code == 0

    build_dir = next(path for path in build_root.iterdir() if path.is_dir() and path.name != "activation-backups")
    (build_dir / "pilot-readiness-report.json").write_text('{"ok": true}\n', encoding="utf-8")
    (build_dir / "pilot-closed-loop-report.json").write_text('{"ok": true}\n', encoding="utf-8")

    activate_outputs: list[str] = []
    activate_code = main(
        [
            "knowledge",
            "activate",
            "--build-root",
            str(build_root),
            "--build-id",
            build_dir.name,
        ],
        output_fn=activate_outputs.append,
    )
    assert activate_code == 0
    backup_id = json.loads((build_dir / "activation-manifest.json").read_text(encoding="utf-8"))["backup_id"]

    rollback_outputs: list[str] = []
    rollback_code = main(
        [
            "knowledge",
            "rollback",
            "--build-root",
            str(build_root),
            "--backup-id",
            backup_id,
        ],
        output_fn=rollback_outputs.append,
    )
    assert rollback_code == 0


def test_build_input_prompt_stays_plain_for_non_interactive_input():
    prompt = _build_input_prompt(
        input_fn=lambda prompt: prompt,
        stdin=FakeTTY(True),
        stdout=FakeTTY(True),
    )

    assert prompt == "Sengent> "


def test_build_input_prompt_uses_ansi_for_interactive_tty():
    prompt = _build_input_prompt(
        input_fn=input,
        stdin=FakeTTY(True),
        stdout=FakeTTY(True),
    )

    assert prompt != "Sengent> "
    assert "Sengent>" in prompt
    assert prompt.endswith("\x1b[0m ")


def test_chat_loop_answers_once_and_quits():
    prompts = iter(["Sentieon 202503 license 报错", "/quit"])
    outputs: list[str] = []
    statuses: list[tuple[str, bool]] = []
    input_prompts: list[str] = []

    def fake_input(prompt: str) -> str:
        input_prompts.append(prompt)
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "【问题判断】\n这是一个 Sentieon license 相关问题。",
        status_writer=lambda text, clear=False: statuses.append((text, clear)),
        stream_output_fn=outputs.append,
    )
    assert code == 0
    assert any("Sengent" in item for item in outputs)
    assert any("【问题判断】" in item for item in outputs)
    assert any("已退出" in item for item in outputs)
    assert statuses
    assert any(text == "正在思考中..." for text, clear in statuses if not clear)
    assert any(text.startswith("正在思考中") for text, clear in statuses if not clear)
    assert any(clear for text, clear in statuses)
    assert input_prompts
    assert input_prompts[0] == "Sengent> "


def test_chat_loop_emits_thinking_status_before_planning(monkeypatch):
    prompts = iter(["介绍下 sentieon", "/quit"])
    outputs: list[str] = []
    statuses: list[tuple[str, bool]] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    import sentieon_assist.cli as cli_module

    original_plan_support_turn = cli_module.plan_support_turn
    saw_thinking_before_planning = False

    def wrapped_plan_support_turn(*args, **kwargs):
        nonlocal saw_thinking_before_planning
        saw_thinking_before_planning = any(
            text == "正在思考中..." for text, clear in statuses if not clear
        )
        return original_plan_support_turn(*args, **kwargs)

    monkeypatch.setattr("sentieon_assist.cli.plan_support_turn", wrapped_plan_support_turn)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "SHOULD_NOT_RUN",
        status_writer=lambda text, clear=False: statuses.append((text, clear)),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert saw_thinking_before_planning is True


def test_chat_loop_help_includes_feedback_entrypoint():
    prompts = iter(["/help", "/quit"])
    outputs: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=outputs.append,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "SHOULD_NOT_RUN",
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert any("/feedback" in item for item in outputs)
    assert any("/feedback session" in item for item in outputs)


def test_chat_loop_feedback_writes_last_turn_record(tmp_path, monkeypatch):
    feedback_path = tmp_path / "runtime-feedback.jsonl"
    runtime_directory = tmp_path / "runtime"
    prompts = iter(
        [
            "DNAscope 是做什么的",
            "/feedback",
            "模块介绍太泛了",
            "希望它先说明适用场景",
            "module",
            "reference",
            "/quit",
        ]
    )
    outputs: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    monkeypatch.setattr("sentieon_assist.cli.run_query", lambda query, **kwargs: "【模块介绍】\nDNAscope：用于 germline variant calling")

    code = main(
        ["--feedback-path", str(feedback_path), "chat"],
        input_fn=fake_input,
        output_fn=outputs.append,
        runtime_directory=str(runtime_directory),
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "SHOULD_NOT_RUN",
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert feedback_path.exists()
    records = [json.loads(line) for line in feedback_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 1
    record = records[0]
    assert record["scope"] == "last"
    assert record["summary"] == "模块介绍太泛了"
    assert record["expected_answer"] == "希望它先说明适用场景"
    assert record["expected_mode"] == "module_intro"
    assert record["expected_task"] == "reference_lookup"
    assert record["session_id"]
    assert len(record["selected_turn_ids"]) == 1
    assert "captured_turns" not in record
    assert (runtime_directory / "sessions" / f"{record['session_id']}.jsonl").exists()
    assert any("已记录问题反馈" in item for item in outputs)


def test_chat_loop_feedback_session_writes_full_context(tmp_path, monkeypatch):
    feedback_path = tmp_path / "runtime-feedback.jsonl"
    runtime_directory = tmp_path / "runtime"
    prompts = iter(
        [
            "能提供个wes参考脚本吗",
            "短读长二倍体呢",
            "/feedback session",
            "第二轮才给到脚本",
            "第一轮就该更明确说明下一步",
            "",
            "",
            "/quit",
        ]
    )
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "能提供个wes参考脚本吗":
            return "【流程指导】\n- 先确认胚系还是体细胞。\n\n【需要确认的信息】\n- 样本是否来自二倍体生物（diploid organism）？"
        if query == "能提供个wes参考脚本吗 短读长二倍体呢":
            return "【参考命令】\n- sentieon-cli dnascope ..."
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["--feedback-path", str(feedback_path), "chat"],
        input_fn=fake_input,
        output_fn=outputs.append,
        runtime_directory=str(runtime_directory),
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "SHOULD_NOT_RUN",
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["能提供个wes参考脚本吗", "能提供个wes参考脚本吗 短读长二倍体呢"]
    records = [json.loads(line) for line in feedback_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(records) == 1
    record = records[0]
    assert record["scope"] == "session"
    assert record["summary"] == "第二轮才给到脚本"
    assert record["expected_answer"] == "第一轮就该更明确说明下一步"
    assert record["session_id"]
    assert len(record["selected_turn_ids"]) == 2
    assert "captured_turns" not in record
    assert (runtime_directory / "sessions" / f"{record['session_id']}.jsonl").exists()


def test_chat_loop_writes_reference_trace_metadata_into_session_log(tmp_path):
    runtime_directory = tmp_path / "runtime"
    prompts = iter(
        [
            "为什么我的服务器明明有 128 个核心，但 Sentieon 运行时似乎只占用了很少的 CPU 资源？",
            "/quit",
        ]
    )
    outputs: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=outputs.append,
        runtime_directory=str(runtime_directory),
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "SHOULD_NOT_RUN",
        stream_output_fn=outputs.append,
    )

    assert code == 0
    session_logs = sorted((runtime_directory / "sessions").glob("*.jsonl"))
    session_logs = [path for path in session_logs if path.name != "index.jsonl"]
    assert len(session_logs) == 1
    events = [json.loads(line) for line in session_logs[0].read_text(encoding="utf-8").splitlines() if line.strip()]
    turn_events = [event for event in events if event.get("event_type") == "turn_resolved"]
    assert len(turn_events) == 1
    answer = turn_events[0]["answer"]
    assert answer["resolver_path"] == ["doc_reference"]
    assert answer["boundary_tags"] == []
    assert answer["sources"]


def test_chat_loop_writes_troubleshooting_trace_metadata_into_session_log(tmp_path):
    runtime_directory = tmp_path / "runtime"
    prompts = iter(
        [
            "Sentieon 202503 license 报错，找不到 license 文件",
            "/quit",
        ]
    )
    outputs: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=outputs.append,
        runtime_directory=str(runtime_directory),
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "SHOULD_NOT_RUN",
        stream_output_fn=outputs.append,
    )

    assert code == 0
    session_logs = sorted((runtime_directory / "sessions").glob("*.jsonl"))
    session_logs = [path for path in session_logs if path.name != "index.jsonl"]
    assert len(session_logs) == 1
    events = [json.loads(line) for line in session_logs[0].read_text(encoding="utf-8").splitlines() if line.strip()]
    turn_events = [event for event in events if event.get("event_type") == "turn_resolved"]
    assert len(turn_events) == 1
    answer = turn_events[0]["answer"]
    assert answer["resolver_path"] == ["troubleshooting_rule"]
    assert answer["boundary_tags"] == []
    assert answer["sources"] == []


def test_chat_loop_passes_terse_example_followup_with_workflow_context(monkeypatch):
    prompts = iter(
        [
            "我要做wgs分析，能给个示例脚本吗",
            "短读长胚系二倍体",
            "我就要个示例",
            "/quit",
        ]
    )
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先按胚系/体细胞和短读长/长读长分流。"
        if query == "我要做wgs分析，能给个示例脚本吗 短读长胚系二倍体":
            return "【流程指导】\n- 先看样本是否来自二倍体生物（diploid organism）。"
        if query == "我要做wgs分析，能给个示例脚本吗 短读长胚系二倍体 我就要个示例":
            return "【参考命令】\n- sentieon-cli dnascope ..."
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == [
        "我要做wgs分析，能给个示例脚本吗",
        "我要做wgs分析，能给个示例脚本吗 短读长胚系二倍体",
        "我要做wgs分析，能给个示例脚本吗 短读长胚系二倍体 我就要个示例",
    ]
    assert any("【参考命令】" in item for item in outputs)


def test_chat_loop_does_not_reuse_parameter_anchor_for_new_reference_request(monkeypatch):
    prompts = iter(
        [
            "GVCFtyper 的 --emit_mode 是什么",
            "能提供个 wes 参考脚本吗",
            "能提供个 joint call 参考脚本吗",
            "/quit",
        ]
    )
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "GVCFtyper 的 --emit_mode 是什么":
            return "【常用参数】\n- GVCFtyper 的 --emit_mode：..."
        if query == "能提供个 wes 参考脚本吗":
            return "【流程指导】\n- 先按 WES 主线分流。"
        if query == "能提供个 joint call 参考脚本吗":
            return "【参考命令】\n- sentieon driver --algo GVCFtyper ..."
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == [
        "GVCFtyper 的 --emit_mode 是什么",
        "能提供个 wes 参考脚本吗",
        "能提供个 joint call 参考脚本吗",
    ]


def test_chat_loop_switches_workflow_anchor_when_new_request_is_standalone(monkeypatch):
    prompts = iter(
        [
            "能提供个tumor only参考脚本吗",
            "能提供个ont分析脚本吗",
            "/quit",
        ]
    )
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "能提供个tumor only参考脚本吗":
            return "【流程指导】\n- 这是 tumor-only 主线。"
        if query == "能提供个ont分析脚本吗":
            return "【流程指导】\n- 这是 long-read 主线。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == [
        "能提供个tumor only参考脚本吗",
        "能提供个ont分析脚本吗",
    ]


def test_chat_loop_does_not_reuse_open_clarification_slots_for_new_standalone_request(monkeypatch):
    prompts = iter(
        [
            "能提供个 wes 参考脚本吗",
            "LICSRVR、Poetry",
            "/quit",
        ]
    )
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "能提供个 wes 参考脚本吗":
            return "【流程指导】\n- 这是 WES 主线。\n\n【需要确认的信息】\n- 样本是否来自二倍体生物（diploid organism）？"
        if query == "LICSRVR、Poetry":
            return "【资料说明】\n- LICSRVR ...\n- Poetry ..."
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == [
        "能提供个 wes 参考脚本吗",
        "LICSRVR、Poetry",
    ]


def test_chat_loop_does_not_require_user_message_renderer(monkeypatch):
    prompts = iter(["DNAscope 是做什么的", "/quit"])
    outputs: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    class FakeUI:
        def render_welcome_panel(self) -> None:
            outputs.append("WELCOME")

        def render_streaming_answer_header(self) -> None:
            outputs.append("HEADER")

        def render_answer(self, text: str) -> None:
            outputs.append(text)

    monkeypatch.setattr("sentieon_assist.cli._build_chat_ui", lambda output_fn: FakeUI())
    monkeypatch.setattr("sentieon_assist.cli.run_query", lambda query, **kwargs: "【模块介绍】\nDNAscope：...")

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "SHOULD_NOT_RUN",
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert "WELCOME" in outputs
    assert any("【模块介绍】" in item for item in outputs)


def test_chat_loop_renders_user_and_answer_in_order_with_reference_status(monkeypatch):
    prompts = iter(["DNAscope 是做什么的", "/quit"])
    outputs: list[str] = []
    statuses: list[tuple[str, bool]] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr("sentieon_assist.cli.run_query", lambda query, **kwargs: "【模块介绍】\nDNAscope：...")

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "SHOULD_NOT_RUN",
        status_writer=lambda text, clear=False: statuses.append((text, clear)),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    joined = "\n".join(outputs)
    joined_after_welcome = "\n".join(outputs[1:])
    assert "─ 你 ─" not in joined
    assert "事件流" not in joined
    assert "DNAscope 是做什么的" not in joined_after_welcome
    assert any(text.startswith("正在思考中") for text, clear in statuses if not clear)


def test_chat_loop_emits_missing_info_statuses_before_followup_answer(monkeypatch):
    prompts = iter(["license 报错", "/quit"])
    outputs: list[str] = []
    statuses: list[tuple[str, bool]] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr("sentieon_assist.cli.run_query", lambda query, **kwargs: "需要补充以下信息：Sentieon 版本")

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "请告诉我 Sentieon 版本号，例如 202503.03。",
        status_writer=lambda text, clear=False: statuses.append((text, clear)),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    joined = "\n".join(outputs)
    assert "事件流" not in joined
    assert "请告诉我 Sentieon 版本号，例如 202503.03。" in joined
    assert any(text.startswith("正在思考中") for text, clear in statuses if not clear)
    assert any(text.startswith("正在生成回复") for text, clear in statuses if not clear)


def test_render_chat_response_keeps_structured_answer_stable_without_polish():
    generated_calls: list[str] = []
    streamed_calls: list[str] = []

    rendered, streamed = render_chat_response(
        "DNAscope 是做什么的",
        "【资料查询】\n- 命中模块索引：DNAscope",
        model_generate=lambda prompt, **kwargs: generated_calls.append(prompt) or "SHOULD_NOT_RUN",
        model_stream_generate=lambda prompt, on_chunk, **kwargs: streamed_calls.append(prompt) or "SHOULD_NOT_RUN",
    )

    assert rendered == "【资料查询】\n- 命中模块索引：DNAscope"
    assert streamed is False
    assert generated_calls == []
    assert streamed_calls == []


def test_render_chat_response_keeps_external_error_association_stable_without_polish():
    generated_calls: list[str] = []
    streamed_calls: list[str] = []
    raw_response = (
        "【资料查询】\n"
        "- 命中外部错误关联：Contig naming / sequence dictionary mismatch\n\n"
        "【关联判断】\n"
        "- 这更像是 contig 命名、顺序或 sequence dictionary 组织不一致的问题。"
    )

    rendered, streamed = render_chat_response(
        "VCF 报 contig not found 是什么情况",
        raw_response,
        model_generate=lambda prompt, **kwargs: generated_calls.append(prompt) or "SHOULD_NOT_RUN",
        model_stream_generate=lambda prompt, on_chunk, **kwargs: streamed_calls.append(prompt) or "SHOULD_NOT_RUN",
    )

    assert rendered == raw_response
    assert streamed is False
    assert generated_calls == []
    assert streamed_calls == []


def test_run_query_returns_boundary_for_roadmap_style_reference_prompt():
    text = run_query("目前发布的 HPRC minigraph-cactus 构建已支持多少个样本网络？Sentieon 如何应对即将发布的大规模 400 样本图谱？")

    assert "【资料边界】" in text
    assert "roadmap" in text or "未来" in text or "精确数值" in text


def test_run_query_returns_boundary_for_install_packaging_reference_prompt():
    text = run_query("如何通过命令行安装 Sentieon 工具？使用 sdist 安装 sentieon-cli 时，想结合 Poetry 虚拟环境进行依赖管理，具体配置步骤是什么？")

    assert "【资料说明】" in text
    assert "Poetry" in text


def test_run_query_returns_boundary_for_license_service_reference_prompt():
    text = run_query("许可服务的配置方式是什么？在多节点集群环境中，如何配置 LICSRVR 动态分配许可证，并使用 LICCLNT 检查服务器状态？")

    assert "【资料说明】" in text
    assert "LICSRVR" in text


def test_run_query_supports_too_many_open_files_troubleshooting_prompt():
    text = run_query(
        "为什么我在运行包含多个样本的联合分析或高深度数据比对时，程序突然崩溃并提示 Too many open files？"
        "这是否是软件 Bug？我该如何通过修改系统配置来解决？"
    )

    assert "【资料说明】" in text
    assert "ulimit -n" in text
    assert "文件句柄" in text or "open files" in text
    assert "【资料边界】" not in text


def test_run_query_supports_thread_count_guidance_for_low_cpu_utilization_prompt():
    text = run_query("为什么我的服务器明明有 128 个核心，但 Sentieon 运行时似乎只占用了很少的 CPU 资源？")

    assert "【资料说明】" in text
    assert "-t" in text or "NUMBER_THREADS" in text
    assert "线程" in text or "CPU" in text
    assert "【能力说明】" not in text


def test_run_query_supports_driver_vs_cli_doc_prompt():
    text = run_query(
        "官方教程里有时用 sentieon driver --algo DNAscope，有时又用最新的 sentieon-cli dnascope。"
        "这两个命令有什么区别？sentieon-cli 是如何包装底层二进制文件的？"
    )

    assert "【资料说明】" in text
    assert "sentieon driver" in text
    assert "sentieon-cli" in text
    assert "【资料边界】" not in text


def test_run_query_supports_dnascope_pcr_free_question_with_hyphenated_alias():
    text = run_query(
        "客户明确说明样本使用的是 PCR-free 建库方案。在运行 DNAscope 流程时，"
        "我需要修改哪个特定参数例如 --pcr_indel_model none 或 --pcr-free 来防止软件对 Indel 进行不必要的 PCR 伪影过滤？"
    )

    assert "【常用参数】" in text
    assert "DNAscope 的 --pcr_free" in text
    assert "PCR-free" in text
    assert "【资料边界】" not in text


def test_run_query_does_not_fall_back_to_capability_for_wes_model_mismatch_prompt():
    text = run_query(
        "我的数据是 Agilent SureSelect 捕获的外显子数据，如果我直接使用了 DNAscope Illumina WGS 机器学习模型进行过滤，"
        "变异检测的准确率会发生什么变化？"
    )

    assert "【能力说明】" not in text
    assert "【资料边界】" in text


def test_run_query_supports_tnscope_tumor_only_vs_tumor_normal_prompt():
    text = run_query(
        "在运行体细胞突变检测模块 TNscope 时，我只输入了肿瘤样本 Tumor-only。"
        "这是否可行？与同时输入肿瘤-正常 Tumor-Normal 配对样本相比，对低频突变及假阳性过滤的策略有何差异？"
    )

    assert "TNscope" in text
    assert "tumor-only" in text or "tumor only" in text
    assert "tumor-normal" in text or "tumor normal" in text
    assert "germline" in text or "胚系变异" in text
    assert "【资料边界】" not in text


def test_run_query_routes_verbose_pcr_free_prompt_to_parameter_answer():
    text = run_query(
        "客户明确说明样本使用的是 PCR-free 无扩增建库方案。在运行 DNAscope 流程时，我需要修改哪个特定参数例如 --pcr_indel_model none 或 --pcr-free 来防止软件对 Indel 进行不必要的 PCR 伪影过滤？"
    )

    assert "【常用参数】" in text
    assert "DNAscope 的 --pcr_free" in text or "--pcr_indel_model" in text


def test_run_query_prefers_parameter_answer_when_pcr_free_prompt_mentions_command_line():
    text = run_query("对于 PCR-free 建库样本，在运行 DNAscope 时，如何通过命令行参数如 --pcr_indel_model none 来关闭对 PCR 引入 Indel 的过滤？")

    assert "【常用参数】" in text
    assert "DNAscope 的 --pcr_free" in text


def test_run_query_returns_boundary_for_wes_wgs_model_accuracy_prompt():
    text = run_query(
        "我的数据是 Agilent SureSelect 捕获的外显子 WES 数据，如果我直接使用了 DNAscope Illumina WGS 机器学习模型进行过滤，变异检测的准确率会发生什么变化？"
    )

    assert "【资料边界】" in text
    assert "【能力说明】" not in text


def test_run_query_returns_boundary_for_samtools_collate_vs_picard_prompt():
    text = run_query(
        "客户给了一个旧的 BAM 文件，我打算提取 FASTQ 重新比对。为什么不推荐使用 Picard 的 SamToFastq 拆分文件，而是建议使用 samtools collate 结合管道操作直连 BWA？"
    )

    assert "【资料说明】" in text
    assert "samtools collate" in text
    assert "SamToFastq" in text
    assert "BWA" in text


def test_run_query_returns_doc_answer_for_cpu_thread_usage_prompt():
    text = run_query("为什么我的服务器明明有 128 个核心，但 Sentieon 运行时似乎只占用了很少的 CPU 资源？")

    assert "【资料说明】" in text
    assert "-t" in text


def test_run_query_returns_doc_answer_for_license_tool_selection_prompt():
    text = run_query(
        "当我配置好本地 License 服务器后，如果分析任务报错提示 License 获取失败，我该使用哪个官方二进制工具如 LICCLNT 来测试服务器连通性并检查可用授权数？"
    )

    assert "【资料说明】" in text
    assert "LICCLNT" in text


def test_run_query_returns_boundary_for_bwa_turbo_prompt():
    text = run_query(
        "听说 Sentieon BWA-turbo 能把比对速度再提升 4 倍。这是需要额外下载一个软件，还是只需要在现有的 BWA 命令中通过 -x 参数挂载特定的 .model 文件即可启用？"
    )

    assert "【资料边界】" in text


def test_run_query_returns_boundary_for_svsolver_break_end_prompt():
    text = run_query(
        "在流程后期，SVSolver 模块是如何对 DNAscope 输出的 Break-end (BND) 候选项进行组装与最终定型输出的？"
    )

    assert "【资料边界】" in text
    assert "具体参数名" not in text


def test_run_query_does_not_treat_module_support_prompt_as_capability_question():
    text = run_query("LongReadUtil 模块对 Oxford Nanopore 的三代单细胞 RNA 测序数据含有细胞条形码时，有哪些针对性的提取与 demultiplexing 支持？")

    assert "【资料边界】" in text
    assert "【能力说明】" not in text


def test_render_chat_response_sanitizes_stable_markdown_artifacts():
    rendered, streamed = render_chat_response(
        "介绍下 Sentieon",
        (
            "【模块介绍】\n"
            "**1. 比对模块（Alignment）**\n"
            "*   **Sentieon BWA:** 适用于短读长 DNA 比对。\n"
            "*   **使用流程：** 常见路径包括 `sentieon-cli`。"
        ),
    )

    assert streamed is False
    assert "**" not in rendered
    assert "`" not in rendered
    assert "*   " not in rendered
    assert "1. 比对模块（Alignment）" in rendered
    assert "- Sentieon BWA: 适用于短读长 DNA 比对。" in rendered
    assert "- 使用流程： 常见路径包括 sentieon-cli。" in rendered


def test_render_chat_response_keeps_parameter_disambiguation_stable_without_polish():
    generated_calls: list[str] = []
    streamed_calls: list[str] = []
    raw_response = (
        "需要确认模块：参数 --genotype_model 同时出现在多个模块中（GVCFtyper；Joint Call）。"
        "请补充模块名后再查询，例如：GVCFtyper 的 --genotype_model 是什么"
    )

    rendered, streamed = render_chat_response(
        "--genotype_model 是什么",
        raw_response,
        model_generate=lambda prompt, **kwargs: generated_calls.append(prompt) or "SHOULD_NOT_RUN",
        model_stream_generate=lambda prompt, on_chunk, **kwargs: streamed_calls.append(prompt) or "SHOULD_NOT_RUN",
    )

    assert rendered == raw_response
    assert streamed is False
    assert generated_calls == []
    assert streamed_calls == []


def test_render_chat_response_keeps_mvp_boundary_message_stable_without_polish():
    generated_calls: list[str] = []
    streamed_calls: list[str] = []
    raw_response = "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"

    rendered, streamed = render_chat_response(
        "有哪些功能",
        raw_response,
        model_generate=lambda prompt, **kwargs: generated_calls.append(prompt) or "SHOULD_NOT_RUN",
        model_stream_generate=lambda prompt, on_chunk, **kwargs: streamed_calls.append(prompt) or "SHOULD_NOT_RUN",
    )

    assert rendered == raw_response
    assert streamed is False
    assert generated_calls == []
    assert streamed_calls == []


def test_chat_loop_streams_model_output_chunks():
    prompts = iter(["license 报错", "/quit"])
    outputs: list[str] = []
    statuses: list[tuple[str, bool]] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    streamed: list[str] = []

    def fake_stream_generate(prompt: str, on_chunk, **kwargs) -> str:
        chunks = ["请告诉我", " Sentieon 版本号，例如 202503.03。"]
        for chunk in chunks:
            streamed.append(chunk)
            on_chunk(chunk)
        return "".join(chunks)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "SHOULD_NOT_BE_USED",
        model_stream_generate=fake_stream_generate,
        status_writer=lambda text, clear=False: statuses.append((text, clear)),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert streamed == ["请告诉我", " Sentieon 版本号，例如 202503.03。"]
    assert "请告诉我 Sentieon 版本号，例如 202503.03。" in "".join(outputs)
    assert any(clear for text, clear in statuses)


def test_chat_loop_keeps_mvp_boundary_message_fast_without_generation(monkeypatch):
    prompts = iter(["有哪些功能", "/quit"])
    outputs: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr(
        "sentieon_assist.cli.run_query",
        lambda query, **kwargs: "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。",
    )

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not polish boundary message")),
        model_stream_generate=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not stream boundary message")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    joined = "\n".join(outputs)
    assert "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。" in joined
    assert "正在生成回复" not in joined


def test_chat_loop_uses_default_stream_writer_when_no_stream_output_fn(monkeypatch):
    prompts = iter(["license 报错", "/quit"])
    outputs: list[str] = []
    streamed_chunks: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    monkeypatch.setattr("sentieon_assist.cli._default_stream_output_fn", streamed_chunks.append)

    def fake_stream_generate(prompt: str, on_chunk, **kwargs) -> str:
        for chunk in ["请告诉我", " Sentieon 版本号，例如 202503.03。"]:
            on_chunk(chunk)
        return "请告诉我 Sentieon 版本号，例如 202503.03。"

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_stream_generate=fake_stream_generate,
    )

    assert code == 0
    assert streamed_chunks == ["请告诉我", " Sentieon 版本号，例如 202503.03。", "\n"]
    assert not any(item == "请告诉我" for item in outputs)
    assert any("Sengent" in item for item in outputs)


def test_chat_loop_prefers_explicit_non_stream_model_generate_over_backend_stream(monkeypatch):
    prompts = iter(["Sentieon 202503 license 报错", "/quit"])
    outputs: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fail_if_stream_used(*args, **kwargs):
        raise AssertionError("stream backend should not be used when model_generate is explicitly injected")

    monkeypatch.setattr("sentieon_assist.cli._chat_model_stream_generate", fail_if_stream_used)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "【问题判断】\n这是一个 Sentieon license 相关问题。",
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert any("【问题判断】" in item for item in outputs)


def test_chat_loop_falls_back_to_non_stream_generate_when_stream_fails():
    prompts = iter(["license 报错", "/quit"])
    outputs: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: "请告诉我 Sentieon 版本号，例如 202503.03。",
        model_stream_generate=lambda prompt, on_chunk, **kwargs: (_ for _ in ()).throw(RuntimeError("stream failed")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert "请告诉我 Sentieon 版本号，例如 202503.03。" in "\n".join(outputs)


def test_chat_loop_carries_pending_question_context(monkeypatch):
    prompts = iter(["license 报错", "202503.03", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "license 报错":
            return "需要补充以下信息：Sentieon 版本"
        if query == "license 报错 202503.03":
            return "【问题判断】\n这是一个 Sentieon license 相关问题。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    generated_prompts: list[str] = []

    def fake_model_generate(prompt: str, **kwargs) -> str:
        generated_prompts.append(prompt)
        if "需要补充以下信息" in prompt:
            return "请告诉我 Sentieon 版本号，例如 202503.03。"
        return "【问题判断】\n这是一个 Sentieon license 相关问题。"

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=fake_model_generate,
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["license 报错", "license 报错 202503.03"]
    assert "请告诉我 Sentieon 版本号，例如 202503.03。" in "\n".join(outputs)
    assert any("【问题判断】" in item for item in outputs)
    assert generated_prompts


def test_chat_loop_reset_clears_pending_question(monkeypatch):
    prompts = iter(["license 报错", "/reset", "Sentieon 202503 license 报错", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "license 报错":
            return "需要补充以下信息：Sentieon 版本"
        if query == "Sentieon 202503 license 报错":
            return "【问题判断】\n这是一个 Sentieon license 相关问题。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (
            "请告诉我 Sentieon 版本号，例如 202503.03。"
            if "需要补充以下信息" in prompt
            else "【问题判断】\n这是一个 Sentieon license 相关问题。"
        ),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["license 报错", "Sentieon 202503 license 报错"]
    assert any("已清空当前补问上下文" in item for item in outputs)
    assert any("【问题判断】" in item for item in outputs)


def test_chat_loop_starts_new_query_when_pending_context_exists_but_user_enters_full_new_question(monkeypatch):
    prompts = iter(["license 报错", "Sentieon 202503 install 失败，命令不可用", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "license 报错":
            return "需要补充以下信息：Sentieon 版本"
        if query == "Sentieon 202503 install 失败，命令不可用":
            return "【问题判断】\n这是一个 Sentieon 安装相关问题。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (
            "请告诉我 Sentieon 版本号，例如 202503.03。"
            if "需要补充以下信息" in prompt
            else "【问题判断】\n这是一个 Sentieon 安装相关问题。"
        ),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["license 报错", "Sentieon 202503 install 失败，命令不可用"]
    assert any("安装相关问题" in item for item in outputs)


def test_chat_loop_carries_pending_parameter_disambiguation_context(monkeypatch):
    prompts = iter(["--genotype_model 是什么", "GVCFtyper", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "--genotype_model 是什么":
            return "需要确认模块：参数 --genotype_model 同时出现在多个模块中（GVCFtyper；Joint Call）。请补充模块名后再查询，例如：GVCFtyper 的 --genotype_model 是什么"
        if query == "--genotype_model 是什么 GVCFtyper":
            return "【资料查询】\n- 命中模块索引：GVCFtyper\n- 命中参数：--genotype_model"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: prompt,
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["--genotype_model 是什么", "--genotype_model 是什么 GVCFtyper"]
    assert any("需要确认模块" in item for item in outputs)
    assert any("命中模块索引：GVCFtyper" in item for item in outputs)


def test_chat_loop_carries_reference_context_for_script_followup(monkeypatch):
    prompts = iter(["介绍下 rnaseq", "示例脚本也可以", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "介绍下 rnaseq":
            return "【模块介绍】\nRNAseq：RNA 变异调用流程。\n\n【常用参数】\n- 可继续追问：RNAseq 参考脚本。"
        if query == "介绍下 rnaseq 示例脚本也可以":
            return "【模块介绍】\nRNAseq：...\n\n【参考命令】\n- RNA short-variant calling skeleton"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: prompt,
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["介绍下 rnaseq", "介绍下 rnaseq 示例脚本也可以"]
    assert any("RNA short-variant calling skeleton" in item for item in outputs)


def test_chat_loop_carries_reference_context_for_parameter_followup(monkeypatch):
    prompts = iter(["介绍下 dnascope", "参数呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "介绍下 dnascope":
            return "【模块介绍】\nDNAscope：短读长胚系主流程。\n\n【常用参数】\n- 可继续追问：DNAscope 的 --pcr_free 是什么。"
        if query == "介绍下 dnascope 参数呢":
            return "【常用参数】\nDNAscope 的 --pcr_free：按 PCR-free 文库模式调用。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: prompt,
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["介绍下 dnascope", "介绍下 dnascope 参数呢"]
    assert any("PCR-free" in item for item in outputs)


def test_chat_loop_carries_reference_context_for_workflow_fragment_followup(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "那 panel 呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是 WGS、WES 还是 panel。"
        if query == "我要做wgs分析，能给个示例脚本吗 那 panel 呢":
            return "【流程指导】\n- 这是 targeted panel 场景的流程分流问题。"
        if query == "那 panel 呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "我要做wgs分析，能给个示例脚本吗 那 panel 呢"]
    assert any("targeted panel" in item for item in outputs)


def test_chat_loop_carries_reference_context_for_long_read_fragment_followup(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "那 long-read 呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先按短读长/长读长分流。"
        if query == "我要做wgs分析，能给个示例脚本吗 那 long-read 呢":
            return "【流程指导】\n- 这是长读长 WGS 的官方流程分流问题。"
        if query == "那 long-read 呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "我要做wgs分析，能给个示例脚本吗 那 long-read 呢"]
    assert any("长读长 WGS" in item for item in outputs)


def test_chat_loop_canonicalizes_short_read_wgs_fragment_followup(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "那短读长呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先按胚系/体细胞和短读长/长读长分流。"
        if query == "我要做wgs分析，能给个示例脚本吗 那 short-read 呢":
            return "【流程指导】\n- 这是短读长 WGS 的流程分流问题。"
        if query == "那短读长呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "我要做wgs分析，能给个示例脚本吗 那 short-read 呢"]
    assert any("短读长 WGS" in item for item in outputs)


def test_chat_loop_reuses_wgs_anchor_for_polyploid_short_read_followup(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "我的是多倍体，wgs，短读长的", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先按胚系/体细胞和短读长/长读长分流。\n\n【需要确认的信息】\n- 是胚系还是体细胞？\n- 是短读长还是 PacBio HiFi / ONT 长读长？\n- 如果是短读长胚系，样本是否来自二倍体生物（diploid organism）？"
        if query == "我要做wgs分析，能给个示例脚本吗 我的是多倍体，wgs，短读长的":
            return "【参考命令】\n- sentieon bwa mem ...\n- --algo Haplotyper ..."
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == [
        "我要做wgs分析，能给个示例脚本吗",
        "我要做wgs分析，能给个示例脚本吗 我的是多倍体，wgs，短读长的",
    ]
    assert any("【参考命令】" in item for item in outputs)


def test_chat_loop_short_read_wes_panel_fragment_followup_for_wes(monkeypatch):
    prompts = iter(["我要做wes分析，能给个示例脚本吗", "那 short-read 呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wes分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是胚系还是体细胞。"
        if query == "我要做wes分析，能给个示例脚本吗 那 short-read 呢":
            return "【流程指导】\n- 这是短读长 WES 的流程分流问题。"
        if query == "那 short-read 呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wes分析，能给个示例脚本吗", "我要做wes分析，能给个示例脚本吗 那 short-read 呢"]
    assert any("短读长 WES" in item for item in outputs)


def test_chat_loop_short_read_wes_panel_fragment_followup_for_panel(monkeypatch):
    prompts = iter(["我要做panel分析，能给个示例脚本吗", "那短读长呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做panel分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是胚系还是体细胞。"
        if query == "我要做panel分析，能给个示例脚本吗 那 short-read 呢":
            return "【流程指导】\n- 这是短读长 panel 的流程分流问题。"
        if query == "那短读长呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做panel分析，能给个示例脚本吗", "我要做panel分析，能给个示例脚本吗 那 short-read 呢"]
    assert any("短读长 panel" in item for item in outputs)


def test_chat_loop_canonicalizes_hybrid_followup_from_joint_analysis_phrase(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "那联合分析呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先按胚系/体细胞和短读长/长读长分流。"
        if query == "我要做wgs分析，能给个示例脚本吗 那 hybrid 呢":
            return "【流程指导】\n- 这是 hybrid 联合分析的流程分流问题。"
        if query == "那联合分析呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "我要做wgs分析，能给个示例脚本吗 那 hybrid 呢"]
    assert any("hybrid 联合分析" in item for item in outputs)


def test_chat_loop_canonicalizes_hybrid_followup_from_joint_input_phrase(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "那 short-read + long-read 呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先按胚系/体细胞和短读长/长读长分流。"
        if query == "我要做wgs分析，能给个示例脚本吗 那 hybrid 呢":
            return "【流程指导】\n- 这是 hybrid 联合分析的流程分流问题。"
        if query == "那 short-read + long-read 呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "我要做wgs分析，能给个示例脚本吗 那 hybrid 呢"]
    assert any("hybrid 联合分析" in item for item in outputs)


def test_chat_loop_carries_reference_context_for_fastq_fragment_followup(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "那 FASTQ 呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先按胚系/体细胞和输入形态分流。"
        if query == "我要做wgs分析，能给个示例脚本吗 那 FASTQ 呢":
            return "【流程指导】\n- 这是 WGS 下基于 FASTQ 输入的流程分流问题。"
        if query == "那 FASTQ 呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "我要做wgs分析，能给个示例脚本吗 那 FASTQ 呢"]
    assert any("FASTQ" in item for item in outputs)


def test_chat_loop_carries_reference_context_for_bam_fragment_followup(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "那 BAM 呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先按胚系/体细胞和输入形态分流。"
        if query == "我要做wgs分析，能给个示例脚本吗 那 BAM 呢":
            return "【流程指导】\n- 这是 WGS 下基于已对齐 BAM/CRAM 输入的流程分流问题。"
        if query == "那 BAM 呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "我要做wgs分析，能给个示例脚本吗 那 BAM 呢"]
    assert any("BAM/CRAM" in item for item in outputs)


def test_chat_loop_carries_reference_context_for_ont_fragment_followup(monkeypatch):
    prompts = iter(["我要做long-read分析，能给个示例脚本吗", "那 ONT 呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做long-read分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是 PacBio HiFi 还是 ONT。"
        if query == "我要做long-read分析，能给个示例脚本吗 那 ONT 呢":
            return "【流程指导】\n- 这是 long-read 场景里 ONT 平台的流程分流问题。"
        if query == "那 ONT 呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做long-read分析，能给个示例脚本吗", "我要做long-read分析，能给个示例脚本吗 那 ONT 呢"]
    assert any("ONT" in item for item in outputs)


def test_chat_loop_carries_reference_context_for_hifi_fragment_followup(monkeypatch):
    prompts = iter(["我要做long-read分析，能给个示例脚本吗", "那 HiFi 呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做long-read分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是 PacBio HiFi 还是 ONT。"
        if query == "我要做long-read分析，能给个示例脚本吗 那 HiFi 呢":
            return "【流程指导】\n- 这是 long-read 场景里 PacBio HiFi 平台的流程分流问题。"
        if query == "那 HiFi 呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做long-read分析，能给个示例脚本吗", "我要做long-read分析，能给个示例脚本吗 那 HiFi 呢"]
    assert any("HiFi" in item for item in outputs)


def test_chat_loop_canonicalizes_paired_somatic_fragment_followup(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "那配对呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先按胚系/体细胞分流。"
        if query == "我要做wgs分析，能给个示例脚本吗 那 tumor-normal 呢":
            return "【流程指导】\n- 这是有 matched normal 的体细胞 WGS 流程分流问题。"
        if query == "那配对呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "我要做wgs分析，能给个示例脚本吗 那 tumor-normal 呢"]
    assert any("体细胞 WGS" in item for item in outputs)


def test_chat_loop_canonicalizes_unpaired_somatic_fragment_followup(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "那无对照呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先按胚系/体细胞分流。"
        if query == "我要做wgs分析，能给个示例脚本吗 那 tumor-only 呢":
            return "【流程指导】\n- 这是没有 matched normal 的体细胞 WGS 流程分流问题。"
        if query == "那无对照呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "我要做wgs分析，能给个示例脚本吗 那 tumor-only 呢"]
    assert any("体细胞 WGS" in item for item in outputs)


def test_chat_loop_canonicalizes_paired_somatic_wes_fragment_followup(monkeypatch):
    prompts = iter(["我要做wes分析，能给个示例脚本吗", "那配对呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wes分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是胚系还是体细胞。"
        if query == "我要做wes分析，能给个示例脚本吗 那 tumor-normal 呢":
            return "【流程指导】\n- 这是有 matched normal 的体细胞 WES 流程分流问题。"
        if query == "那配对呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wes分析，能给个示例脚本吗", "我要做wes分析，能给个示例脚本吗 那 tumor-normal 呢"]
    assert any("体细胞 WES" in item for item in outputs)


def test_chat_loop_canonicalizes_unpaired_somatic_panel_fragment_followup(monkeypatch):
    prompts = iter(["我要做panel分析，能给个示例脚本吗", "那无对照呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做panel分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是胚系还是体细胞。"
        if query == "我要做panel分析，能给个示例脚本吗 那 tumor-only 呢":
            return "【流程指导】\n- 这是没有 matched normal 的体细胞 panel 流程分流问题。"
        if query == "那无对照呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做panel分析，能给个示例脚本吗", "我要做panel分析，能给个示例脚本吗 那 tumor-only 呢"]
    assert any("体细胞 panel" in item for item in outputs)


def test_chat_loop_canonicalizes_semantic_fragment_followup_for_somatic_wes(monkeypatch):
    prompts = iter(["我要做wes分析，能给个示例脚本吗", "那体细胞呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wes分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是胚系还是体细胞。"
        if query == "我要做wes分析，能给个示例脚本吗 那 somatic 呢":
            return "【流程指导】\n- 这是体细胞 WES 的流程分流问题。"
        if query == "那体细胞呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wes分析，能给个示例脚本吗", "我要做wes分析，能给个示例脚本吗 那 somatic 呢"]
    assert any("体细胞 WES" in item for item in outputs)


def test_chat_loop_canonicalizes_semantic_fragment_followup_for_somatic_panel(monkeypatch):
    prompts = iter(["我要做panel分析，能给个示例脚本吗", "那体细胞呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做panel分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是胚系还是体细胞。"
        if query == "我要做panel分析，能给个示例脚本吗 那 somatic 呢":
            return "【流程指导】\n- 这是体细胞 panel 的流程分流问题。"
        if query == "那体细胞呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做panel分析，能给个示例脚本吗", "我要做panel分析，能给个示例脚本吗 那 somatic 呢"]
    assert any("体细胞 panel" in item for item in outputs)


def test_chat_loop_canonicalizes_semantic_fragment_followup_for_germline_panel(monkeypatch):
    prompts = iter(["我要做panel分析，能给个示例脚本吗", "那胚系呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做panel分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是胚系还是体细胞。"
        if query == "我要做panel分析，能给个示例脚本吗 那 germline 呢":
            return "【流程指导】\n- 这是胚系 panel 的流程分流问题。"
        if query == "那胚系呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做panel分析，能给个示例脚本吗", "我要做panel分析，能给个示例脚本吗 那 germline 呢"]
    assert any("胚系 panel" in item for item in outputs)


def test_chat_loop_reset_clears_reference_context(monkeypatch):
    prompts = iter(["介绍下 rnaseq", "/reset", "示例脚本也可以", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "介绍下 rnaseq":
            return "【模块介绍】\nRNAseq：RNA 变异调用流程。"
        if query == "示例脚本也可以":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: prompt,
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["介绍下 rnaseq", "示例脚本也可以"]
    assert any("已清空当前补问上下文" in item for item in outputs)


def test_chat_loop_reference_context_does_not_reuse_for_ambiguous_reference_other_followup(monkeypatch):
    prompts = iter(["介绍下 rnaseq", "还有别的吗", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "介绍下 rnaseq":
            return "【模块介绍】\nRNAseq：RNA 变异调用流程。"
        if query == "还有别的吗":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: '{"intent":"reference_other","confidence":0.87}',
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["介绍下 rnaseq", "还有别的吗"]


def test_chat_loop_reference_context_does_not_reuse_for_deictic_followup_without_model(monkeypatch):
    prompts = iter(["我要做wgs分析，能给个示例脚本吗", "那这个呢", "/quit"])
    outputs: list[str] = []
    seen_queries: list[str] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    def fake_run_query(query: str, **kwargs) -> str:
        seen_queries.append(query)
        if query == "我要做wgs分析，能给个示例脚本吗":
            return "【流程指导】\n- 先确认是 WGS、WES 还是 panel。"
        if query == "那这个呢":
            return "当前 MVP 仅支持 license 和 install 问题，请补充更明确的问题类型。"
        raise AssertionError(f"unexpected query: {query}")

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    code = main(
        ["chat"],
        input_fn=fake_input,
        output_fn=fake_output,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        model_generate=lambda prompt, **kwargs: (_ for _ in ()).throw(AssertionError("should not call model")),
        stream_output_fn=outputs.append,
    )

    assert code == 0
    assert seen_queries == ["我要做wgs分析，能给个示例脚本吗", "那这个呢"]


def test_chat_mode_requires_local_model(monkeypatch):
    outputs: list[str] = []

    code = main(
        ["chat"],
        input_fn=lambda prompt: "/quit",
        output_fn=outputs.append,
        api_probe=lambda base_url: {"ok": True, "model_available": False, "version": "0.20.0"},
    )

    assert code == 2
    assert any("gemma4:e4b" in item for item in outputs)
    assert any("不可用" in item for item in outputs)


def test_chat_mode_warms_up_model_before_loop():
    outputs: list[str] = []
    warmup_calls: list[tuple[str, str]] = []

    code = main(
        ["chat"],
        input_fn=lambda prompt: "/quit",
        output_fn=outputs.append,
        api_probe=lambda base_url: {"ok": True, "model_available": True, "version": "0.20.0"},
        warmup_model=lambda model, base_url: warmup_calls.append((model, base_url)),
    )

    assert code == 0
    assert warmup_calls == [("gemma4:e4b", "http://127.0.0.1:11434")]


def test_run_query_passes_source_directory_to_answer_query(monkeypatch):
    monkeypatch.setattr("sentieon_assist.cli.classify_query", lambda query: "install")
    monkeypatch.setattr(
        "sentieon_assist.cli.extract_info_from_query",
        lambda query: {
            "version": "202503",
            "input_type": "",
            "error": "Sentieon 202503 install 失败",
            "error_keywords": "",
            "step": "install",
            "data_type": "",
        },
    )
    monkeypatch.setattr("sentieon_assist.cli.next_state", lambda current_state, has_missing_info: "ANSWERED")

    seen: dict[str, str] = {}

    def fake_answer_query(issue_type, query, info, **kwargs):
        seen["source_directory"] = kwargs["source_directory"]
        return "OK"

    monkeypatch.setattr("sentieon_assist.cli.answer_query", fake_answer_query)

    text = run_query("Sentieon 202503 install 失败", source_directory="/tmp/custom-sources")
    assert text == "OK"
    assert seen["source_directory"] == "/tmp/custom-sources"


def test_run_query_routes_semantic_reference_query_to_reference_answer(monkeypatch):
    monkeypatch.setattr("sentieon_assist.cli.classify_query", lambda query: "other")
    monkeypatch.setattr("sentieon_assist.cli.is_reference_query", lambda query: False)

    from sentieon_assist.reference_intents import ReferenceIntent

    monkeypatch.setattr(
        "sentieon_assist.cli.parse_reference_intent",
        lambda query, **kwargs: ReferenceIntent(intent="module_overview", confidence=0.88),
    )

    seen: dict[str, str] = {}

    def fake_answer_reference_query(query, **kwargs):
        seen["query"] = query
        seen["source_directory"] = kwargs["source_directory"]
        return "【模块介绍】\nSentieon 主要模块可以先按 6 组理解。"

    monkeypatch.setattr("sentieon_assist.cli.answer_reference_query", fake_answer_reference_query)

    text = run_query("sentieon都有哪些模块", source_directory="/tmp/custom-sources")

    assert text == "【模块介绍】\nSentieon 主要模块可以先按 6 组理解。"
    assert seen["query"] == "sentieon都有哪些模块"
    assert seen["source_directory"] == "/tmp/custom-sources"


def test_run_query_trace_collector_receives_reference_resolver_metadata():
    seen: dict[str, object] = {}

    text = run_query(
        "为什么我的服务器明明有 128 个核心，但 Sentieon 运行时似乎只占用了很少的 CPU 资源？",
        trace_collector=lambda trace: seen.update(trace),
    )

    assert "【资料说明】" in text
    assert seen["sources"]
    assert seen["resolver_path"] == ["doc_reference"]
    assert seen["boundary_tags"] == []


def test_run_query_trace_collector_receives_troubleshooting_metadata():
    seen: dict[str, object] = {}

    text = run_query(
        "Sentieon 202503 license 报错，找不到 license 文件",
        trace_collector=lambda trace: seen.update(trace),
    )

    assert "【问题判断】" in text
    assert seen["sources"] == []
    assert seen["resolver_path"] == ["troubleshooting_rule"]
    assert seen["boundary_tags"] == []


def test_run_query_routes_semantic_script_query_to_reference_answer(monkeypatch):
    monkeypatch.setattr("sentieon_assist.cli.classify_query", lambda query: "other")
    monkeypatch.setattr("sentieon_assist.cli.is_reference_query", lambda query: False)

    from sentieon_assist.reference_intents import ReferenceIntent

    monkeypatch.setattr(
        "sentieon_assist.cli.parse_reference_intent",
        lambda query, **kwargs: ReferenceIntent(intent="script_example", module="RNAseq", confidence=0.9),
    )

    seen: dict[str, object] = {}

    def fake_answer_reference_query(query, **kwargs):
        seen["query"] = query
        seen["parsed_intent"] = kwargs["parsed_intent"]
        return "【参考命令】\nRNA short-variant calling skeleton"

    monkeypatch.setattr("sentieon_assist.cli.answer_reference_query", fake_answer_reference_query)

    text = run_query("能给个 rnaseq 的参考脚本吗")

    assert text == "【参考命令】\nRNA short-variant calling skeleton"
    assert seen["query"] == "能给个 rnaseq 的参考脚本吗"
    assert getattr(seen["parsed_intent"], "intent", "") == "script_example"


def test_run_query_passes_semantic_intent_even_when_reference_rule_also_matches(monkeypatch):
    monkeypatch.setattr("sentieon_assist.cli.classify_query", lambda query: "other")
    monkeypatch.setattr("sentieon_assist.cli.is_reference_query", lambda query: True)

    from sentieon_assist.reference_intents import ReferenceIntent

    monkeypatch.setattr(
        "sentieon_assist.cli.parse_reference_intent",
        lambda query, **kwargs: ReferenceIntent(intent="script_example", module="Joint Call", confidence=0.92),
    )

    seen: dict[str, object] = {}

    def fake_answer_reference_query(query, **kwargs):
        seen["parsed_intent"] = kwargs["parsed_intent"]
        return "【参考命令】\nGVCFtyper joint-calling skeleton"

    monkeypatch.setattr("sentieon_assist.cli.answer_reference_query", fake_answer_reference_query)

    text = run_query("joint call 的参考命令是什么")

    assert text == "【参考命令】\nGVCFtyper joint-calling skeleton"
    assert getattr(seen["parsed_intent"], "intent", "") == "script_example"


def test_run_query_routes_semantic_workflow_guidance_query_to_reference_answer(monkeypatch):
    monkeypatch.setattr("sentieon_assist.cli.classify_query", lambda query: "other")
    monkeypatch.setattr("sentieon_assist.cli.is_reference_query", lambda query: False)

    from sentieon_assist.reference_intents import ReferenceIntent

    monkeypatch.setattr(
        "sentieon_assist.cli.parse_reference_intent",
        lambda query, **kwargs: ReferenceIntent(intent="workflow_guidance", confidence=0.93),
    )

    seen: dict[str, object] = {}

    def fake_answer_reference_query(query, **kwargs):
        seen["query"] = query
        seen["parsed_intent"] = kwargs["parsed_intent"]
        return "【流程指导】\n- 先按胚系/体细胞和短读长/长读长分流。"

    monkeypatch.setattr("sentieon_assist.cli.answer_reference_query", fake_answer_reference_query)

    text = run_query("如果我要做wgs分析，能不能给个指导")

    assert text == "【流程指导】\n- 先按胚系/体细胞和短读长/长读长分流。"
    assert seen["query"] == "如果我要做wgs分析，能不能给个指导"
    assert getattr(seen["parsed_intent"], "intent", "") == "workflow_guidance"


def test_run_query_routes_semantic_external_error_query_to_reference_answer(monkeypatch):
    monkeypatch.setattr("sentieon_assist.cli.classify_query", lambda query: "other")
    monkeypatch.setattr("sentieon_assist.cli.is_reference_query", lambda query: False)

    from sentieon_assist.reference_intents import ReferenceIntent

    monkeypatch.setattr(
        "sentieon_assist.cli.parse_reference_intent",
        lambda query, **kwargs: ReferenceIntent(intent="reference_other", confidence=0.93),
    )

    seen: dict[str, object] = {}

    def fake_answer_reference_query(query, **kwargs):
        seen["query"] = query
        seen["parsed_intent"] = kwargs["parsed_intent"]
        return "【资料查询】\n- 命中外部错误关联：Read Group / header inconsistency\n\n【关联判断】\n- 这更像是 BAM header 里的 Read Group 组织不一致。"

    monkeypatch.setattr("sentieon_assist.cli.answer_reference_query", fake_answer_reference_query)

    text = run_query("BAM 报错说 read group 不一致怎么办")

    assert "【关联判断】" in text
    assert seen["query"] == "BAM 报错说 read group 不一致怎么办"
    assert getattr(seen["parsed_intent"], "intent", "") == "reference_other"


def test_run_query_routes_semantic_external_explanatory_query_to_reference_answer(monkeypatch):
    monkeypatch.setattr("sentieon_assist.cli.classify_query", lambda query: "other")
    monkeypatch.setattr("sentieon_assist.cli.is_reference_query", lambda query: False)

    from sentieon_assist.reference_intents import ReferenceIntent

    monkeypatch.setattr(
        "sentieon_assist.cli.parse_reference_intent",
        lambda query, **kwargs: ReferenceIntent(intent="reference_other", confidence=0.9),
    )

    seen: dict[str, object] = {}

    def fake_answer_reference_query(query, **kwargs):
        seen["query"] = query
        seen["parsed_intent"] = kwargs["parsed_intent"]
        return "【资料说明】\nFastQC：原始测序数据质量控制工具。"

    monkeypatch.setattr("sentieon_assist.cli.answer_reference_query", fake_answer_reference_query)

    text = run_query("FastQC 是做什么的")

    assert text == "【资料说明】\nFastQC：原始测序数据质量控制工具。"
    assert seen["query"] == "FastQC 是做什么的"
    assert getattr(seen["parsed_intent"], "intent", "") == "reference_other"


def test_run_query_routes_shell_query_to_reference_answer(monkeypatch):
    monkeypatch.setattr("sentieon_assist.cli.classify_query", lambda query: "other")
    monkeypatch.setattr("sentieon_assist.cli.is_reference_query", lambda query: False)

    seen: dict[str, object] = {}

    def fake_answer_reference_query(query, **kwargs):
        seen["query"] = query
        seen["parsed_intent"] = kwargs["parsed_intent"]
        return "【资料说明】\nShell quoting / pipeline basics"

    monkeypatch.setattr("sentieon_assist.cli.answer_reference_query", fake_answer_reference_query)

    text = run_query("bash 的引号和管道怎么用")

    assert text == "【资料说明】\nShell quoting / pipeline basics"
    assert seen["query"] == "bash 的引号和管道怎么用"
    assert getattr(seen["parsed_intent"], "intent", "") == "reference_other"


def test_run_query_prefers_sentieon_module_script_query_over_shell_terms(monkeypatch):
    monkeypatch.setattr("sentieon_assist.cli.classify_query", lambda query: "other")
    monkeypatch.setattr("sentieon_assist.cli.is_reference_query", lambda query: False)

    seen: dict[str, object] = {}

    def fake_answer_reference_query(query, **kwargs):
        seen["query"] = query
        seen["parsed_intent"] = kwargs["parsed_intent"]
        return "【参考命令】\nDNAscope script"

    monkeypatch.setattr("sentieon_assist.cli.answer_reference_query", fake_answer_reference_query)

    text = run_query("DNAscope 的 bash 脚本")

    assert text == "【参考命令】\nDNAscope script"
    assert seen["query"] == "DNAscope 的 bash 脚本"
    assert getattr(seen["parsed_intent"], "intent", "") == "script_example"


def test_run_query_routes_broad_capability_prompt_to_support_explanation():
    text = run_query("你能做什么")

    assert "我可以帮你做这些 Sentieon 技术支持工作" in text
    assert "当前 MVP 仅支持 license 和 install 问题" not in text


def test_run_query_routes_sentieon_capability_prompt_to_support_explanation():
    text = run_query("你不是可以提供sentieon的功能吗")

    assert "我可以帮你做这些 Sentieon 技术支持工作" in text
    assert "当前 MVP 仅支持 license 和 install 问题" not in text


def test_main_passes_override_directories_to_run_query(monkeypatch):
    seen: dict[str, str] = {}

    def fake_run_query(query: str, **kwargs) -> str:
        seen["knowledge_directory"] = kwargs["knowledge_directory"]
        seen["source_directory"] = kwargs["source_directory"]
        return "OK"

    monkeypatch.setattr("sentieon_assist.cli.run_query", fake_run_query)

    outputs: list[str] = []
    code = main(
        [
            "--knowledge-dir",
            "/tmp/custom-knowledge",
            "--source-dir",
            "/tmp/custom-sources",
            "Sentieon",
            "202503",
            "install",
            "失败",
        ],
        output_fn=outputs.append,
    )
    assert code == 0
    assert outputs == ["OK"]
    assert seen["knowledge_directory"] == "/tmp/custom-knowledge"
    assert seen["source_directory"] == "/tmp/custom-sources"


def test_main_passes_override_source_directory_to_search(monkeypatch):
    seen: dict[str, str] = {}

    def fake_print_search_results(keyword: str, **kwargs) -> int:
        seen["keyword"] = keyword
        seen["source_directory"] = kwargs["source_directory"]
        return 0

    monkeypatch.setattr("sentieon_assist.cli.print_search_results", fake_print_search_results)

    code = main(["--source-dir", "/tmp/custom-sources", "search", "SENTIEON_LICENSE"])
    assert code == 0
    assert seen["keyword"] == "SENTIEON_LICENSE"
    assert seen["source_directory"] == "/tmp/custom-sources"


def test_main_prints_doctor_report(monkeypatch):
    monkeypatch.setattr("sentieon_assist.cli.gather_doctor_report", lambda **kwargs: {"status": "ok"})
    monkeypatch.setattr("sentieon_assist.cli.format_doctor_report", lambda report: "DOCTOR_OK")

    outputs: list[str] = []
    code = main(["doctor"], output_fn=outputs.append)

    assert code == 0
    assert outputs == ["DOCTOR_OK"]


def test_cli_knowledge_activate_rejects_incomplete_candidate_pack_set(tmp_path: Path):
    source_dir = tmp_path / "sentieon-note"
    _write_activation_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"
    build_id = "build-missing-pack"
    build_dir = build_root / build_id
    candidate_dir = build_dir / "candidate-packs"
    candidate_dir.mkdir(parents=True)
    (candidate_dir / "sentieon-modules.json").write_text(
        json.dumps({"version": "", "entries": [{"id": "fastdedup", "name": "FastDedup"}]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (candidate_dir / "workflow-guides.json").write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    (candidate_dir / "external-format-guides.json").write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    (candidate_dir / "external-error-associations.json").write_text('{"version":"","entries":[]}\n', encoding="utf-8")
    (candidate_dir / "manifest.json").write_text('{"status":"candidate_only"}\n', encoding="utf-8")
    (build_dir / "pilot-readiness-report.json").write_text('{"ok": true}\n', encoding="utf-8")
    (build_dir / "pilot-closed-loop-report.json").write_text('{"ok": true}\n', encoding="utf-8")

    outputs: list[str] = []
    code = main(
        [
            "--source-dir",
            str(source_dir),
            "knowledge",
            "activate",
            "--build-root",
            str(build_root),
            "--build-id",
            build_id,
        ],
        output_fn=outputs.append,
    )

    assert code == 2
    assert any("external-tool-guides.json" in item for item in outputs)


def test_cli_knowledge_rollback_rejects_incomplete_backup_pack_set(tmp_path: Path):
    source_dir = tmp_path / "sentieon-note"
    _write_activation_source_packs(source_dir)
    build_root = tmp_path / "runtime" / "knowledge-build"
    backup_dir = build_root / "activation-backups" / "broken-backup"
    backup_dir.mkdir(parents=True)
    (backup_dir / "manifest.json").write_text(
        json.dumps(
            {
                "backup_id": "broken-backup",
                "source_directory": str(source_dir),
                "source_files": [
                    "sentieon-modules.json",
                    "workflow-guides.json",
                    "external-format-guides.json",
                    "external-tool-guides.json",
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for name in (
        "sentieon-modules.json",
        "workflow-guides.json",
        "external-format-guides.json",
        "external-tool-guides.json",
    ):
        (backup_dir / name).write_text('{"version":"","entries":[]}\n', encoding="utf-8")

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
            "broken-backup",
        ],
        output_fn=outputs.append,
    )

    assert code == 2
    assert any("external-error-associations.json" in item for item in outputs)


def test_sources_command_prints_source_names(tmp_path):
    (tmp_path / "guide.pdf").write_text("fake")
    outputs: list[str] = []

    def fake_output(message: str) -> None:
        outputs.append(message)

    code = main(["sources"], output_fn=fake_output, source_directory=str(tmp_path))
    assert code == 0
    assert any("guide.pdf" in item for item in outputs)
    assert any("[other]" in item for item in outputs)


def test_search_command_prints_match_snippet(tmp_path):
    (tmp_path / "notes.md").write_text("prefix SENTIEON_LICENSE suffix")
    outputs: list[str] = []

    def fake_output(message: str) -> None:
        outputs.append(message)

    code = main(["search", "SENTIEON_LICENSE"], output_fn=fake_output, source_directory=str(tmp_path))
    assert code == 0
    assert any("notes.md" in item for item in outputs)
    assert any("[other]" in item for item in outputs)
    assert any("SENTIEON_LICENSE" in item for item in outputs)
