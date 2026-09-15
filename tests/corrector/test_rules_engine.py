from corrector.core.issue import Category, Level
from corrector.core.settings import Settings
from corrector.docx_io import model
from corrector.rules import base, context, engine, resources
from tests.corrector.conftest import make_docx


class HelloRule(base.Rule):
    id = "test.hello"
    lang = "ru"
    category = Category.STYLE
    level = Level.HINT
    message = "нашли «привет»"

    def check(self, para, doc):
        position = para.text.find("привет")
        return [base.make_issue(self, para, position, position + 6, ["здравствуйте"])] if position >= 0 else []


class CountRule(base.Rule):
    id = "test.count"
    lang = "any"
    category = Category.STYLE
    level = Level.HINT
    message = "абзацев"
    document_level = True

    def check_document(self, doc):
        first = doc.paragraphs[0]
        return [base.make_issue(self, first, 0, 1, message=f"абзацев: {len(doc.paragraphs)}")]


def make_doc(tmp_path, texts, langs, settings=None):
    doc = model.load(make_docx(tmp_path / "а.docx", body=list(texts)))
    return context.build_contexts(doc, list(langs), settings or Settings(), resources.RuleResources())


def test_contexts_have_tokens_and_sentences(tmp_path):
    doc = make_doc(tmp_path, ["Суд решил. Иск удовлетворить.", "Сот шешті."], ["ru", "kk"])
    first = doc.paragraphs[0]
    assert first.lang == "ru" and first.where == "body"
    assert [t.text for t in first.words] == ["Суд", "решил", "Иск", "удовлетворить"]
    assert len(first.sentences) == 2 and doc.paragraphs[1].lang == "kk"


def test_engine_runs_rules_by_language_and_document_level(tmp_path):
    doc = make_doc(tmp_path, ["привет суду", "привет сотқа"], ["ru", "kk"])
    issues = engine.RulesEngine([HelloRule(), CountRule()]).run(doc)
    assert [(i.rule_id, i.paragraph, i.engine) for i in issues] == [("test.count", 0, "rules"), ("test.hello", 0, "rules")]
    assert issues[1].suggestions == ["здравствуйте"] and issues[1].message == "нашли «привет»"
    assert issues[0].message == "абзацев: 2"


def test_make_issue_uses_rule_fields(tmp_path):
    doc = make_doc(tmp_path, ["привет"], ["ru"])
    issue = base.make_issue(HelloRule(), doc.paragraphs[0], 0, 6)
    assert (issue.category, issue.level, issue.rule_id, issue.engine) == (Category.STYLE, Level.HINT, "test.hello", "rules")
