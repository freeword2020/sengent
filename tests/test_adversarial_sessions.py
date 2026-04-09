from pathlib import Path

from sentieon_assist.adversarial_sessions import run_support_session


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
