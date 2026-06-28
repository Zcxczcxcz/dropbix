from __future__ import annotations
import sys
import threading
import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget
import uvicorn

from ..backend.api import app as backend_app
from .api_client import ApiClient
from .pages import SharedFilesPage, PendingPage, HistoryPage, ArchivePage, TrashPage, DevicesPage, FavoritesPage, SettingsPage


class LocalHubWindow(QMainWindow):
    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self.api = api
        self.setWindowTitle("LocalHub")
        self.setMinimumSize(1024, 640)
        self._init_ui()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_all)
        self._refresh_timer.start(6000)

    def _init_ui(self) -> None:
        container = QWidget()
        self.setCentralWidget(container)

        navigation = QListWidget()
        navigation.setFixedWidth(220)
        navigation.addItem(QListWidgetItem("Общие файлы"))
        navigation.addItem(QListWidgetItem("Ожидающие изменения"))
        navigation.addItem(QListWidgetItem("История"))
        navigation.addItem(QListWidgetItem("Архив"))
        navigation.addItem(QListWidgetItem("Корзина"))
        navigation.addItem(QListWidgetItem("Устройства"))
        navigation.addItem(QListWidgetItem("Избранное"))
        navigation.addItem(QListWidgetItem("Настройки"))
        navigation.currentRowChanged.connect(self._switch_page)

        self.stack = QStackedWidget()
        self.pages = [
            SharedFilesPage(self.api),
            PendingPage(self.api),
            HistoryPage(self.api),
            ArchivePage(self.api),
            TrashPage(self.api),
            DevicesPage(self.api),
            FavoritesPage(self.api),
            SettingsPage(self.api),
        ]
        for page in self.pages:
            self.stack.addWidget(page)

        main_layout = QHBoxLayout()
        main_layout.addWidget(navigation)
        main_layout.addWidget(self.stack, 1)

        root = QVBoxLayout()
        header = QLabel("LocalHub — локальная рабочая площадка")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold; margin: 16px 0;")
        root.addWidget(header)
        root.addLayout(main_layout)
        container.setLayout(root)
        navigation.setCurrentRow(0)

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

    def refresh_all(self) -> None:
        for page in self.pages:
            page.refresh()


class LocalHubApp:
    def __init__(self) -> None:
        self.api = ApiClient()
        self.server_thread = threading.Thread(target=self._start_backend, daemon=True)

    def _start_backend(self) -> None:
        uvicorn.run(backend_app, host="127.0.0.1", port=8743, log_level="warning")

    def run(self) -> None:
        self.server_thread.start()
        time.sleep(0.8)
        app = QApplication(sys.argv)
        window = LocalHubWindow(self.api)
        window.show()
        sys.exit(app.exec())
