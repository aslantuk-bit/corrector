import docx
import pytest

from corrector.app.session import Session
from corrector.app.window import MainWindow
from corrector.core.userdict import UserDictionary
from corrector.engines import factory
from tests.corrector.conftest import make_docx


@pytest.fixture(scope="module")
def engines(tmp_path_factory):
    base = tmp_path_factory.mktemp("движки")
    engines = factory.build_engines(UserDictionary(base / "словарь.txt"), no_lt=True, user_dir=base)
    yield engines
    engines.close()


def make_window(qtbot, tmp_path, engines, body):
    window = MainWindow(Session(engines, tmp_path), help_text="справка", interactive=False)
    qtbot.addWidget(window)
    path = make_docx(tmp_path / "акт.docx", body=body)
    with qtbot.waitSignal(window.check_finished, timeout=30000):
        window.load_path(path)
    return window


def test_window_loads_document_and_lists_issues(qtbot, tmp_path, engines):
    window = make_window(qtbot, tmp_path, engines, ["Соттын шешімі заңды.", "Истец подал ходатайтсво в суд ,  решил."])
    assert window.panel.list.count() >= 3
    assert "ходатайтсво" in window.view.toPlainText()
    assert window.counters.text().startswith("Ошибок 2")
    assert "недоступна" in window.engines_label.text()
    assert len(window.view.spans) == window.panel.list.count()


def test_apply_from_panel_updates_text_and_moves_on(qtbot, tmp_path, engines):
    window = make_window(qtbot, tmp_path, engines, ["Истец подал ходатайтсво в суд ,  решил."])
    before = window.panel.list.count()
    spelling = next(i for i in window.session.visible_items() if window.session.fragment(i) == "ходатайтсво")
    window.panel.select(spelling.id)
    window.panel.apply_requested.emit(spelling.id, "ходатайство")
    assert "ходатайство" in window.view.toPlainText()
    assert window.panel.list.count() == before - 1
    assert window.panel.current_id is not None


def test_dictionary_and_disable_and_category(qtbot, tmp_path, engines):
    window = make_window(qtbot, tmp_path, engines, ["Соттын шешімі. Истец подал ходатайтсво в суд ,  решил."])
    name = next(i for i in window.session.visible_items() if window.session.fragment(i) == "Соттын")
    window.panel.dictionary_requested.emit(name.id)
    assert "Соттын" in (tmp_path / "словарь.txt").read_text(encoding="utf-8")
    typo = next(i for i in window.session.visible_items() if i.issue.rule_id == "typo.double_space")
    window.panel.disable_requested.emit(typo.id)
    assert all(i.issue.rule_id != "typo.double_space" for i in window.session.visible_items())
    box = next(b for b, keys in window.boxes if keys == ["typography"])
    box.setChecked(False)
    assert all(i.issue.category.value != "typography" for i in window.session.visible_items())


def test_save_with_comments(qtbot, tmp_path, engines):
    window = make_window(qtbot, tmp_path, engines, ["Истец подал ходатайтсво в суд ,  решил."])
    target = window.save(with_comments=True)
    assert target == tmp_path / "акт_проверено.docx"
    assert len(list(docx.Document(str(target)).comments)) >= 2


def test_screenshot(qtbot, tmp_path, engines):
    window = make_window(qtbot, tmp_path, engines, ["Соттын шешімі заңды.", "Истец подал ходатайтсво в суд ,  решил. Действуя в соответствие с законом."])
    window.resize(1200, 760)
    window.show()
    qtbot.waitExposed(window)
    assert window.grab().save(str(tmp_path / "окно.png"))
    (tmp_path / "окно.png").replace("/tmp/корректор-окно.png")
