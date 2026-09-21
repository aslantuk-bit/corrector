import json

import pytest

from corrector import __version__, cli
from tests.corrector.conftest import make_docx


def test_check_file_prints_summary_and_writes_report(tmp_path, capsys):
    path = make_docx(tmp_path / "акт.docx", body=["Соттын шешімі заңды.", "Истец подал ходатайтсво."])
    code = cli.main(["--check", str(path), "--report", "--no-lt"])
    assert code == 0
    out = capsys.readouterr().out
    assert "акт.docx: 2 замечаний (ошибок 2, предупреждений 0, подсказок 0)" in out
    report = (tmp_path / "акт_отчёт.txt").read_text(encoding="utf-8-sig")
    assert "абзац 1 | Орфография | ошибка | «Соттын» → " in report and "оттың" in report
    assert "абзац 2 | Орфография | ошибка | «ходатайтсво» → ходатайство" in report
    assert "lt — недоступен" in report


def test_json_output(tmp_path, capsys):
    path = make_docx(tmp_path / "акт.docx", body=["Соттын шешімі заңды."])
    assert cli.main(["--check", str(path), "--json", "--no-lt"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["fragment"] == "Соттын" and data[0]["category"] == "spelling" and data[0]["file"].endswith("акт.docx")


def test_folder_and_out_dir(tmp_path, capsys):
    folder = tmp_path / "папка"
    folder.mkdir()
    make_docx(folder / "а.docx", body=["Соттын шешімі."])
    make_docx(folder / "б.docx", body=["Чистый текст без ошибок."])
    (folder / "~$а.docx").write_bytes(b"lock")
    out = tmp_path / "отчёты"
    assert cli.main(["--check", str(folder), "--report", "--out", str(out), "--no-lt"]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["а_отчёт.txt", "б_отчёт.txt"]
    assert "б.docx: 0 замечаний" in capsys.readouterr().out


def test_broken_file_returns_two(tmp_path, capsys):
    bad = tmp_path / "плохой.docx"
    bad.write_bytes("нет".encode("utf-8"))
    assert cli.main(["--check", str(bad), "--no-lt"]) == 2
    assert "не документ Word" in capsys.readouterr().err


def test_version(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--version"])
    assert __version__ in capsys.readouterr().out


def test_cli_reports_bad_user_rule(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr("corrector.core.paths.user_dir", lambda: tmp_path)
    (tmp_path / "правила.yaml").write_text("- id: плохое\n  найти: '['\n  сообщение: m\n", encoding="utf-8")
    path = make_docx(tmp_path / "акт.docx", body=["Текст."])
    assert cli.main(["--check", str(path), "--no-lt"]) == 0
    assert "правило 1 (плохое)" in capsys.readouterr().err


def test_output_survives_ascii_console(tmp_path, monkeypatch):
    """В консоли Windows с кодовой страницей cp1252 печать русского текста не должна ронять программу."""
    import io
    import sys
    stream = io.TextIOWrapper(io.BytesIO(), encoding="ascii", errors="strict")
    monkeypatch.setattr(sys, "stdout", stream)
    path = make_docx(tmp_path / "акт.docx", body=["Соттын шешімі заңды."])
    assert cli.main(["--check", str(path), "--no-lt"]) == 0
    stream.flush()
    assert "1" in stream.buffer.getvalue().decode("utf-8", errors="replace")
