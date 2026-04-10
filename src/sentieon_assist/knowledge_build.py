from __future__ import annotations

import importlib.util
import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from sentieon_assist.app_paths import default_knowledge_build_root, default_knowledge_inbox_dir, default_runtime_root


TEXT_FILE_TYPES = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".json": "json",
    ".html": "html",
    ".htm": "html",
}
PDF_FILE_TYPE = "pdf"
GATE_COMMANDS: tuple[str, ...] = (
    "python scripts/pilot_readiness_eval.py",
    "python scripts/pilot_closed_loop.py",
)
PACK_ENTRY_TYPES: dict[str, str] = {
    "sentieon-modules.json": "module",
    "workflow-guides.json": "workflow",
    "external-format-guides.json": "external_format",
    "external-tool-guides.json": "external_tool",
    "external-error-associations.json": "external_error",
}
MANAGED_PACK_FILES: tuple[str, ...] = tuple(sorted(PACK_ENTRY_TYPES))
SCAFFOLD_KIND_TO_PACK_TARGET: dict[str, str] = {
    "module": "sentieon-modules.json",
    "workflow": "workflow-guides.json",
    "external-format": "external-format-guides.json",
    "external-tool": "external-tool-guides.json",
    "external-error": "external-error-associations.json",
}
PILOT_READINESS_REPORT_NAME = "pilot-readiness-report.json"
PILOT_CLOSED_LOOP_REPORT_NAME = "pilot-closed-loop-report.json"
ACTIVATION_MANIFEST_NAME = "activation-manifest.json"
ROLLBACK_MANIFEST_NAME = "rollback-manifest.json"
ACTIVATION_BACKUP_DIRECTORY_NAME = "activation-backups"
MAX_ACTIVATION_BACKUPS = 3


@dataclass(frozen=True)
class SourceInventoryEntry:
    path: str
    relative_path: str
    file_type: str
    parser_name: str
    metadata_missing: list[str]
    status: str


@dataclass(frozen=True)
class CanonicalDocumentRecord:
    build_id: str
    doc_id: str
    path: str
    relative_path: str
    file_type: str
    parser_name: str
    product: str
    origin: str
    pack_target: str | None
    entry_type: str | None
    metadata_missing: list[str]
    source_metadata: dict[str, Any]
    text_length: int


@dataclass(frozen=True)
class CanonicalSectionRecord:
    build_id: str
    doc_id: str
    section_id: str
    relative_path: str
    section_index: int
    heading: str
    text: str


@dataclass(frozen=True)
class ScriptCandidateRecord:
    build_id: str
    doc_id: str
    script_candidate_id: str
    relative_path: str
    source_kind: str
    block_index: int
    module_hint: str | None
    confidence: str
    command_lines: list[str]


@dataclass(frozen=True)
class ParameterCandidateRecord:
    build_id: str
    doc_id: str
    script_candidate_id: str
    source_relative_path: str
    module_hint: str | None
    confidence: str
    parameter_name: str


@dataclass(frozen=True)
class ParameterPromotionReviewRecord:
    build_id: str
    doc_id: str
    relative_path: str
    module_id: str
    parameter_name: str
    status: str
    evidence_status: str
    confidence: str
    detail: str


@dataclass(frozen=True)
class ParameterReviewSuggestionRecord:
    build_id: str
    doc_id: str
    relative_path: str
    module_id: str
    parameter_name: str
    suggested_action: str
    template: dict[str, Any]
    detail: str


@dataclass(frozen=True)
class KnowledgeBuildException:
    path: str
    relative_path: str
    file_type: str
    exception_type: str
    detail: str


@dataclass(frozen=True)
class CompileSkip:
    relative_path: str
    reason: str


@dataclass(frozen=True)
class CandidatePackBuildResult:
    compiled_entry_count: int
    compile_skips: list[CompileSkip]
    exceptions: list[KnowledgeBuildException]
    pack_diffs: dict[str, dict[str, Any]]
    parameter_promotion_reviews: list[ParameterPromotionReviewRecord]
    parameter_review_suggestions: list[ParameterReviewSuggestionRecord]


@dataclass(frozen=True)
class KnowledgeBuildResult:
    build_id: str
    build_dir: Path
    inventory_count: int
    canonical_document_count: int
    exception_count: int
    compiled_entry_count: int
    compile_skip_count: int
    docling_available: bool


@dataclass(frozen=True)
class ActivationResult:
    build_id: str
    build_dir: Path
    activated_files: tuple[str, ...]
    backup_id: str


@dataclass(frozen=True)
class ActivationBackupResult:
    backup_id: str
    backup_dir: Path
    source_files: tuple[str, ...]


@dataclass(frozen=True)
class RollbackResult:
    backup_id: str
    backup_dir: Path
    restored_files: tuple[str, ...]


@dataclass(frozen=True)
class KnowledgeScaffoldResult:
    inbox_directory: Path
    markdown_path: Path
    metadata_path: Path
    action: str
    kind: str


@dataclass(frozen=True)
class KnowledgeReviewResult:
    build_dir: Path
    build_id: str
    report_text: str


def default_inbox_dir(*, repo_root: str | Path | None = None, product: str = "sentieon") -> Path:
    if repo_root is not None:
        return Path(repo_root) / "knowledge-inbox" / product
    return default_knowledge_inbox_dir(product=product)


def default_build_root(*, runtime_root: str | Path | None = None) -> Path:
    if runtime_root is not None:
        return Path(runtime_root) / "knowledge-build"
    return default_knowledge_build_root()


def docling_available() -> bool:
    return importlib.util.find_spec("docling") is not None


