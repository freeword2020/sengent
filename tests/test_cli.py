import sys

from sentieon_assist.cli import _build_input_prompt
from sentieon_assist.cli import main
from sentieon_assist.cli import render_chat_response
from sentieon_assist.cli import run_query


class FakeTTY:
    def __init__(self, is_tty: bool) -> None:
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty


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
    assert any(text.startswith("正在思考中") for text, clear in statuses if not clear)
    assert any(clear for text, clear in statuses)
    assert input_prompts
    assert input_prompts[0] == "Sengent> "


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
