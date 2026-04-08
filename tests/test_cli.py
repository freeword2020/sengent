import sys

from sentieon_assist.cli import main
from sentieon_assist.cli import run_query


def test_cli_requires_query(capsys):
    code = main([])
    out = capsys.readouterr().out
    assert code == 2
    assert "query is required" in out


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


def test_chat_loop_answers_once_and_quits():
    prompts = iter(["Sentieon 202503 license 报错", "/quit"])
    outputs: list[str] = []
    statuses: list[tuple[str, bool]] = []

    def fake_input(_prompt: str) -> str:
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
    assert any("进入交互模式" in item for item in outputs)
    assert any("【问题判断】" in item for item in outputs)
    assert any("已退出" in item for item in outputs)
    assert statuses
    assert any(text.startswith("思考中") for text, clear in statuses if not clear)
    assert any(clear for text, clear in statuses)


def test_chat_loop_streams_model_output_chunks():
    prompts = iter(["Sentieon 202503 license 报错", "/quit"])
    outputs: list[str] = []
    statuses: list[tuple[str, bool]] = []

    def fake_input(_prompt: str) -> str:
        return next(prompts)

    def fake_output(message: str) -> None:
        outputs.append(message)

    streamed: list[str] = []

    def fake_stream_generate(prompt: str, on_chunk, **kwargs) -> str:
        chunks = ["【问题判断】\n", "这是一个 Sentieon license 相关问题。"]
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
    assert streamed == ["【问题判断】\n", "这是一个 Sentieon license 相关问题。"]
    assert any("【问题判断】" in item for item in outputs)
    assert any(clear for text, clear in statuses)


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
    assert "请告诉我 Sentieon 版本号，例如 202503.03。" in outputs


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
    assert "请告诉我 Sentieon 版本号，例如 202503.03。" in outputs
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
