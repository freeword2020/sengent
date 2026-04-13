from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_chinese_readme_exists_and_links_to_installed_command():
    readme = REPO_ROOT / "README.zh-CN.md"

    assert readme.exists()
    text = readme.read_text(encoding="utf-8")
    assert "sengent" in text
    assert "安装" in text
    assert "sengent doctor" in text


def test_english_readme_links_to_chinese_readme():
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "README.zh-CN.md" in text


def test_readmes_explain_how_to_get_the_package_before_install():
    english = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    assert "GitHub Releases" in english
    assert "Download ZIP" in english
    assert "GitHub Releases" in chinese
    assert "Download ZIP" in chinese


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
