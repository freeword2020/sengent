from __future__ import annotations

import re
import subprocess
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
from sentieon_assist.dataset_export import export_reviewed_gap_dataset, format_dataset_export_summary
from sentieon_assist.external_guides import is_external_error_query
from sentieon_assist.extractor import extract_info_from_query
from sentieon_assist.feedback_runtime import (
    append_feedback_record,
    build_feedback_record,
    default_feedback_path,
    format_chat_help,
    format_feedback_hint,
    normalize_expected_mode,
    normalize_expected_task,
    normalize_feedback_scope,
)
from sentieon_assist.gap_intake import export_gap_turn_to_inbox
from sentieon_assist.gap_review import apply_gap_review_decision
from sentieon_assist.knowledge_build import (
    activate_knowledge_build,
    default_build_root,
    default_inbox_dir,
    rollback_knowledge_backup,
    review_knowledge_build,
    run_knowledge_build,
    scaffold_knowledge_source,
)
from sentieon_assist.knowledge_review import build_maintainer_queue, format_maintainer_queue
from sentieon_assist.llm_backends import build_backend_router
from sentieon_assist.prompts import build_chat_missing_info_prompt, build_chat_polish_prompt
from sentieon_assist.reference_intents import parse_reference_intent
from sentieon_assist.runtime_guidance import format_ollama_runtime_error
from sentieon_assist.session_events import (
    SupportSessionRecord,
    SupportTurnView,
    append_feedback_recorded_event,
    append_session_record,
    append_turn_event,
    build_feedback_recorded_event,
    build_turn_event,
    classify_response_mode,
    default_runtime_root,
    turn_view_from_event,
)
from sentieon_assist.support_experience import format_support_answer_card
from sentieon_assist.source_intake import intake_source_to_inbox
from sentieon_assist.sources import list_sources, search_sources
from sentieon_assist.state_machine import next_state
from sentieon_assist.support_coordinator import plan_support_turn, select_support_route, update_support_state
from sentieon_assist.support_state import SupportSessionState
from sentieon_assist.trace_vocab import ResolverPath

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
HELP_FLAGS = {"--help", "-h", "help"}
GLOBAL_OPTION_NAMES = {"--knowledge-dir", "--source-dir", "--feedback-path"}


def format_cli_help() -> str:
    return "\n".join(
        [
            "Usage: sengent <command> [options]",
            "",
            "Common commands:",
            "  sengent chat",
            "  sengent doctor [--skip-ollama]",
            "  sengent sources",
            "  sengent search <keyword>",
            '  sengent "<your question>"',
            "",
            "Knowledge maintenance:",
            "  sengent knowledge scaffold --kind <kind> --id <id> [--name <name>]",
            "  sengent knowledge intake-source --source-class <class> --source-path <path> --kind <kind> --id <id> --name <name>",
            "  sengent knowledge intake-gap --session-id <id> [--turn-id <id> | --latest] [--runtime-root <dir>] [--inbox-dir <dir>]",
            "  sengent knowledge build [--inbox-dir <dir>] [--build-root <dir>]",
            "  sengent knowledge queue [--build-id <id>] [--build-root <dir>]",
            "  sengent knowledge export-dataset --output <path> [--build-id <id>] [--build-root <dir>] [--runtime-root <dir>]",
            "  sengent knowledge review [--build-id <id>] [--build-root <dir>]",
            "  sengent knowledge triage-gap --build-id <id> --entry-id <id> --decision <decision> [--expected-mode <mode>] [--expected-task <task>]",
            "  sengent knowledge activate --build-id <id> [--build-root <dir>]",
            "  sengent knowledge rollback --backup-id <id> [--build-root <dir>]",
            "",
            "Global options (must appear before the command):",
            "  --source-dir <dir>",
            "  --knowledge-dir <dir>",
            "  --feedback-path <path>",
            "",
            "Help:",
            "  sengent --help",
            "  sengent chat --help",
            "  sengent doctor --help",
            "  sengent knowledge --help",
        ]
    )


def format_chat_command_help() -> str:
    return "\n".join(
        [
            "Usage: sengent chat",
            "",
            "Start the interactive Sengent support shell.",
            "",
            "In-chat commands:",
            format_chat_help().rstrip(),
        ]
    )


def format_doctor_command_help() -> str:
    return "\n".join(
        [
            "Usage: sengent doctor [--skip-ollama]",
            "",
            "Check runtime prerequisites, source packs, and build-time extras.",
            "",
            "Options:",
            "  --skip-ollama    Skip Ollama probing on build-only hosts",
        ]
    )


