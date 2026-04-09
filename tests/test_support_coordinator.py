from sentieon_assist.reference_intents import parse_reference_intent
from sentieon_assist.support_coordinator import is_capability_question, select_support_route


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
