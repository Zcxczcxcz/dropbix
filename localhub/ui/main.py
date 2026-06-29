from __future__ import annotations
import sys
import threading
import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
import uvicorn

from ..backend.api import app as backend_app
from ..backend.config import HTTP_PORT
from .api_client import ApiClient
from .pages import (
    SharedFilesPage,
    PendingPage,
    HistoryPage,
    ArchivePage,
    TrashPage,
    DevicesPage,
    FavoritesPage,
    SettingsPage,
)
from .theme import APP_STYLESHEET

NAV_ITEMS = [
    ("📁", "Общие файлы"),
    ("⏳", "Ожидающие"),
    ("📜", "История"),
    ("🗄", "Архив"),
    ("🗑", "Корзина"),
    ("💻", "Устройства"),
    ("⭐", "Избранное"),
    ("⚙", "Настройки"),
]


class LocalHubWindow(QMainWindow):
    def __init__(self, api: ApiClient) -> None:
        super().__init__()
        self.api = api
        self.setWindowTitle("LocalHub")
        self.setMinimumSize(1100, 680)
        self.resize(1280, 760)
        self._init_ui()
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self.refresh_all)
        self._refresh_timer.start(5000)
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(3000)
        self._update_status()

    def _init_ui(self) -> None:
        container = QWidget()
        self.setCentralWidget(container)
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        top_bar = QFrame()
        top_bar.setStyleSheet("background-color: #161b22; border-bottom: 1px solid #2d333b; padding: 12px 20px;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 8, 16, 8)

        title = QLabel("LocalHub")
        title.setObjectName("appTitle")
        top_layout.addWidget(title)

        subtitle = QLabel("Локальная рабочая площадка")
        subtitle.setStyleSheet("color: #8b949e; font-size: 13px; margin-left: 12px;")
        top_layout.addWidget(subtitle)
        top_layout.addStretch()

        self.role_label = QLabel("")
        self.role_label.setStyleSheet("color: #3fb950; font-weight: 600; padding: 4px 12px; background: #0d2818; border-radius: 12px;")
        top_layout.addWidget(self.role_label)
        root.addWidget(top_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self.navigation = QListWidget()
        self.navigation.setObjectName("sidebar")
        self.navigation.setFixedWidth(230)
        for icon, label in NAV_ITEMS:
            item = QListWidgetItem(f"  {icon}  {label}")
            self.navigation.addItem(item)
        self.navigation.currentRowChanged.connect(self._switch_page)

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

        body.addWidget(self.navigation)
        body.addWidget(self.stack, 1)
        root.addLayout(body, 1)

        status_bar = QFrame()
        status_bar.setObjectName("statusBar")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 4, 16, 4)
        self.status_label = QLabel("Подключение...")
        self.status_label.setObjectName("statusLabel")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        self.device_label = QLabel("")
        self.device_label.setObjectName("statusLabel")
        status_layout.addWidget(self.device_label)
        root.addWidget(status_bar)

        container.setLayout(root)
        self.navigation.setCurrentRow(0)

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if 0 <= index < len(self.pages):
            self.pages[index].refresh()

    def _update_status(self) -> None:
        status = self.api.status()
        if not status:
            self.status_label.setText("⚫ Сервер недоступен")
            return
        role = status.get("role", "master")
        role_text = "Мастер" if role == "master" else "Клиент"
        self.role_label.setText(role_text)
        name = status.get("device_name") or status.get("hostname", "Устройство")
        scanning = " · поиск..." if status.get("scanning") else ""
        self.status_label.setText(f"🟢 Сервер работает · порт {HTTP_PORT}{scanning}")
        device_id = status.get("device_id", "")
        short_id = f"{device_id[:8]}…" if len(device_id) > 8 else device_id
        self.device_label.setText(f"{name} · {short_id}")

    def refresh_all(self) -> None:
        current = self.stack.currentIndex()
        if 0 <= current < len(self.pages):
            self.pages[current].refresh()


class LocalHubApp:
    def __init__(self) -> None:
        self.api = ApiClient()
        self.server_thread = threading.Thread(target=self._start_backend, daemon=True)

    def _start_backend(self) -> None:
        uvicorn.run(backend_app, host="0.0.0.0", port=HTTP_PORT, log_level="warning")

    def run(self) -> None:
        self.server_thread.start()
        time.sleep(1.0)
        app = QApplication(sys.argv)
        app.setStyleSheet(APP_STYLESHEET)
        window = LocalHubWindow(self.api)
        window.show()
        sys.exit(app.exec())
