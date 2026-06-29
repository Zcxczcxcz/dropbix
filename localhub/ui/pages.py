from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .api_client import ApiClient
from .dialogs import AddDeviceDialog


class PageBase(QWidget):
    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self.api = api
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(24, 20, 24, 20)
        self.layout.setSpacing(12)
        self.setLayout(self.layout)

    def refresh(self) -> None:
        pass

    def notice(self, text: str, title: str = "Сообщение") -> None:
        QMessageBox.information(self, title, text)

    def warn(self, text: str, title: str = "Внимание") -> None:
        QMessageBox.warning(self, title, text)

    def add_header(self, title: str, subtitle: str = "") -> None:
        header = QLabel(title)
        header.setObjectName("pageTitle")
        self.layout.addWidget(header)
        if subtitle:
            sub = QLabel(subtitle)
            sub.setObjectName("pageSubtitle")
            sub.setWordWrap(True)
            self.layout.addWidget(sub)


class SharedFilesPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.add_header("Общие файлы", "Загружайте и управляйте файлами рабочей области")

        toolbar = QHBoxLayout()
        upload_btn = QPushButton("Загрузить файл")
        upload_btn.setObjectName("primaryButton")
        upload_btn.clicked.connect(self.upload_file)
        toolbar.addWidget(upload_btn)

        fav_btn = QPushButton("В избранное")
        fav_btn.clicked.connect(self.add_to_favorites)
        toolbar.addWidget(fav_btn)

        sync_btn = QPushButton("Синхронизировать")
        sync_btn.clicked.connect(self.manual_sync)
        toolbar.addWidget(sync_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        self.layout.addLayout(toolbar)

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Путь"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.layout.addWidget(self.table)

        actions = QHBoxLayout()
        delete_btn = QPushButton("Удалить")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self.delete_selected)
        actions.addWidget(delete_btn)
        actions.addStretch()
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
        if status == "pending":
            self.notice("Файл отправлен на рассмотрение мастеру")
        elif status == "saved":
            self.notice("Файл успешно сохранён")
        else:
            self.warn("Не удалось загрузить файл")
        self.refresh()

    def delete_selected(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return self.warn("Выберите файл.")
        path = selected[0].text()
        reply = QMessageBox.question(self, "Подтверждение", f"Переместить «{path}» в корзину?")
        if reply != QMessageBox.Yes:
            return
        self.api.delete_file(path)
        self.notice("Файл перемещён в корзину")
        self.refresh()

    def add_to_favorites(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return self.warn("Выберите файл.")
        path = selected[0].text()
        self.api.add_favorite(path)
        self.notice(f"«{path}» добавлен в избранное")

    def manual_sync(self) -> None:
        self.api.manual_sync()
        self.notice("Синхронизация запущена")
        self.refresh()


class PendingPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.add_header("Ожидающие изменения", "Предложения от клиентов, ожидающие подтверждения")

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Файл", "Устройство", "Комментарий", "Статус"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnHidden(0, True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.layout.addWidget(self.table)

        actions = QHBoxLayout()
        accept = QPushButton("Принять")
        accept.setObjectName("primaryButton")
        reject = QPushButton("Отклонить")
        reject.setObjectName("dangerButton")
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
            self.table.setItem(index, 3, QTableWidgetItem(row.get("comment") or ""))
            self.table.setItem(index, 4, QTableWidgetItem(row["status"]))

    def _selected_proposal(self) -> int | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def accept_selected(self) -> None:
        proposal_id = self._selected_proposal()
        if proposal_id is None:
            return self.warn("Выберите изменение.")
        result = self.api.accept_proposal(proposal_id)
        if result.get("status") == "accepted":
            self.notice("Изменение принято")
        else:
            self.warn("Не удалось принять изменение. Возможно, у вас нет прав мастера.")
        self.refresh()

    def reject_selected(self) -> None:
        proposal_id = self._selected_proposal()
        if proposal_id is None:
            return self.warn("Выберите изменение.")
        result = self.api.reject_proposal(proposal_id)
        if result.get("status") == "rejected":
            self.notice("Изменение отклонено")
        else:
            self.warn("Не удалось отклонить изменение.")
        self.refresh()


class HistoryPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.add_header("История версий", "Все сохранённые версии файлов")

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Файл", "Версия", "Автор", "Дата", "Комментарий"])
        self.table.setColumnHidden(0, True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.layout.addWidget(self.table)

        restore = QPushButton("Восстановить выбранную версию")
        restore.setObjectName("primaryButton")
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
            self.table.setItem(index, 5, QTableWidgetItem(row.get("comment") or ""))

    def _selected_version(self) -> int | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        return int(self.table.item(selected[0].row(), 0).text())

    def restore_selected(self) -> None:
        version_id = self._selected_version()
        if not version_id:
            return self.warn("Выберите версию.")
        result = self.api.restore_version(version_id)
        if result.get("status") == "restored":
            self.notice("Версия восстановлена")
        else:
            self.warn("Не удалось восстановить версию.")
        self.refresh()


class ArchivePage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.add_header("Архив событий", "Журнал всех действий в системе")

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Событие"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
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
        self.add_header("Корзина", "Удалённые файлы, которые можно восстановить")

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Файл"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.layout.addWidget(self.table)

        restore = QPushButton("Восстановить файл")
        restore.setObjectName("primaryButton")
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
            return self.warn("Выберите файл.")
        path = selected[0].text()
        result = self.api.restore_trash(path)
        if result.get("status") == "restored":
            self.notice("Файл восстановлен")
        else:
            self.warn("Не удалось восстановить файл.")
        self.refresh()


class DevicesPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.add_header("Устройства", "Автоматический поиск и управление устройствами в локальной сети")

        toolbar = QHBoxLayout()
        self.scan_btn = QPushButton("🔍  Найти устройства")
        self.scan_btn.setObjectName("primaryButton")
        self.scan_btn.clicked.connect(self.start_scan)
        toolbar.addWidget(self.scan_btn)

        add_btn = QPushButton("➕  Добавить вручную")
        add_btn.clicked.connect(self.add_manual)
        toolbar.addWidget(add_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)

        self.scan_label = QLabel("")
        self.scan_label.setObjectName("pageSubtitle")
        toolbar.addWidget(self.scan_label)
        toolbar.addStretch()
        self.layout.addLayout(toolbar)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Имя", "IP", "Статус", "Доверено", "Роль"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnHidden(0, True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.layout.addWidget(self.table)

        actions = QHBoxLayout()
        trust_btn = QPushButton("Доверить")
        trust_btn.setObjectName("primaryButton")
        untrust_btn = QPushButton("Заблокировать")
        remove_btn = QPushButton("Удалить")
        remove_btn.setObjectName("dangerButton")
        trust_btn.clicked.connect(self.trust_selected)
        untrust_btn.clicked.connect(self.untrust_selected)
        remove_btn.clicked.connect(self.remove_selected)
        actions.addWidget(trust_btn)
        actions.addWidget(untrust_btn)
        actions.addWidget(remove_btn)
        actions.addStretch()
        self.layout.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        scan = self.api.scan_status()
        if scan.get("scanning"):
            self.scan_label.setText("⏳ Идёт поиск устройств...")
            self.scan_btn.setEnabled(False)
        else:
            last = scan.get("last_scan_at")
            self.scan_label.setText(f"Последний поиск: {last}" if last else "")
            self.scan_btn.setEnabled(True)

        rows = self.api.list_devices()
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            self.table.setItem(index, 0, QTableWidgetItem(row["device_id"]))
            self.table.setItem(index, 1, QTableWidgetItem(row["name"]))
            self.table.setItem(index, 2, QTableWidgetItem(row.get("ip") or ""))
            online = "🟢 Онлайн" if row.get("online") else "⚫ Офлайн"
            self.table.setItem(index, 3, QTableWidgetItem(online))
            trusted = row.get("trusted")
            trusted_text = "✅ Да" if trusted in (True, 1, "1") else "❌ Нет"
            self.table.setItem(index, 4, QTableWidgetItem(trusted_text))
            role = row.get("role") or "—"
            role_text = "Мастер" if role == "master" else ("Клиент" if role == "client" else "—")
            self.table.setItem(index, 5, QTableWidgetItem(role_text))

    def start_scan(self) -> None:
        self.api.scan_devices()
        self.scan_label.setText("⏳ Идёт поиск устройств...")
        self.scan_btn.setEnabled(False)
        self.notice("Поиск устройств запущен. Результаты появятся через несколько секунд.")

    def add_manual(self) -> None:
        dialog = AddDeviceDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
        ip, name = dialog.get_values()
        result = self.api.add_device(ip, name)
        if result.get("status") == "added":
            device = result.get("device", {})
            self.notice(f"Устройство «{device.get('name', ip)}» добавлено")
        else:
            self.warn("Не удалось добавить устройство. Проверьте IP-адрес.")
        self.refresh()

    def _selected_device(self) -> str | None:
        selected = self.table.selectedItems()
        if not selected:
            return None
        return self.table.item(selected[0].row(), 0).text()

    def trust_selected(self) -> None:
        device_id = self._selected_device()
        if not device_id:
            return self.warn("Выберите устройство.")
        result = self.api.trust_device(device_id)
        if result.get("status") == "trusted":
            self.notice("Устройство доверено")
        else:
            self.warn("Не удалось доверить устройство.")
        self.refresh()

    def untrust_selected(self) -> None:
        device_id = self._selected_device()
        if not device_id:
            return self.warn("Выберите устройство.")
        result = self.api.untrust_device(device_id)
        if result.get("status") == "untrusted":
            self.notice("Устройство заблокировано")
        else:
            self.warn("Не удалось заблокировать устройство.")
        self.refresh()

    def remove_selected(self) -> None:
        device_id = self._selected_device()
        if not device_id:
            return self.warn("Выберите устройство.")
        reply = QMessageBox.question(self, "Подтверждение", "Удалить выбранное устройство из списка?")
        if reply != QMessageBox.Yes:
            return
        result = self.api.remove_device(device_id)
        if result.get("status") == "removed":
            self.notice("Устройство удалено")
        else:
            self.warn("Не удалось удалить устройство.")
        self.refresh()


class FavoritesPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.add_header("Избранное", "Быстрый доступ к важным файлам")

        self.table = QTableWidget(0, 1)
        self.table.setHorizontalHeaderLabels(["Файл"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.layout.addWidget(self.table)

        remove_btn = QPushButton("Убрать из избранного")
        remove_btn.setObjectName("dangerButton")
        remove_btn.clicked.connect(self.remove_selected)
        self.layout.addWidget(remove_btn)
        self.refresh()

    def refresh(self) -> None:
        rows = self.api.list_favorites()
        self.table.setRowCount(len(rows))
        for index, item in enumerate(rows):
            self.table.setItem(index, 0, QTableWidgetItem(item))

    def remove_selected(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return self.warn("Выберите файл.")
        path = selected[0].text()
        self.api.remove_favorite(path)
        self.notice("Убрано из избранного")
        self.refresh()


class SettingsPage(PageBase):
    def __init__(self, api: ApiClient) -> None:
        super().__init__(api)
        self.add_header("Настройки", "Конфигурация этого устройства")

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)

        form_row = QHBoxLayout()
        name_label = QLabel("Имя устройства:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Как вас видят другие устройства")
        form_row.addWidget(name_label)
        form_row.addWidget(self.name_input, 1)
        card_layout.addLayout(form_row)

        role_row = QHBoxLayout()
        role_label = QLabel("Роль:")
        self.role_combo = QComboBox()
        self.role_combo.addItems(["master", "client"])
        role_row.addWidget(role_label)
        role_row.addWidget(self.role_combo)
        role_row.addStretch()
        card_layout.addLayout(role_row)

        self.auto_sync_check = QCheckBox("Автоматическая синхронизация файлов")
        card_layout.addWidget(self.auto_sync_check)

        self.device_id_label = QLabel("")
        self.device_id_label.setWordWrap(True)
        self.device_id_label.setStyleSheet("color: #8b949e; font-size: 11px; margin-top: 8px;")
        card_layout.addWidget(self.device_id_label)

        save_btn = QPushButton("Сохранить настройки")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self.save_settings)
        card_layout.addWidget(save_btn)

        self.layout.addWidget(card)
        self.layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        settings = self.api.get_settings()
        self.name_input.setText(settings.get("device_name") or "")
        role = settings.get("role", "master")
        idx = self.role_combo.findText(role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)
        self.auto_sync_check.setChecked(bool(settings.get("auto_sync", True)))
        device_id = settings.get("device_id", "")
        self.device_id_label.setText(f"ID устройства: {device_id[:16]}…{device_id[-8:]}" if len(device_id) > 24 else f"ID устройства: {device_id}")

    def save_settings(self) -> None:
        result = self.api.update_settings(
            role=self.role_combo.currentText(),
            auto_sync=self.auto_sync_check.isChecked(),
            device_name=self.name_input.text().strip(),
        )
        if result:
            self.notice("Настройки сохранены")
        else:
            self.warn("Не удалось сохранить настройки")
