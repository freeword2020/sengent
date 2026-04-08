from __future__ import annotations

import re
import subprocess
from collections import OrderedDict
from pathlib import Path


RELEASE_FILE_PATTERN = re.compile(r"Sentieon(?P<release>\d{6}\.\d{2})\.pdf", re.IGNORECASE)
RELEASE_TEXT_PATTERN = re.compile(r"Release\s*(?P<release>\d{6}\.\d{2})", re.IGNORECASE)
DATE_PATTERN = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}\b")


def _source_priority(path: Path) -> int:
    name = path.name.lower()
    if path.suffix.lower() == ".pdf" and name.startswith("sentieon20"):
        return 0
    if name == "sentieon-doc-map.md":
        return 1
    if name == "sentieon-github-map.md":
        return 2
    if name.startswith("thread-") and name.endswith("-summary.md"):
        return 3
    if name == "readme.md":
        return 4
    if name == "sentieon-chinese-reference.md":
        return 5
    return 10


def _source_trust(path: Path) -> str:
    name = path.name.lower()
    if path.suffix.lower() == ".pdf" and name.startswith("sentieon20"):
        return "official"
    if name == "sentieon-chinese-reference.md":
        return "secondary"
    if name in {"sentieon-doc-map.md", "sentieon-github-map.md", "readme.md"}:
        return "derived"
    if name.startswith("thread-") and name.endswith("-summary.md"):
        return "derived"
    return "other"


def _source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix in {".txt"}:
        return "text"
    return "other"


def extract_source_text(path: str | Path) -> str:
    source_path = Path(path)
    source_type = _source_type(source_path)
    try:
        if source_type in {"markdown", "text", "other"}:
            return source_path.read_text(errors="ignore")
        if source_type == "pdf":
            result = subprocess.run(
                ["pdftotext", str(source_path), "-"],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
    except (OSError, subprocess.CalledProcessError):
        return ""
    return ""


def _build_snippet(text: str, keyword: str, radius: int = 60) -> str:
    normalized_text = text.replace("\n", " ")
    lowered = normalized_text.lower()
    lowered_keyword = keyword.lower()
    index = lowered.find(lowered_keyword)
    if index == -1:
        return ""
    start = max(0, index - radius)
    end = min(len(normalized_text), index + len(keyword) + radius)
    return normalized_text[start:end].strip()


def list_sources(directory: str | Path) -> list[dict[str, str]]:
    root = Path(directory)
    if not root.exists():
        return []

    sources: list[dict[str, str]] = []
    for path in sorted(root.iterdir(), key=lambda item: (_source_priority(item), item.name.lower())):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        sources.append(
            {
                "name": path.name,
                "path": str(path),
                "type": _source_type(path),
                "trust": _source_trust(path),
                "priority": str(_source_priority(path)),
            }
        )
    return sources


def collect_source_bundle_metadata(directory: str | Path) -> dict[str, str]:
    metadata = {
        "primary_release": "",
        "primary_date": "",
        "primary_reference": "",
    }
    for source in list_sources(directory):
        release_match = RELEASE_FILE_PATTERN.search(source["name"])
        if release_match and not metadata["primary_release"]:
            metadata["primary_release"] = release_match.group("release")
            metadata["primary_reference"] = source["name"]

        if metadata["primary_release"] and metadata["primary_date"]:
            continue

        text = extract_source_text(source["path"])
        if text:
            if not metadata["primary_release"]:
                text_release_match = RELEASE_TEXT_PATTERN.search(text) or RELEASE_FILE_PATTERN.search(text)
                if text_release_match:
                    metadata["primary_release"] = text_release_match.group("release")
                    if not metadata["primary_reference"]:
                        metadata["primary_reference"] = source["name"]
            if not metadata["primary_date"]:
                date_match = DATE_PATTERN.search(text)
                if date_match:
                    metadata["primary_date"] = date_match.group(0)
        if metadata["primary_release"] and metadata["primary_date"]:
            break
    return metadata


def search_sources(directory: str | Path, keyword: str) -> list[dict[str, str]]:
    matches: list[dict[str, str]] = []
    for source in list_sources(directory):
        text = extract_source_text(source["path"])
        snippet = _build_snippet(text, keyword)
        if not snippet:
            continue
        matches.append(
            {
                **source,
                "snippet": snippet,
            }
        )
    return matches


def _query_terms(issue_type: str, query: str, info: dict[str, str]) -> list[str]:
    terms: list[str] = []
    for candidate in (
        issue_type,
        info.get("version", ""),
        info.get("error_keywords", ""),
        info.get("step", ""),
    ):
        value = str(candidate).strip()
        if value:
            terms.append(value)
    for token in query.replace("，", " ").replace(",", " ").split():
        token = token.strip()
        if len(token) >= 4:
            terms.append(token)
    deduped = list(OrderedDict((term.lower(), term) for term in terms).values())
    return deduped


def collect_source_evidence(
    directory: str | Path,
    *,
    issue_type: str,
    query: str,
    info: dict[str, str],
    max_matches: int = 4,
) -> list[dict[str, str]]:
    combined: OrderedDict[tuple[str, str], dict[str, str]] = OrderedDict()
    for term in _query_terms(issue_type, query, info):
        for match in search_sources(directory, term):
            key = (match["name"], match["snippet"])
            if key not in combined:
                combined[key] = match
            if len(combined) >= max_matches:
                return list(combined.values())
    return list(combined.values())
