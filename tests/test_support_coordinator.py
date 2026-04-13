from sentieon_assist.reference_intents import ReferenceIntent, parse_reference_intent
from sentieon_assist.support_coordinator import (
    is_capability_question,
    plan_support_turn,
    select_support_route,
    update_support_state,
)
from sentieon_assist.support_state import SupportSessionState


def test_is_capability_question_matches_generic_function_prompt():
    assert is_capability_question("你有什么功能") is True


def test_select_support_route_uses_reference_intent_for_cpu_thread_doc_prompt():
    route = select_support_route(
        "为什么我的服务器明明有 128 个核心，但 Sentieon 运行时似乎只占用了很少的 CPU 资源？",
        parse_reference_intent_fn=lambda query, **kwargs: parse_reference_intent(
            query,
            model_generate=lambda prompt: '{"intent":"not_reference","confidence":0.08}',
        ),
    )

    assert route.task == "reference_lookup"
    assert route.reason == "reference_other"
    assert route.parsed_intent.intent == "reference_other"
    assert route.support_intent == "concept_understanding"
    assert route.fallback_mode == ""
    assert route.vendor_id == "sentieon"
    assert route.vendor_version == "202503.03"


def test_select_support_route_uses_reference_intent_for_license_tool_selection_prompt():
    route = select_support_route(
        "当我配置好本地 License 服务器后，如果分析任务报错提示 License 获取失败，我该使用哪个官方二进制工具如 LICCLNT 来测试服务器连通性并检查可用授权数？",
        parse_reference_intent_fn=lambda query, **kwargs: parse_reference_intent(
            query,
            model_generate=lambda prompt: '{"intent":"not_reference","confidence":0.08}',
        ),
    )

    assert route.task == "reference_lookup"
    assert route.reason == "reference_other"
    assert route.parsed_intent.intent == "reference_other"
    assert route.support_intent == "concept_understanding"


def test_select_support_route_uses_reference_intent_for_bwa_turbo_boundary_prompt():
    route = select_support_route(
        "听说 Sentieon BWA-turbo 能把比对速度再提升 4 倍。这是需要额外下载一个软件，还是只需要在现有的 BWA 命令中通过 -x 参数挂载特定的 .model 文件即可启用？",
        parse_reference_intent_fn=lambda query, **kwargs: parse_reference_intent(
            query,
            model_generate=lambda prompt: '{"intent":"parameter_lookup","confidence":0.88}',
        ),
    )

    assert route.task == "reference_lookup"
    assert route.reason == "reference_other"
    assert route.parsed_intent.intent == "reference_other"
    assert route.support_intent == "concept_understanding"


def test_select_support_route_does_not_upgrade_install_doc_prompt_without_reference_intent():
    route = select_support_route(
        "Poetry 是什么",
        classify_query_fn=lambda query: "install",
        parse_reference_intent_fn=lambda query, **kwargs: ReferenceIntent(),
    )

    assert route.task == "troubleshooting"
    assert route.reason == "issue_type:install"
    assert route.parsed_intent.intent == "not_reference"
    assert route.support_intent == "troubleshooting"


def test_select_support_route_does_not_upgrade_license_doc_prompt_without_reference_intent():
    route = select_support_route(
        "LICCLNT 是什么",
        classify_query_fn=lambda query: "license",
        parse_reference_intent_fn=lambda query, **kwargs: ReferenceIntent(),
    )

    assert route.task == "troubleshooting"
    assert route.reason == "issue_type:license"
    assert route.parsed_intent.intent == "not_reference"
    assert route.support_intent == "troubleshooting"


def test_select_support_route_marks_unsupported_vendor_version():
    route = select_support_route(
        "Sentieon 202401.01 的 DNAscope 是什么",
        parse_reference_intent_fn=lambda query, **kwargs: ReferenceIntent(
            intent="module_intro",
            module="DNAscope",
            confidence=0.92,
        ),
    )

    assert route.task == "reference_lookup"
    assert route.support_intent == "concept_understanding"
    assert route.vendor_id == "sentieon"
    assert route.vendor_version == "202401.01"
    assert route.fallback_mode == "unsupported-version"


def test_select_support_route_keeps_same_family_vendor_version_supported():
    route = select_support_route(
        "Sentieon 202503 license 报错，找不到 license 文件",
        classify_query_fn=lambda query: "license",
        parse_reference_intent_fn=lambda query, **kwargs: ReferenceIntent(),
    )

    assert route.task == "troubleshooting"
    assert route.vendor_version == "202503"
    assert route.fallback_mode == ""


def test_select_support_route_marks_unsupported_vendor_patch_version():
    route = select_support_route(
        "Sentieon 202503.99 license 报错，找不到 license 文件",
        classify_query_fn=lambda query: "license",
        parse_reference_intent_fn=lambda query, **kwargs: ReferenceIntent(),
    )

    assert route.task == "troubleshooting"
    assert route.vendor_version == "202503.99"
    assert route.fallback_mode == "unsupported-version"


def test_select_support_route_marks_workflow_guidance_as_task_guidance():
    route = select_support_route(
        "能提供个 wes 参考脚本吗",
        parse_reference_intent_fn=lambda query, **kwargs: ReferenceIntent(
            intent="workflow_guidance",
            confidence=0.88,
        ),
    )

    assert route.task == "onboarding_guidance"
    assert route.support_intent == "task_guidance"


def test_select_support_route_uses_resolved_default_vendor(monkeypatch):
    import sentieon_assist.support_coordinator as support_coordinator

    seen: list[object] = []
    monkeypatch.setattr(
        support_coordinator,
        "resolve_vendor_id",
        lambda vendor_id=None: seen.append(vendor_id) or "sentieon",
        raising=False,
    )

    route = select_support_route(
        "Poetry 是什么",
        classify_query_fn=lambda query: "install",
        parse_reference_intent_fn=lambda query, **kwargs: ReferenceIntent(),
    )

    assert route.vendor_id == "sentieon"
    assert seen == [None]


def test_update_support_state_tracks_clarification_rounds_and_caps_at_vendor_policy():
    state = SupportSessionState()
    planned_turn = plan_support_turn(
        "能提供个 wes 参考脚本吗",
        state,
        parse_reference_intent_fn=lambda query, **kwargs: ReferenceIntent(
            intent="workflow_guidance",
            confidence=0.88,
        ),
    )
    clarify_response = "【流程指导】\n- 先判断分析模式。\n\n【需要确认的信息】\n- FASTQ、uBAM/uCRAM，还是已对齐 BAM/CRAM"

    state = update_support_state(state, planned_turn=planned_turn, response=clarify_response)
    assert state.clarification_rounds == 1

    state = update_support_state(state, planned_turn=planned_turn, response=clarify_response)
    assert state.clarification_rounds == 2

    state = update_support_state(state, planned_turn=planned_turn, response=clarify_response)
    assert state.clarification_rounds == 2
