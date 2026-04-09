from __future__ import annotations

import re
import sys
import threading
from pathlib import Path
from typing import Any, Callable

from sentieon_assist.answering import (
    answer_query,
    answer_reference_query,
    format_capability_explanation_answer,
    missing_required_fields,
    normalize_model_answer,
)
from sentieon_assist.chat_events import event_generate_reply
from sentieon_assist.chat_ui import ChatUI, build_console
from sentieon_assist.classifier import classify_query, is_reference_query
from sentieon_assist.config import load_config
from sentieon_assist.doctor import format_doctor_report, gather_doctor_report
from sentieon_assist.external_guides import is_external_error_query
from sentieon_assist.extractor import extract_info_from_query
from sentieon_assist.feedback_runtime import (
    FeedbackTurnSnapshot,
    append_feedback_record,
    build_feedback_record,
    default_feedback_path,
    format_chat_help,
    format_feedback_hint,
    normalize_expected_mode,
    normalize_expected_task,
    normalize_feedback_scope,
)
from sentieon_assist.llm_backends import build_backend_router
from sentieon_assist.prompts import build_chat_missing_info_prompt, build_chat_polish_prompt
from sentieon_assist.reference_intents import parse_reference_intent
from sentieon_assist.sources import list_sources, search_sources
from sentieon_assist.state_machine import next_state
from sentieon_assist.support_coordinator import plan_support_turn, select_support_route, update_support_state
from sentieon_assist.support_state import SupportSessionState

try:
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None

PROMPT_LABEL = "Sengent>"
PROMPT_STYLE_PREFIX = "\x1b[1;38;5;208m"
PROMPT_STYLE_SUFFIX = "\x1b[0m"
DEICTIC_REFERENCE_FOLLOWUP_PATTERN = re.compile(
    r"^(?:这个|那个|那这个|这条|那条|这一条|那一条)(?:模块|流程|方向|方案)?(?:呢|怎么样|咋样|如何)?$"
)
REFERENCE_FOLLOWUP_CANONICAL_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:配对|有对照|有matchednormal|matchednormal|tumor[- ]normal|肿瘤配对|肿瘤对照)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 tumor-normal 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:无对照|没对照|没有对照|无matchednormal|tumor[- ]only|单肿瘤|单样本肿瘤)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 tumor-only 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:体细胞(?:的)?|somatic|肿瘤(?:的)?)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 somatic 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:胚系(?:的)?|germline)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 germline 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:短读长|short[- ]read)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 short-read 呢",
    ),
    (
        re.compile(
            r"(?:那|如果换成|换成|改成|改走)?\s*(?:hybrid|联合分析|short[- ]read\s*\+\s*long[- ]read|short\s+read\s*\+\s*long\s+read|短读长\s*\+\s*长读长)\s*(?:呢|的话呢|怎么样|如何)?$"
        ),
        "那 hybrid 呢",
    ),
)


def _default_status_writer(text: str, *, clear: bool = False) -> None:
    if clear:
        sys.stdout.write("\r" + (" " * 32) + "\r")
    else:
        sys.stdout.write("\r" + text)
    sys.stdout.flush()


def _default_stream_output_fn(chunk: str) -> None:
    sys.stdout.write(chunk)
    sys.stdout.flush()


def _build_input_prompt(
    *,
    input_fn=input,
    stdin=None,
    stdout=None,
) -> str:
    prompt = f"{PROMPT_LABEL} "
    effective_stdin = sys.stdin if stdin is None else stdin
    effective_stdout = sys.stdout if stdout is None else stdout
    if input_fn is not input:
        return prompt
    if not getattr(effective_stdin, "isatty", lambda: False)():
        return prompt
    if not getattr(effective_stdout, "isatty", lambda: False)():
        return prompt
    return f"{PROMPT_STYLE_PREFIX}{PROMPT_LABEL}{PROMPT_STYLE_SUFFIX} "


