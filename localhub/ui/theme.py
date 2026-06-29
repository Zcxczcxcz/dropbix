"""Modern stylesheet for LocalHub desktop UI."""

APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0f1117;
    color: #e8eaed;
    font-family: "Segoe UI", "SF Pro Display", system-ui, sans-serif;
    font-size: 13px;
}

QLabel#appTitle {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
    padding: 4px 0;
}

QLabel#pageTitle {
    font-size: 18px;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 4px;
}

QLabel#pageSubtitle {
    font-size: 12px;
    color: #9aa0a6;
    margin-bottom: 12px;
}

QLabel#statusLabel {
    font-size: 11px;
    color: #9aa0a6;
    padding: 6px 12px;
}

QListWidget#sidebar {
    background-color: #161b22;
    border: none;
    border-right: 1px solid #2d333b;
    padding: 12px 8px;
    outline: none;
}

QListWidget#sidebar::item {
    padding: 10px 14px;
    border-radius: 8px;
    margin: 2px 4px;
    color: #c9d1d9;
}

QListWidget#sidebar::item:selected {
    background-color: #238636;
    color: #ffffff;
    font-weight: 600;
}

QListWidget#sidebar::item:hover:!selected {
    background-color: #21262d;
}

QPushButton {
    background-color: #21262d;
    color: #e8eaed;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #30363d;
    border-color: #484f58;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton#primaryButton {
    background-color: #238636;
    border-color: #2ea043;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #2ea043;
}

QPushButton#dangerButton {
    background-color: #da3633;
    border-color: #f85149;
    color: #ffffff;
}

QPushButton#dangerButton:hover {
    background-color: #f85149;
}

QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}

QTableWidget {
    background-color: #161b22;
    alternate-background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 10px;
    gridline-color: #21262d;
    selection-background-color: #238636;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 6px 8px;
}

QHeaderView::section {
    background-color: #21262d;
    color: #8b949e;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #30363d;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
}

QLineEdit, QComboBox {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px 12px;
    color: #e8eaed;
    min-height: 18px;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #238636;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    border: 1px solid #30363d;
    selection-background-color: #238636;
}

QCheckBox {
    spacing: 8px;
    color: #c9d1d9;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #30363d;
    background-color: #0d1117;
}

QCheckBox::indicator:checked {
    background-color: #238636;
    border-color: #2ea043;
}

QFrame#card {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 16px;
}

QFrame#statusBar {
    background-color: #161b22;
    border-top: 1px solid #2d333b;
}

QScrollBar:vertical {
    background: #0d1117;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #30363d;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #484f58;
}

QMessageBox {
    background-color: #161b22;
}

QToolTip {
    background-color: #21262d;
    color: #e8eaed;
    border: 1px solid #30363d;
    padding: 6px;
    border-radius: 6px;
}
"""
