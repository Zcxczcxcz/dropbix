from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QFileDialog, QMessageBox

from .api_client import ApiClient


class PageBase(QWidget):
    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self.api = api
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

    def refresh(self) -> None:
        pass

    def notice(self, text: str) -> None:
        QMessageBox.information(self, "Сообщение", text)


class SharedFilesPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        header = QLabel("Общие файлы")
        header.setStyleSheet("font-size: 16px; font-weight: 600; margin-bottom: 8px;")
        self.layout.addWidget(header)

        toolbar = QHBoxLayout()
        upload_button = QPushButton("Загрузить файл")
        upload_button.clicked.connect(self.upload_file)
        toolbar.addWidget(upload_button)

        sync_button = QPushButton("Обновить список")
        sync_button.clicked.connect(self.refresh)
        toolbar.addWidget(sync_button)
        toolbar.addStretch()
        self.layout.addLayout(toolbar)

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Путь"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)
        actions = QHBoxLayout()
        delete_button = QPushButton("Удалить")
        delete_button.clicked.connect(self.delete_selected)
        actions.addWidget(delete_button)
        self.layout.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        files = self.api.list_files()
        self.table.setRowCount(len(files))
        for row, file_path in enumerate(files):
            item = QTableWidgetItem(file_path)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table.setItem(row, 0, item)

    def upload_file(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, "Выберите файл для загрузки")
        if not selected:
            return
        name = Path(selected).name
        with open(selected, "rb") as handle:
            response = self.api.upload_file(name, handle.read(), comment="Загрузка через LocalHub")
            status = response.get("status")
            self.notice("Файл отправлен для сохранения" if status != "saved" else "Файл успешно сохранён")
        self.refresh()

    def delete_selected(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return self.notice("Выберите файл.")
        path = selected[0].text()
        self.api.delete_file(path)
        self.notice("Файл перемещён в корзину")
        self.refresh()


class PendingPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.layout.addWidget(QLabel("Ожидающие изменения"))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Файл", "Устройство", "Комментарий", "Статус"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnHidden(0, True)
        self.layout.addWidget(self.table)

        actions = QHBoxLayout()
        accept = QPushButton("Принять")
        reject = QPushButton("Отклонить")
        accept.clicked.connect(self.accept_selected)
        reject.clicked.connect(self.reject_selected)
        actions.addWidget(accept)
        actions.addWidget(reject)
        actions.addStretch()
        self.layout.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        rows = self.api.list_pending()
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            self.table.setItem(index, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(index, 1, QTableWidgetItem(row["file_path"]))
            self.table.setItem(index, 2, QTableWidgetItem(row["sender_device"]))
            self.table.setItem(index, 3, QTableWidgetItem(row["comment"] or ""))
            self.table.setItem(index, 4, QTableWidgetItem(row["status"]))

    def _selected_proposal(self) -> int | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def accept_selected(self) -> None:
        proposal_id = self._selected_proposal()
        if proposal_id is None:
            return self.notice("Выберите изменение.")
        self.api.accept_proposal(proposal_id)
        self.notice("Изменение принято")
        self.refresh()

    def reject_selected(self) -> None:
        proposal_id = self._selected_proposal()
        if not proposal_id:
            return self.notice("Выберите изменение.")
        self.api.reject_proposal(proposal_id)
        self.notice("Изменение отклонено")
        self.refresh()


class HistoryPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.layout.addWidget(QLabel("История версий"))
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Файл", "Версия", "Автор", "Дата", "Комментарий"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)
        restore = QPushButton("Восстановить выбранную версию")
        restore.clicked.connect(self.restore_selected)
        self.layout.addWidget(restore)
        self.refresh()

    def refresh(self) -> None:
        rows = self.api.history()
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            self.table.setItem(index, 0, QTableWidgetItem(str(row["id"])))
            self.table.setItem(index, 1, QTableWidgetItem(row["file_path"]))
            self.table.setItem(index, 2, QTableWidgetItem(str(row["version"])))
            self.table.setItem(index, 3, QTableWidgetItem(row["author"]))
            self.table.setItem(index, 4, QTableWidgetItem(row["timestamp"]))
            self.table.setItem(index, 5, QTableWidgetItem(row["comment"] or ""))

    def _selected_version(self) -> int | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def restore_selected(self) -> None:
        version_id = self._selected_version()
        if not version_id:
            return self.notice("Выберите версию.")
        self.api.restore_version(version_id)
        self.notice("Версия восстановлена")
        self.refresh()


class ArchivePage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.layout.addWidget(QLabel("Архив событий"))
        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Запись"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)
        self.refresh()

    def refresh(self) -> None:
        rows = self.api.list_archive()
        self.table.setRowCount(len(rows))
        for index, item in enumerate(rows):
            self.table.setItem(index, 0, QTableWidgetItem(item))


class TrashPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.layout.addWidget(QLabel("Корзина"))
        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Файл"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)
        restore = QPushButton("Восстановить файл")
        restore.clicked.connect(self.restore_selected)
        self.layout.addWidget(restore)
        self.refresh()

    def refresh(self) -> None:
        rows = self.api.list_trash()
        self.table.setRowCount(len(rows))
        for index, item in enumerate(rows):
            self.table.setItem(index, 0, QTableWidgetItem(item))

    def restore_selected(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return self.notice("Выберите файл.")
        path = selected[0].text()
        self.api.restore_trash(path)
        self.notice("Файл восстановлен")
        self.refresh()


class DevicesPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        header = QLabel("Устройства")
        header.setStyleSheet("font-size: 16px; font-weight: 600; margin-bottom: 8px;")
        self.layout.addWidget(header)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Имя", "IP", "Доверено"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnHidden(0, True)
        self.layout.addWidget(self.table)

        actions = QHBoxLayout()
        trust_button = QPushButton("Доверить")
        untrust_button = QPushButton("Заблокировать")
        trust_button.clicked.connect(self.trust_selected)
        untrust_button.clicked.connect(self.untrust_selected)
        actions.addWidget(trust_button)
        actions.addWidget(untrust_button)
        actions.addStretch()
        self.layout.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        rows = self.api.list_devices()
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            self.table.setItem(index, 0, QTableWidgetItem(row["device_id"]))
            self.table.setItem(index, 1, QTableWidgetItem(row["name"]))
            self.table.setItem(index, 2, QTableWidgetItem(row["ip"] or ""))
            self.table.setItem(index, 3, QTableWidgetItem("Да" if row["trusted"] else "Нет"))

    def _selected_device(self) -> str | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        return self.table.item(selected[0].row(), 0).text()

    def trust_selected(self) -> None:
        device_id = self._selected_device()
        if not device_id:
            return self.notice("Выберите устройство.")
        self.api.trust_device(device_id)
        self.notice("Устройство доверено")
        self.refresh()

    def untrust_selected(self) -> None:
        device_id = self._selected_device()
        if not device_id:
            return self.notice("Выберите устройство.")
        self.api.untrust_device(device_id)
        self.notice("Устройство больше не доверено")
        self.refresh()


class FavoritesPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.layout.addWidget(QLabel("Избранное"))
        self.notice("Любимые файлы появятся здесь после их пометки в общей области.")

    def refresh(self) -> None:
        pass


class SettingsPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.layout.addWidget(QLabel("Настройки"))
        self.notice("Настройки будут доступны в следующих версиях приложения.")

    def refresh(self) -> None:
        pass