def start_thinking_animation(
    *,
    status_writer: Callable[..., None] | None = None,
    interval_seconds: float = 0.2,
    label: str = "思考中",
) -> Callable[[], None]:
    writer = status_writer or _default_status_writer
    frames = (f"{label}.", f"{label}..", f"{label}...")
    stop_event = threading.Event()
    writer(frames[0], clear=False)

    def animate() -> None:
        index = 1
        while not stop_event.wait(interval_seconds):
            writer(frames[index % len(frames)], clear=False)
            index += 1

    thread = threading.Thread(target=animate, daemon=True)
    thread.start()

    def stop() -> None:
        if stop_event.is_set():
            return
        stop_event.set()
        thread.join(timeout=interval_seconds)
        writer("", clear=True)

    return stop


def require_chat_model(
    *,
    api_probe: Callable[[str], dict[str, Any]] | None = None,
) -> None:
    config = load_config()
    probe = api_probe or (lambda base_url: build_backend_router(config).probe_primary())
    result = probe(config.ollama_base_url)
    if not result.get("ok") or not result.get("model_available"):
        raise RuntimeError(f"本地 Ollama 模型不可用：{config.ollama_model}")


def _chat_model_generate(
    prompt: str,
    *,
    model_generate: Callable[..., str] | None = None,
) -> str:
    if model_generate is not None:
        return model_generate(prompt)
    return build_backend_router(load_config()).generate(prompt)


def _chat_model_stream_generate(
    prompt: str,
    *,
    on_chunk: Callable[[str], None],
    model_stream_generate: Callable[..., str] | None = None,
) -> str:
    if model_stream_generate is not None:
        return model_stream_generate(prompt, on_chunk=on_chunk)
    return build_backend_router(load_config()).generate_stream(prompt, on_chunk=on_chunk)


def _is_stable_chat_response(raw_response: str) -> bool:
    stable_prefixes = (
        "【",
        "需要确认模块",
        "当前 MVP",
        "未在本地资料中找到相关模块或参数",
    )
    return raw_response.startswith(stable_prefixes)


def render_chat_response(
    query: str,
    raw_response: str,
    *,
    model_generate: Callable[..., str] | None = None,
    model_stream_generate: Callable[..., str] | None = None,
    stream_output_fn: Callable[[str], None] | None = None,
    clear_status_fn: Callable[[], None] | None = None,
) -> tuple[str, bool]:
    if _is_stable_chat_response(raw_response):
        if clear_status_fn is not None:
            clear_status_fn()
        return normalize_model_answer(raw_response).strip(), False
    prompt = build_chat_polish_prompt(query, raw_response)
    if raw_response.startswith("需要补充以下信息"):
        prompt = build_chat_missing_info_prompt(query, raw_response)
    should_try_stream = stream_output_fn is not None and (model_stream_generate is not None or model_generate is None)
    if should_try_stream:
        streamed_chunks: list[str] = []
        saw_chunk = False
        try:
            text = _chat_model_stream_generate(
                prompt,
                on_chunk=lambda chunk: _handle_stream_chunk(
                    chunk,
                    streamed_chunks,
                    stream_output_fn,
                    clear_status_fn,
                ),
                model_stream_generate=model_stream_generate,
            )
            saw_chunk = bool(streamed_chunks)
            if saw_chunk:
                stream_output_fn("\n")
                return "".join(streamed_chunks).strip() or text.strip(), True
            if clear_status_fn is not None:
                clear_status_fn()
            return text.strip(), False
        except RuntimeError:
            pass
    text = _chat_model_generate(prompt, model_generate=model_generate).strip()
    if clear_status_fn is not None:
        clear_status_fn()
    return text, False


def _handle_stream_chunk(
    chunk: str,
    streamed_chunks: list[str],
    stream_output_fn: Callable[[str], None],
    clear_status_fn: Callable[[], None] | None,
) -> None:
    if not streamed_chunks and clear_status_fn is not None:
        clear_status_fn()
    streamed_chunks.append(chunk)
    stream_output_fn(chunk)


def _requires_followup(response: str) -> bool:
    return response.startswith("需要补充以下信息") or response.startswith("需要确认模块")


