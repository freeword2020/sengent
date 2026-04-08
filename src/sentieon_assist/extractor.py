from __future__ import annotations

import json
import re
from typing import Any

from sentieon_assist.models import EXTRACTION_FIELDS

LICENSE_ERROR_TERMS = ("license", "licence", "许可证", "授权", "激活")
INSTALL_STEP_TERMS = ("install", "安装", "部署", "解压")
ERROR_MARKERS = ("报错", "error", "failed", "找不到", "失败", "异常", "不可用")


def parse_extracted_json(raw_text: str) -> dict[str, Any]:
    data = json.loads(raw_text)
    if not isinstance(data, dict):
        raise ValueError("extracted content must be a JSON object")
    return data


def validate_extracted_info(info: dict[str, Any]) -> dict[str, str]:
    validated: dict[str, str] = {}
    for key in EXTRACTION_FIELDS:
        value = info.get(key, "")
        validated[key] = "" if value in (None, []) else str(value).strip()
    return validated


def extract_info_from_query(query: str) -> dict[str, str]:
    version_match = re.search(r"(?<!\d)(20\d{4}(?:\.\d{2})?)(?!\d)", query)
    lowered = query.lower()
    input_type = ""
    if "fastq" in lowered:
        input_type = "fastq"
    elif "bam" in lowered:
        input_type = "bam"

    has_error_marker = any(marker in lowered for marker in ERROR_MARKERS)
    raw_info = {
        "version": version_match.group(1) if version_match else "",
        "input_type": input_type,
        "error": query if has_error_marker else "",
        "error_keywords": "license" if any(term in lowered for term in LICENSE_ERROR_TERMS) else "",
        "step": "install" if any(term in lowered for term in INSTALL_STEP_TERMS) else "",
        "data_type": "",
    }
    return validate_extracted_info(raw_info)