def run_knowledge_build(
    *,
    source_directory: str | Path,
    inbox_directory: str | Path,
    build_root: str | Path | None = None,
) -> KnowledgeBuildResult:
    resolved_source_directory = Path(source_directory)
    resolved_inbox_directory = Path(inbox_directory)
    resolved_build_root = Path(build_root) if build_root is not None else default_build_root()
    require_complete_managed_pack_set(resolved_source_directory, label="active source directory")

    build_id = _build_id()
    build_dir = resolved_build_root / build_id
    build_dir.mkdir(parents=True, exist_ok=True)

    inventory: list[SourceInventoryEntry] = []
    doc_records: list[CanonicalDocumentRecord] = []
    section_records: list[CanonicalSectionRecord] = []
    script_candidate_records: list[ScriptCandidateRecord] = []
    parameter_candidate_records: list[ParameterCandidateRecord] = []
    exceptions: list[KnowledgeBuildException] = []
    docling_is_available = docling_available()

    for path in _iter_inbox_files(resolved_inbox_directory):
        relative_path = path.relative_to(resolved_inbox_directory).as_posix()
        file_type = _detect_file_type(path)
        parser_name = _parser_name_for_type(file_type, docling_is_available=docling_is_available)
        metadata_missing = _metadata_missing_from_path(path, source_metadata={})
        if file_type == PDF_FILE_TYPE and not docling_is_available:
            inventory.append(
                SourceInventoryEntry(
                    path=str(path),
                    relative_path=relative_path,
                    file_type=file_type,
                    parser_name=parser_name,
                    metadata_missing=metadata_missing,
                    status="exception",
                )
            )
            exceptions.append(
                KnowledgeBuildException(
                    path=str(path),
                    relative_path=relative_path,
                    file_type=file_type,
                    exception_type="parser_unavailable",
                    detail="Docling is required to parse PDF sources in the local build pipeline.",
                )
            )
            continue
        if file_type == "unsupported":
            inventory.append(
                SourceInventoryEntry(
                    path=str(path),
                    relative_path=relative_path,
                    file_type=file_type,
                    parser_name=parser_name,
                    metadata_missing=metadata_missing,
                    status="exception",
                )
            )
            exceptions.append(
                KnowledgeBuildException(
                    path=str(path),
                    relative_path=relative_path,
                    file_type=file_type,
                    exception_type="unsupported_file",
                    detail="The current P0 knowledge build only supports text-like files and optional Docling-backed PDFs.",
                )
            )
            continue

        try:
            text, source_metadata = _parse_document(path, file_type=file_type, docling_is_available=docling_is_available)
        except Exception as error:
            inventory.append(
                SourceInventoryEntry(
                    path=str(path),
                    relative_path=relative_path,
                    file_type=file_type,
                    parser_name=parser_name,
                    metadata_missing=metadata_missing,
                    status="exception",
                )
            )
            exceptions.append(
                KnowledgeBuildException(
                    path=str(path),
                    relative_path=relative_path,
                    file_type=file_type,
                    exception_type="document_parse_error",
                    detail=str(error),
                )
            )
            continue
        try:
            sidecar_metadata = _load_sidecar_metadata(path)
        except Exception as error:
            sidecar_metadata = {}
            exceptions.append(
                KnowledgeBuildException(
                    path=str(path),
                    relative_path=relative_path,
                    file_type=file_type,
                    exception_type="sidecar_metadata_error",
                    detail=str(error),
                )
            )
        source_metadata = _merge_metadata(source_metadata, sidecar_metadata)
        metadata_missing = _metadata_missing_from_path(path, source_metadata=source_metadata)
        doc_id = uuid4().hex
        inventory.append(
            SourceInventoryEntry(
                path=str(path),
                relative_path=relative_path,
                file_type=file_type,
                parser_name=parser_name,
                metadata_missing=metadata_missing,
                status="parsed",
            )
        )
        doc_records.append(
            CanonicalDocumentRecord(
                build_id=build_id,
                doc_id=doc_id,
                path=str(path),
                relative_path=relative_path,
                file_type=file_type,
                parser_name=parser_name,
                product=_product_from_path(path),
                origin="local_inbox",
                pack_target=_string_or_none(source_metadata.get("pack_target")),
                entry_type=_string_or_none(source_metadata.get("entry_type")),
                metadata_missing=metadata_missing,
                source_metadata=source_metadata,
                text_length=len(text),
            )
        )
        extracted_script_candidates, extraction_exceptions = _extract_script_candidates(
            build_id=build_id,
            doc_id=doc_id,
            path=path,
            relative_path=relative_path,
            file_type=file_type,
            text=text,
            source_metadata=source_metadata,
        )
        script_candidate_records.extend(extracted_script_candidates)
        parameter_candidate_records.extend(
            _extract_parameter_candidates(
                build_id=build_id,
                doc_id=doc_id,
                relative_path=relative_path,
                script_candidates=extracted_script_candidates,
            )
        )
        exceptions.extend(extraction_exceptions)
        for index, section_text in enumerate(_split_sections(text), start=1):
            section_records.append(
                CanonicalSectionRecord(
                    build_id=build_id,
                    doc_id=doc_id,
                    section_id=uuid4().hex,
                    relative_path=relative_path,
                    section_index=index,
                    heading="",
                    text=section_text,
                )
            )

    candidate_pack_result = _compile_candidate_packs(
        resolved_source_directory,
        build_dir / "candidate-packs",
        build_id=build_id,
        doc_records=doc_records,
        script_candidates=script_candidate_records,
        parameter_candidates=parameter_candidate_records,
    )
    exceptions.extend(candidate_pack_result.exceptions)
    _write_json(build_dir / "inventory.json", _inventory_payload(build_id, resolved_inbox_directory, inventory, docling_is_available))
    _write_jsonl(build_dir / "canonical_doc_record.jsonl", doc_records)
    _write_jsonl(build_dir / "canonical_section_record.jsonl", section_records)
    _write_jsonl(build_dir / "script_candidate_record.jsonl", script_candidate_records)
    _write_jsonl(build_dir / "parameter_candidate_record.jsonl", parameter_candidate_records)
    _write_jsonl(build_dir / "parameter_promotion_review.jsonl", candidate_pack_result.parameter_promotion_reviews)
    _write_jsonl(build_dir / "parameter_review_suggestion.jsonl", candidate_pack_result.parameter_review_suggestions)
    _write_jsonl(build_dir / "exceptions.jsonl", exceptions)
    (build_dir / "report.md").write_text(
        _build_report(
            build_id=build_id,
            inbox_directory=resolved_inbox_directory,
            inventory=inventory,
            exceptions=exceptions,
            doc_records=doc_records,
            build_dir=build_dir,
            candidate_pack_result=candidate_pack_result,
            script_candidate_records=script_candidate_records,
            parameter_candidate_records=parameter_candidate_records,
            parameter_promotion_reviews=candidate_pack_result.parameter_promotion_reviews,
            parameter_review_suggestions=candidate_pack_result.parameter_review_suggestions,
            docling_is_available=docling_is_available,
        ),
        encoding="utf-8",
    )

    return KnowledgeBuildResult(
        build_id=build_id,
        build_dir=build_dir,
        inventory_count=len(inventory),
        canonical_document_count=len(doc_records),
        exception_count=len(exceptions),
        compiled_entry_count=candidate_pack_result.compiled_entry_count,
        compile_skip_count=len(candidate_pack_result.compile_skips),
        docling_available=docling_is_available,
    )


def activate_knowledge_build(
    *,
    source_directory: str | Path,
    build_root: str | Path,
    build_id: str,
) -> ActivationResult:
    resolved_source_directory = Path(source_directory)
    resolved_build_root = Path(build_root)
    build_dir = resolved_build_root / build_id
    candidate_directory = build_dir / "candidate-packs"
    manifest_path = candidate_directory / "manifest.json"
    if not build_dir.exists():
        raise ValueError(f"knowledge build not found: {build_dir}")
    if not candidate_directory.exists() or not manifest_path.exists():
        raise ValueError(f"candidate packs are incomplete for build {build_id}")
    require_complete_managed_pack_set(resolved_source_directory, label="active source directory")
    require_complete_managed_pack_set(candidate_directory, label=f"candidate packs for build {build_id}")
    readiness_report = _load_required_gate_report(build_dir / PILOT_READINESS_REPORT_NAME, label="pilot readiness")
    closed_loop_report = _load_required_gate_report(build_dir / PILOT_CLOSED_LOOP_REPORT_NAME, label="pilot closed loop")
    if not readiness_report.get("ok"):
        raise ValueError("candidate build activation blocked: pilot readiness gate did not pass")
    if not closed_loop_report.get("ok"):
        raise ValueError("candidate build activation blocked: pilot closed loop gate did not pass")

    backup = _create_activation_backup(
        source_directory=resolved_source_directory,
        build_root=resolved_build_root,
        build_id=build_id,
    )
    activated_files = _managed_pack_files_from_directory(candidate_directory)
    try:
        _replace_managed_pack_set(
            target_directory=resolved_source_directory,
            incoming_directory=candidate_directory,
            incoming_files=activated_files,
            rollback_directory=backup.backup_dir,
            rollback_files=backup.source_files,
            failure_label="knowledge activation failed",
        )
    except ValueError:
        _prune_activation_backups(resolved_build_root, keep=MAX_ACTIVATION_BACKUPS)
        raise

    _write_json(
        build_dir / ACTIVATION_MANIFEST_NAME,
        {
            "build_id": build_id,
            "activated_at": datetime.now(timezone.utc).isoformat(),
            "source_directory": str(resolved_source_directory),
            "activated_files": activated_files,
            "backup_id": backup.backup_id,
            "backup_directory": str(backup.backup_dir),
            "backup_files": list(backup.source_files),
            "gate_reports": {
                PILOT_READINESS_REPORT_NAME: {"ok": bool(readiness_report.get("ok"))},
                PILOT_CLOSED_LOOP_REPORT_NAME: {"ok": bool(closed_loop_report.get("ok"))},
            },
        },
    )
    _prune_activation_backups(resolved_build_root, keep=MAX_ACTIVATION_BACKUPS)
    return ActivationResult(
        build_id=build_id,
        build_dir=build_dir,
        activated_files=tuple(activated_files),
        backup_id=backup.backup_id,
    )


