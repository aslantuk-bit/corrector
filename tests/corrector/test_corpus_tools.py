from tools import corpus_run


def test_report_table_marks_noisy_rules():
    issues = [
        {"file": "а.docx", "engine": "lt", "rule_id": "X", "category": "spelling", "fragment": "Кызылорда", "suggestions": ["Кызыл орда"], "message": "м"},
        {"file": "б.docx", "engine": "lt", "rule_id": "X", "category": "spelling", "fragment": "Астана", "suggestions": [], "message": "м"},
        {"file": "а.docx", "engine": "rules", "rule_id": "typo.dash", "category": "typography", "fragment": " - ", "suggestions": [" — "], "message": "м"},
    ]
    text = corpus_run.format_report(issues, files=["а.docx", "б.docx", "в.docx"], lang="ru", seconds=12.5)
    assert "| lt:X | 2 | 2/3 (67 %) ⚠ разобрать |" in text
    assert "| rules:typo.dash | 1 | 1/3 (33 %) |" in text
    assert "Кызылорда → Кызыл орда" in text
    assert "с заглавной буквы: 2 из 2" in text
