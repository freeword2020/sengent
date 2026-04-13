from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from sentieon_assist.source_intake import intake_source_to_inbox


def test_intake_source_to_inbox_writes_markdown_and_sidecar_with_provenance(tmp_path: Path):
    source_path = tmp_path / "vendor-doc.md"
    source_path.write_text("# FastDedup\n\nUse FastDedup before alignment.\n", encoding="utf-8")
    inbox_dir = tmp_path / "knowledge-inbox" / "sentieon"

    result = intake_source_to_inbox(
        inbox_directory=inbox_dir,
        source_class="vendor-official",
        source_path=source_path,
        kind="module",
        entry_id="fastdedup-source",
        name="FastDedup Source",
    )

    assert result.markdown_path.exists()
    assert result.metadata_path.exists()
    markdown = result.markdown_path.read_text(encoding="utf-8")
    assert "Imported via source intake." in markdown
    assert str(source_path) in markdown
    assert "Use FastDedup before alignment." in markdown

    metadata = yaml.safe_load(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["origin"] == "factory-source-intake"
    assert metadata["source_class"] == "vendor-official"
    assert metadata["factory_intake_status"] == "pending_review"
    assert metadata["version"] == "source-intake-v1"
    assert metadata["source_provenance"]["path"] == str(source_path.resolve())
    assert metadata["source_provenance"]["file_type"] == "markdown"
    assert metadata["review_hints"]["recommended_next_step"]
    assert metadata["review_hints"]["maintainer_checks"]


def test_intake_source_to_inbox_rejects_unsupported_file_type(tmp_path: Path):
    source_path = tmp_path / "vendor-doc.pdf"
    source_path.write_bytes(b"%PDF-1.4\n")

    with pytest.raises(ValueError, match="unsupported source file type"):
        intake_source_to_inbox(
            inbox_directory=tmp_path / "knowledge-inbox" / "sentieon",
            source_class="vendor-official",
            source_path=source_path,
            kind="module",
            entry_id="fastdedup-source",
            name="FastDedup Source",
        )