def rollback_knowledge_backup(
    *,
    source_directory: str | Path,
    build_root: str | Path,
    backup_id: str,
) -> RollbackResult:
    resolved_source_directory = Path(source_directory)
    resolved_build_root = Path(build_root)
    backup_dir = _activation_backup_root(resolved_build_root) / backup_id
    manifest = _load_activation_backup_manifest(backup_dir)
    source_files = manifest.get("source_files")
    if not isinstance(source_files, list) or not all(isinstance(item, str) for item in source_files):
        raise ValueError(f"knowledge backup is invalid: {backup_dir}")
    require_complete_managed_pack_list(source_files, label=f"knowledge backup manifest {backup_id}")
    require_complete_managed_pack_set(backup_dir, label=f"knowledge backup {backup_id}")

    rollback_guard = _snapshot_runtime_state(
        source_directory=resolved_source_directory,
        build_root=resolved_build_root,
        label="rollback-guard",
    )
    try:
        _replace_managed_pack_set(
            target_directory=resolved_source_directory,
            incoming_directory=backup_dir,
            incoming_files=source_files,
            rollback_directory=rollback_guard,
            rollback_files=_managed_pack_files_from_directory(rollback_guard),
            failure_label="knowledge rollback failed",
        )
    finally:
        shutil.rmtree(rollback_guard, ignore_errors=True)
    restored_files = sorted(source_files)

    _write_json(
        resolved_build_root / ROLLBACK_MANIFEST_NAME,
        {
            "backup_id": backup_id,
            "backup_directory": str(backup_dir),
            "restored_at": datetime.now(timezone.utc).isoformat(),
            "source_directory": str(resolved_source_directory),
            "restored_files": restored_files,
        },
    )
    return RollbackResult(
        backup_id=backup_id,
        backup_dir=backup_dir,
        restored_files=tuple(restored_files),
    )


def scaffold_knowledge_source(
    *,
    inbox_directory: str | Path,
    kind: str,
    entry_id: str,
    name: str | None = None,
    action: str = "upsert",
    file_stem: str | None = None,
) -> KnowledgeScaffoldResult:
    normalized_kind = kind.strip().lower()
    if normalized_kind not in SCAFFOLD_KIND_TO_PACK_TARGET:
        raise ValueError(f"unsupported scaffold kind: {kind}")
    normalized_action = _normalize_scaffold_action(action)
    if normalized_action == "upsert" and not _string_or_none(name):
        raise ValueError("knowledge scaffold requires --name for upsert actions")

    resolved_inbox_directory = Path(inbox_directory)
    resolved_inbox_directory.mkdir(parents=True, exist_ok=True)
    stem = _string_or_none(file_stem) or (f"retire-{entry_id}" if normalized_action == "delete" else entry_id)
    markdown_path = resolved_inbox_directory / f"{stem}.md"
    metadata_path = resolved_inbox_directory / f"{stem}.meta.yaml"

    if not markdown_path.exists():
        markdown_path.write_text(
            _scaffold_markdown_body(
                kind=normalized_kind,
                entry_id=entry_id,
                name=name,
                action=normalized_action,
            ),
            encoding="utf-8",
        )

    defaults = _scaffold_metadata_defaults(
        kind=normalized_kind,
        entry_id=entry_id,
        name=name,
        action=normalized_action,
    )
    existing_metadata = {}
    if metadata_path.exists():
        payload = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            existing_metadata = _normalize_metadata_dict(payload)
    merged_metadata = _merge_metadata(existing_metadata, defaults)
    _write_yaml(metadata_path, merged_metadata)

    return KnowledgeScaffoldResult(
        inbox_directory=resolved_inbox_directory,
        markdown_path=markdown_path,
        metadata_path=metadata_path,
        action=normalized_action,
        kind=normalized_kind,
    )


def review_knowledge_build(
    *,
    build_root: str | Path,
    build_id: str | None = None,
) -> KnowledgeReviewResult:
    resolved_build_root = Path(build_root)
    if build_id:
        build_dir = resolved_build_root / build_id
    else:
        build_dir = _latest_build_directory(resolved_build_root)
    if build_dir is None or not build_dir.exists():
        raise ValueError(f"knowledge build not found under {resolved_build_root}")
    report_path = build_dir / "report.md"
    if not report_path.exists():
        raise ValueError(f"knowledge build report missing: {report_path}")
    return KnowledgeReviewResult(
        build_dir=build_dir,
        build_id=build_dir.name,
        report_text=report_path.read_text(encoding="utf-8"),
    )


def _build_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]


def _backup_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]


def _latest_build_directory(build_root: Path) -> Path | None:
    if not build_root.exists():
        return None
    directories = sorted(
        path
        for path in build_root.iterdir()
        if path.is_dir() and (path / "report.md").exists()
    )
    return directories[-1] if directories else None


