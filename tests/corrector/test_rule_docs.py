from pathlib import Path

import pytest

from corrector.core import paths
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, doctests, engine, resources
from tests.corrector.conftest import make_docx

CASES = doctests.parse_rule_docs(paths.app_dir() / "docs" / "rules-ru.md") + doctests.parse_rule_docs(paths.app_dir() / "docs" / "rules-kk.md")


@pytest.fixture(scope="module")
def rules_engine():
    res = resources.load_resources(paths.data_dir(), Path("/nonexistent"))
    return engine.RulesEngine(engine.default_rules(res), res)


def test_docs_have_cases():
    assert len(CASES) >= 1


@pytest.mark.parametrize("case", CASES, ids=[f"{c.lang}:{c.rule_id}:{c.line}" for c in CASES])
def test_rule_doc_case(case, rules_engine, tmp_path):
    doc = model.load(make_docx(tmp_path / "п.docx", body=[case.wrong]))
    ctx = context.build_contexts(doc, [case.lang], Settings(), rules_engine.resources)
    issues = [i for i in rules_engine.run(ctx) if i.rule_id == case.rule_id]
    if case.right == "✓":
        assert issues == [], f"лишнее замечание: {[(i.start, i.end, i.message) for i in issues]}"
        return
    assert issues, f"правило {case.rule_id} не сработало на «{case.wrong}»"
    if case.right != "—":
        first = issues[0]
        assert first.suggestions, "нет варианта замены"
        fixed = case.wrong[: first.start] + first.suggestions[0] + case.wrong[first.end:]
        assert fixed == case.right
