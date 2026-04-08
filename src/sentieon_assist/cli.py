from __future__ import annotations

import sys
import threading
from typing import Any, Callable

from sentieon_assist.answering import answer_query, answer_reference_query, missing_required_fields
from sentieon_assist.chat_events import (
    event_check_missing_info,
    event_detect_issue_type,
    event_generate_reply,
    event_prepare_reference_answer,
    event_search_sources,
)
from sentieon_assist.chat_ui import ChatUI, build_console
from sentieon_assist.classifier import classify_query, is_reference_query
from sentieon_assist.config import load_config
from sentieon_assist.doctor import format_doctor_report, gather_doctor_report
from sentieon_assist.extractor import extract_info_from_query
from sentieon_assist.llm_backends import build_backend_router
from sentieon_assist.prompts import build_chat_missing_info_prompt, build_chat_polish_prompt
from sentieon_assist.sources import list_sources, search_sources
from sentieon_assist.state_machine import next_state

try:
    import readline  # noqa: F401
except ImportError:  # pragma: no cover
    readline = None


def _default_status_writer(text: str, *, clear: bool = False) -> None:
    if clear:
        sys.stdout.write("\r" + (" " * 32) + "\r")
    else:
        sys.stdout.write("\r" + text)
    sys.stdout.flush()


def _default_stream_output_fn(chunk: str) -> None:
    sys.stdout.write(chunk)
    sys.stdout.flush()


def start_thinking_animation(
    *,
    status_writer: Callable[..., None] | None = None,
    interval_seconds: float = 0.2,
) -> Callable[[], None]:
    writer = status_writer or _default_status_writer
    frames = ("思考中.", "思考中..", "思考中...")
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
    return raw_response.startswith("【") or raw_response.startswith("需要确认模块")


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
        return raw_response.strip(), False
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
    if clear_status_fn is not None:
        clear_status_fn()
    return _chat_model_generate(prompt, model_generate=model_generate).strip(), False


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


def _build_chat_events(query: str, response: str) -> list[str]:
    issue_type, missing = _chat_issue_type_and_missing(query)
    events = [event_detect_issue_type(issue_type)]
    if issue_type == "reference":
        events.append(event_search_sources())
        events.append(event_prepare_reference_answer())
    else:
        events.append("正在检查缺失信息")
        events.append(event_check_missing_info(missing))
    if not _is_stable_chat_response(response):
        events.append(event_generate_reply())
    return events


def _looks_like_new_query(query: str) -> bool:
    issue_type = classify_query(query)
    return issue_type != "other" or is_reference_query(query)


def parse_global_options(args: list[str]) -> tuple[str | None, str | None, list[str]]:
    knowledge_directory: str | None = None
    source_directory: str | None = None
    index = 0
    while index < len(args):
        option = args[index]
        if option not in {"--knowledge-dir", "--source-dir"}:
            break
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--knowledge-dir":
            knowledge_directory = args[index]
        else:
            source_directory = args[index]
        index += 1
    return knowledge_directory, source_directory, args[index:]


def run_query(
    query: str,
    *,
    model_fallback=None,
    knowledge_directory: str | None = None,
    source_directory: str | None = None,
) -> str:
    issue_type = classify_query(query)
    if issue_type == "other" and is_reference_query(query):
        return answer_reference_query(
            query,
            model_fallback=model_fallback,
            source_directory=source_directory,
        )
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
    pending_query: str | None = None
    while True:
        query = input_fn("Sengent> ").strip()
        if not query:
            continue
        if query in {"/quit", "quit", "exit"}:
            output_fn("已退出交互模式。")
            return 0
        if query == "/reset":
            pending_query = None
            output_fn("已清空当前补问上下文。")
            continue
        effective_query = query if pending_query is None or _looks_like_new_query(query) else f"{pending_query} {query}"
        ui.render_user_message(query)
        clear_status = start_thinking_animation(status_writer=status_writer)
        response = run_query(
            effective_query,
            model_fallback=model_fallback,
            knowledge_directory=knowledge_directory,
            source_directory=source_directory,
        )
        clear_status()
        if _requires_followup(response):
            pending_query = effective_query
        else:
            pending_query = None
        ui.render_events(_build_chat_events(effective_query, response))
        effective_stream_output_fn = stream_output_fn or _default_stream_output_fn
        streamed_started = False

        def wrapped_stream_output(chunk: str) -> None:
            nonlocal streamed_started
            if not streamed_started:
                ui.render_streaming_answer_header()
                streamed_started = True
            effective_stream_output_fn(chunk)

        rendered, streamed = render_chat_response(
            effective_query,
            response,
            model_generate=model_generate,
            model_stream_generate=model_stream_generate,
            stream_output_fn=wrapped_stream_output,
            clear_status_fn=None,
        )
        if not streamed:
            ui.render_answer(rendered)


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
        cli_knowledge_directory, cli_source_directory, args = parse_global_options(args)
    except ValueError as error:
        output_fn(str(error))
        return 2
    effective_knowledge_directory = knowledge_directory or cli_knowledge_directory
    effective_source_directory = source_directory or cli_source_directory
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
