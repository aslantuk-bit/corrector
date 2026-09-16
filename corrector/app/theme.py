"""Оформление окна: бумага и чернила. Лист документа — белый, с засечками, как в самих актах;
пометки корректора — красный, янтарный, синий; интерфейс вокруг — тихий, холодно-серый, один акцент — чернильно-синий."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

from corrector.core.issue import Level

INK = "#1B2430"
MUTED = "#5B6470"
LINE = "#C9D0D8"
CHROME = "#E9ECF0"
PANEL = "#F5F6F8"
PAPER = "#FFFFFF"
ACCENT = "#23508F"
ACCENT_DARK = "#1C4276"
LEVEL_COLORS = {Level.ERROR: "#B3261E", Level.WARNING: "#B26A00", Level.HINT: "#2F62A8"}
LEVEL_TITLES = {Level.ERROR: "ошибка", Level.WARNING: "предупреждение", Level.HINT: "подсказка"}
SIGNATURE = "Автор: TAS. Пользуйтесь свободно."

UI_FONT = '"Segoe UI", "SF Pro Text", "Helvetica Neue", Arial, sans-serif'
DOC_FONT = '"Times New Roman", Georgia, "Noto Serif", serif'

STYLE = f"""
QMainWindow, QDialog {{ background: {CHROME}; }}
QWidget {{ font-family: {UI_FONT}; font-size: 10.5pt; color: {INK}; }}
QWidget#header {{ background: {PANEL}; border-bottom: 1px solid {LINE}; }}
QLabel#title {{ font-family: {DOC_FONT}; font-size: 20pt; color: {INK}; }}
QLabel#subtitle {{ color: {MUTED}; font-size: 9.5pt; }}
QLabel#signature {{ color: {MUTED}; font-size: 9pt; }}
QLabel#cardHeader {{ font-size: 11pt; font-weight: 600; }}
QLabel#fragment {{ font-family: {DOC_FONT}; font-size: 12.5pt; background: {PAPER}; border: 1px solid {LINE};
                   border-radius: 3px; padding: 8px 10px; }}
QLabel#message {{ font-size: 10.5pt; }}
QLabel#engine {{ padding: 3px 10px; border-radius: 10px; background: #DDEBDD; color: #1F5C2A; font-size: 9pt; }}
QLabel#engine[state="off"] {{ background: #FFE9B8; color: #6B4A00; }}
QTextEdit#document {{ background: {PAPER}; border: 1px solid {LINE}; font-family: {DOC_FONT}; font-size: 13pt;
                      selection-background-color: #CFE0F5; }}
QListWidget {{ background: {PAPER}; border: 1px solid {LINE}; outline: 0; font-size: 10pt; }}
QListWidget::item {{ padding: 6px 8px; border-bottom: 1px solid #EEF1F4; }}
QListWidget::item:selected {{ background: #E3ECF8; color: {INK}; }}
QPushButton {{ background: {PAPER}; border: 1px solid {LINE}; border-radius: 3px; padding: 6px 14px; min-height: 18px; }}
QPushButton:hover {{ border-color: {ACCENT}; background: #F3F6FA; }}
QPushButton:pressed {{ background: #DCE6F3; border-color: {ACCENT_DARK}; padding-top: 7px; padding-bottom: 5px; }}
QPushButton:disabled {{ color: #9AA3AE; border-color: #E1E5EA; }}
QPushButton[kind="primary"] {{ background: {ACCENT}; color: white; border-color: {ACCENT}; }}
QPushButton[kind="primary"]:hover {{ background: {ACCENT_DARK}; border-color: {ACCENT_DARK}; }}
QPushButton[kind="primary"]:pressed {{ background: #16365F; border-color: #16365F; }}
QPushButton[kind="primary"]:disabled {{ background: #AFC0D8; border-color: #AFC0D8; color: white; }}
QPushButton[kind="quiet"] {{ border: none; background: transparent; color: {MUTED}; padding: 4px 6px; }}
QPushButton[kind="quiet"]:hover {{ color: {ACCENT}; }}
QLineEdit {{ background: {PAPER}; border: 1px solid {LINE}; border-radius: 3px; padding: 6px 8px; min-height: 18px; }}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QCheckBox {{ spacing: 6px; padding: 4px 10px; border: 1px solid {LINE}; border-radius: 12px; background: {PAPER}; }}
QCheckBox:checked {{ background: #E3ECF8; border-color: {ACCENT}; }}
QCheckBox::indicator {{ width: 0; height: 0; }}
QSplitter::handle {{ background: {CHROME}; width: 8px; }}
QStatusBar {{ background: {PANEL}; border-top: 1px solid {LINE}; }}
QStatusBar::item {{ border: none; }}
QProgressBar {{ border: 1px solid {LINE}; border-radius: 3px; background: {PAPER}; max-height: 10px; }}
QProgressBar::chunk {{ background: {ACCENT}; }}
QTextBrowser {{ background: {PAPER}; border: 1px solid {LINE}; font-size: 10.5pt; }}
QScrollBar:vertical {{ background: {PANEL}; width: 12px; }}
QScrollBar::handle:vertical {{ background: {LINE}; border-radius: 4px; min-height: 30px; margin: 2px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""


def level_icon(level: Level) -> QIcon:
    pixmap = QPixmap(12, 12)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(LEVEL_COLORS[level]))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(1, 1, 10, 10, 3, 3)
    painter.end()
    return QIcon(pixmap)


def counters_html(counts: dict[Level, int]) -> str:
    parts = []
    for level, word in ((Level.ERROR, "ошибок"), (Level.WARNING, "предупреждений"), (Level.HINT, "подсказок")):
        parts.append(f'<span style="color:{LEVEL_COLORS[level]}">&#9679;</span> {word} {counts[level]}')
    return "&nbsp;&nbsp;&nbsp;".join(parts)
