from pathlib import Path

REPO = "bounchich1/sfu_converter"
OLD_REPO = "Nikita2005qwe/sfu_converter"
EXPECTED_SKILLS = [
    "sfu-common",
    "sfu-coursework",
    "sfu-practice",
    "sfu-report-lab",
    "sfu-research",
    "sfu-small-works",
    "sfu-vkr",
]


def test_profile_skills_are_present_with_frontmatter():
    skills_root = Path("plugins/sfu-converter/skills")

    assert sorted(path.name for path in skills_root.iterdir() if path.is_dir()) == EXPECTED_SKILLS
    assert Path("plugins/sfu-converter/references").is_dir()

    for skill_name in EXPECTED_SKILLS:
        skill_path = skills_root / skill_name / "SKILL.md"
        body = skill_path.read_text(encoding="utf-8")

        assert body.startswith("---\n")
        frontmatter = body.split("---", 2)[1]
        assert f"name: {skill_name}" in frontmatter
        assert "description:" in frontmatter


def test_codex_plugin_uses_single_router_skill():
    manifest = Path("plugins/sfu-converter/.codex-plugin/plugin.json").read_text(encoding="utf-8")
    codex_skills_root = Path("plugins/sfu-converter/codex-skills")
    skill_path = codex_skills_root / "sfu-converter" / "SKILL.md"

    assert '"name": "sfu-converter"' in manifest
    assert '"skills": "./codex-skills/"' in manifest
    assert sorted(path.name for path in codex_skills_root.iterdir() if path.is_dir()) == ["sfu-converter"]

    body = skill_path.read_text(encoding="utf-8")
    assert body.startswith("---\n")
    frontmatter = body.split("---", 2)[1]
    assert "name: sfu-converter" in frontmatter
    assert "description:" in frontmatter
    assert "../../skills/sfu-common/SKILL.md" in body


def test_codex_marketplace_points_at_plugin_package():
    marketplace = Path(".agents/plugins/marketplace.json").read_text(encoding="utf-8")

    assert '"name": "sfu-converter"' in marketplace
    assert '"path": "./plugins/sfu-converter"' in marketplace
    assert '"policy"' in marketplace


def test_public_installation_files_use_canonical_repo_slug():
    checked_paths = [
        Path("README.md"),
        Path("docs/installation.md"),
        Path("plugins/sfu-converter/README.md"),
        Path("plugins/sfu-converter/.claude-plugin/plugin.json"),
        Path("plugins/sfu-converter/.codex-plugin/plugin.json"),
        Path(".claude-plugin/marketplace.json"),
        Path(".agents/plugins/marketplace.json"),
        Path("pyproject.toml"),
    ]

    for path in checked_paths:
        content = path.read_text(encoding="utf-8")

        assert OLD_REPO not in content, path

    assert REPO in Path("docs/installation.md").read_text(encoding="utf-8")
    assert REPO in Path("plugins/sfu-converter/.claude-plugin/plugin.json").read_text(encoding="utf-8")
    assert REPO in Path("plugins/sfu-converter/.codex-plugin/plugin.json").read_text(encoding="utf-8")
