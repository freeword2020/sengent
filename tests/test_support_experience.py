from sentieon_assist.support_experience import build_support_answer_card, format_support_answer_card


def test_build_support_answer_card_reorders_module_answer_into_judgment_next_step_and_evidence():
    raw = (
        "【资料查询】\n"
        "- 命中模块索引：DNAscope\n"
        "- 模块类别：variant-calling\n\n"
        "【模块介绍】\n"
        "DNAscope：用于 germline variant calling\n"
        "- 常见输入：FASTQ；uBAM\n\n"
        "【常用参数】\n"
        "- 当前模块索引优先覆盖模块定位、输入输出、适用范围和相关模块。\n"
        "- 可继续追问：DNAscope 的输入是什么；DNAscope 参考脚本。"
    )

    card = build_support_answer_card(raw)

    assert [section.title for section in card.sections] == ["【模块介绍】", "【建议下一步】", "【证据依据】"]
    assert "DNAscope：用于 germline variant calling" in card.sections[0].lines
    assert "DNAscope 的输入是什么；DNAscope 参考脚本。" in "\n".join(card.sections[1].lines)
    assert "命中模块索引：DNAscope" in "\n".join(card.sections[2].lines)

    rendered = format_support_answer_card(raw)
    assert "【资料查询】" not in rendered
    assert "【模块介绍】" in rendered
    assert "【建议下一步】" in rendered
    assert "【证据依据】" in rendered


def test_build_support_answer_card_adds_reply_hint_for_clarify_answer():
    raw = (
        "需要补充以下信息：Sentieon 版本\n\n"
        "【当前判断】\n"
        "- 现有信息还不足以给出确定性建议。\n\n"
        "【需要确认的信息】\n"
        "- Sentieon 版本\n\n"
        "【建议下一步】\n"
        "- 请直接补充上面列出的关键信息后再继续。"
    )

    card = build_support_answer_card(raw)

    assert [section.title for section in card.sections] == [
        "【当前判断】",
        "【需要确认的信息】",
        "【建议下一步】",
        "【下一条可直接回复】",
    ]
    assert card.sections[3].lines == ("- Sentieon 版本：<请填写>",)

    rendered = format_support_answer_card(raw)
    assert "【下一条可直接回复】" in rendered
    assert "Sentieon 版本：<请填写>" in rendered


def test_build_support_answer_card_converts_module_disambiguation_into_clarify_card():
    raw = (
        "需要确认模块：参数 --genotype_model 同时出现在多个模块中（DNAscope；GVCFtyper）。"
        "请补充模块名后再查询，例如：DNAscope 的 --genotype_model 是什么"
    )

    card = build_support_answer_card(raw)

    assert [section.title for section in card.sections] == [
        "【需要确认的信息】",
        "【建议下一步】",
        "【下一条可直接回复】",
    ]
    assert "参数 --genotype_model 同时出现在多个模块中" in "\n".join(card.sections[0].lines)
    assert "请补充模块名后再查询" in "\n".join(card.sections[1].lines)
    assert card.sections[2].lines == ("- DNAscope 的 --genotype_model 是什么",)


def test_format_support_answer_card_keeps_troubleshooting_structure_and_adds_reply_hint_when_missing_info_present():
    raw = (
        "【问题判断】\n"
        "这是一个 Sentieon license 相关问题。\n\n"
        "【可能原因】\n"
        "- 环境变量未设置\n\n"
        "【建议步骤】\n"
        "- 检查 SENTIEON_LICENSE\n\n"
        "【需要补充的信息】\n"
        "- 完整报错信息"
    )

    rendered = format_support_answer_card(raw)

    assert "【问题判断】" in rendered
    assert "【可能原因】" in rendered
    assert "【建议步骤】" in rendered
    assert "【需要补充的信息】" in rendered
    assert "【下一条可直接回复】" in rendered
    assert "完整报错信息：<请填写>" in rendered
