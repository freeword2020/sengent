from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Callable

from sentieon_assist.config import load_config
from sentieon_assist.factory_backends import build_factory_backend
from sentieon_assist.kernel.pack_runtime import ordered_required_pack_file_names, required_pack_status
from sentieon_assist.llm_backends import build_backend_router
from sentieon_assist.runtime_guidance import doctor_guidance_lines
from sentieon_assist.rules import knowledge_dir as default_knowledge_dir
from sentieon_assist.sources import collect_source_bundle_metadata, list_sources
from sentieon_assist.vendors import resolve_vendor_id


def _manifest_entry_value(entry: Any, field: str) -> Any:
    if hasattr(entry, field):
        return getattr(entry, field)
    if isinstance(entry, dict):
        return entry[field]
    raise AttributeError(f"pack manifest entry does not expose {field}")


def _managed_pack_file_names() -> tuple[str, ...]:
    return ordered_required_pack_file_names(resolve_vendor_id(None))


def _missing_managed_pack_files(directory: Path) -> list[str]:
    resolved_vendor_id = resolve_vendor_id(None)
    return [
        status.file_name
        for status in required_pack_status(directory, resolved_vendor_id)
        if status.required and not status.exists
    ]


def _invalid_managed_pack_files(directory: Path) -> list[str]:
    resolved_vendor_id = resolve_vendor_id(None)
    return [
        status.file_name
        for status in required_pack_status(directory, resolved_vendor_id)
        if status.required and status.exists and not status.valid
    ]


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
    skip_ollama_probe: bool = False,
    api_probe: Callable[[str], dict[str, Any]] | None = None,
    factory_api_probe: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    config = load_config()
    effective_knowledge_directory = Path(knowledge_directory) if knowledge_directory else default_knowledge_dir()
    effective_source_directory = Path(source_directory or config.source_dir)

    probe = api_probe or (lambda base_url: build_backend_router(config).probe_primary())
    runtime_llm = {
        "provider": config.runtime_llm_provider,
        "base_url": config.ollama_base_url,
        "model": config.ollama_model,
    }
    if skip_ollama_probe:
        runtime_llm.update({"ok": False, "skipped": True, "error": "ollama probe skipped"})
    else:
        try:
            runtime_llm.update(probe(config.ollama_base_url))
        except RuntimeError as exc:
            runtime_llm.update({"ok": False, "error": str(exc)})

    factory_hosted = {
        "provider": config.factory_hosted_provider,
        "base_url": config.factory_hosted_base_url,
        "model": config.factory_hosted_model,
        "enabled": bool(config.factory_hosted_provider),
        "review_only": True,
    }
    if not factory_hosted["enabled"]:
        factory_hosted.update({"ok": False, "status": "disabled", "reason": "factory hosted provider disabled"})
    elif not config.factory_hosted_base_url or not config.factory_hosted_model:
        factory_hosted.update(
            {
                "ok": False,
                "status": "misconfigured",
                "reason": "factory hosted provider requires base_url and model",
            }
        )
    else:
        hosted_probe = factory_api_probe or (lambda _base_url: build_factory_backend(config).probe())
        try:
            factory_hosted.update(hosted_probe(config.factory_hosted_base_url))
            factory_hosted.setdefault("status", "ok" if factory_hosted.get("ok") else "error")
        except RuntimeError as exc:
            factory_hosted.update({"ok": False, "status": "error", "error": str(exc)})

    docling_is_available = importlib.util.find_spec("docling") is not None
    missing_pack_files = _missing_managed_pack_files(effective_source_directory)
    invalid_pack_files = _invalid_managed_pack_files(effective_source_directory)
    sources = _directory_summary(effective_source_directory)
    sources["file_count"] = len(list_sources(effective_source_directory))
    sources["files"] = [item["name"] for item in list_sources(effective_source_directory)]
    sources.update(collect_source_bundle_metadata(effective_source_directory))
    sources["managed_pack_complete"] = not missing_pack_files and not invalid_pack_files
    sources["missing_managed_pack_files"] = missing_pack_files
    sources["invalid_managed_pack_files"] = invalid_pack_files

    return {
        "runtime_llm": runtime_llm,
        "ollama": runtime_llm,
        "build_runtime": {
            "pyyaml_available": True,
            "pyyaml_mode": "mandatory-installed",
            "docling_available": docling_is_available,
            "docling_mode": (
                "optional-pdf-parser-available"
                if docling_is_available
            else "optional-pdf-parser-missing"
            ),
        },
        "factory_hosted": factory_hosted,
        "knowledge": _directory_summary(effective_knowledge_directory),
        "sources": sources,
    }


