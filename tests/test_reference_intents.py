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