def _is_reference_answer(response: str) -> bool:
    return response.startswith(("【资料查询】", "【模块介绍】", "【常用参数】", "【流程指导】"))


def _looks_like_reference_followup(
    query: str,
    *,
    model_generate: Callable[..., str] | None = None,
) -> bool:
    normalized = query.strip().lower()
    if not normalized:
        return False
    normalized_compact = re.sub(r"\s+", "", normalized)
    if DEICTIC_REFERENCE_FOLLOWUP_PATTERN.fullmatch(normalized_compact):
        return False
    if _normalize_reference_followup_fragment(query) != query.strip():
        return True
    if "--" in normalized:
        return True
    if any(
        cue in normalized
        for cue in (
            "wgs",
            "wes",
            "whole exome",
            "exome",
            "全基因组",
            "全外显子",
            "panel",
            "rna",
            "rnaseq",
            "rna-seq",
            "fastq",
            "ubam",
            "ucram",
            "bam",
            "cram",
            "胚系",
            "体细胞",
            "肿瘤",
            "tumor",
            "tumor-only",
            "tumor only",
            "tumor-normal",
            "tumor normal",
            "normal",
            "短读长",
            "short-read",
            "short read",
            "长读长",
            "long-read",
            "long read",
            "hifi",
            "ont",
            "pacbio",
            "nanopore",
            "hybrid",
            "diploid",
            "二倍体",
            "pangenome",
            "graph",
            "泛基因组",
        )
    ):
        return True
    if any(cue in normalized for cue in ("参数", "脚本", "示例", "命令", "workflow", "pipeline", "输入", "输出", "区别", "对比")):
        return True
    parsed_intent = parse_reference_intent(query, model_generate=model_generate)
    return parsed_intent.intent in {"parameter_lookup", "script_example", "workflow_guidance"}


def _normalize_reference_followup_fragment(query: str) -> str:
    stripped = query.strip()
    normalized_compact = re.sub(r"\s+", "", stripped.lower())
    for pattern, replacement in REFERENCE_FOLLOWUP_CANONICAL_RULES:
        if pattern.search(normalized_compact):
            return replacement
    return stripped


def _build_chat_ui(output_fn: Callable[[str], None]) -> ChatUI:
    if output_fn is print:
        return ChatUI()
    return ChatUI(console=build_console(output_fn=output_fn))


def _chat_issue_type_and_missing(query: str) -> tuple[str, list[str]]:
    issue_type = classify_query(query)
    if issue_type == "other" and is_reference_query(query):
        return "reference", []
    info = extract_info_from_query(query)
    return issue_type, missing_required_fields(issue_type, info)


def _looks_like_new_query(query: str) -> bool:
    issue_type = classify_query(query)
    return issue_type != "other" or is_reference_query(query)


def _build_pre_answer_status(query: str) -> str:
    return "正在思考中"


def parse_global_options(args: list[str]) -> tuple[str | None, str | None, str | None, list[str]]:
    knowledge_directory: str | None = None
    source_directory: str | None = None
    feedback_path: str | None = None
    index = 0
    while index < len(args):
        option = args[index]
        if option not in {"--knowledge-dir", "--source-dir", "--feedback-path"}:
            break
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--knowledge-dir":
            knowledge_directory = args[index]
        elif option == "--feedback-path":
            feedback_path = args[index]
        else:
            source_directory = args[index]
        index += 1
    return knowledge_directory, source_directory, feedback_path, args[index:]


def _parse_feedback_command(query: str) -> str | None:
    stripped = query.strip()
    if not stripped.startswith("/feedback"):
        return None
    parts = stripped.split(maxsplit=1)
    if len(parts) == 1:
        return ""
    return parts[1]


