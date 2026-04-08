from sentieon_assist.classifier import classify_query, is_reference_query, normalize_issue_type


def test_normalize_issue_type_accepts_license():
    assert normalize_issue_type("license") == "license"


def test_normalize_issue_type_accepts_install_case_insensitively():
    assert normalize_issue_type("INSTALL") == "install"


def test_normalize_issue_type_falls_back_to_other():
    assert normalize_issue_type("pipeline") == "other"


def test_classify_query_supports_chinese_license_terms():
    assert classify_query("许可证激活失败，怎么办") == "license"


def test_classify_query_supports_chinese_install_terms():
    assert classify_query("部署后找不到 sentieon 命令") == "install"


def test_is_reference_query_detects_module_intro_question():
    assert is_reference_query("DNAscope 是做什么的") is True


def test_is_reference_query_detects_parameter_question():
    assert is_reference_query("sentieon-cli dnascope 的 --pcr_free 是什么") is True
