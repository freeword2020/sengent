from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_chinese_readme_exists_and_links_to_installed_command():
    readme = REPO_ROOT / "README.zh-CN.md"

    assert readme.exists()
    text = readme.read_text(encoding="utf-8")
    assert "sengent" in text
    assert "安装" in text
    assert "sengent doctor" in text
    assert "OpenAI-compatible API" in text
    assert "Sengent 1.0" in text


def test_english_readme_links_to_chinese_readme():
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "README.zh-CN.md" in text
    assert "Sengent 1.0 used Ollama" in text
    assert "OpenAI-compatible API" in text


def test_readmes_explain_how_to_get_the_package_before_install():
    english = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    assert "GitHub Releases" in english
    assert "Download ZIP" in english
    assert "GitHub Releases" in chinese
    assert "Download ZIP" in chinese
    assert "SENGENT_RUNTIME_LLM_PROVIDER" in english
    assert "SENGENT_FACTORY_HOSTED_PROVIDER" in english
    assert "SENGENT_RUNTIME_LLM_PROVIDER" in chinese
    assert "SENGENT_FACTORY_HOSTED_PROVIDER" in chinese


def test_bilingual_user_and_maintainer_guides_exist_with_hosted_api_install_notes():
    english_user = (REPO_ROOT / "docs/sengent-user-guide.en.md").read_text(encoding="utf-8")
    chinese_user = (REPO_ROOT / "docs/sengent-user-guide.md").read_text(encoding="utf-8")
    english_maintainer = (REPO_ROOT / "docs/sengent-maintainer-guide.en.md").read_text(encoding="utf-8")
    chinese_maintainer = (REPO_ROOT / "docs/sengent-maintainer-guide.md").read_text(encoding="utf-8")

    assert "OpenAI-compatible API" in english_user
    assert "SENGENT_RUNTIME_LLM_PROVIDER" in english_user
    assert "OpenAI-compatible API" in chinese_user
    assert "SENGENT_RUNTIME_LLM_PROVIDER" in chinese_user
    assert "OpenAI-compatible API" in english_maintainer
    assert "SENGENT_FACTORY_HOSTED_PROVIDER" in english_maintainer
    assert "OpenAI-compatible API" in chinese_maintainer
    assert "SENGENT_FACTORY_HOSTED_PROVIDER" in chinese_maintainer


def test_bilingual_release_package_docs_exist_with_version_shift_notes():
    english = (
        REPO_ROOT
        / "docs/superpowers/operators/2026-04-14-sengent-2-1-github-release-package.md"
    ).read_text(encoding="utf-8")
    chinese = (
        REPO_ROOT
        / "docs/superpowers/operators/2026-04-14-sengent-2-1-github-release-package.zh-CN.md"
    ).read_text(encoding="utf-8")

    assert "Sengent 1.0 used Ollama" in english
    assert "OpenAI-compatible API" in english
    assert "SENGENT_RUNTIME_LLM_PROVIDER" in english
    assert "Sengent 1.0" in chinese
    assert "OpenAI-compatible API" in chinese
    assert "SENGENT_RUNTIME_LLM_PROVIDER" in chinese


def test_bilingual_2_1_0_release_notes_exist_with_release_assets():
    english = (
        REPO_ROOT
        / "docs/superpowers/operators/2026-04-14-sengent-2-1-0-release-notes.md"
    ).read_text(encoding="utf-8")
    chinese = (
        REPO_ROOT
        / "docs/superpowers/operators/2026-04-14-sengent-2-1-0-release-notes.zh-CN.md"
    ).read_text(encoding="utf-8")

    assert "Sengent 2.1.0" in english
    assert "OpenAI-compatible API" in english
    assert "sengent-2.1.0.tar.gz" in english
    assert "Sengent 2.1.0" in chinese
    assert "OpenAI-compatible API" in chinese
    assert "sengent-2.1.0.tar.gz" in chinese


def test_platform_principles_doc_exists_with_kernel_rules():
    text = (
        REPO_ROOT
        / "docs/superpowers/architecture/2026-04-12-sengent-2-0-platform-principles.md"
    ).read_text(encoding="utf-8")

    assert "support kernel" in text
    assert "vendor profile" in text
    assert "evidence hierarchy" in text
    assert "证据不足时先澄清" in text
    assert "answer contract" in text
    assert "controlled learning loop" in text


def test_vendor_onboarding_contract_doc_exists_with_required_sources():
    text = (
        REPO_ROOT
        / "docs/superpowers/operators/2026-04-12-sengent-vendor-onboarding-contract.md"
    ).read_text(encoding="utf-8")

    assert "official sources" in text
    assert "domain standards" in text
    assert "playbooks" in text
    assert "incident cases" in text
    assert "eval corpus" in text
    assert "support boundaries" in text


def test_pre_human_test_gate_doc_exists_with_required_boundary_terms():
    text = (
        REPO_ROOT
        / "docs/superpowers/operators/2026-04-13-sengent-2-1-pre-human-test-gate.md"
    ).read_text(encoding="utf-8")

    assert "pre-human-test gate" in text
    assert "runtime provider env/config" in text
    assert "factory provider env/config" in text
    assert "doctor checks" in text
    assert "prohibited operations" in text
    assert "expected review-only behavior for factory drafts" in text
    assert "manual test categories" in text


def test_stage_handoff_doc_exists_with_status_and_architecture_summary():
    text = (
        REPO_ROOT
        / "docs/superpowers/operators/2026-04-13-sengent-2-1-stage-handoff.md"
    ).read_text(encoding="utf-8")

    assert "governance-first PoC completed" in text
    assert "hosted runtime + hosted factory internal branch" in text
    assert "vendor / domain / playbook / incident" in text
    assert "factory hosted learning pilot" in text
    assert "live provider smoke" in text
    assert "structured human testing" in text
