"""
Диалог настроек синхронизации с Google Drive.
"""
import logging
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QMessageBox, QCheckBox, QGroupBox,
    QFileDialog
)
from PyQt6.QtCore import Qt

from utils.settings import Settings

logger = logging.getLogger(__name__)


class GoogleDriveSettingsDialog(QDialog):
    """Диалог настроек синхронизации с Google Drive."""
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Инициализирует интерфейс диалога."""
        self.setWindowTitle("Настройки синхронизации Google Drive")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Группа настроек Google Drive
        drive_group = QGroupBox("Google Drive")
        drive_layout = QFormLayout()
        
        # Включить синхронизацию
        self.enabled_checkbox = QCheckBox()
        self.enabled_checkbox.setToolTip("Включить синхронизацию с Google Drive")
        enabled_label = QLabel("Включить синхронизацию:")
        enabled_label.setStyleSheet("font-size: 11pt;")
        drive_layout.addRow(enabled_label, self.enabled_checkbox)
        
        # Информация о Google Drive
        info_label = QLabel(
            "Google Drive API использует официальный OAuth 2.0 для безопасной аутентификации.\n\n"
            "Преимущества:\n"
            "• Работает на Linux и Android\n"
            "• Официальный API Google\n"
            "• Заметки хранятся как .md файлы\n"
            "• Доступ с любого устройства через Google Drive\n\n"
            "Для настройки:\n"
            "1. Создайте проект в Google Cloud Console\n"
            "2. Включите Google Drive API\n"
            "3. Создайте OAuth 2.0 credentials (Desktop app)\n"
            "4. Скачайте credentials.json\n"
            "5. Укажите путь к файлу ниже"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 10pt; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        drive_layout.addRow(info_label)
        
        # Путь к credentials.json
        credentials_layout = QHBoxLayout()
        self.credentials_input = QLineEdit()
        self.credentials_input.setPlaceholderText("Путь к credentials.json")
        self.credentials_input.setStyleSheet("font-size: 10pt; padding: 5px;")
        self.credentials_input.setFixedHeight(28)
        self.credentials_input.setFixedWidth(350)
        
        browse_btn = QPushButton("Обзор...")
        browse_btn.setFixedHeight(28)
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self.browse_credentials)
        
        credentials_layout.addWidget(self.credentials_input)
        credentials_layout.addWidget(browse_btn)
        credentials_layout.addStretch()
        
        credentials_label = QLabel("Credentials файл:")
        credentials_label.setStyleSheet("font-size: 11pt;")
        drive_layout.addRow(credentials_label, credentials_layout)
        
        drive_group.setLayout(drive_layout)
        layout.addWidget(drive_group)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        test_btn = QPushButton("Тест соединения")
        test_btn.clicked.connect(self.test_connection)
        buttons_layout.addWidget(test_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def browse_credentials(self):
        """Открывает диалог выбора файла credentials.json."""
        default_path = str(Path.home() / ".notes-google-keep" / "credentials.json")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите credentials.json",
            default_path if os.path.exists(default_path) else str(Path.home()),
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.credentials_input.setText(file_path)
    
    def load_settings(self):
        """Загружает настройки из Settings."""
        enabled = self.settings.get('google_drive.enabled', False)
        self.enabled_checkbox.setChecked(enabled)
        
        credentials_file = self.settings.get('google_drive.credentials_file', '')
        if credentials_file:
            self.credentials_input.setText(credentials_file)
        else:
            # Устанавливаем путь по умолчанию
            default_path = str(Path.home() / ".notes-google-keep" / "credentials.json")
            self.credentials_input.setText(default_path)
    
    def save_settings(self):
        """Сохраняет настройки в Settings."""
        self.settings.set('google_drive.enabled', self.enabled_checkbox.isChecked())
        self.settings.set('google_drive.credentials_file', self.credentials_input.text().strip())
        self.settings.save()
    
    def test_connection(self):
        """Тестирует соединение с Google Drive."""
        credentials_file = self.credentials_input.text().strip()
        
        if not credentials_file:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Укажите путь к файлу credentials.json"
            )
            return
        
        if not os.path.exists(credentials_file):
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Файл credentials.json не найден:\n{credentials_file}\n\n"
                "Создайте credentials.json в Google Cloud Console:\n"
                "1. Перейдите на https://console.cloud.google.com/\n"
                "2. Создайте проект (или выберите существующий)\n"
                "3. Включите Google Drive API\n"
                "4. Создайте OAuth 2.0 credentials (Desktop app)\n"
                "5. Скачайте credentials.json"
            )
            return
        
        try:
            from services.google_drive_auth import GoogleDriveAuth
            
            auth = GoogleDriveAuth(credentials_file=credentials_file)
            if auth.authenticate(parent_widget=self):
                QMessageBox.information(
                    self,
                    "Успех",
                    "Соединение с Google Drive установлено успешно!\n\n"
                    "Не забудьте нажать 'OK' для сохранения настроек."
                )
            else:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    "Не удалось установить соединение с Google Drive"
                )
        except Exception as e:
            logger.error(f"Ошибка при тестировании соединения: {e}")
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Ошибка при тестировании соединения:\n{str(e)}"
            )
    
    def accept(self):
        """Сохраняет настройки и закрывает диалог."""
        self.save_settings()
        super().accept()