def format_sources_command_help() -> str:
    return "\n".join(
        [
            "Usage: sengent sources",
            "",
            "List the currently visible structured source packs.",
        ]
    )


def format_search_command_help() -> str:
    return "\n".join(
        [
            "Usage: sengent search <keyword>",
            "",
            "Search structured source packs for a keyword.",
        ]
    )


def format_knowledge_help() -> str:
    return "\n".join(
        [
            "Usage: sengent knowledge <subcommand> [options]",
            "",
            "Subcommands:",
            "  scaffold    Create an inbox template for add/update/delete",
            "  intake-source  Import a local source file into inbox-ready artifacts",
            "  intake-gap  Export a captured runtime gap into the knowledge inbox",
            "  build       Compile inbox content into candidate packs",
            "  queue       Show the maintainer queue and next actions for a build",
            "  export-dataset  Export audited reviewed-gap training samples",
            "  review      Show the latest or selected build report",
            "  triage-gap  Record a maintainer decision for a captured gap entry",
            "  activate    Promote a gated build into active packs",
            "  rollback    Restore active packs from a backup",
        ]
    )


def format_knowledge_subcommand_help(subcommand: str) -> str:
    if subcommand == "build":
        return "\n".join(
            [
                "Usage: sengent knowledge build [--inbox-dir <dir>] [--build-root <dir>]",
                "",
                "Compile inbox documents and metadata into candidate packs.",
            ]
        )
    if subcommand == "scaffold":
        return "\n".join(
            [
                "Usage: sengent knowledge scaffold --kind <kind> --id <id> [--name <name>] [--action <upsert|delete>] [--inbox-dir <dir>] [--file-stem <stem>]",
                "",
                "Create or update an inbox markdown + metadata template.",
            ]
        )
    if subcommand == "intake-gap":
        return "\n".join(
            [
                "Usage: sengent knowledge intake-gap --session-id <id> [--turn-id <id> | --latest] [--runtime-root <dir>] [--inbox-dir <dir>]",
                "",
                "Export a captured runtime gap record into an inbox incident artifact.",
            ]
        )
    if subcommand == "intake-source":
        return "\n".join(
            [
                "Usage: sengent knowledge intake-source --source-class <class> --source-path <path> --kind <kind> --id <id> --name <name> [--inbox-dir <dir>] [--file-stem <stem>]",
                "",
                "Import a local source file into inbox-ready markdown + metadata artifacts.",
            ]
        )
    if subcommand == "activate":
        return "\n".join(
            [
                "Usage: sengent knowledge activate --build-id <id> [--build-root <dir>]",
                "",
                "Activate a gated knowledge build and back up the previous active packs first.",
            ]
        )
    if subcommand == "queue":
        return "\n".join(
            [
                "Usage: sengent knowledge queue [--build-id <id>] [--build-root <dir>]",
                "",
                "Show the maintainer queue and next actions for the latest or selected build.",
            ]
        )
    if subcommand == "export-dataset":
        return "\n".join(
            [
                "Usage: sengent knowledge export-dataset --output <path> [--build-id <id>] [--build-root <dir>] [--runtime-root <dir>]",
                "",
                "Export audited reviewed-gap support samples into a JSONL dataset artifact.",
            ]
        )
    if subcommand == "triage-gap":
        return "\n".join(
            [
                "Usage: sengent knowledge triage-gap --build-id <id> --entry-id <id> --decision <decision> [--status <status>] [--expected-mode <mode>] [--expected-task <task>] [--scope <last|session>] [--note <text>] [--build-root <dir>]",
                "",
                "Write a maintainer gap triage decision back into the source sidecar metadata.",
            ]
        )
    if subcommand == "rollback":
        return "\n".join(
            [
                "Usage: sengent knowledge rollback --backup-id <id> [--build-root <dir>]",
                "",
                "Restore active packs from a recorded activation backup.",
            ]
        )
    if subcommand == "review":
        return "\n".join(
            [
                "Usage: sengent knowledge review [--build-id <id>] [--build-root <dir>]",
                "",
                "Show the latest or selected build report.",
            ]
        )
    return format_knowledge_help()


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
    frames = (f"{label}...", f"{label}.", f"{label}..")
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
    if not result.get("ok"):
        raise RuntimeError(
            format_ollama_runtime_error(
                error_text=str(result.get("error", "ollama probe failed")).strip(),
                base_url=config.ollama_base_url,
                model=config.ollama_model,
                issue_kind="connectivity",
            )
        )
    if not result.get("model_available"):
        raise RuntimeError(
            format_ollama_runtime_error(
                error_text=f"target model is not available: {config.ollama_model}",
                base_url=config.ollama_base_url,
                model=config.ollama_model,
                issue_kind="model_missing",
            )
        )


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


