from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from sentieon_assist.config import load_config
from sentieon_assist.ollama_client import probe_ollama
from sentieon_assist.rules import knowledge_dir as default_knowledge_dir
from sentieon_assist.sources import collect_source_bundle_metadata, list_sources


def _directory_summary(directory: str | Path) -> dict[str, Any]:
    root = Path(directory)
    files = [path.name for path in sorted(root.iterdir()) if path.is_file()] if root.exists() else []
    return {
        "directory": str(root),
        "exists": root.exists(),
        "file_count": len(files),
        "files": files,
    }


def gather_doctor_report(
    *,
    knowledge_directory: str | None = None,
    source_directory: str | None = None,
    api_probe: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    config = load_config()
    effective_knowledge_directory = Path(knowledge_directory) if knowledge_directory else default_knowledge_dir()
    effective_source_directory = Path(source_directory or config.source_dir)

    probe = api_probe or (lambda base_url: probe_ollama(base_url, config.ollama_model))
    ollama = {
        "base_url": config.ollama_base_url,
        "model": config.ollama_model,
    }
    try:
        ollama.update(probe(config.ollama_base_url))
    except RuntimeError as exc:
        ollama.update({"ok": False, "error": str(exc)})

    sources = _directory_summary(effective_source_directory)
    sources["file_count"] = len(list_sources(effective_source_directory))
    sources["files"] = [item["name"] for item in list_sources(effective_source_directory)]
    sources.update(collect_source_bundle_metadata(effective_source_directory))

    return {
        "ollama": ollama,
        "knowledge": _directory_summary(effective_knowledge_directory),
        "sources": sources,
    }


def _format_file_list(files: list[str]) -> str:
    return ", ".join(files) if files else "-"


def format_doctor_report(report: dict[str, Any]) -> str:
    ollama = report["ollama"]
    knowledge = report["knowledge"]
    sources = report["sources"]
    ollama_lines = [
        "【Ollama】",
        f"base_url: {ollama['base_url']}",
        f"model: {ollama['model']}",
        f"status: {'ok' if ollama.get('ok') else 'error'}",
    ]
    if ollama.get("ok"):
        ollama_lines.append(f"version: {ollama.get('version') or '-'}")
        if "load_duration_ms" in ollama:
            ollama_lines.append(f"load_duration_ms: {ollama.get('load_duration_ms')}")
        if "eval_duration_ms" in ollama:
            ollama_lines.append(f"eval_duration_ms: {ollama.get('eval_duration_ms')}")
        if "model_available" in ollama:
            ollama_lines.append(f"model_available: {'yes' if ollama.get('model_available') else 'no'}")
    else:
        ollama_lines.append(f"error: {ollama.get('error', '-')}")

    return "\n".join(
        ollama_lines
        + [
            "",
            "【Knowledge】",
            f"directory: {knowledge['directory']}",
            f"exists: {'yes' if knowledge['exists'] else 'no'}",
            f"file_count: {knowledge['file_count']}",
            f"files: {_format_file_list(knowledge['files'])}",
            "",
            "【Sources】",
            f"directory: {sources['directory']}",
            f"exists: {'yes' if sources['exists'] else 'no'}",
            f"file_count: {sources['file_count']}",
            f"files: {_format_file_list(sources['files'])}",
            f"primary_release: {sources.get('primary_release') or '-'}",
            f"primary_date: {sources.get('primary_date') or '-'}",
            f"primary_reference: {sources.get('primary_reference') or '-'}",
        ]
    )
