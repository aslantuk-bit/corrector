from PySide6.QtGui import QTextCursor

from corrector.app.document_view import DocumentView
from corrector.docx_io import model
from tests.corrector.conftest import make_docx


def test_view_renders_tables_and_keeps_offsets(qtbot, tmp_path):
    path = make_docx(tmp_path / "а.docx", body=["До таблицы"], table=[["Я1", "Я2"], ["Я3", "Я4"]])
    doc = model.load(make_docx(tmp_path / "б.docx", body=["До таблицы"], table=[["Я1", "Я2"], ["Я3", "Я4"]]))
    view = DocumentView()
    qtbot.addWidget(view)
    view.set_model(doc)
    assert view.document().rootFrame().childFrames(), "таблица должна стать настоящей QTextTable"
    plain = view.toPlainText()
    for para in doc.paragraphs:
        start = view.absolute(para.index, 0)
        assert plain[start:start + len(para.text)] == para.text, para.text


def test_view_applies_run_formatting(qtbot, tmp_path):
    doc = model.load(make_docx(tmp_path / "а.docx", body=[[("Жирный", {"bold": True}), (" обычный", {})]]))
    view = DocumentView()
    qtbot.addWidget(view)
    view.set_model(doc)
    cursor = QTextCursor(view.document())
    cursor.setPosition(view.absolute(0, 1))
    assert cursor.charFormat().font().bold() is True
    cursor.setPosition(view.absolute(0, 9))
    assert cursor.charFormat().font().bold() is False


def test_view_highlights_inside_table(qtbot, tmp_path):
    from corrector.app.session import Session
    from corrector.core.userdict import UserDictionary
    from corrector.engines import factory
    doc_path = make_docx(tmp_path / "а.docx", body=["Тело"], table=[["Соттын шешімі", "норма"]])
    engines = factory.build_engines(UserDictionary(tmp_path / "с.txt"), no_lt=True, user_dir=tmp_path)
    try:
        session = Session(engines, tmp_path)
        session.open(doc_path)
        items = session.check()
        view = DocumentView()
        qtbot.addWidget(view)
        view.set_model(session.model)
        view.set_highlights(session, items)
        spans = {(s, e) for s, e, _ in view.spans}
        item = next(i for i in items if session.fragment(i) == "Соттын")
        start = view.absolute(item.issue.paragraph, item.issue.start)
        assert (start, start + 6) in spans
        assert view.toPlainText()[start:start + 6] == "Соттын"
    finally:
        engines.close()
