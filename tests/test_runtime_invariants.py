from __future__ import annotations

import pytest

from sentieon_assist.runtime_invariants import (
    PromotionState,
    ToolRequirement,
    TruthSource,
    normalize_promotion_state,
    normalize_tool_requirement,
    normalize_truth_source,
)


def test_runtime_truth_source_rejects_raw_ingestion_when_used_as_truth():
    with pytest.raises(ValueError, match="raw ingestion cannot be treated as runtime truth"):
        normalize_truth_source(TruthSource.RAW_INGESTION)


def test_runtime_truth_source_normalizer_accepts_explicit_raw_ingestion_when_allowed():
    assert normalize_truth_source("raw_ingestion", allow_raw_ingestion=True) == TruthSource.RAW_INGESTION


def test_promotion_state_defaults_model_outputs_to_review_needed():
    assert normalize_promotion_state(None) == PromotionState.REVIEW_NEEDED


def test_tool_requirement_normalizer_rejects_unknown_value():
    with pytest.raises(ValueError, match="unsupported tool requirement"):
        normalize_tool_requirement("tool-maybe")


def test_tool_requirement_normalizer_accepts_required():
    assert normalize_tool_requirement(ToolRequirement.REQUIRED) == ToolRequirement.REQUIRED
