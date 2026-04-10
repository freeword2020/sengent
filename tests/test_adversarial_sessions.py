from pathlib import Path

from sentieon_assist.adversarial_sessions import classify_response_mode, run_support_session


def test_run_support_session_reuses_anchor_for_wes_clarification_followup():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    results = run_support_session(
        [
            "能提供个wes参考脚本吗",
            "短读长二倍体呢",
        ],
        source_directory=str(source_directory),
    )

    assert len(results) == 2
    assert results[1].reused_anchor is True
    assert "【参考命令】" in results[1].response
    assert "sentieon-cli dnascope" in results[1].response


def test_run_support_session_reuses_anchor_for_somatic_followup():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    results = run_support_session(
        [
            "我要做wes分析，能给个示例脚本吗",
            "那 somatic 呢",
        ],
        source_directory=str(source_directory),
    )

    assert len(results) == 2
    assert results[1].reused_anchor is True
    assert "【流程指导】" in results[1].response
    assert "TNseq / TNscope" in results[1].response


def test_run_support_session_does_not_reuse_anchor_for_new_reference_request():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    results = run_support_session(
        [
            "DNAscope 的 --pcr_free 是什么",
            "LICSRVR、Poetry",
        ],
        source_directory=str(source_directory),
    )

    assert len(results) == 2
    assert results[1].reused_anchor is False
    assert "【资料说明】" in results[1].response
    assert "LICSRVR" in results[1].response


def test_run_support_session_records_trace_for_parameter_lookup():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    results = run_support_session(
        [
            "GVCFtyper 的 --emit_mode 是什么",
        ],
        source_directory=str(source_directory),
    )

    assert len(results) == 1
    result = results[0]
    assert result.task == "reference_lookup"
    assert result.issue_type == "other"
    assert result.route_reason == "parameter_lookup"
    assert result.parsed_intent_intent == "parameter_lookup"
    assert result.parsed_intent_module == "GVCFtyper"
    assert result.response_mode == "parameter"


def test_run_support_session_marks_workflow_clarification_as_clarify_mode():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    results = run_support_session(
        [
            "能提供个wes参考脚本吗",
        ],
        source_directory=str(source_directory),
    )

    assert len(results) == 1
    result = results[0]
    assert result.task == "onboarding_guidance"
    assert result.route_reason == "workflow_guidance"
    assert result.parsed_intent_intent == "workflow_guidance"
    assert result.response_mode == "clarify"


def test_run_support_session_returns_unified_turn_view_ids():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    results = run_support_session(
        [
            "DNAscope 的 --pcr_free 是什么",
        ],
        source_directory=str(source_directory),
    )

    assert len(results) == 1
    assert results[0].session_id
    assert results[0].turn_id
    assert results[0].turn_index == 1


def test_classify_response_mode_uses_fixed_modes():
    assert classify_response_mode("【能力说明】\n- A") == "capability"
    assert classify_response_mode("【参考命令】\n- B") == "script"
    assert classify_response_mode("【资料边界】\n- C") == "boundary"
    assert classify_response_mode("【流程指导】\n...\n【需要确认的信息】\n- D") == "clarify"
