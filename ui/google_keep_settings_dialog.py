"""
Диалог настроек синхронизации с Google Keep.
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QMessageBox, QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt

from utils.settings import Settings

logger = logging.getLogger(__name__)


class GoogleKeepSettingsDialog(QDialog):
    """Диалог настроек синхронизации с Google Keep."""
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Инициализирует интерфейс диалога."""
        self.setWindowTitle("Настройки синхронизации Google Keep")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Группа настроек Google Keep
        keep_group = QGroupBox("Google Keep")
        keep_layout = QFormLayout()
        
        # Включить синхронизацию
        self.enabled_checkbox = QCheckBox()
        self.enabled_checkbox.setToolTip("Включить синхронизацию с Google Keep")
        keep_layout.addRow("Включить синхронизацию:", self.enabled_checkbox)
        
        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your.email@gmail.com")
        self.email_input.setEnabled(False)
        keep_layout.addRow("Email:", self.email_input)
        
        # Пароль
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Пароль или токен приложения")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setEnabled(False)
        keep_layout.addRow("Пароль:", self.password_input)
        
        # Понижать расширенный Markdown
        self.downgrade_checkbox = QCheckBox()
        self.downgrade_checkbox.setToolTip("Понижать расширенный Markdown до safe-уровня при синхронизации")
        self.downgrade_checkbox.setEnabled(False)
        keep_layout.addRow("Понижать расширенный Markdown:", self.downgrade_checkbox)
        
        keep_group.setLayout(keep_layout)
        layout.addWidget(keep_group)
        
        # Кнопка тестирования соединения
        self.test_btn = QPushButton("Тест соединения")
        self.test_btn.setEnabled(False)
        self.test_btn.clicked.connect(self.test_connection)
        layout.addWidget(self.test_btn)
        
        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        # Подключаем сигналы
        self.enabled_checkbox.toggled.connect(self.on_enabled_changed)
    
    def on_enabled_changed(self, enabled: bool):
        """Обрабатывает изменение состояния чекбокса включения."""
        self.email_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.downgrade_checkbox.setEnabled(enabled)
        self.test_btn.setEnabled(enabled)
    
    def load_settings(self):
        """Загружает настройки из объекта Settings."""
        enabled = self.settings.get('google_keep.enabled', False)
        email = self.settings.get('google_keep.email', '')
        password = self.settings.get('google_keep.password', '')
        downgrade = self.settings.get('google_keep.downgrade_extended', True)
        
        self.enabled_checkbox.setChecked(enabled)
        self.email_input.setText(email)
        self.password_input.setText(password)
        self.downgrade_checkbox.setChecked(downgrade)
        
        # Обновляем состояние полей
        self.on_enabled_changed(enabled)
    
    def test_connection(self):
        """Тестирует соединение с Google Keep."""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if not email or not password:
            QMessageBox.warning(self, "Ошибка", "Введите email и пароль")
            return
        
        try:
            from services.google_keep_sync import GoogleKeepSync
            from storage.database import DatabaseManager
            
            # Создаем временный экземпляр для теста
            db_manager = DatabaseManager()
            sync = GoogleKeepSync(db_manager, email, password)
            
            if sync.authenticate():
                QMessageBox.information(self, "Успех", "Соединение с Google Keep установлено успешно")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к Google Keep")
        except ImportError:
            QMessageBox.critical(self, "Ошибка", "Библиотека gkeepapi не установлена")
        except Exception as e:
            logger.error(f"Ошибка при тестировании соединения: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения: {str(e)}")
    
    def accept(self):
        """Сохраняет настройки и закрывает диалог."""
        enabled = self.enabled_checkbox.isChecked()
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        downgrade = self.downgrade_checkbox.isChecked()
        
        if enabled and (not email or not password):
            QMessageBox.warning(self, "Ошибка", "Для включения синхронизации необходимо указать email и пароль")
            return
        
        # Сохраняем настройки
        self.settings.set('google_keep.enabled', enabled)
        self.settings.set('google_keep.email', email)
        self.settings.set('google_keep.password', password)
        self.settings.set('google_keep.downgrade_extended', downgrade)
        
        super().accept()
    
    def get_enabled(self) -> bool:
        """Возвращает, включена ли синхронизация."""
        return self.enabled_checkbox.isChecked()
    
    def get_email(self) -> str:
        """Возвращает email."""
        return self.email_input.text().strip()
    
    def get_password(self) -> str:
        """Возвращает пароль."""
        return self.password_input.text().strip()
    
    def get_downgrade_extended(self) -> bool:
        """Возвращает, нужно ли понижать расширенный Markdown."""
        return self.downgrade_checkbox.isChecked()