def _record_feedback_turn(
    *,
    prompt: str,
    planned_turn,
    response: str,
) -> FeedbackTurnSnapshot:
    return FeedbackTurnSnapshot(
        prompt=prompt,
        effective_query=planned_turn.effective_query,
        response=response,
        task=planned_turn.route.task,
        issue_type=planned_turn.route.issue_type,
        route_reason=planned_turn.route.reason,
        parsed_intent_intent=planned_turn.route.parsed_intent.intent,
        parsed_intent_module=planned_turn.route.parsed_intent.module,
        response_mode="capability" if planned_turn.route.task == "capability_explanation" and response.startswith("【能力说明】") else "",
        reused_anchor=planned_turn.reused_anchor,
    )


def _finalize_feedback_turn(snapshot: FeedbackTurnSnapshot) -> FeedbackTurnSnapshot:
    from sentieon_assist.adversarial_sessions import classify_response_mode

    return FeedbackTurnSnapshot(
        prompt=snapshot.prompt,
        effective_query=snapshot.effective_query,
        response=snapshot.response,
        task=snapshot.task,
        issue_type=snapshot.issue_type,
        route_reason=snapshot.route_reason,
        parsed_intent_intent=snapshot.parsed_intent_intent,
        parsed_intent_module=snapshot.parsed_intent_module,
        response_mode=classify_response_mode(snapshot.response, task=snapshot.task),
        reused_anchor=snapshot.reused_anchor,
    )


def _handle_feedback_command(
    raw_argument: str,
    *,
    input_fn=input,
    output_fn=print,
    feedback_path: str | None,
    turn_history: list[FeedbackTurnSnapshot],
) -> None:
    if not turn_history:
        output_fn("当前还没有可反馈的回答。请先完成至少一轮对话。")
        return
    requested_scope = normalize_feedback_scope(raw_argument)
    if not requested_scope:
        requested_scope = normalize_feedback_scope(
            input_fn("反馈范围 [last/session，回车默认 last]: ").strip()
        )
    scope = requested_scope or "last"
    summary = input_fn("请描述哪里不理想（可直接回车跳过）: ").strip()
    expected_answer = input_fn("你期望它怎么答（可直接回车跳过）: ").strip()
    expected_mode = normalize_expected_mode(
        input_fn(
            "可选：期望回答类型 capability/workflow/module/parameter/script/doc/external/boundary/clarify（回车跳过）: "
        ).strip()
    )
    expected_task = normalize_expected_task(
        input_fn("可选：期望任务 capability/reference/workflow/troubleshooting（回车跳过）: ").strip()
    )
    captured_turns = turn_history if scope == "session" else [turn_history[-1]]
    resolved_feedback_path = Path(feedback_path) if feedback_path else default_feedback_path()
    record = build_feedback_record(
        scope=scope,
        captured_turns=captured_turns,
        summary=summary,
        expected_answer=expected_answer,
        expected_mode=expected_mode,
        expected_task=expected_task,
        feedback_path=resolved_feedback_path,
    )
    append_feedback_record(resolved_feedback_path, record)
    scope_label = "整段会话" if scope == "session" else "最近一轮"
    output_fn(f"已记录问题反馈：{scope_label}。路径：{resolved_feedback_path}")
    if expected_mode and expected_task:
        output_fn("这条反馈已带期望 mode/task，后续 closed loop 可直接回放。")
    else:
        output_fn("这条反馈已进入待分诊队列；你也可以下次补充期望 mode/task。")


def _run_troubleshooting_query(
    issue_type: str,
    query: str,
    *,
    model_fallback=None,
    knowledge_directory: str | None = None,
    source_directory: str | None = None,
) -> str:
    current_state = "CLASSIFIED"
    current_state = next_state(current_state, has_missing_info=False)

    info = extract_info_from_query(query)
    missing = missing_required_fields(issue_type, info)
    current_state = next_state(current_state, has_missing_info=bool(missing))
    if current_state == "NEED_INFO":
        return answer_query(
            issue_type,
            query,
            info,
            model_fallback=model_fallback,
            knowledge_directory=knowledge_directory,
            source_directory=source_directory,
        )

    current_state = next_state("READY", has_missing_info=False)
    if current_state != "ANSWERED":
        raise RuntimeError(f"unexpected terminal state: {current_state}")
    return answer_query(
        issue_type,
        query,
        info,
        model_fallback=model_fallback,
        knowledge_directory=knowledge_directory,
        source_directory=source_directory,
    )


