from pathlib import Path

from sentieon_assist.reference_intents import ReferenceIntent
from sentieon_assist.workflow_index import workflow_script_module
from sentieon_assist.reference_retrieval import retrieve_reference_candidates


def test_retrieve_reference_candidates_exposes_script_workflow_entry_for_tumor_only_prompt():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    bundle = retrieve_reference_candidates(
        "能提供个tumor only参考脚本吗",
        source_directory=str(source_directory),
        resolved_intent=ReferenceIntent(intent="workflow_guidance", confidence=0.93),
    )

    assert bundle.workflow_entry is not None
    assert bundle.script_workflow_entry is not None
    assert workflow_script_module(bundle.script_workflow_entry) == "TNscope"


def test_retrieve_reference_candidates_exposes_external_guide_for_fastqc_prompt():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    bundle = retrieve_reference_candidates(
        "FastQC 是做什么的",
        source_directory=str(source_directory),
        resolved_intent=ReferenceIntent(intent="reference_other", confidence=0.91),
    )

    assert bundle.external_entry is not None
    assert bundle.external_entry.get("name") == "FastQC"


def test_retrieve_reference_candidates_exposes_module_and_parameter_matches_for_dnascope_prompt():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    bundle = retrieve_reference_candidates(
        "DNAscope 的 --pcr_free 是什么",
        source_directory=str(source_directory),
        resolved_intent=ReferenceIntent(intent="parameter_lookup", module="DNAscope", confidence=0.93),
    )

    assert bundle.module_matches
    assert bundle.module_matches[0].get("name") == "DNAscope"
    assert bundle.global_parameter_matches
    assert bundle.all_parameter_matches