def _parse_knowledge_build_options(args: list[str]) -> tuple[str | None, str | None]:
    inbox_directory: str | None = None
    build_root: str | None = None
    index = 0
    while index < len(args):
        option = args[index]
        if option not in {"--inbox-dir", "--build-root"}:
            raise ValueError(f"unknown knowledge build option: {option}")
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--inbox-dir":
            inbox_directory = args[index]
        if option == "--build-root":
            build_root = args[index]
        index += 1
    return inbox_directory, build_root


def _parse_knowledge_activate_options(args: list[str]) -> tuple[str | None, str | None]:
    build_root: str | None = None
    build_id: str | None = None
    index = 0
    while index < len(args):
        option = args[index]
        if option not in {"--build-root", "--build-id"}:
            raise ValueError(f"unknown knowledge activate option: {option}")
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--build-root":
            build_root = args[index]
        elif option == "--build-id":
            build_id = args[index]
        index += 1
    return build_root, build_id


def _parse_knowledge_rollback_options(args: list[str]) -> tuple[str | None, str | None]:
    build_root: str | None = None
    backup_id: str | None = None
    index = 0
    while index < len(args):
        option = args[index]
        if option not in {"--build-root", "--backup-id"}:
            raise ValueError(f"unknown knowledge rollback option: {option}")
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--build-root":
            build_root = args[index]
        else:
            backup_id = args[index]
        index += 1
    return build_root, backup_id


def _parse_knowledge_review_options(args: list[str]) -> tuple[str | None, str | None]:
    build_root: str | None = None
    build_id: str | None = None
    index = 0
    while index < len(args):
        option = args[index]
        if option not in {"--build-root", "--build-id"}:
            raise ValueError(f"unknown knowledge review option: {option}")
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--build-root":
            build_root = args[index]
        else:
            build_id = args[index]
        index += 1
    return build_root, build_id


def _parse_knowledge_export_dataset_options(args: list[str]) -> tuple[str | None, str | None, str | None, str | None]:
    build_root: str | None = None
    build_id: str | None = None
    output_path: str | None = None
    runtime_root: str | None = None
    index = 0
    while index < len(args):
        option = args[index]
        if option not in {"--build-root", "--build-id", "--output", "--runtime-root"}:
            raise ValueError(f"unknown knowledge export-dataset option: {option}")
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--build-root":
            build_root = args[index]
        elif option == "--build-id":
            build_id = args[index]
        elif option == "--output":
            output_path = args[index]
        else:
            runtime_root = args[index]
        index += 1
    return build_root, build_id, output_path, runtime_root


def _parse_knowledge_intake_source_options(
    args: list[str],
) -> tuple[str | None, str | None, str | None, str | None, str | None, str | None, str | None]:
    inbox_directory: str | None = None
    source_class: str | None = None
    source_path: str | None = None
    kind: str | None = None
    entry_id: str | None = None
    name: str | None = None
    file_stem: str | None = None
    index = 0
    while index < len(args):
        option = args[index]
        if option not in {"--inbox-dir", "--source-class", "--source-path", "--kind", "--id", "--name", "--file-stem"}:
            raise ValueError(f"unknown knowledge intake-source option: {option}")
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--inbox-dir":
            inbox_directory = args[index]
        elif option == "--source-class":
            source_class = args[index]
        elif option == "--source-path":
            source_path = args[index]
        elif option == "--kind":
            kind = args[index]
        elif option == "--id":
            entry_id = args[index]
        elif option == "--name":
            name = args[index]
        else:
            file_stem = args[index]
        index += 1
    return inbox_directory, source_class, source_path, kind, entry_id, name, file_stem


