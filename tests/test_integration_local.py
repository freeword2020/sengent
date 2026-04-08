from sentieon_assist.cli import run_query


def test_license_query_without_version_requests_more_info():
    text = run_query("license 报错，无法激活")
    assert "需要补充以下信息" in text
    assert "Sentieon 版本" in text


def test_license_query_with_version_returns_rule_answer():
    text = run_query("Sentieon 202503 license 报错，找不到 license 文件")
    assert "【问题判断】" in text
    assert "【可能原因】" in text


def test_chinese_license_query_with_synonyms_returns_rule_answer():
    text = run_query("许可证激活失败，版本是202503.03")
    assert "【问题判断】" in text
    assert "【可能原因】" in text


def test_install_query_can_use_model_fallback():
    def fake_generate(issue_type, query, info):
        assert issue_type == "install"
        assert info["version"] == "202503"
        return "MODEL_FALLBACK_OK"

    text = run_query(
        "Sentieon 202503 install 失败，解压后命令不可用",
        model_fallback=fake_generate,
        knowledge_directory="/tmp/empty-does-not-match",
    )
    assert text.startswith("MODEL_FALLBACK_OK")
    assert "【资料版本】" in text
    assert "【参考资料】" in text


def test_reference_query_uses_local_source_evidence_with_model_fallback():
    def fake_generate(issue_type, query, info, evidence):
        assert issue_type == "reference"
        assert "DNAscope" in query
        assert evidence
        return "【资料查询】\n这是一个 Sentieon 模块资料查询。\n\n【模块介绍】\n- DNAscope 是短读长 germline variant calling 流程。\n\n【常用参数】\n- --pcr_free\n\n【参考资料】\n- thread-019d5249-summary.md"

    text = run_query(
        "DNAscope 是做什么的",
        model_fallback=fake_generate,
        knowledge_directory="/tmp/empty-does-not-match",
    )

    assert "DNAscope" in text
    assert "【模块介绍】" in text
    assert "【资料查询】" not in text
    assert "【资料版本】" not in text
    assert "【参考资料】" not in text
