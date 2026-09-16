# Этапы 5–6 «Окно и Word» — план реализации (сжатый, по просьбе заказчика идти быстрее)

**Goal:** Окно Корректора (PySide6) с подсветкой и списком замечаний, принятием исправлений, словарём и отключением правил; сохранение копии `_проверено.docx` с внесёнными исправлениями и примечаниями Word к оставшимся замечаниям.

**Spec:** `docs/superpowers/specs/2026-09-15-corrector-design.md`, разделы 7, 8, 9, 11.

**Порядок:** сначала этап 6 (правка run и примечания — чистая логика, тестируется без окна), затем состояние сеанса (тоже без Qt), затем виджеты.

## Структура

```
corrector/docx_io/edit.py      split_run(run, offset) -> (Run, Run); apply_replacement(para, start, end, text) -> int (сдвиг);
                               add_comment(model, para, start, end, text, author="Корректор") -> bool;
                               output_path(original: Path) -> Path («_проверено», «(2)»…); save_copy(model, target) -> Path
corrector/app/session.py       Session: open(path) -> None (модель + проверка через движки), issues: list[IssueState],
                               apply(issue_id, replacement) (правит run, сдвигает остальные замечания абзаца),
                               skip(issue_id), add_to_dictionary(issue_id), disable_rule(issue_id),
                               save(with_comments: bool) -> Path, counts(), statuses(); IssueState(issue, status: open|applied|skipped)
corrector/app/worker.py        CheckWorker(QThread): run проверки, сигналы progress(str), finished(list[Issue]), failed(str)
corrector/app/document_view.py DocumentView(QTextEdit): set_model(model), set_highlights(issues), scroll_to(issue), сигнал clicked(issue_id)
corrector/app/issue_panel.py   IssuePanel: список + карточка: категория, сообщение, фрагмент, кнопки вариантов,
                               поле «своё исправление» + «Заменить», «Пропустить», «Добавить в словарь», «Больше не показывать»
corrector/app/window.py        MainWindow: панель кнопок, галочки категорий, сплиттер, строка состояния, перетаскивание .docx,
                               «Справка» (текст инструкции из data/ИНСТРУКЦИЯ.txt), «Открыть в Word» после сохранения
corrector/app/__main__.py      заставка → движки в фоне → окно
data/ИНСТРУКЦИЯ.txt            инструкция пользователя (та же в поставку)
tests/corrector/test_docx_edit.py, test_session.py, test_window.py (pytest-qt, offscreen, движки без LanguageTool)
```

## Задачи

1. **Правка run и примечания** (`docx_io/edit.py`): тесты — замена внутри одного run сохраняет жирный; замена через границу run; табуляции; примечание к фрагменту в середине run (run разрезан, у примечания верный текст); примечания в колонтитуле пропускаются; `output_path` даёт «_проверено» и «(2)»; `save_copy` не трогает оригинал (sha256 до и после).
2. **Сеанс** (`app/session.py`): открыть → замечания; `apply` меняет текст модели и сдвигает замечания того же абзаца правее; замечания, пересекающие заменённый отрезок, закрываются; `skip`; `add_to_dictionary` дописывает `словарь.txt` и закрывает все орфографические замечания с тем же словом; `disable_rule` пишет `настройки.json` и закрывает замечания правила; `save(with_comments)` пишет копию, при `with_comments` — примечания к открытым замечаниям (без колонтитулов); категории из настроек фильтруют список.
3. **Окно**: виджеты и связка с сеансом; проверка в потоке; подсветка через `setExtraSelections` (красный/оранжевый/синий фон); щелчок по тексту выбирает замечание; выбор в списке прокручивает текст; строка состояния с счётчиками и жёлтой плашкой при недоступном LanguageTool; перетаскивание файла; «Справка».
4. **Точка входа**: `python -m corrector.app`; заставка; движки строятся в фоне (LanguageTool стартует до 20 с); ошибки чтения файла — диалог по-русски; непредвиденное исключение — окно «Что-то пошло не так» с путём к журналу.
5. **Проверка вживую**: открыть акт из `/tmp/акты`, принять исправление, сохранить с примечаниями, открыть копию python-docx и убедиться, что примечания на месте.
