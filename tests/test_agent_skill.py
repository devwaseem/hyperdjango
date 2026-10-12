from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "hyperdjango" / "skills" / "hyperdjango" / "SKILL.md"
EVALS_PATH = ROOT / "evals" / "hyperdjango-skill.json"


def test_agent_skill_has_discoverable_agent_skills_metadata() -> None:
    content = SKILL_PATH.read_text(encoding="utf-8")
    frontmatter = content.split("---", 2)[1]

    assert "name: hyperdjango" in frontmatter
    assert "description:" in frontmatter
    assert "Use when" in frontmatter
    assert SKILL_PATH.parent.name == "hyperdjango"


def test_agent_skill_eval_cases_have_positive_and_boundary_assertions() -> (
    None
):
    payload = json.loads(EVALS_PATH.read_text(encoding="utf-8"))
    cases = payload["cases"]
    ids = [case["id"] for case in cases]

    assert len(ids) == len(set(ids))
    assert {
        "rendered-page",
        "page-local-entry",
        "layout-entry",
        "page-action",
        "webhook-boundary",
        "typed-route",
    } == set(ids)

    positive_kinds = {
        "path_exists",
        "file_changed",
        "file_contains",
        "file_contains_any",
    }
    boundary_kinds = {
        "path_absent",
        "glob_absent",
        "file_unchanged",
        "file_not_contains",
    }
    for case in cases:
        kinds = {assertion["kind"] for assertion in case["assertions"]}
        assert kinds & positive_kinds, case["id"]
        assert kinds & boundary_kinds, case["id"]
