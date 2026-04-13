"""
CemByeDPI - GUI Stil Tanımları
Discord temalı koyu renk paleti ile modern QSS stylesheet.
"""

# -- Renk Paleti --
BG_DARKEST  = "#0b0b14"
BG_DARK     = "#0e0e1a"
BG_CARD     = "#16172b"
BG_CARD2    = "#1e1f36"
BG_INPUT    = "#1a1b30"
ACCENT      = "#5865F2"
ACCENT_HOVER = "#4752C4"
GREEN       = "#57F287"
RED         = "#ED4245"
YELLOW      = "#FEE75C"
TEXT        = "#FFFFFF"
TEXT_DIM    = "#8e9297"
TEXT_MUTED  = "#5c5e66"
BORDER      = "#2a2b40"

STYLESHEET = f"""
/* ===== Genel ===== */
* {{
    font-family: 'Segoe UI', 'Inter', sans-serif;
    color: {TEXT};
}}

QMainWindow {{
    background: {BG_DARK};
}}

QWidget#centralWidget {{
    background: {BG_DARK};
}}

/* ===== Etiketler ===== */
QLabel {{
    background: transparent;
    font-size: 13px;
    color: {TEXT};
}}

QLabel#titleLabel {{
    font-size: 22px;
    font-weight: bold;
    color: {ACCENT};
}}

QLabel#subtitleLabel {{
    font-size: 11px;
    color: {TEXT_DIM};
}}

QLabel#statusLabel {{
    font-size: 15px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 8px;
}}

QLabel#sectionTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {TEXT};
    padding-top: 4px;
}}

QLabel#speedResult {{
    font-size: 22px;
    font-weight: bold;
    color: {ACCENT};
}}

QLabel#pingResult {{
    font-size: 15px;
    font-weight: 600;
    color: {GREEN};
}}

QLabel#statValue {{
    font-size: 14px;
    font-weight: 600;
    color: {TEXT};
}}

QLabel#statLabel {{
    font-size: 11px;
    color: {TEXT_DIM};
}}

/* ===== Kartlar ===== */
QFrame#card {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 14px;
}}

QFrame#card2 {{
    background: {BG_CARD2};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 10px;
}}

/* ===== Butonlar ===== */
QPushButton {{
    background: {ACCENT};
    color: {TEXT};
    border: none;
    border-radius: 10px;
    padding: 12px 28px;
    font-size: 14px;
    font-weight: 600;
    min-height: 20px;
}}

QPushButton:hover {{
    background: {ACCENT_HOVER};
}}

QPushButton:pressed {{
    background: #3c45a5;
}}

QPushButton:disabled {{
    background: #2a2b40;
    color: {TEXT_MUTED};
}}

QPushButton#powerBtn {{
    background: {ACCENT};
    border-radius: 40px;
    min-width: 80px;
    min-height: 80px;
    max-width: 80px;
    max-height: 80px;
    font-size: 32px;
    padding: 0px;
}}

QPushButton#powerBtn:checked {{
    background: {RED};
}}

QPushButton#powerBtn:hover {{
    background: {ACCENT_HOVER};
}}

QPushButton#powerBtn:checked:hover {{
    background: #c93b3e;
}}

QPushButton#speedBtn {{
    background: {BG_CARD2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
}}

QPushButton#speedBtn:hover {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}

/* ===== ComboBox ===== */
QComboBox {{
    background: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    min-height: 18px;
    color: {TEXT};
}}

QComboBox:hover {{
    border: 1px solid {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox QAbstractItemView {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    selection-background-color: {ACCENT};
    color: {TEXT};
    padding: 4px;
}}

/* ===== CheckBox ===== */
QCheckBox {{
    font-size: 12px;
    color: {TEXT_DIM};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {BORDER};
    background: {BG_INPUT};
}}

QCheckBox::indicator:checked {{
    background: {ACCENT};
    border-color: {ACCENT};
}}

/* ===== ProgressBar ===== */
QProgressBar {{
    background: {BG_INPUT};
    border: none;
    border-radius: 6px;
    height: 10px;
    text-align: center;
    font-size: 1px;
    color: transparent;
}}

QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {ACCENT}, stop:1 {GREEN});
    border-radius: 6px;
}}

/* ===== Log Alanı ===== */
QTextEdit#logBox {{
    background: {BG_DARKEST};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 11px;
    color: {TEXT_DIM};
    selection-background-color: {ACCENT};
}}

/* ===== ScrollBar ===== */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {TEXT_MUTED};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