def _format_file_list(files: list[str]) -> str:
    return ", ".join(files) if files else "-"


def format_doctor_report(report: dict[str, Any]) -> str:
    runtime_llm = report.get("runtime_llm") or report.get("ollama") or {}
    factory_hosted = report.get("factory_hosted") or {}
    build_runtime = report.get("build_runtime", {})
    knowledge = report["knowledge"]
    sources = report["sources"]
    provider = str(runtime_llm.get("provider", "ollama")).strip() or "ollama"
    runtime_lines = [
        "【Runtime LLM】",
        f"provider: {provider}",
        f"base_url: {runtime_llm['base_url']}",
        f"model: {runtime_llm['model']}",
        f"status: {'skipped' if runtime_llm.get('skipped') else ('ok' if runtime_llm.get('ok') else 'error')}",
    ]
    if runtime_llm.get("ok"):
        runtime_lines.append(f"version: {runtime_llm.get('version') or '-'}")
        if "load_duration_ms" in runtime_llm:
            runtime_lines.append(f"load_duration_ms: {runtime_llm.get('load_duration_ms')}")
        if "eval_duration_ms" in runtime_llm:
            runtime_lines.append(f"eval_duration_ms: {runtime_llm.get('eval_duration_ms')}")
        if "model_available" in runtime_llm:
            runtime_lines.append(f"model_available: {'yes' if runtime_llm.get('model_available') else 'no'}")
    else:
        runtime_lines.append(f"error: {runtime_llm.get('error', '-')}")

    build_runtime_lines = [
        "【Build Runtime】",
        f"pyyaml_available: {'yes' if build_runtime.get('pyyaml_available') else 'no'}",
        f"pyyaml_mode: {build_runtime.get('pyyaml_mode') or '-'}",
        f"docling_available: {'yes' if build_runtime.get('docling_available') else 'no'}",
        f"docling_mode: {build_runtime.get('docling_mode') or '-'}",
    ]
    factory_lines = [
        "【Factory Hosted】",
        f"provider: {factory_hosted.get('provider') or '-'}",
        f"base_url: {factory_hosted.get('base_url') or '-'}",
        f"model: {factory_hosted.get('model') or '-'}",
        f"status: {factory_hosted.get('status') or ('ok' if factory_hosted.get('ok') else 'disabled')}",
        f"review_only: {'yes' if factory_hosted.get('review_only', True) else 'no'}",
        "mode: factory review-only",
    ]
    if factory_hosted.get("ok"):
        if "version" in factory_hosted:
            factory_lines.append(f"version: {factory_hosted.get('version') or '-'}")
        if "model_available" in factory_hosted:
            factory_lines.append(f"model_available: {'yes' if factory_hosted.get('model_available') else 'no'}")
    elif factory_hosted.get("reason"):
        factory_lines.append(f"reason: {factory_hosted.get('reason')}")
    elif factory_hosted.get("error"):
        factory_lines.append(f"error: {factory_hosted.get('error')}")
    guidance_lines = doctor_guidance_lines(runtime_llm=runtime_llm)
    if not factory_hosted.get("enabled"):
        guidance_lines = guidance_lines + [
            "Factory hosted provider is disabled; configure `SENGENT_FACTORY_HOSTED_PROVIDER`, `SENGENT_FACTORY_HOSTED_BASE_URL`, and `SENGENT_FACTORY_HOSTED_MODEL` to enable hosted factory drafting.",
        ]

    return "\n".join(
        runtime_lines
        + [
            "",
        ]
        + build_runtime_lines
        + [
            "",
        ]
        + factory_lines
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
            f"managed_pack_complete: {'yes' if sources.get('managed_pack_complete') else 'no'}",
            f"missing_managed_pack_files: {_format_file_list(sources.get('missing_managed_pack_files') or [])}",
            f"invalid_managed_pack_files: {_format_file_list(sources.get('invalid_managed_pack_files') or [])}",
        ]
        + (
            ["", "【建议下一步】"]
            + [f"- {line}" for line in guidance_lines]
            if guidance_lines
            else []
        )
    )
