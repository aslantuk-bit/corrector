import socket

import pytest

from corrector.core import paths
from corrector.core.issue import Category
from corrector.engines import lt

pytestmark = pytest.mark.lt


@pytest.fixture(scope="module")
def server():
    if not paths.java_exe().exists() or not (paths.lt_home() / "languagetool-server.jar").exists():
        pytest.skip("нет LanguageTool или Java в vendor/")
    server = lt.LanguageToolServer(paths.java_exe(), paths.lt_home(), paths.data_dir() / "lt" / "lt.properties")
    server.start()
    yield server
    server.stop()


def test_server_reports_russian(server):
    client = lt.LanguageToolClient(server.url)
    assert any(item["longCode"] == "ru-RU" for item in client.languages())


def test_engine_finds_known_errors(server):
    engine = lt.LanguageToolEngine(lt.LanguageToolClient(server.url))
    paragraphs = [(0, "Истец обратился в суд с иском о взыскании задолжености."), (1, "Ответчик обязан оплатить за товар ."), (2, "Чистый абзац.")]
    issues = engine.check(paragraphs)
    by_paragraph = {}
    for issue in issues:
        by_paragraph.setdefault(issue.paragraph, []).append(issue)
    assert any(i.category is Category.SPELLING and "задолженности" in i.suggestions for i in by_paragraph[0])
    assert any(i.category is Category.GRAMMAR and i.rule_id == "Upotreblenije_predlogov" for i in by_paragraph[1])
    assert any(i.category is Category.TYPOGRAPHY for i in by_paragraph[1])
    assert 2 not in by_paragraph
    assert engine.status().available is True


def test_disabled_rules_are_respected(server):
    client = lt.LanguageToolClient(server.url, disabled_rules=["COMMA_PARENTHESIS_WHITESPACE"])
    matches = client.check_text("Иск был удовлетворен частично .")
    assert all(m["rule"]["id"] != "COMMA_PARENTHESIS_WHITESPACE" for m in matches)


def test_second_server_gets_other_port_and_stops(server):
    assert server.running
    second = lt.LanguageToolServer(paths.java_exe(), paths.lt_home())
    second.start()
    try:
        assert second.port != server.port
    finally:
        second.stop()
    with socket.socket() as sock:
        sock.settimeout(0.5)
        assert sock.connect_ex(("127.0.0.1", second.port)) != 0