def _normalize_scaffold_action(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in {"upsert", "delete"}:
        raise ValueError(f"unsupported scaffold action: {value}")
    return normalized


def _scaffold_markdown_body(*, kind: str, entry_id: str, name: str | None, action: str) -> str:
    if action == "delete":
        display_name = _string_or_none(name) or entry_id
        return f"# Retire {display_name}\n\nReason for retirement or replacement.\n"
    display_name = _string_or_none(name) or entry_id
    return f"# {display_name}\n\nPaste or summarize source material here.\n"


def _scaffold_metadata_defaults(*, kind: str, entry_id: str, name: str | None, action: str) -> dict[str, Any]:
    pack_target = SCAFFOLD_KIND_TO_PACK_TARGET[kind]
    entry_type = PACK_ENTRY_TYPES[pack_target]
    today = datetime.now(timezone.utc).date().isoformat()
    defaults: dict[str, Any] = {
        "pack_target": pack_target,
        "entry_type": entry_type,
        "id": entry_id,
        "action": action,
        "version": "",
        "date": today,
        "origin": "manual-maintainer",
    }
    if action == "delete":
        defaults["summary"] = "Retirement request."
        return defaults

    display_name = _string_or_none(name) or entry_id
    defaults["name"] = display_name
    if kind == "module":
        defaults.update({"aliases": [], "category": "", "summary": "", "scope": [], "related_modules": []})
    elif kind == "workflow":
        defaults.update({"priority": "50", "summary": "", "guidance": [], "follow_up": []})
    elif kind in {"external-format", "external-tool"}:
        defaults.update(
            {
                "aliases": [],
                "summary": "",
                "details": [],
                "troubleshooting": [],
                "usage_boundary": [],
                "source_notes": [],
                "official_sources": [],
            }
        )
    elif kind == "external-error":
        defaults.update(
            {
                "name": display_name,
                "patterns_any": [],
                "require_any": [],
                "summary": "",
                "checks": [],
                "related_guides": [],
                "usage_boundary": [],
                "source_notes": [],
            }
        )
    return defaults


def _load_required_gate_report(path: Path, *, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"candidate build activation blocked: missing {label} gate report at {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"candidate build activation blocked: invalid {label} gate report at {path}")
    return payload


def _activation_backup_root(build_root: Path) -> Path:
    return build_root / ACTIVATION_BACKUP_DIRECTORY_NAME


def _managed_pack_files_from_directory(directory: Path) -> list[str]:
    return [
        file_name
        for file_name in MANAGED_PACK_FILES
        if (directory / file_name).exists()
    ]


def missing_managed_pack_files(directory: Path) -> list[str]:
    return [
        file_name
        for file_name in MANAGED_PACK_FILES
        if not (directory / file_name).exists()
    ]


def require_complete_managed_pack_set(directory: Path, *, label: str) -> None:
    missing_files = missing_managed_pack_files(directory)
    if missing_files:
        missing_text = ", ".join(missing_files)
        raise ValueError(f"{label} managed packs are incomplete: missing {missing_text}")


def require_complete_managed_pack_list(file_names: list[str] | tuple[str, ...], *, label: str) -> None:
    normalized = {str(item).strip() for item in file_names if str(item).strip()}
    missing_files = [file_name for file_name in MANAGED_PACK_FILES if file_name not in normalized]
    if missing_files:
        missing_text = ", ".join(missing_files)
        raise ValueError(f"{label} is incomplete: missing {missing_text}")


def _create_activation_backup(
    *,
    source_directory: Path,
    build_root: Path,
    build_id: str,
) -> ActivationBackupResult:
    backup_id = _backup_id()
    backup_dir = _activation_backup_root(build_root) / backup_id
    backup_dir.mkdir(parents=True, exist_ok=True)

    source_files = _managed_pack_files_from_directory(source_directory)
    for file_name in source_files:
        shutil.copy2(source_directory / file_name, backup_dir / file_name)

    _write_json(
        backup_dir / "manifest.json",
        {
            "backup_id": backup_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_directory": str(source_directory),
            "source_files": source_files,
            "origin_build_id": build_id,
        },
    )
    return ActivationBackupResult(
        backup_id=backup_id,
        backup_dir=backup_dir,
        source_files=tuple(source_files),
    )


def _prune_activation_backups(build_root: Path, *, keep: int) -> None:
    backup_root = _activation_backup_root(build_root)
    if not backup_root.exists():
        return
    backup_dirs = sorted(path for path in backup_root.iterdir() if path.is_dir())
    while len(backup_dirs) > keep:
        stale_dir = backup_dirs.pop(0)
        shutil.rmtree(stale_dir)


def _snapshot_runtime_state(*, source_directory: Path, build_root: Path, label: str) -> Path:
    snapshot_dir = build_root / f".{label}-{uuid4().hex[:8]}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    for file_name in _managed_pack_files_from_directory(source_directory):
        shutil.copy2(source_directory / file_name, snapshot_dir / file_name)
    return snapshot_dir


def _replace_managed_pack_set(
    *,
    target_directory: Path,
    incoming_directory: Path,
    incoming_files: list[str] | tuple[str, ...],
    rollback_directory: Path | None,
    rollback_files: list[str] | tuple[str, ...],
    failure_label: str,
) -> None:
    desired_files = sorted({str(item) for item in incoming_files if str(item).strip()})
    target_directory.mkdir(parents=True, exist_ok=True)
    try:
        for file_name in desired_files:
            source_path = incoming_directory / file_name
            if not source_path.exists():
                raise ValueError(f"missing managed pack file: {source_path}")
            temp_path = target_directory / f".{file_name}.{uuid4().hex[:8]}.tmp"
            shutil.copy2(source_path, temp_path)
            temp_path.replace(target_directory / file_name)
        for file_name in MANAGED_PACK_FILES:
            if file_name in desired_files:
                continue
            target_path = target_directory / file_name
            if target_path.exists():
                target_path.unlink()
    except Exception as error:
        if rollback_directory is not None:
            try:
                _restore_managed_pack_set(
                    target_directory=target_directory,
                    restore_directory=rollback_directory,
                    restore_files=rollback_files,
                )
            except Exception as rollback_error:  # pragma: no cover - defensive path
                raise ValueError(f"{failure_label}: {error}; restore also failed: {rollback_error}") from error
        raise ValueError(f"{failure_label}: {error}") from error


def _restore_managed_pack_set(
    *,
    target_directory: Path,
    restore_directory: Path,
    restore_files: list[str] | tuple[str, ...],
) -> None:
    desired_files = sorted({str(item) for item in restore_files if str(item).strip()})
    for file_name in desired_files:
        source_path = restore_directory / file_name
        if not source_path.exists():
            raise ValueError(f"missing restore pack file: {source_path}")
        temp_path = target_directory / f".{file_name}.{uuid4().hex[:8]}.tmp"
        shutil.copy2(source_path, temp_path)
        temp_path.replace(target_directory / file_name)
    for file_name in MANAGED_PACK_FILES:
        if file_name in desired_files:
            continue
        target_path = target_directory / file_name
        if target_path.exists():
            target_path.unlink()


def _load_activation_backup_manifest(backup_dir: Path) -> dict[str, Any]:
    if not backup_dir.exists():
        raise ValueError(f"knowledge backup not found: {backup_dir.name}")
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"knowledge backup is incomplete: missing {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"knowledge backup is invalid: {backup_dir}")
    return payload


def _iter_inbox_files(inbox_directory: Path) -> list[Path]:
    if not inbox_directory.exists():
        return []
    return sorted(path for path in inbox_directory.rglob("*") if path.is_file() and not _is_sidecar_metadata_file(path))


def _is_sidecar_metadata_file(path: Path) -> bool:
    lower_name = path.name.lower()
    return lower_name.endswith(".meta.yaml") or lower_name.endswith(".meta.yml")


def _detect_file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in TEXT_FILE_TYPES:
        return TEXT_FILE_TYPES[suffix]
    if suffix == ".pdf":
        return PDF_FILE_TYPE
    return "unsupported"


def _parser_name_for_type(file_type: str, *, docling_is_available: bool) -> str:
    if file_type == PDF_FILE_TYPE:
        return "docling" if docling_is_available else "docling-unavailable"
    if file_type == "unsupported":
        return "unsupported"
    return "plain-text"


def _metadata_missing_from_path(path: Path, *, source_metadata: dict[str, Any]) -> list[str]:
    missing = []
    for field in ("version", "date"):
        if not _string_or_none(source_metadata.get(field)):
            missing.append(field)
    if path.suffix.lower() in {".md", ".markdown"} and not _string_or_none(source_metadata.get("origin")):
        missing.append("origin")
    return missing


def _product_from_path(path: Path) -> str:
    parts = [part.lower() for part in path.parts]
    if "sentieon" in parts:
        return "sentieon"
    return path.parent.name.lower()


def _parse_document(path: Path, *, file_type: str, docling_is_available: bool) -> tuple[str, dict[str, Any]]:
    if file_type == PDF_FILE_TYPE:
        return (_parse_pdf(path), {}) if docling_is_available else ("", {})
    text = path.read_text(encoding="utf-8", errors="replace")
    if file_type == "markdown":
        return _extract_front_matter(text)
    return text, {}


def _load_sidecar_metadata(path: Path) -> dict[str, Any]:
    for candidate in _sidecar_metadata_candidates(path):
        if not candidate.exists():
            continue
        payload = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
        if isinstance(payload, dict):
            return _normalize_metadata_dict(payload)
    return {}


def _sidecar_metadata_candidates(path: Path) -> tuple[Path, ...]:
    return (
        path.parent / f"{path.stem}.meta.yaml",
        path.parent / f"{path.stem}.meta.yml",
    )


def _merge_metadata(primary: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    merged = dict(primary)
    for key, fallback_value in fallback.items():
        primary_value = merged.get(key)
        if isinstance(primary_value, dict) and isinstance(fallback_value, dict):
            merged[key] = _merge_metadata(primary_value, fallback_value)
            continue
        if _metadata_value_missing(primary_value) and not _metadata_value_missing(fallback_value):
            merged[key] = fallback_value
    return merged


def _metadata_value_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _parse_pdf(path: Path) -> str:
    try:
        from docling.document_converter import DocumentConverter  # type: ignore
    except Exception as error:  # pragma: no cover - exercised only when docling is installed but broken
        raise RuntimeError(f"Docling import failed: {error}") from error
    converter = DocumentConverter()
    result = converter.convert(str(path))
    document = getattr(result, "document", None)
    if document is None:
        return ""
    export = getattr(document, "export_to_markdown", None)
    if callable(export):
        return str(export())
    return str(document)


def _split_sections(text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    return chunks or [text.strip()]


def _extract_front_matter(text: str) -> tuple[str, dict[str, Any]]:
    normalized_text = text.replace("\r\n", "\n")
    if not normalized_text.startswith("---\n"):
        return normalized_text, {}
    end_index = normalized_text.find("\n---\n", 4)
    if end_index == -1:
        return normalized_text, {}
    front_matter_text = normalized_text[4:end_index]
    body = normalized_text[end_index + len("\n---\n") :]
    payload = yaml.safe_load(front_matter_text) or {}
    if not isinstance(payload, dict):
        return body, {}
    return body, _normalize_metadata_dict(payload)


def _normalize_metadata_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _normalize_metadata_value(value) for key, value in payload.items()}


def _normalize_metadata_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _normalize_metadata_dict(value)
    if isinstance(value, list):
        return [_normalize_metadata_value(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_metadata_value(item) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)):
        return str(value)
    return value


def _extract_script_candidates(
    *,
    build_id: str,
    doc_id: str,
    path: Path,
    relative_path: str,
    file_type: str,
    text: str,
    source_metadata: dict[str, Any],
) -> tuple[list[ScriptCandidateRecord], list[KnowledgeBuildException]]:
    block_payloads: list[tuple[str, int, str]] = []
    if file_type == "markdown":
        for block_index, block_text in enumerate(_extract_markdown_script_blocks(text), start=1):
            block_payloads.append(("markdown_fence", block_index, block_text))
    elif file_type == "shell":
        block_payloads.append(("shell_file", 1, text))

    records: list[ScriptCandidateRecord] = []
    exceptions: list[KnowledgeBuildException] = []
    for source_kind, block_index, block_text in block_payloads:
        command_lines = _normalize_command_lines(block_text)
        if not command_lines or not any("sentieon" in line.lower() for line in command_lines):
            continue
        module_hint, confidence = _infer_module_hint(command_lines=command_lines, source_metadata=source_metadata)
        script_candidate_id = uuid4().hex
        records.append(
            ScriptCandidateRecord(
                build_id=build_id,
                doc_id=doc_id,
                script_candidate_id=script_candidate_id,
                relative_path=relative_path,
                source_kind=source_kind,
                block_index=block_index,
                module_hint=module_hint,
                confidence=confidence,
                command_lines=command_lines,
            )
        )
        if confidence == "low":
            exceptions.append(
                KnowledgeBuildException(
                    path=str(path),
                    relative_path=relative_path,
                    file_type=file_type,
                    exception_type="extraction_ambiguity",
                    detail="Extracted script candidate needs review because module ownership could not be inferred confidently.",
                )
            )
    return records, exceptions


def _extract_markdown_script_blocks(text: str) -> list[str]:
    pattern = re.compile(r"```(?P<lang>[^\n`]*)\n(?P<body>.*?)\n```", re.DOTALL)
    blocks: list[str] = []
    for match in pattern.finditer(text):
        language = match.group("lang").strip().lower()
        body = match.group("body")
        if language and language not in {"bash", "sh", "shell", "zsh"}:
            continue
        if "sentieon" not in body.lower():
            continue
        blocks.append(body)
    return blocks


def _normalize_command_lines(text: str) -> list[str]:
    lines = [line.rstrip() for line in text.splitlines()]
    command_lines: list[str] = []
    current = ""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if current:
            current = f"{current} {stripped}"
        else:
            current = stripped
        if current.endswith("\\"):
            current = current[:-1].rstrip()
            continue
        command_lines.append(current)
        current = ""
    if current:
        command_lines.append(current)
    return command_lines


def _infer_module_hint(*, command_lines: list[str], source_metadata: dict[str, Any]) -> tuple[str | None, str]:
    explicit_module = _string_or_none(source_metadata.get("module_id"))
    if explicit_module:
        return _normalize_module_hint(explicit_module), "high"
    if (
        source_metadata.get("pack_target") == "sentieon-modules.json"
        and source_metadata.get("entry_type") == "module"
        and _string_or_none(source_metadata.get("id"))
    ):
        return _normalize_module_hint(str(source_metadata["id"])), "high"

    inferred_hints = {
        hint
        for line in command_lines
        for hint in (_module_hint_from_command_line(line),)
        if hint is not None
    }
    if len(inferred_hints) == 1:
        return next(iter(inferred_hints)), "high"
    return None, "low"


def _module_hint_from_command_line(line: str) -> str | None:
    cli_match = re.search(r"(?:^|\s)sentieon-cli\s+([A-Za-z0-9_-]+)", line)
    if cli_match:
        return _normalize_module_hint(cli_match.group(1))
    algo_match = re.search(r"--algo\s+([A-Za-z0-9_-]+)", line)
    if algo_match:
        return _normalize_module_hint(algo_match.group(1))
    return None


def _normalize_module_hint(value: str) -> str:
    return value.strip().lower()


def _extract_parameter_candidates(
    *,
    build_id: str,
    doc_id: str,
    relative_path: str,
    script_candidates: list[ScriptCandidateRecord],
) -> list[ParameterCandidateRecord]:
    records: list[ParameterCandidateRecord] = []
    for script_candidate in script_candidates:
        seen_parameters: set[str] = set()
        for line in script_candidate.command_lines:
            long_options = re.findall(r"--[A-Za-z0-9_][A-Za-z0-9_-]*", line)
            short_options = re.findall(r"(?<!\S)-[A-Za-z]\b", line)
            for parameter_name in (*long_options, *short_options):
                if parameter_name in seen_parameters:
                    continue
                seen_parameters.add(parameter_name)
                records.append(
                    ParameterCandidateRecord(
                        build_id=build_id,
                        doc_id=doc_id,
                        script_candidate_id=script_candidate.script_candidate_id,
                        source_relative_path=relative_path,
                        module_hint=script_candidate.module_hint,
                        confidence=script_candidate.confidence,
                        parameter_name=parameter_name,
                    )
                )
    return records


def _inventory_payload(
    build_id: str,
    inbox_directory: Path,
    inventory: list[SourceInventoryEntry],
    docling_is_available: bool,
) -> dict[str, Any]:
    return {
        "build_id": build_id,
        "inbox_directory": str(inbox_directory),
        "docling_available": docling_is_available,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [asdict(item) for item in inventory],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _write_jsonl(path: Path, records: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def _compile_candidate_packs(
    source_directory: Path,
    target_directory: Path,
    *,
    build_id: str,
    doc_records: list[CanonicalDocumentRecord],
    script_candidates: list[ScriptCandidateRecord],
    parameter_candidates: list[ParameterCandidateRecord],
) -> CandidatePackBuildResult:
    target_directory.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    payloads: dict[str, dict[str, Any]] = {}
    active_payloads: dict[str, dict[str, Any]] = {}
    for path in sorted(source_directory.glob("*.json")):
        shutil.copy2(path, target_directory / path.name)
        copied.append(path.name)
        active_payload = json.loads(path.read_text(encoding="utf-8"))
        active_payloads[path.name] = active_payload
        payloads[path.name] = json.loads(json.dumps(active_payload, ensure_ascii=False))
    active_module_parameter_index = _build_active_module_parameter_index(active_payloads.get("sentieon-modules.json", {}))

    compile_skips: list[CompileSkip] = []
    build_exceptions: list[KnowledgeBuildException] = []
    compiled_entry_count = 0
    compiled_sources: dict[tuple[str, str], str] = {}
    parameter_promotion_reviews: list[ParameterPromotionReviewRecord] = []
    parameter_review_suggestions: list[ParameterReviewSuggestionRecord] = []
    for record in doc_records:
        compiled_entry = _compile_candidate_entry(
            record,
            script_candidates=script_candidates,
            parameter_candidates=parameter_candidates,
            build_id=build_id,
            active_module_parameter_index=active_module_parameter_index,
        )
        if compiled_entry is None:
            skip_reason = _compile_skip_reason(record)
            if skip_reason is not None:
                compile_skips.append(CompileSkip(relative_path=record.relative_path, reason=skip_reason))
            continue
        build_exceptions.extend(compiled_entry["exceptions"])
        parameter_promotion_reviews.extend(compiled_entry["parameter_promotion_reviews"])
        parameter_review_suggestions.extend(compiled_entry["parameter_review_suggestions"])
        pack_target = compiled_entry["pack_target"]
        candidate_id = str(compiled_entry.get("entry_id") or compiled_entry["entry"]["id"])
        seen_key = (pack_target, candidate_id)
        if seen_key in compiled_sources:
            build_exceptions.append(
                KnowledgeBuildException(
                    path=record.path,
                    relative_path=record.relative_path,
                    file_type=record.file_type,
                    exception_type="duplicate_candidate",
                    detail=(
                        f"Duplicate candidate id '{candidate_id}' for {pack_target}; "
                        f"first seen in {compiled_sources[seen_key]}."
                    ),
                )
            )
            continue
        payload = payloads.setdefault(pack_target, {"version": "", "entries": []})
        entries = payload.setdefault("entries", [])
        if not isinstance(entries, list):
            entries = []
            payload["entries"] = entries
        if compiled_entry.get("action") == "delete":
            removed = _remove_entry(entries, candidate_id)
            if not removed:
                build_exceptions.append(
                    KnowledgeBuildException(
                        path=record.path,
                        relative_path=record.relative_path,
                        file_type=record.file_type,
                        exception_type="delete_target_missing",
                        detail=f"Delete request for {candidate_id} did not match any active entry in {pack_target}.",
                    )
                )
        else:
            _upsert_entry(entries, compiled_entry["entry"])
        compiled_sources[seen_key] = record.relative_path
        compiled_entry_count += 1

    pack_diffs: dict[str, dict[str, Any]] = {}
    for pack_name, payload in payloads.items():
        pack_diffs[pack_name] = _build_pack_diff(
            active_payload=active_payloads.get(pack_name, {"version": "", "entries": []}),
            candidate_payload=payload,
        )
        _write_json(target_directory / pack_name, payload)
    _write_json(
        target_directory / "manifest.json",
        {
            "build_id": build_id,
            "active_source_directory": str(source_directory),
            "copied_files": copied,
            "compiled_entry_count": compiled_entry_count,
            "compile_skips": [asdict(item) for item in compile_skips],
            "exceptions": [asdict(item) for item in build_exceptions],
            "pack_diffs": pack_diffs,
            "parameter_promotion_reviews": [asdict(item) for item in parameter_promotion_reviews],
            "parameter_review_suggestions": [asdict(item) for item in parameter_review_suggestions],
            "status": "candidate_only",
            "note": "candidate packs are not active runtime packs yet",
        },
    )
    return CandidatePackBuildResult(
        compiled_entry_count=compiled_entry_count,
        compile_skips=compile_skips,
        exceptions=build_exceptions,
        pack_diffs=pack_diffs,
        parameter_promotion_reviews=parameter_promotion_reviews,
        parameter_review_suggestions=parameter_review_suggestions,
    )


def _compile_skip_reason(record: CanonicalDocumentRecord) -> str | None:
    if record.file_type != "markdown":
        return None
    if _string_or_none(record.source_metadata.get("action")) == "delete":
        required_fields = ["id"]
        missing_fields = [field for field in required_fields if not _string_or_none(record.source_metadata.get(field))]
        if not record.pack_target and not record.entry_type:
            return "missing pack metadata"
        if not record.pack_target:
            return "missing pack_target"
        if not record.entry_type:
            return "missing entry_type"
        if record.pack_target not in PACK_ENTRY_TYPES:
            return f"unsupported pack_target: {record.pack_target}"
        expected_entry_type = PACK_ENTRY_TYPES[record.pack_target]
        if record.entry_type != expected_entry_type:
            return f"unsupported entry_type for {record.pack_target}: {record.entry_type}"
        if missing_fields:
            return f"missing required metadata: {', '.join(missing_fields)}"
        return None
    if not record.pack_target and not record.entry_type:
        return "missing pack metadata"
    if not record.pack_target:
        return "missing pack_target"
    if not record.entry_type:
        return "missing entry_type"
    if record.pack_target not in PACK_ENTRY_TYPES:
        return f"unsupported pack_target: {record.pack_target}"
    expected_entry_type = PACK_ENTRY_TYPES[record.pack_target]
    if record.entry_type != expected_entry_type:
        return f"unsupported entry_type for {record.pack_target}: {record.entry_type}"
    required_fields = ["id", "name"]
    missing_fields = [field for field in required_fields if not _string_or_none(record.source_metadata.get(field))]
    if missing_fields:
        return f"missing required metadata: {', '.join(missing_fields)}"
    return None


def _compile_candidate_entry(
    record: CanonicalDocumentRecord,
    *,
    script_candidates: list[ScriptCandidateRecord],
    parameter_candidates: list[ParameterCandidateRecord],
    build_id: str,
    active_module_parameter_index: dict[str, set[str]],
) -> dict[str, Any] | None:
    skip_reason = _compile_skip_reason(record)
    if skip_reason is not None:
        return None
    metadata = record.source_metadata
    if _string_or_none(metadata.get("action")) == "delete":
        return {
            "pack_target": record.pack_target,
            "entry_id": str(metadata["id"]),
            "action": "delete",
            "exceptions": [],
            "parameter_promotion_reviews": [],
            "parameter_review_suggestions": [],
        }
    if record.pack_target == "sentieon-modules.json":
        entry: dict[str, Any] = {
            "id": str(metadata["id"]),
            "name": str(metadata["name"]),
            "aliases": _string_list(metadata.get("aliases")),
            "category": str(metadata.get("category", "")),
            "summary": str(metadata.get("summary", "")),
            "scope": _string_list(metadata.get("scope")),
            "related_modules": _string_list(metadata.get("related_modules")),
            "sources": [record.relative_path],
        }
        compiled_parameters, parameter_review_records, parameter_exceptions = _compile_module_parameters(
            record,
            build_id=build_id,
            parameter_candidates=parameter_candidates,
            script_candidates=script_candidates,
            active_module_parameter_index=active_module_parameter_index,
        )
        parameter_suggestion_records = _build_parameter_review_suggestions(parameter_review_records)
        if compiled_parameters or isinstance(metadata.get("parameters"), list):
            entry["parameters"] = compiled_parameters
        matching_script_candidates = [
            item
            for item in script_candidates
            if item.doc_id == record.doc_id and item.confidence == "high" and item.module_hint == _normalize_module_hint(str(metadata["id"]))
        ]
        if matching_script_candidates:
            entry["script_examples"] = [
                {
                    "title": f"{str(metadata['name'])} extracted script",
                    "summary": "Auto-extracted from local knowledge build source.",
                    "when_to_use": [],
                    "command_lines": item.command_lines,
                    "notes": ["Auto-extracted script candidate; review before activation."],
                    "sources": [record.relative_path],
                }
                for item in matching_script_candidates
            ]
        return {
            "pack_target": record.pack_target,
            "entry": entry,
            "exceptions": parameter_exceptions,
            "parameter_promotion_reviews": parameter_review_records,
            "parameter_review_suggestions": parameter_suggestion_records,
        }
    if record.pack_target == "workflow-guides.json":
        workflow_entry: dict[str, Any] = {
            "id": str(metadata["id"]),
            "name": str(metadata["name"]),
            "priority": _int_value(metadata.get("priority"), default=50),
            "summary": str(metadata.get("summary", "")),
            "guidance": _string_list(metadata.get("guidance")),
            "follow_up": _string_list(metadata.get("follow_up")),
            "sources": [record.relative_path],
        }
        optional_list_fields = ("prerequisites", "exclude_any", "prefer_any")
        for field in optional_list_fields:
            values = _string_list(metadata.get(field))
            if values:
                workflow_entry[field] = values
        require_any_groups = _nested_string_list(metadata.get("require_any_groups"))
        if require_any_groups:
            workflow_entry["require_any_groups"] = require_any_groups
        script_module = _string_or_none(metadata.get("script_module"))
        if script_module:
            workflow_entry["script_module"] = script_module
        if isinstance(metadata.get("direct_script_handoff"), bool):
            workflow_entry["direct_script_handoff"] = metadata["direct_script_handoff"]
        return {
            "pack_target": record.pack_target,
            "entry": workflow_entry,
            "exceptions": [],
            "parameter_promotion_reviews": [],
            "parameter_review_suggestions": [],
        }
    if record.pack_target in {"external-format-guides.json", "external-tool-guides.json"}:
        external_entry: dict[str, Any] = {
            "id": str(metadata["id"]),
            "name": str(metadata["name"]),
            "aliases": _string_list(metadata.get("aliases")),
            "summary": str(metadata.get("summary", "")),
            "details": _string_list(metadata.get("details")),
            "troubleshooting": _string_list(metadata.get("troubleshooting")),
            "usage_boundary": _string_list(metadata.get("usage_boundary")),
            "source_notes": _string_list(metadata.get("source_notes")),
            "official_sources": _string_list(metadata.get("official_sources")),
        }
        return {
            "pack_target": record.pack_target,
            "entry": external_entry,
            "exceptions": [],
            "parameter_promotion_reviews": [],
            "parameter_review_suggestions": [],
        }
    if record.pack_target == "external-error-associations.json":
        error_entry: dict[str, Any] = {
            "id": str(metadata["id"]),
            "name": str(metadata["name"]),
            "patterns_any": _string_list(metadata.get("patterns_any")),
            "require_any": _string_list(metadata.get("require_any")),
            "summary": str(metadata.get("summary", "")),
            "checks": _string_list(metadata.get("checks")),
            "related_guides": _string_list(metadata.get("related_guides")),
            "usage_boundary": _string_list(metadata.get("usage_boundary")),
            "source_notes": _string_list(metadata.get("source_notes")),
        }
        return {
            "pack_target": record.pack_target,
            "entry": error_entry,
            "exceptions": [],
            "parameter_promotion_reviews": [],
            "parameter_review_suggestions": [],
        }
    return None


def _compile_module_parameters(
    record: CanonicalDocumentRecord,
    *,
    build_id: str,
    parameter_candidates: list[ParameterCandidateRecord],
    script_candidates: list[ScriptCandidateRecord],
    active_module_parameter_index: dict[str, set[str]],
) -> tuple[list[dict[str, Any]], list[ParameterPromotionReviewRecord], list[KnowledgeBuildException]]:
    raw_parameters = record.source_metadata.get("parameters")
    if not isinstance(raw_parameters, list):
        raw_parameters = []

    module_id = _normalize_module_hint(str(record.source_metadata["id"]))
    eligible_script_candidate_ids = {
        item.script_candidate_id
        for item in script_candidates
        if item.doc_id == record.doc_id and _script_candidate_supports_module_review(item, module_id=module_id)
    }
    high_confidence_candidates = [
        item
        for item in parameter_candidates
        if item.doc_id == record.doc_id
        and item.module_hint == module_id
        and item.confidence == "high"
        and item.script_candidate_id in eligible_script_candidate_ids
    ]
    extracted_names = {_normalize_parameter_name(item.parameter_name) for item in high_confidence_candidates}

    compiled_parameters: list[dict[str, Any]] = []
    review_records: list[ParameterPromotionReviewRecord] = []
    exceptions: list[KnowledgeBuildException] = []
    promoted_names: set[str] = set()

    for item in raw_parameters:
        if not isinstance(item, dict):
            exceptions.append(
                KnowledgeBuildException(
                    path=record.path,
                    relative_path=record.relative_path,
                    file_type=record.file_type,
                    exception_type="invalid_parameter_definition",
                    detail="Structured module parameters must be objects with at least name and summary.",
                )
            )
            continue

        parameter_name = _string_or_none(item.get("name"))
        summary = _string_or_none(item.get("summary"))
        if parameter_name is None or summary is None:
            exceptions.append(
                KnowledgeBuildException(
                    path=record.path,
                    relative_path=record.relative_path,
                    file_type=record.file_type,
                    exception_type="invalid_parameter_definition",
                    detail="Structured module parameters require both name and summary before promotion.",
                )
            )
            continue

        normalized_name = _normalize_parameter_name(parameter_name)
        if normalized_name in promoted_names:
            exceptions.append(
                KnowledgeBuildException(
                    path=record.path,
                    relative_path=record.relative_path,
                    file_type=record.file_type,
                    exception_type="duplicate_parameter_definition",
                    detail=f"Duplicate structured parameter definition for {parameter_name}.",
                )
            )
            continue
        promoted_names.add(normalized_name)
        compiled_parameters.append(
            {
                "name": parameter_name,
                "aliases": _string_list(item.get("aliases")),
                "summary": summary,
                "details": _string_list(item.get("details")),
                "values": _string_list(item.get("values")),
            }
        )
        if normalized_name in extracted_names:
            evidence_status = "matched"
            confidence = "high"
            detail = "Structured parameter promotion matched a high-confidence extracted parameter candidate."
        elif high_confidence_candidates:
            evidence_status = "missing"
            confidence = "reviewed"
            detail = "Structured parameter promotion has no matching extracted parameter candidate in the same source."
        else:
            evidence_status = "not_available"
            confidence = "reviewed"
            detail = "Structured parameter promotion has no high-confidence extracted evidence in the same source."
        review_records.append(
            ParameterPromotionReviewRecord(
                build_id=build_id,
                doc_id=record.doc_id,
                relative_path=record.relative_path,
                module_id=module_id,
                parameter_name=parameter_name,
                status="promoted",
                evidence_status=evidence_status,
                confidence=confidence,
                detail=detail,
            )
        )

    for candidate in high_confidence_candidates:
        normalized_name = _normalize_parameter_name(candidate.parameter_name)
        if normalized_name in promoted_names:
            continue
        if normalized_name in active_module_parameter_index.get(module_id, set()):
            review_records.append(
                ParameterPromotionReviewRecord(
                    build_id=build_id,
                    doc_id=record.doc_id,
                    relative_path=record.relative_path,
                    module_id=module_id,
                    parameter_name=candidate.parameter_name,
                    status="covered_by_module",
                    evidence_status="active_pack",
                    confidence=candidate.confidence,
                    detail="High-confidence extracted parameter candidate is already covered by the active module pack.",
                )
            )
            continue
        if module_id != "sentieon-cli" and normalized_name in active_module_parameter_index.get("sentieon-cli", set()):
            review_records.append(
                ParameterPromotionReviewRecord(
                    build_id=build_id,
                    doc_id=record.doc_id,
                    relative_path=record.relative_path,
                    module_id=module_id,
                    parameter_name=candidate.parameter_name,
                    status="covered_by_shared_module",
                    evidence_status="active_pack",
                    confidence=candidate.confidence,
                    detail="High-confidence extracted parameter candidate is already covered by the shared sentieon-cli module.",
                )
            )
            continue
        review_records.append(
            ParameterPromotionReviewRecord(
                build_id=build_id,
                doc_id=record.doc_id,
                relative_path=record.relative_path,
                module_id=module_id,
                parameter_name=candidate.parameter_name,
                status="candidate_only",
                evidence_status="candidate_only",
                confidence=candidate.confidence,
                detail="High-confidence extracted parameter candidate needs structured metadata before promotion.",
            )
        )

    return compiled_parameters, review_records, exceptions


def _build_parameter_review_suggestions(
    review_records: list[ParameterPromotionReviewRecord],
) -> list[ParameterReviewSuggestionRecord]:
    suggestions: list[ParameterReviewSuggestionRecord] = []
    for item in review_records:
        if item.status != "candidate_only":
            continue
        suggestions.append(
            ParameterReviewSuggestionRecord(
                build_id=item.build_id,
                doc_id=item.doc_id,
                relative_path=item.relative_path,
                module_id=item.module_id,
                parameter_name=item.parameter_name,
                suggested_action="add_structured_parameter_metadata",
                template={
                    "name": item.parameter_name,
                    "aliases": [],
                    "summary": "",
                    "details": [],
                    "values": [],
                },
                detail="High-confidence extracted parameter candidate is not yet covered by structured metadata.",
            )
        )
    return suggestions


def _build_active_module_parameter_index(payload: dict[str, Any]) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for entry in payload.get("entries", []):
        if not isinstance(entry, dict):
            continue
        module_id = _string_or_none(entry.get("id"))
        if module_id is None:
            continue
        parameter_names: set[str] = set()
        for parameter in entry.get("parameters", []):
            if not isinstance(parameter, dict):
                continue
            name = _string_or_none(parameter.get("name"))
            if name is None:
                continue
            parameter_names.add(_normalize_parameter_name(name))
        index[_normalize_module_hint(module_id)] = parameter_names
    return index


def _script_candidate_supports_module_review(candidate: ScriptCandidateRecord, *, module_id: str) -> bool:
    inferred_hints = {
        hint
        for line in candidate.command_lines
        for hint in (_module_hint_from_command_line(line),)
        if hint is not None
    }
    return len(inferred_hints) == 1 and next(iter(inferred_hints)) == module_id


def _upsert_entry(entries: list[dict[str, Any]], new_entry: dict[str, Any]) -> None:
    new_id = new_entry.get("id")
    for index, entry in enumerate(entries):
        if entry.get("id") == new_id:
            entries[index] = new_entry
            return
    entries.append(new_entry)


def _remove_entry(entries: list[dict[str, Any]], entry_id: str) -> bool:
    for index, entry in enumerate(entries):
        if entry.get("id") == entry_id:
            del entries[index]
            return True
    return False


def _build_pack_diff(*, active_payload: dict[str, Any], candidate_payload: dict[str, Any]) -> dict[str, Any]:
    active_entries = _entries_by_id(active_payload.get("entries"))
    candidate_entries = _entries_by_id(candidate_payload.get("entries"))
    added_ids = sorted(entry_id for entry_id in candidate_entries if entry_id not in active_entries)
    removed_ids = sorted(entry_id for entry_id in active_entries if entry_id not in candidate_entries)
    updated_ids = sorted(
        entry_id
        for entry_id, candidate_entry in candidate_entries.items()
        if entry_id in active_entries and candidate_entry != active_entries[entry_id]
    )
    return {
        "added_ids": added_ids,
        "removed_ids": removed_ids,
        "updated_ids": updated_ids,
        "unchanged": not added_ids and not removed_ids and not updated_ids,
    }


def _entries_by_id(raw_entries: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_entries, list):
        return {}
    entries_by_id: dict[str, dict[str, Any]] = {}
    for item in raw_entries:
        if not isinstance(item, dict):
            continue
        entry_id = _string_or_none(item.get("id"))
        if entry_id is None:
            continue
        entries_by_id[entry_id] = item
    return entries_by_id


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return []


def _nested_string_list(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        return []
    groups: list[list[str]] = []
    for item in value:
        if isinstance(item, list):
            group = _string_list(item)
            if group:
                groups.append(group)
    return groups


def _int_value(value: Any, *, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _normalize_parameter_name(value: str) -> str:
    return value.strip().lower()


def _build_report(
    *,
    build_id: str,
    inbox_directory: Path,
    inventory: list[SourceInventoryEntry],
    exceptions: list[KnowledgeBuildException],
    doc_records: list[CanonicalDocumentRecord],
    build_dir: Path,
    candidate_pack_result: CandidatePackBuildResult,
    script_candidate_records: list[ScriptCandidateRecord],
    parameter_candidate_records: list[ParameterCandidateRecord],
    parameter_promotion_reviews: list[ParameterPromotionReviewRecord],
    parameter_review_suggestions: list[ParameterReviewSuggestionRecord],
    docling_is_available: bool,
) -> str:
    candidate_pack_directory = build_dir / "candidate-packs"
    metadata_gap_records = [record for record in doc_records if record.metadata_missing]
    extraction_ambiguities = [item for item in exceptions if item.exception_type == "extraction_ambiguity"]
    promoted_parameters = [item for item in parameter_promotion_reviews if item.status == "promoted"]
    candidate_only_parameters = [item for item in parameter_promotion_reviews if item.status == "candidate_only"]
    promoted_without_evidence = [item for item in promoted_parameters if item.evidence_status == "missing"]
    covered_by_module = [item for item in parameter_promotion_reviews if item.status == "covered_by_module"]
    covered_by_shared_module = [item for item in parameter_promotion_reviews if item.status == "covered_by_shared_module"]
    changed_pack_diffs = {
        pack_name: diff
        for pack_name, diff in candidate_pack_result.pack_diffs.items()
        if not bool(diff.get("unchanged"))
    }
    lines = [
        "# Knowledge Build Report",
        "",
        f"- Build ID: `{build_id}`",
        f"- Inbox: `{inbox_directory}`",
        f"- Build dir: `{build_dir}`",
        f"- Docling available: {'yes' if docling_is_available else 'no'}",
        "",
        "## Exceptions First",
    ]
    if exceptions:
        for item in exceptions:
            lines.append(f"- `{item.exception_type}`: `{item.relative_path}`")
            lines.append(f"  - {item.detail}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Summary",
            f"- Inventory files: {len(inventory)}",
            f"- Canonical documents: {len(doc_records)}",
            f"- Exceptions: {len(exceptions)}",
            f"- Compiled entries: {candidate_pack_result.compiled_entry_count}",
            f"- Compile skips: {len(candidate_pack_result.compile_skips)}",
            f"- Script candidates: {len(script_candidate_records)}",
            f"- Parameter candidates: {len(parameter_candidate_records)}",
            "",
            "## Metadata gaps",
        ]
    )
    if metadata_gap_records:
        for record in metadata_gap_records:
            lines.append(f"- `{record.relative_path}`: {', '.join(record.metadata_missing)}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Extraction ambiguities",
        ]
    )
    if extraction_ambiguities:
        for item in extraction_ambiguities:
            lines.append(f"- `{item.relative_path}`: {item.detail}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Parameter promotion review",
            f"- Promoted parameters: {len(promoted_parameters)}",
            f"- Extracted but unpromoted parameters: {len(candidate_only_parameters)}",
            f"- Covered by module: {len(covered_by_module)}",
            f"- Covered by shared module: {len(covered_by_shared_module)}",
            f"- Promoted parameters without matched extracted evidence: {len(promoted_without_evidence)}",
            f"- Parameter review suggestions: {len(parameter_review_suggestions)}",
            f"- Suggestion artifact: `{build_dir / 'parameter_review_suggestion.jsonl'}`",
        ]
    )
    review_needed = candidate_only_parameters + promoted_without_evidence
    if review_needed:
        for item in review_needed:
            lines.append(f"- `{item.relative_path}`: `{item.parameter_name}` ({item.status}, {item.evidence_status})")
            lines.append(f"  - {item.detail}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Changed candidate packs",
        ]
    )
    if changed_pack_diffs:
        for pack_name, diff in sorted(changed_pack_diffs.items()):
            changed_ids = list(diff.get("added_ids", [])) + list(diff.get("removed_ids", [])) + list(diff.get("updated_ids", []))
            lines.append(
                f"- `{pack_name}`: added={', '.join(diff.get('added_ids', [])) or 'none'}; "
                f"removed={', '.join(diff.get('removed_ids', [])) or 'none'}; "
                f"updated={', '.join(diff.get('updated_ids', [])) or 'none'}"
            )
            if changed_ids:
                lines.append(f"  - changed ids: {', '.join(changed_ids)}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Candidate Packs",
            "- candidate packs are not active runtime packs yet",
            f"- Candidate pack directory: `{candidate_pack_directory}`",
            "",
            "## Compile skips",
        ]
    )
    if candidate_pack_result.compile_skips:
        for item in candidate_pack_result.compile_skips:
            lines.append(f"- `{item.relative_path}`: {item.reason}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Next Gates",
        ]
    )
    for command in _gate_commands_for_candidate_directory(candidate_pack_directory):
        lines.append(f"- `{command}`")
    return "\n".join(lines) + "\n"


def _gate_commands_for_candidate_directory(candidate_pack_directory: Path) -> tuple[str, ...]:
    build_dir = candidate_pack_directory.parent
    return (
        f"{GATE_COMMANDS[0]} --source-dir {candidate_pack_directory} --json-out {build_dir / PILOT_READINESS_REPORT_NAME}",
        f"{GATE_COMMANDS[1]} --source-dir {candidate_pack_directory} --json-out {build_dir / PILOT_CLOSED_LOOP_REPORT_NAME}",
    )
