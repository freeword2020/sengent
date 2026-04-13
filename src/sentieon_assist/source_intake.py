from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from sentieon_assist.knowledge_build import scaffold_knowledge_source


SOURCE_INTAKE_ORIGIN = "factory-source-intake"
SOURCE_INTAKE_VERSION = "source-intake-v1"
SOURCE_INTAKE_PENDING_REVIEW = "pending_review"

SUPPORTED_SOURCE_CLASSES = {
    "vendor-official",
    "release-notes",
    "domain-standard",
    "support-incident",
    "maintainer-note",
}

SUPPORTED_SOURCE_FILE_TYPES = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".txt": "text",
    ".html": "html",
    ".htm": "html",
    ".json": "json",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
}


@dataclass(frozen=True)
class SourceIntakeResult:
    source_class: str
    source_path: Path
    source_file_type: str
    markdown_path: Path
    metadata_path: Path
    kind: str
    entry_id: str


def intake_source_to_inbox(
    *,
    inbox_directory: str | Path,
    source_class: str,
    source_path: str | Path,
    kind: str,
    entry_id: str,
    name: str,
    file_stem: str | None = None,
) -> SourceIntakeResult:
    normalized_source_class = normalize_source_class(source_class)
    resolved_source_path = Path(source_path)
    if not resolved_source_path.exists():
        raise ValueError(f"source file not found: {resolved_source_path}")
    source_file_type = detect_source_file_type(resolved_source_path)
    source_text = resolved_source_path.read_text(encoding="utf-8")
    imported_at = datetime.now(timezone.utc).isoformat()

    scaffold = scaffold_knowledge_source(
        inbox_directory=inbox_directory,
        kind=kind,
        entry_id=entry_id,
        name=name,
        file_stem=file_stem,
    )

    scaffold.markdown_path.write_text(
        _render_imported_markdown(
            name=name,
            source_class=normalized_source_class,
            source_path=resolved_source_path.resolve(),
            imported_at=imported_at,
            source_text=source_text,
        ),
        encoding="utf-8",
    )

    payload = yaml.safe_load(scaffold.metadata_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"source intake metadata must be a mapping: {scaffold.metadata_path}")
    payload.update(
        {
            "origin": SOURCE_INTAKE_ORIGIN,
            "version": SOURCE_INTAKE_VERSION,
            "date": datetime.now(timezone.utc).date().isoformat(),
            "source_class": normalized_source_class,
            "factory_intake_status": SOURCE_INTAKE_PENDING_REVIEW,
            "source_provenance": {
                "path": str(resolved_source_path.resolve()),
                "file_type": source_file_type,
                "imported_at": imported_at,
            },
            "review_hints": {
                "recommended_next_step": (
                    "Review the imported source, extract the relevant structured facts, "
                    "then clear pending review before compiling it into candidate packs."
                ),
                "maintainer_checks": [
                    "Confirm the scaffold kind and entry metadata match the imported source.",
                    "Trim or rewrite the imported body into structured maintainer-ready notes before activation.",
                ],
            },
        }
    )
    scaffold.metadata_path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return SourceIntakeResult(
        source_class=normalized_source_class,
        source_path=resolved_source_path.resolve(),
        source_file_type=source_file_type,
        markdown_path=scaffold.markdown_path,
        metadata_path=scaffold.metadata_path,
        kind=kind,
        entry_id=entry_id,
    )


def normalize_source_class(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in SUPPORTED_SOURCE_CLASSES:
        raise ValueError(f"unsupported source class: {value}")
    return normalized


def detect_source_file_type(path: Path) -> str:
    file_type = SUPPORTED_SOURCE_FILE_TYPES.get(path.suffix.lower())
    if file_type is None:
        raise ValueError(f"unsupported source file type: {path.suffix.lower() or path.name}")
    return file_type


def _render_imported_markdown(
    *,
    name: str,
    source_class: str,
    source_path: Path,
    imported_at: str,
    source_text: str,
) -> str:
    return (
        f"# {name}\n\n"
        "Imported via source intake.\n\n"
        "## Source Intake\n"
        f"- Source class: `{source_class}`\n"
        f"- Source path: `{source_path}`\n"
        f"- Imported at: `{imported_at}`\n\n"
        "## Source Material\n\n"
        f"{source_text.rstrip()}\n"
    )