def run_query(
    query: str,
    *,
    model_fallback=None,
    knowledge_directory: str | None = None,
    source_directory: str | None = None,
    route_decision=None,
) -> str:
    decision = route_decision or select_support_route(
        query,
        classify_query_fn=classify_query,
        parse_reference_intent_fn=parse_reference_intent,
        is_reference_query_fn=is_reference_query,
        extract_info_fn=extract_info_from_query,
        is_external_error_query_fn=is_external_error_query,
    )
    if decision.task == "capability_explanation":
        return format_capability_explanation_answer()
    if decision.task in {"reference_lookup", "onboarding_guidance"} or decision.issue_type == "other":
        parsed_intent = decision.parsed_intent if decision.parsed_intent.is_reference else None
        return answer_reference_query(
            query,
            model_fallback=model_fallback,
            source_directory=source_directory,
            parsed_intent=parsed_intent,
        )
    return _run_troubleshooting_query(
        decision.issue_type,
        query,
        model_fallback=model_fallback,
        knowledge_directory=knowledge_directory,
        source_directory=source_directory,
    )


def chat_loop(
    *,
    input_fn=input,
    output_fn=print,
    model_fallback=None,
    model_generate: Callable[..., str] | None = None,
    model_stream_generate: Callable[..., str] | None = None,
    api_probe: Callable[[str], dict[str, Any]] | None = None,
    warmup_model: Callable[[str, str], None] | None = None,
    status_writer: Callable[..., None] | None = None,
    stream_output_fn: Callable[[str], None] | None = None,
    knowledge_directory: str | None = None,
    source_directory: str | None = None,
    feedback_path: str | None = None,
) -> int:
    require_chat_model(api_probe=api_probe)
    config = load_config()
    ui = _build_chat_ui(output_fn)
    if warmup_model is not None:
        warmup = warmup_model
    elif model_generate is not None or model_stream_generate is not None:
        warmup = lambda model, base_url: None
    else:
        warmup = lambda model, base_url: build_backend_router(config).warmup_primary()
    warmup(config.ollama_model, config.ollama_base_url)
    ui.render_welcome_panel()
    support_state = SupportSessionState()
    turn_history: list[FeedbackTurnSnapshot] = []
    while True:
        query = input_fn(_build_input_prompt(input_fn=input_fn)).strip()
        if not query:
            continue
        if query in {"/quit", "quit", "exit"}:
            output_fn("已退出交互模式。")
            return 0
        if query == "/help":
            output_fn(format_chat_help())
            continue
        if query == "/reset":
            support_state = support_state.cleared()
            output_fn("已清空当前补问上下文。")
            continue
        feedback_argument = _parse_feedback_command(query)
        if feedback_argument is not None:
            _handle_feedback_command(
                feedback_argument,
                input_fn=input_fn,
                output_fn=output_fn,
                feedback_path=feedback_path,
                turn_history=turn_history,
            )
            continue
        planned_turn = plan_support_turn(
            query,
            support_state,
            classify_query_fn=classify_query,
            parse_reference_intent_fn=parse_reference_intent,
            is_reference_query_fn=is_reference_query,
            extract_info_fn=extract_info_from_query,
            is_external_error_query_fn=is_external_error_query,
        )
        effective_query = planned_turn.effective_query
        clear_status = start_thinking_animation(
            status_writer=status_writer,
            label=_build_pre_answer_status(effective_query),
        )
        response = run_query(
            effective_query,
            model_fallback=model_fallback,
            knowledge_directory=knowledge_directory,
            source_directory=source_directory,
            route_decision=planned_turn.route,
        )
        clear_status()
        support_state = update_support_state(
            support_state,
            planned_turn=planned_turn,
            response=response,
        )
        turn_history.append(
            _finalize_feedback_turn(
                _record_feedback_turn(
                    prompt=query,
                    planned_turn=planned_turn,
                    response=response,
                )
            )
        )
        effective_stream_output_fn = stream_output_fn or _default_stream_output_fn
        streamed_started = False
        clear_generation_status: Callable[[], None] | None = None
        if not _is_stable_chat_response(response):
            clear_generation_status = start_thinking_animation(
                status_writer=status_writer,
                label=event_generate_reply(),
            )

        def wrapped_stream_output(chunk: str) -> None:
            nonlocal streamed_started
            if not streamed_started:
                if clear_generation_status is not None:
                    clear_generation_status()
                ui.render_streaming_answer_header()
                streamed_started = True
            effective_stream_output_fn(chunk)

        rendered, streamed = render_chat_response(
            effective_query,
            response,
            model_generate=model_generate,
            model_stream_generate=model_stream_generate,
            stream_output_fn=wrapped_stream_output,
            clear_status_fn=clear_generation_status,
        )
        if not streamed:
            ui.render_answer(rendered)
        output_fn(format_feedback_hint())


