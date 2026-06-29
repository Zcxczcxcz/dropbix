from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class AddDeviceDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Добавить устройство")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        hint = QLabel("Введите IP-адрес устройства в локальной сети.\nLocalHub автоматически определит его при наличии.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #9aa0a6; margin-bottom: 8px;")
        layout.addWidget(hint)

        form = QFormLayout()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("192.168.1.100")
        form.addRow("IP-адрес:", self.ip_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Необязательно")
        form.addRow("Имя:", self.name_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_values(self) -> tuple[str, str]:
        return self.ip_input.text().strip(), self.name_input.text().strip()

    def accept(self) -> None:
        if not self.ip_input.text().strip():
            self.ip_input.setFocus()
            return
        super().accept()
