import pytest

from sentieon_assist.extractor import extract_info_from_query, parse_extracted_json, validate_extracted_info


def test_validate_extracted_info_fills_missing_keys():
    info = validate_extracted_info({"version": "202503"})
    assert info["version"] == "202503"
    assert info["error"] == ""
    assert info["step"] == ""
    assert info["data_type"] == ""


def test_validate_extracted_info_drops_unknown_keys():
    info = validate_extracted_info({"version": "202503", "random": "x"})
    assert "random" not in info


def test_parse_extracted_json_requires_json_object():
    with pytest.raises(ValueError, match="JSON object"):
        parse_extracted_json('["not", "an", "object"]')


def test_extract_info_from_query_keeps_patch_release_when_present():
    info = extract_info_from_query("Sentieon 202503.01 install 失败")
    assert info["version"] == "202503.01"


def test_extract_info_from_query_detects_version_next_to_chinese_text():
    info = extract_info_from_query("我的版本是202503.03，sentieon 安装报错怎么办")
    assert info["version"] == "202503.03"


def test_extract_info_from_query_detects_chinese_license_keywords():
    info = extract_info_from_query("许可证激活失败，版本是202503.03")
    assert info["version"] == "202503.03"
    assert info["error_keywords"] == "license"
    assert info["error"] == "许可证激活失败，版本是202503.03"


def test_extract_info_from_query_detects_chinese_install_synonyms_and_input_type():
    info = extract_info_from_query("部署后找不到 sentieon，版本是202503，用的是BAM")
    assert info["version"] == "202503"
    assert info["step"] == "install"
    assert info["input_type"] == "bam"
