from types import SimpleNamespace

from sentieon_assist.reference_intents import parse_reference_intent


def test_parse_reference_intent_reads_module_overview_json():
    result = parse_reference_intent(
        "sentieon都有哪些模块",
        model_generate=lambda prompt: '{"intent":"module_overview","module":"","confidence":0.91}',
    )

    assert result.intent == "module_overview"
    assert result.module == ""
    assert result.confidence == 0.91


def test_parse_reference_intent_extracts_wrapped_json_block():
    result = parse_reference_intent(
        "sentieon都有哪些模块",
        model_generate=lambda prompt: '判断如下：```json\n{"intent":"module_overview","confidence":0.82}\n```',
    )

    assert result.intent == "module_overview"
    assert result.confidence == 0.82


def test_parse_reference_intent_reads_script_example_json_when_heuristic_does_not_apply():
    result = parse_reference_intent(
        "能给个这个模块的参考脚本吗",
        model_generate=lambda prompt: '{"intent":"script_example","module":"RNAseq","confidence":0.89}',
    )

    assert result.intent == "script_example"
    assert result.module == "RNAseq"
    assert result.confidence == 0.89


def test_parse_reference_intent_falls_back_to_not_reference_for_invalid_output():
    result = parse_reference_intent(
        "随便聊聊",
        model_generate=lambda prompt: "I am not sure",
    )

    assert result.intent == "not_reference"
    assert result.confidence == 0.0


def test_parse_reference_intent_uses_script_heuristic_when_model_fails():
    result = parse_reference_intent(
        "能给个 rnaseq 的参考脚本吗",
        model_generate=lambda prompt: (_ for _ in ()).throw(RuntimeError("ollama down")),
    )

    assert result.intent == "script_example"
    assert result.confidence > 0.0


def test_parse_reference_intent_prefers_script_heuristic_over_model_intro():
    result = parse_reference_intent(
        "能给个 dnascope 做 wgs 分析的示例脚本吗",
        model_generate=lambda prompt: '{"intent":"module_intro","module":"DNAscope","confidence":0.93}',
    )

    assert result.intent == "script_example"
    assert result.module == "DNAscope"
    assert result.confidence > 0.0


def test_parse_reference_intent_prefers_workflow_guidance_heuristic_over_model_intro():
    result = parse_reference_intent(
        "如果我要做wgs分析，能不能给个指导",
        model_generate=lambda prompt: '{"intent":"module_intro","module":"DNAscope","confidence":0.91}',
    )

    assert result.intent == "workflow_guidance"
    assert result.confidence > 0.0


def test_parse_reference_intent_marks_external_format_question_as_reference_other():
    result = parse_reference_intent(
        "VCF 的 INFO 和 FORMAT 有什么区别",
        model_generate=lambda prompt: '{"intent":"not_reference","confidence":0.12}',
    )

    assert result.intent == "reference_other"
    assert result.confidence > 0.0


def test_parse_reference_intent_marks_read_group_question_as_reference_other():
    result = parse_reference_intent(
        "read group 是什么，为什么会影响 BAM",
        model_generate=lambda prompt: '{"intent":"not_reference","confidence":0.12}',
    )

    assert result.intent == "reference_other"
    assert result.confidence > 0.0


def test_parse_reference_intent_marks_contig_error_question_as_reference_other():
    result = parse_reference_intent(
        "VCF 报 contig not found 是什么情况",
        model_generate=lambda prompt: '{"intent":"not_reference","confidence":0.12}',
    )

    assert result.intent == "reference_other"
    assert result.confidence > 0.0


def test_parse_reference_intent_marks_contig_error_question_as_must_tool():
    result = parse_reference_intent(
        "VCF 报 contig not found 是什么情况",
        model_generate=lambda prompt: '{"intent":"not_reference","confidence":0.12}',
    )

    assert result.tool_requirement == "required"


def test_parse_reference_intent_does_not_mark_option_scope_error_as_must_tool():
    result = parse_reference_intent(
        "GVCFtyper: Unrecognized option '--interval'",
        model_generate=lambda prompt: '{"intent":"parameter_lookup","module":"GVCFtyper","confidence":0.72}',
    )

    assert result.intent == "parameter_lookup"
    assert result.module == "GVCFtyper"
    assert result.tool_requirement == "none"


def test_parse_reference_intent_does_not_mark_read_group_mismatch_as_must_tool():
    result = parse_reference_intent(
        "BAM 报错说 read group 不一致怎么办",
        model_generate=lambda prompt: '{"intent":"reference_other","confidence":0.61}',
    )

    assert result.intent == "reference_other"
    assert result.tool_requirement == "none"