def _parse_knowledge_triage_gap_options(
    args: list[str],
) -> tuple[str | None, str | None, str | None, str | None, str, str, str, str, str]:
    build_root: str | None = None
    build_id: str | None = None
    entry_id: str | None = None
    decision: str | None = None
    status = "triaged"
    expected_mode = ""
    expected_task = ""
    scope = "last"
    note = ""
    index = 0
    while index < len(args):
        option = args[index]
        if option not in {
            "--build-root",
            "--build-id",
            "--entry-id",
            "--decision",
            "--status",
            "--expected-mode",
            "--expected-task",
            "--scope",
            "--note",
        }:
            raise ValueError(f"unknown knowledge triage-gap option: {option}")
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--build-root":
            build_root = args[index]
        elif option == "--build-id":
            build_id = args[index]
        elif option == "--entry-id":
            entry_id = args[index]
        elif option == "--decision":
            decision = args[index]
        elif option == "--status":
            status = args[index]
        elif option == "--expected-mode":
            expected_mode = args[index]
        elif option == "--expected-task":
            expected_task = args[index]
        elif option == "--scope":
            scope = args[index]
        else:
            note = args[index]
        index += 1
    return build_root, build_id, entry_id, decision, status, expected_mode, expected_task, scope, note


def _parse_knowledge_scaffold_options(
    args: list[str],
) -> tuple[str | None, str | None, str | None, str | None, str, str | None]:
    inbox_directory: str | None = None
    kind: str | None = None
    entry_id: str | None = None
    name: str | None = None
    action = "upsert"
    file_stem: str | None = None
    index = 0
    while index < len(args):
        option = args[index]
        if option not in {"--inbox-dir", "--kind", "--id", "--name", "--action", "--file-stem"}:
            raise ValueError(f"unknown knowledge scaffold option: {option}")
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--inbox-dir":
            inbox_directory = args[index]
        elif option == "--kind":
            kind = args[index]
        elif option == "--id":
            entry_id = args[index]
        elif option == "--name":
            name = args[index]
        elif option == "--action":
            action = args[index]
        else:
            file_stem = args[index]
        index += 1
    return inbox_directory, kind, entry_id, name, action, file_stem


def _parse_knowledge_intake_gap_options(
    args: list[str],
) -> tuple[str | None, str | None, str | None, bool, str | None]:
    inbox_directory: str | None = None
    session_id: str | None = None
    turn_id: str | None = None
    latest = False
    runtime_root: str | None = None
    index = 0
    while index < len(args):
        option = args[index]
        if option == "--latest":
            latest = True
            index += 1
            continue
        if option not in {"--inbox-dir", "--session-id", "--turn-id", "--runtime-root"}:
            raise ValueError(f"unknown knowledge intake-gap option: {option}")
        index += 1
        if index >= len(args):
            raise ValueError(f"missing value for {option}")
        if option == "--inbox-dir":
            inbox_directory = args[index]
        elif option == "--session-id":
            session_id = args[index]
        elif option == "--turn-id":
            turn_id = args[index]
        else:
            runtime_root = args[index]
        index += 1
    return inbox_directory, session_id, turn_id, latest, runtime_root


def _parse_doctor_options(args: list[str]) -> bool:
    skip_ollama = False
    index = 0
    while index < len(args):
        option = args[index]
        if option != "--skip-ollama":
            raise ValueError(f"unknown doctor option: {option}")
        skip_ollama = True
        index += 1
    return skip_ollama


def _format_cli_runtime_error(error: RuntimeError) -> str:
    message = str(error).strip()
    if message.startswith("【运行时模型不可用】"):
        return message
    if "ollama" not in message.lower():
        return message
    config = load_config()
    return format_ollama_runtime_error(
        error_text=message,
        base_url=config.ollama_base_url,
        model=config.ollama_model,
        issue_kind="model_missing" if "target model is not available" in message else "connectivity",
    )


def _format_misplaced_global_option(option: str, command: str, value: str = "<value>") -> str:
    return (
        f"global option {option} must appear before the command, "
        f"for example: sengent {option} {value} {command}"
    )


def _parse_feedback_command(query: str) -> str | None:
    stripped = query.strip()
    if not stripped.startswith("/feedback"):
        return None
    parts = stripped.split(maxsplit=1)
    if len(parts) == 1:
        return ""
    return parts[1]


