from corrector.core.issue import Category, Level
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import context, resources
from corrector.rules.patterns import PatternRule
from tests.corrector.conftest import make_docx


def para(tmp_path, text, lang="ru"):
    doc = model.load(make_docx(tmp_path / "п.docx", body=[text]))
    ctx = context.build_contexts(doc, [lang], Settings(), resources.RuleResources())
    return ctx.paragraphs[0], ctx


def test_pattern_rule_finds_and_replaces(tmp_path):
    rule = PatternRule("typo.test", "any", Category.TYPOGRAPHY, Level.WARNING, "двойной пробел", r" {2,}", " ")
    p, ctx = para(tmp_path, "Суд  решил   дело.")
    issues = rule.check(p, ctx)
    assert [(i.start, i.end, i.suggestions) for i in issues] == [(3, 5, [" "]), (10, 13, [" "])]
    assert issues[0].rule_id == "typo.test" and issues[0].engine == "rules"


def test_pattern_rule_groups_and_condition(tmp_path):
    rule = PatternRule("legal.test", "ru", Category.GRAMMAR, Level.ERROR, "в соответствии с",
                       r"\bв соответствие (с|со)\b", r"в соответствии \1",
                       condition=lambda m, p, d: not p.text[max(0, m.start() - 9):m.start()].lower().endswith("привести "))
    p, ctx = para(tmp_path, "Действуя в соответствие с законом, привести в соответствие с ним.")
    issues = rule.check(p, ctx)
    assert len(issues) == 1 and issues[0].suggestions == ["в соответствии с"]


def test_pattern_rule_ignores_identity_replacement(tmp_path):
    rule = PatternRule("x.y", "any", Category.STYLE, Level.HINT, "м", r"слово", r"слово")
    p, ctx = para(tmp_path, "слово")
    assert rule.check(p, ctx) == []
