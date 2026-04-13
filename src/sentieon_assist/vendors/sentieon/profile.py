from __future__ import annotations

from sentieon_assist.kernel.pack_contract import PackManifestEntry
from sentieon_assist.vendors.base import VendorProfile, VendorRuntimeWording


SENTIEON_RUNTIME_WORDING = VendorRuntimeWording(
    field_labels={
        "version": "Sentieon 版本",
        "error": "完整报错信息",
        "input_type": "输入文件类型",
        "data_type": "数据类型",
        "step": "执行步骤",
    },
    capability_summary_lines=(
        "入门导航：帮你判断 WGS/WES/panel、胚系/体细胞、短读长/长读长 该先看哪条流程。",
        "排障：帮你定位 license、安装、运行报错和常见格式/文件问题。",
        "资料/脚本查询：帮你查模块介绍、参数含义、输入输出和参考命令骨架。",
    ),
    capability_example_queries=(
        "我要做 WES 分析该怎么选",
        "license 报错原文是什么",
        "DNAscope 是什么",
    ),
    official_material_terms=("manual", "release notes", "app note"),
)


SENTIEON_PROFILE = VendorProfile(
    vendor_id="sentieon",
    display_name="Sentieon",
    default_version="202503.03",
    supported_versions=("202503.03",),
    pack_manifest={
        "vendor-reference": PackManifestEntry(
            required=True,
            file_name="sentieon-modules.json",
            entry_schema_version="2.0",
            load_order=10,
        ),
        "vendor-decision": PackManifestEntry(
            required=True,
            file_name="workflow-guides.json",
            entry_schema_version="2.0",
            load_order=20,
        ),
        "domain-standard": PackManifestEntry(
            required=True,
            file_name="external-format-guides.json",
            entry_schema_version="2.0",
            load_order=30,
        ),
        "playbook": PackManifestEntry(
            required=True,
            file_name="external-tool-guides.json",
            entry_schema_version="2.0",
            load_order=40,
        ),
        "troubleshooting": PackManifestEntry(
            required=True,
            file_name="external-error-associations.json",
            entry_schema_version="2.0",
            load_order=50,
        ),
        "incident-memory": PackManifestEntry(
            required=True,
            file_name="incident-memory.json",
            entry_schema_version="2.0",
            load_order=60,
        ),
    },
    domain_dependencies=(
        "VCF",
        "BAM",
        "CRAM",
        "FASTA",
        "BED",
        "sequence-dictionary",
    ),
    clarification_policy={
        "default_slots": ("vendor", "version", "workflow", "inputs", "error"),
        "max_rounds": 2,
    },
    support_boundaries=(
        "unsupported-version",
        "benchmarking",
        "roadmap",
        "deep-mechanism",
    ),
    runtime_wording=SENTIEON_RUNTIME_WORDING,
)
