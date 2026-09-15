from launchcheck import app, report
from tests.launchcheck.conftest import make_fake_java


def test_report_only_writes_file_and_returns_zero(tmp_path, capsys):
    java = make_fake_java(tmp_path)
    out = tmp_path / "отчёт"
    out.mkdir()
    code = app.main(["--report-only", "--out", str(out), "--java", str(java)])
    assert code == 0
    text = (out / report.REPORT_NAME).read_text(encoding="utf-8-sig")
    assert "Java: OK" in text
    assert report.OK_LINE in text
    assert f"Отчёт сохранён: {out / report.REPORT_NAME}" in capsys.readouterr().out


def test_report_only_missing_java_returns_one(tmp_path):
    code = app.main(["--report-only", "--out", str(tmp_path), "--java", str(tmp_path / "нет" / "java")])
    assert code == 1
    assert "Java: ОШИБКА" in (tmp_path / report.REPORT_NAME).read_text(encoding="utf-8-sig")


def test_window_mode_calls_show(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr("launchcheck.window.show", lambda text, base_dir: calls.append((text, base_dir)) or 0)
    code = app.main(["--out", str(tmp_path), "--java", str(make_fake_java(tmp_path))])
    assert code == 0
    assert len(calls) == 1
    assert "Java: OK" in calls[0][0]
