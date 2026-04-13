from pathlib import Path

from sentieon_assist.reference_intents import ReferenceIntent
from sentieon_assist.reference_resolution import resolve_reference_answer


def test_resolve_reference_answer_prioritizes_doc_style_answer_for_cpu_prompt():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    resolved = resolve_reference_answer(
        "为什么我的服务器明明有 128 个核心，但 Sentieon 运行时似乎只占用了很少的 CPU 资源？",
        source_directory=str(source_directory),
        resolved_intent=ReferenceIntent(intent="reference_other", confidence=0.41),
    )

    assert resolved is not None
    assert "【资料说明】" in resolved.text
    assert "【资料边界】" not in resolved.text
    assert resolved.resolver_path == ["doc_reference"]
    assert resolved.boundary_tags == []
    assert "sentieon-modules.json" in resolved.sources or "Sentieon202503.03.pdf" in resolved.sources


def test_resolve_reference_answer_prioritizes_parameter_answer_for_dnascope_pcr_free_prompt():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    resolved = resolve_reference_answer(
        "客户明确说明样本使用的是 PCR-free 无扩增建库方案。在运行 DNAscope 流程时，我需要修改哪个特定参数例如 --pcr_indel_model none 或 --pcr-free 来防止软件对 Indel 进行不必要的 PCR 伪影过滤？",
        source_directory=str(source_directory),
        resolved_intent=ReferenceIntent(intent="parameter_lookup", module="DNAscope", confidence=0.42),
    )

    assert resolved is not None
    assert "【常用参数】" in resolved.text
    assert "DNAscope 的 --pcr_free" in resolved.text or "--pcr_indel_model" in resolved.text
    assert resolved.resolver_path == ["module_parameter"]
    assert resolved.boundary_tags == []
    assert "sentieon-modules.json" in resolved.sources


def test_resolve_reference_answer_uses_boundary_contract_for_svsolver_break_end_prompt():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    resolved = resolve_reference_answer(
        "在流程后期，SVSolver 模块是如何对 DNAscope 输出的 Break-end (BND) 候选项进行组装与最终定型输出的？",
        source_directory=str(source_directory),
        resolved_intent=ReferenceIntent(intent="reference_other", module="DNAscope", confidence=0.41),
    )

    assert resolved is not None
    assert "【资料边界】" in resolved.text
    assert "具体参数名" not in resolved.text
    assert "【需要补充的材料】" in resolved.text
    assert resolved.resolver_path == ["boundary_reference"]
    assert "deep_mechanism" in resolved.boundary_tags


def test_resolve_reference_answer_honors_must_tool_reference_intent():
    source_directory = Path(__file__).resolve().parent.parent / "sentieon-note"

    resolved = resolve_reference_answer(
        "VCF 报 contig not found 是什么情况",
        source_directory=str(source_directory),
        resolved_intent=ReferenceIntent(intent="reference_other", confidence=0.41, tool_requirement="required"),
    )

    assert resolved is not None
    assert resolved.text.startswith("【资料边界】")
    assert "确定性检查" in resolved.text
    assert resolved.resolver_path == ["arbitration_must_tool"]