def test_parse_reference_intent_ignores_invalid_tool_requirement_value():
    result = parse_reference_intent(
        "LICCLNT 是什么",
        model_generate=lambda prompt: '{"intent":"reference_other","confidence":0.44,"tool_requirement":"tool-maybe"}',
    )

    assert result.intent == "reference_other"
    assert result.tool_requirement == "none"


def test_parse_reference_intent_short_circuits_generic_wgs_script_request_to_workflow_guidance():
    result = parse_reference_intent(
        "我要做wgs分析，能给个示例脚本吗",
        model_generate=lambda prompt: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert result.intent == "workflow_guidance"
    assert result.confidence > 0.0


def test_parse_reference_intent_short_circuits_generic_wes_script_request_to_workflow_guidance():
    result = parse_reference_intent(
        "我要做wes分析，能给个示例脚本吗",
        model_generate=lambda prompt: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert result.intent == "workflow_guidance"
    assert result.confidence > 0.0


def test_parse_reference_intent_short_circuits_generic_panel_script_request_to_workflow_guidance():
    result = parse_reference_intent(
        "我要做panel分析，能给个示例脚本吗",
        model_generate=lambda prompt: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert result.intent == "workflow_guidance"
    assert result.confidence > 0.0


def test_parse_reference_intent_short_circuits_generic_rna_script_request_to_workflow_guidance():
    result = parse_reference_intent(
        "我要做rna分析，能给个示例脚本吗",
        model_generate=lambda prompt: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert result.intent == "workflow_guidance"
    assert result.confidence > 0.0


def test_parse_reference_intent_short_circuits_explicit_module_script_request():
    result = parse_reference_intent(
        "我要做hybrid分析，能给个示例脚本吗",
        model_generate=lambda prompt: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert result.intent == "script_example"
    assert result.module == "DNAscope Hybrid"
    assert result.confidence > 0.0


def test_parse_reference_intent_recognizes_joint_call_script_request_with_repeated_spaces():
    result = parse_reference_intent(
        "能提供个 joint  call 参考脚本吗",
        model_generate=lambda prompt: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert result.intent == "script_example"
    assert result.module == "Joint Call"
    assert result.confidence > 0.0


def test_parse_reference_intent_prefers_workflow_guidance_for_hybrid_followup_under_wgs_context():
    result = parse_reference_intent(
        "我要做wgs分析，能给个示例脚本吗 那 hybrid 呢",
        model_generate=lambda prompt: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert result.intent == "workflow_guidance"
    assert result.confidence > 0.0


def test_parse_reference_intent_prefers_workflow_guidance_for_hybrid_followup_under_long_read_context():
    result = parse_reference_intent(
        "我要做long-read分析，能给个示例脚本吗 那 hybrid 呢",
        model_generate=lambda prompt: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert result.intent == "workflow_guidance"
    assert result.confidence > 0.0


def test_parse_reference_intent_short_circuits_explicit_parameter_lookup():
    result = parse_reference_intent(
        "sentieon-cli 的 -t 是什么",
        model_generate=lambda prompt: (_ for _ in ()).throw(AssertionError("should not call model")),
    )

    assert result.intent == "parameter_lookup"
    assert result.module == "sentieon-cli"
    assert result.confidence > 0.0


def test_parse_reference_intent_uses_global_option_heuristic_when_model_fails():
    result = parse_reference_intent(
        "sentieon-cli 的 -t 是什么",
        model_generate=lambda prompt: (_ for _ in ()).throw(RuntimeError("ollama down")),
    )

    assert result.intent == "parameter_lookup"
    assert result.module == "sentieon-cli"
    assert result.confidence > 0.0


def test_parse_reference_intent_uses_gene_edit_parameter_heuristic_when_model_fails():
    result = parse_reference_intent(
        "GeneEditEvaluator 的参数有哪些",
        model_generate=lambda prompt: (_ for _ in ()).throw(RuntimeError("ollama down")),
    )

    assert result.intent == "parameter_lookup"
    assert result.module == "GeneEditEvaluator"
    assert result.confidence > 0.0


def test_parse_reference_intent_prefers_gene_edit_script_heuristic_over_model_intro():
    result = parse_reference_intent(
        "能给个 GeneEditEvaluator 的参考脚本吗",
        model_generate=lambda prompt: '{"intent":"module_intro","module":"GeneEditEvaluator","confidence":0.93}',
    )

    assert result.intent == "script_example"
    assert result.module == "GeneEditEvaluator"
    assert result.confidence > 0.0


def test_parse_reference_intent_marks_cpu_thread_usage_prompt_as_reference_other():
    result = parse_reference_intent(
        "为什么我的服务器明明有 128 个核心，但 Sentieon 运行时似乎只占用了很少的 CPU 资源？",
        model_generate=lambda prompt: '{"intent":"not_reference","confidence":0.08}',
    )

    assert result.intent == "reference_other"
    assert result.confidence > 0.0


def test_parse_reference_intent_hosted_prompt_redacts_local_path_email_and_secret_like_text():
    captured: dict[str, str] = {}

    def capture_prompt(prompt: str) -> str:
        captured["prompt"] = prompt
        return '{"intent":"reference_other","confidence":0.62}'

    result = parse_reference_intent(
        "我想问 FooFeature 是做什么的，日志在 /Users/alice/project/run.log，联系 alice@example.com，token=secret-token-1234567890",
        model_generate=capture_prompt,
    )

    assert result.intent == "reference_other"
    assert "/Users/alice/project/run.log" not in captured["prompt"]
    assert "alice@example.com" not in captured["prompt"]
    assert "secret-token-1234567890" not in captured["prompt"]
    assert "[PATH]" in captured["prompt"]
    assert "[EMAIL]" in captured["prompt"]
    assert "[REDACTED]" in captured["prompt"]


def test_parse_reference_intent_hosted_prompt_keeps_reference_semantics_after_redaction():
    captured: dict[str, str] = {}

    def capture_prompt(prompt: str) -> str:
        captured["prompt"] = prompt
        return '{"intent":"reference_other","confidence":0.51}'

    result = parse_reference_intent(
        "我想知道 FooFeature 是做什么的，日志在 /data/case-001/run.log",
        model_generate=capture_prompt,
    )

    assert result.intent == "reference_other"
    assert "FooFeature" in captured["prompt"]
    assert "/data/case-001/run.log" not in captured["prompt"]
    assert "[PATH]" in captured["prompt"]


def test_parse_reference_intent_marks_license_tool_selection_prompt_as_reference_other():
    result = parse_reference_intent(
        "当我配置好本地 License 服务器后，如果分析任务报错提示 License 获取失败，我该使用哪个官方二进制工具如 LICCLNT 来测试服务器连通性并检查可用授权数？",
        model_generate=lambda prompt: '{"intent":"not_reference","confidence":0.08}',
    )

    assert result.intent == "reference_other"
    assert result.confidence > 0.0


def test_parse_reference_intent_prefers_reference_other_over_parameter_lookup_for_bwa_turbo_boundary_prompt():
    result = parse_reference_intent(
        "听说 Sentieon BWA-turbo 能把比对速度再提升 4 倍。这是需要额外下载一个软件，还是只需要在现有的 BWA 命令中通过 -x 参数挂载特定的 .model 文件即可启用？",
        model_generate=lambda prompt: '{"intent":"parameter_lookup","confidence":0.88}',
    )

    assert result.intent == "reference_other"
    assert result.confidence > 0.0


def test_parse_reference_intent_prefers_parameter_lookup_over_boundary_for_dnascope_pcr_free_prompt():
    result = parse_reference_intent(
        "客户明确说明样本使用的是 PCR-free 无扩增建库方案。在运行 DNAscope 流程时，我需要修改哪个特定参数例如 --pcr_indel_model none 或 --pcr-free 来防止软件对 Indel 进行不必要的 PCR 伪影过滤？",
        model_generate=lambda prompt: '{"intent":"not_reference","confidence":0.05}',
    )

    assert result.intent == "parameter_lookup"
    assert result.module == "DNAscope"
    assert result.confidence > 0.0


def test_parse_reference_intent_uses_structured_outbound_request_for_backend_generation(monkeypatch):
    import sentieon_assist.reference_intents as reference_intents

    captured: dict[str, object] = {}

    class FakeRouter:
        def generate(self, request):
            captured["request"] = request
            return '{"intent":"module_intro","module":"DNAscope","confidence":0.77}'

    monkeypatch.setattr(reference_intents, "_heuristic_reference_intent", lambda query: reference_intents.ReferenceIntent(intent="module_intro", confidence=0.2))
    monkeypatch.setattr(reference_intents, "build_backend_router", lambda config: FakeRouter())

    result = reference_intents.parse_reference_intent(
        "我想了解这个模块",
        config=SimpleNamespace(runtime_llm_provider="openai_compatible"),
    )

    request = captured["request"]
    assert result.intent == "module_intro"
    assert request.purpose == "reference_intent"
    assert request.stream is False
    assert request.trust_boundary_summary["policy_name"] == "reference-intent-outbound-v1"
