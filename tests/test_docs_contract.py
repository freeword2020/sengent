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