def print_sources(*, output_fn=print, source_directory: str | None = None) -> int:
    config = load_config()
    sources = list_sources(source_directory or config.source_dir)
    if not sources:
        output_fn("未发现可用资料。")
        return 0
    for source in sources:
        output_fn(f"{source['type']}[{source['trust']}]: {source['name']}")
    return 0


def print_search_results(keyword: str, *, output_fn=print, source_directory: str | None = None) -> int:
    config = load_config()
    matches = search_sources(source_directory or config.source_dir, keyword)
    if not matches:
        output_fn(f"未找到关键词：{keyword}")
        return 0
    for match in matches:
        output_fn(f"{match['type']}[{match['trust']}]: {match['name']}")
        output_fn(match["snippet"])
    return 0


def main(
    argv: list[str] | None = None,
    *,
    input_fn=input,
    output_fn=print,
    model_generate: Callable[..., str] | None = None,
    model_stream_generate: Callable[..., str] | None = None,
    api_probe: Callable[[str], dict[str, Any]] | None = None,
    warmup_model: Callable[[str, str], None] | None = None,
    status_writer: Callable[..., None] | None = None,
    stream_output_fn: Callable[[str], None] | None = None,
    source_directory: str | None = None,
    knowledge_directory: str | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        cli_knowledge_directory, cli_source_directory, cli_feedback_path, args = parse_global_options(args)
    except ValueError as error:
        output_fn(str(error))
        return 2
    effective_knowledge_directory = knowledge_directory or cli_knowledge_directory
    effective_source_directory = source_directory or cli_source_directory
    effective_feedback_path = cli_feedback_path
    if args and args[0] == "chat":
        try:
            return chat_loop(
                input_fn=input_fn,
                output_fn=output_fn,
                model_generate=model_generate,
                model_stream_generate=model_stream_generate,
                api_probe=api_probe,
                warmup_model=warmup_model,
                status_writer=status_writer,
                stream_output_fn=stream_output_fn,
                knowledge_directory=effective_knowledge_directory,
                source_directory=effective_source_directory,
                feedback_path=effective_feedback_path,
            )
        except RuntimeError as error:
            output_fn(str(error))
            return 2
    if args and args[0] == "sources":
        return print_sources(output_fn=output_fn, source_directory=effective_source_directory)
    if args and args[0] == "doctor":
        report = gather_doctor_report(
            knowledge_directory=effective_knowledge_directory,
            source_directory=effective_source_directory,
        )
        output_fn(format_doctor_report(report))
        return 0
    if args and args[0] == "search":
        keyword = " ".join(args[1:]).strip()
        if not keyword:
            output_fn("search keyword is required")
            return 2
        return print_search_results(keyword, output_fn=output_fn, source_directory=effective_source_directory)
    query = " ".join(args).strip()
    if not query:
        output_fn("query is required")
        return 2
    output_fn(
        run_query(
            query,
            knowledge_directory=effective_knowledge_directory,
            source_directory=effective_source_directory,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