def _runtime_git_sha(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _handle_feedback_command(
    raw_argument: str,
    *,
    input_fn=input,
    output_fn=print,
    feedback_path: str | None,
    runtime_root: Path,
    session_record: SupportSessionRecord,
    turn_history: list[SupportTurnView],
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
    selected_turns = turn_history if scope == "session" else [turn_history[-1]]
    resolved_feedback_path = Path(feedback_path) if feedback_path else default_feedback_path()
    record = build_feedback_record(
        scope=scope,
        session_id=session_record.session_id,
        selected_turn_ids=[turn.turn_id for turn in selected_turns],
        summary=summary,
        expected_answer=expected_answer,
        expected_mode=expected_mode,
        expected_task=expected_task,
        feedback_path=resolved_feedback_path,
    )
    append_feedback_record(resolved_feedback_path, record)
    append_feedback_recorded_event(
        build_feedback_recorded_event(
            session_id=session_record.session_id,
            feedback_record_id=str(record["record_id"]),
            scope=scope,
            selected_turn_ids=[turn.turn_id for turn in selected_turns],
        ),
        runtime_root=runtime_root,
    )
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
    route_decision=None,
    clarification_rounds: int = 0,
    model_fallback=None,
    knowledge_directory: str | None = None,
    source_directory: str | None = None,
    trace_collector: Callable[[dict[str, object]], None] | None = None,
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
            route_decision=route_decision,
            clarification_rounds=clarification_rounds,
            model_fallback=model_fallback,
            knowledge_directory=knowledge_directory,
            source_directory=source_directory,
            trace_collector=lambda trace: trace_collector(
                {
                    "sources": list(trace.sources),
                    "boundary_tags": list(trace.boundary_tags),
                    "resolver_path": list(trace.resolver_path),
                    "gap_record": trace.gap_record,
                }
            )
            if trace_collector is not None
            else None,
        )

    current_state = next_state("READY", has_missing_info=False)
    if current_state != "ANSWERED":
        raise RuntimeError(f"unexpected terminal state: {current_state}")
    return answer_query(
        issue_type,
        query,
        info,
        route_decision=route_decision,
        clarification_rounds=clarification_rounds,
        model_fallback=model_fallback,
        knowledge_directory=knowledge_directory,
        source_directory=source_directory,
        trace_collector=lambda trace: trace_collector(
            {
                "sources": list(trace.sources),
                "boundary_tags": list(trace.boundary_tags),
                "resolver_path": list(trace.resolver_path),
                "gap_record": trace.gap_record,
            }
        )
        if trace_collector is not None
        else None,
    )


def run_query(
    query: str,
    *,
    model_fallback=None,
    knowledge_directory: str | None = None,
    source_directory: str | None = None,
    route_decision=None,
    clarification_rounds: int = 0,
    trace_collector: Callable[[dict[str, object]], None] | None = None,
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
        if trace_collector is not None:
            trace_collector({"sources": [], "boundary_tags": [], "resolver_path": [ResolverPath.CAPABILITY_EXPLANATION]})
        return format_capability_explanation_answer()
    if decision.task in {"reference_lookup", "onboarding_guidance"} or decision.issue_type == "other":
        parsed_intent = decision.parsed_intent if decision.parsed_intent.is_reference else None
        return answer_reference_query(
            query,
            route_decision=decision,
            clarification_rounds=clarification_rounds,
            model_fallback=model_fallback,
            source_directory=source_directory,
            parsed_intent=parsed_intent,
            trace_collector=lambda trace: trace_collector(
                {
                    "sources": list(trace.sources),
                    "boundary_tags": list(trace.boundary_tags),
                    "resolver_path": list(trace.resolver_path),
                    "gap_record": trace.gap_record,
                }
            )
            if trace_collector is not None
            else None,
        )
    return _run_troubleshooting_query(
        decision.issue_type,
        query,
        route_decision=decision,
        clarification_rounds=clarification_rounds,
        model_fallback=model_fallback,
        knowledge_directory=knowledge_directory,
        source_directory=source_directory,
        trace_collector=trace_collector,
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
    runtime_directory: str | None = None,
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
    repo_root = Path(__file__).resolve().parents[2]
    runtime_root = Path(runtime_directory) if runtime_directory else default_runtime_root()
    session_record = SupportSessionRecord.new(
        repo_root=str(repo_root),
        git_sha=_runtime_git_sha(repo_root),
        source_directory=str(source_directory or ""),
        knowledge_directory=str(knowledge_directory or ""),
        mode="interactive",
    )
    append_session_record(session_record, runtime_root=runtime_root)
    support_state = SupportSessionState()
    turn_history: list[SupportTurnView] = []
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
                runtime_root=runtime_root,
                session_record=session_record,
                turn_history=turn_history,
            )
            continue
        clear_status: Callable[[], None] | None = None
        try:
            clear_status = start_thinking_animation(
                status_writer=status_writer,
                label=_build_pre_answer_status(query),
            )
            state_before = support_state.to_snapshot()
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
            trace: dict[str, object] = {"sources": [], "boundary_tags": [], "resolver_path": []}
            response = run_query(
                effective_query,
                model_fallback=model_fallback,
                knowledge_directory=knowledge_directory,
                source_directory=source_directory,
                route_decision=planned_turn.route,
                clarification_rounds=support_state.clarification_rounds,
                trace_collector=lambda payload: trace.update(payload),
            )
        finally:
            if clear_status is not None:
                clear_status()
        support_state = update_support_state(
            support_state,
            planned_turn=planned_turn,
            response=response,
        )
        response_mode = classify_response_mode(response, task=planned_turn.route.task)
        turn_event = build_turn_event(
            session_id=session_record.session_id,
            turn_index=len(turn_history) + 1,
            raw_query=query,
            effective_query=planned_turn.effective_query,
            reused_anchor=planned_turn.reused_anchor,
            task=planned_turn.route.task,
            issue_type=planned_turn.route.issue_type,
            route_reason=planned_turn.route.reason,
            support_intent=planned_turn.route.support_intent,
            fallback_mode=planned_turn.route.fallback_mode,
            vendor_id=planned_turn.route.vendor_id,
            vendor_version=planned_turn.route.vendor_version,
            parsed_intent_intent=planned_turn.route.parsed_intent.intent,
            parsed_intent_module=planned_turn.route.parsed_intent.module,
            response_text=response,
            response_mode=response_mode,
            state_before=state_before,
            state_after=support_state.to_snapshot(),
            sources=[str(item) for item in trace.get("sources", [])],
            boundary_tags=[str(item) for item in trace.get("boundary_tags", [])],
            resolver_path=[str(item) for item in trace.get("resolver_path", [])],
            gap_record=trace.get("gap_record"),
        )
        append_turn_event(turn_event, runtime_root=runtime_root)
        turn_history.append(turn_view_from_event(turn_event))
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
    runtime_directory: str | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        cli_knowledge_directory, cli_source_directory, cli_feedback_path, args = parse_global_options(args)
    except ValueError as error:
        output_fn(str(error))
        return 2
    if not args or args[0] in HELP_FLAGS:
        output_fn(format_cli_help())
        return 0
    config = load_config()
    effective_knowledge_directory = knowledge_directory or cli_knowledge_directory or (config.knowledge_dir or None)
    effective_source_directory = source_directory or cli_source_directory or config.source_dir
    effective_feedback_path = cli_feedback_path
    if args and args[0] in {"chat", "sources", "doctor", "knowledge", "search"}:
        for index, option in enumerate(args[1:], start=1):
            if option in GLOBAL_OPTION_NAMES:
                value = args[index + 1] if index + 1 < len(args) else "<value>"
                output_fn(_format_misplaced_global_option(option, args[0], value))
                return 2
    if args and args[0] == "chat":
        if len(args) >= 2 and args[1] in HELP_FLAGS:
            output_fn(format_chat_command_help())
            return 0
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
                runtime_directory=runtime_directory,
            )
        except RuntimeError as error:
            output_fn(_format_cli_runtime_error(error))
            return 2
    if args and args[0] == "sources":
        if len(args) >= 2 and args[1] in HELP_FLAGS:
            output_fn(format_sources_command_help())
            return 0
        return print_sources(output_fn=output_fn, source_directory=effective_source_directory)
    if args and args[0] == "doctor":
        if len(args) >= 2 and args[1] in HELP_FLAGS:
            output_fn(format_doctor_command_help())
            return 0
        try:
            skip_ollama = _parse_doctor_options(args[1:])
        except ValueError as error:
            output_fn(str(error))
            return 2
        report = gather_doctor_report(
            knowledge_directory=effective_knowledge_directory,
            source_directory=effective_source_directory,
            skip_ollama_probe=skip_ollama,
        )
        output_fn(format_doctor_report(report))
        return 0
    if args and args[0] == "knowledge":
        if len(args) == 1 or args[1] in HELP_FLAGS:
            output_fn(format_knowledge_help())
            return 0
        if len(args) >= 3 and args[2] in HELP_FLAGS:
            output_fn(format_knowledge_subcommand_help(args[1]))
            return 0
    if len(args) >= 2 and args[0] == "knowledge" and args[1] == "build":
        try:
            inbox_directory, build_root = _parse_knowledge_build_options(args[2:])
        except ValueError as error:
            output_fn(str(error))
            return 2
        resolved_inbox_directory = inbox_directory or str(default_inbox_dir())
        resolved_build_root = build_root or str(default_build_root(runtime_root=runtime_directory))
        try:
            result = run_knowledge_build(
                source_directory=effective_source_directory,
                inbox_directory=resolved_inbox_directory,
                build_root=resolved_build_root,
            )
        except ValueError as error:
            output_fn(str(error))
            return 2
        output_fn(
            "Knowledge build completed: "
            f"{result.build_dir} "
            f"(inventory={result.inventory_count}, canonical_docs={result.canonical_document_count}, exceptions={result.exception_count})"
        )
        return 0
    if len(args) >= 2 and args[0] == "knowledge" and args[1] == "scaffold":
        try:
            inbox_directory, kind, entry_id, name, action, file_stem = _parse_knowledge_scaffold_options(args[2:])
        except ValueError as error:
            output_fn(str(error))
            return 2
        if not kind:
            output_fn("knowledge scaffold requires --kind")
            return 2
        if not entry_id:
            output_fn("knowledge scaffold requires --id")
            return 2
        resolved_inbox_directory = inbox_directory or str(default_inbox_dir())
        try:
            result = scaffold_knowledge_source(
                inbox_directory=resolved_inbox_directory,
                kind=kind,
                entry_id=entry_id,
                name=name,
                action=action,
                file_stem=file_stem,
            )
        except ValueError as error:
            output_fn(str(error))
            return 2
        output_fn(
            "Knowledge scaffold completed: "
            f"{result.markdown_path} "
            f"(metadata={result.metadata_path}, action={result.action}, kind={result.kind})"
        )
        return 0
    if len(args) >= 2 and args[0] == "knowledge" and args[1] == "intake-gap":
        try:
            inbox_directory, session_id, turn_id, latest, runtime_root = _parse_knowledge_intake_gap_options(args[2:])
        except ValueError as error:
            output_fn(str(error))
            return 2
        if not session_id:
            output_fn("knowledge intake-gap requires --session-id")
            return 2
        resolved_inbox_directory = inbox_directory or str(default_inbox_dir())
        resolved_runtime_root = runtime_root or runtime_directory
        try:
            result = export_gap_turn_to_inbox(
                session_id=session_id,
                inbox_directory=resolved_inbox_directory,
                runtime_root=resolved_runtime_root,
                turn_id=turn_id,
                latest=latest,
            )
        except ValueError as error:
            output_fn(str(error))
            return 2
        output_fn(
            "Knowledge gap intake completed: "
            f"{result.markdown_path} "
            f"(metadata={result.metadata_path}, session_id={result.session_id}, turn_id={result.turn_id}, gap_type={result.gap_type})"
        )
        return 0
    if len(args) >= 2 and args[0] == "knowledge" and args[1] == "intake-source":
        try:
            inbox_directory, source_class, source_path, kind, entry_id, name, file_stem = (
                _parse_knowledge_intake_source_options(args[2:])
            )
        except ValueError as error:
            output_fn(str(error))
            return 2
        if not source_class:
            output_fn("knowledge intake-source requires --source-class")
            return 2
        if not source_path:
            output_fn("knowledge intake-source requires --source-path")
            return 2
        if not kind:
            output_fn("knowledge intake-source requires --kind")
            return 2
        if not entry_id:
            output_fn("knowledge intake-source requires --id")
            return 2
        if not name:
            output_fn("knowledge intake-source requires --name")
            return 2
        resolved_inbox_directory = inbox_directory or str(default_inbox_dir())
        try:
            result = intake_source_to_inbox(
                inbox_directory=resolved_inbox_directory,
                source_class=source_class,
                source_path=source_path,
                kind=kind,
                entry_id=entry_id,
                name=name,
                file_stem=file_stem,
            )
        except ValueError as error:
            output_fn(str(error))
            return 2
        output_fn(
            "Knowledge source intake completed: "
            f"{result.markdown_path} "
            f"(metadata={result.metadata_path}, source_class={result.source_class}, source_path={result.source_path})"
        )
        return 0
    if len(args) >= 2 and args[0] == "knowledge" and args[1] == "triage-gap":
        try:
            build_root, build_id, entry_id, decision, status, expected_mode, expected_task, scope, note = (
                _parse_knowledge_triage_gap_options(args[2:])
            )
        except ValueError as error:
            output_fn(str(error))
            return 2
        if not build_id:
            output_fn("knowledge triage-gap requires --build-id")
            return 2
        if not entry_id:
            output_fn("knowledge triage-gap requires --entry-id")
            return 2
        if not decision:
            output_fn("knowledge triage-gap requires --decision")
            return 2
        resolved_build_root = build_root or str(default_build_root(runtime_root=runtime_directory))
        try:
            result = apply_gap_review_decision(
                Path(resolved_build_root) / build_id,
                entry_id=entry_id,
                status=status,
                decision=decision,
                expected_mode=expected_mode,
                expected_task=expected_task,
                scope=scope,
                note=note,
            )
        except ValueError as error:
            output_fn(str(error))
            return 2
        output_fn(
            "Knowledge gap triage updated: "
            f"{result.metadata_path} "
            f"(build_id={build_id}, entry_id={result.entry_id}, decision={result.review['decision']})"
        )
        return 0
    if len(args) >= 2 and args[0] == "knowledge" and args[1] == "activate":
        try:
            build_root, build_id = _parse_knowledge_activate_options(args[2:])
        except ValueError as error:
            output_fn(str(error))
            return 2
        if not build_id:
            output_fn("knowledge activate requires --build-id")
            return 2
        resolved_build_root = build_root or str(default_build_root(runtime_root=runtime_directory))
        try:
            result = activate_knowledge_build(
                source_directory=effective_source_directory,
                build_root=resolved_build_root,
                build_id=build_id,
            )
        except ValueError as error:
            output_fn(str(error))
            return 2
        output_fn(
            "Knowledge activation completed: "
            f"{result.build_dir} "
            f"(files={len(result.activated_files)}, backup_id={result.backup_id})"
        )
        return 0
    if len(args) >= 2 and args[0] == "knowledge" and args[1] == "rollback":
        try:
            build_root, backup_id = _parse_knowledge_rollback_options(args[2:])
        except ValueError as error:
            output_fn(str(error))
            return 2
        if not backup_id:
            output_fn("knowledge rollback requires --backup-id")
            return 2
        resolved_build_root = build_root or str(default_build_root(runtime_root=runtime_directory))
        try:
            result = rollback_knowledge_backup(
                source_directory=effective_source_directory,
                build_root=resolved_build_root,
                backup_id=backup_id,
            )
        except ValueError as error:
            output_fn(str(error))
            return 2
        output_fn(
            "Knowledge rollback completed: "
            f"{result.backup_dir} "
            f"(files={len(result.restored_files)}, backup_id={result.backup_id})"
        )
        return 0
    if len(args) >= 2 and args[0] == "knowledge" and args[1] == "queue":
        try:
            build_root, build_id = _parse_knowledge_review_options(args[2:])
        except ValueError as error:
            output_fn(str(error))
            return 2
        resolved_build_root = build_root or str(default_build_root(runtime_root=runtime_directory))
        try:
            result = build_maintainer_queue(build_root=resolved_build_root, build_id=build_id)
        except ValueError as error:
            output_fn(str(error))
            return 2
        output_fn(format_maintainer_queue(result))
        return 0
    if len(args) >= 2 and args[0] == "knowledge" and args[1] == "review":
        try:
            build_root, build_id = _parse_knowledge_review_options(args[2:])
        except ValueError as error:
            output_fn(str(error))
            return 2
        resolved_build_root = build_root or str(default_build_root(runtime_root=runtime_directory))
        try:
            result = review_knowledge_build(build_root=resolved_build_root, build_id=build_id)
        except ValueError as error:
            output_fn(str(error))
            return 2
        output_fn(f"Knowledge review: {result.build_dir}")
        output_fn(result.report_text.rstrip())
        return 0
    if len(args) >= 2 and args[0] == "knowledge" and args[1] == "export-dataset":
        try:
            build_root, build_id, output_path, export_runtime_root = _parse_knowledge_export_dataset_options(args[2:])
        except ValueError as error:
            output_fn(str(error))
            return 2
        if not output_path:
            output_fn("knowledge export-dataset requires --output")
            return 2
        resolved_build_root = build_root or str(default_build_root(runtime_root=runtime_directory))
        result = export_reviewed_gap_dataset(
            build_root=resolved_build_root,
            build_id=build_id,
            runtime_root=export_runtime_root or runtime_directory,
            output_path=output_path,
        )
        output_fn(format_dataset_export_summary(result))
        return 0
    if args and args[0] == "search":
        if len(args) >= 2 and args[1] in HELP_FLAGS:
            output_fn(format_search_command_help())
            return 0
        keyword = " ".join(args[1:]).strip()
        if not keyword:
            output_fn("search keyword is required")
            return 2
        return print_search_results(keyword, output_fn=output_fn, source_directory=effective_source_directory)
    query = " ".join(args).strip()
    try:
        output_fn(
            format_support_answer_card(
                run_query(
                    query,
                    knowledge_directory=effective_knowledge_directory,
                    source_directory=effective_source_directory,
                )
            )
        )
    except RuntimeError as error:
        output_fn(_format_cli_runtime_error(error))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
