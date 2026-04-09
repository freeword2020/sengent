from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sentieon_assist.external_guides import match_external_error_association, match_external_guide_entry
from sentieon_assist.module_index import match_module_entries, match_parameter_entries
from sentieon_assist.reference_intents import ReferenceIntent
from sentieon_assist.sources import collect_source_evidence
from sentieon_assist.workflow_index import (
    match_workflow_entry,
    workflow_allows_direct_script_handoff,
    workflow_script_module,
)


@dataclass(frozen=True)
class ReferenceRetrievalBundle:
    workflow_entry: dict[str, Any] | None = None
    script_workflow_entry: dict[str, Any] | None = None
    external_error_association: dict[str, Any] | None = None
    external_entry: dict[str, Any] | None = None
    module_matches: list[dict[str, Any]] = field(default_factory=list)
    global_parameter_matches: list[dict[str, Any]] = field(default_factory=list)
    all_parameter_matches: list[dict[str, Any]] = field(default_factory=list)


def retrieve_reference_candidates(
    query: str,
    *,
    source_directory: str | Path,
    resolved_intent: ReferenceIntent,
) -> ReferenceRetrievalBundle:
    workflow_entry = None
    script_workflow_entry = None
    if resolved_intent.intent == "workflow_guidance":
        workflow_entry = match_workflow_entry(query, source_directory)
        if workflow_entry is not None:
            if workflow_script_module(workflow_entry):
                script_workflow_entry = workflow_entry
            else:
                candidate = match_workflow_entry(query, source_directory, require_script_module=True)
                if candidate is not None and workflow_allows_direct_script_handoff(candidate):
                    script_workflow_entry = candidate

    external_error_association = None
    external_entry = None
    if resolved_intent.intent == "reference_other":
        external_error_association = match_external_error_association(query, source_directory)
        external_entry = match_external_guide_entry(query, source_directory)

    return ReferenceRetrievalBundle(
        workflow_entry=workflow_entry,
        script_workflow_entry=script_workflow_entry,
        external_error_association=external_error_association,
        external_entry=external_entry,
        module_matches=match_module_entries(query, source_directory, max_matches=1),
        global_parameter_matches=match_parameter_entries(query, source_directory, max_matches=1),
        all_parameter_matches=match_parameter_entries(query, source_directory),
    )


def collect_reference_fallback_evidence(
    query: str,
    *,
    source_directory: str | Path,
    preferred_evidence: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    evidence = collect_source_evidence(
        source_directory,
        issue_type="reference",
        query=query,
        info={
            "version": "",
            "input_type": "",
            "error": "",
            "error_keywords": "",
            "step": "",
            "data_type": "",
        },
    )
    if not preferred_evidence:
        return evidence

    preferred_names = {str(item.get("name", "")).strip().lower() for item in preferred_evidence if str(item.get("name", "")).strip()}
    return [*preferred_evidence, *[item for item in evidence if str(item.get("name", "")).strip().lower() not in preferred_names]]
