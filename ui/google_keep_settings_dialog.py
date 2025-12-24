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
        enabled_label = QLabel("Включить синхронизацию:")
        enabled_label.setStyleSheet("font-size: 11pt;")
        keep_layout.addRow(enabled_label, self.enabled_checkbox)
        
        # Email
        email_label = QLabel("Email:")
        email_label.setStyleSheet("font-size: 11pt;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your.email@gmail.com")
        self.email_input.setFixedWidth(350)
        self.email_input.setFixedHeight(28)
        self.email_input.setStyleSheet("font-size: 10pt;")
        keep_layout.addRow(email_label, self.email_input)
        
        # Пароль / Токен приложения
        password_label = QLabel("Токен приложения:")
        password_label.setStyleSheet("font-size: 11pt;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("16-символьный токен приложения")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedWidth(350)
        self.password_input.setFixedHeight(28)
        self.password_input.setStyleSheet("font-size: 10pt;")
        self.password_input.setToolTip(
            "Для получения токена приложения:\n"
            "1. Включите двухфакторную аутентификацию в Google аккаунте\n"
            "2. Перейдите: https://myaccount.google.com/apppasswords\n"
            "3. Создайте токен для 'Mail' или 'Other'\n"
            "4. Используйте 16-символьный токен (без пробелов)"
        )
        keep_layout.addRow(password_label, self.password_input)
        
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
        self.email_input.textChanged.connect(self._update_test_button_state)
        self.password_input.textChanged.connect(self._update_test_button_state)
    
    def _update_test_button_state(self):
        """Обновляет состояние кнопки теста соединения."""
        # Кнопка активна, если заполнены оба поля (независимо от чекбокса)
        has_email = bool(self.email_input.text().strip())
        has_password = bool(self.password_input.text().strip())
        self.test_btn.setEnabled(has_email and has_password)
    
    def on_enabled_changed(self, enabled: bool):
        """Обрабатывает изменение состояния чекбокса включения."""
        # Поля ввода всегда активны, только кнопка теста зависит от включения
        self._update_test_button_state()
    
    def load_settings(self):
        """Загружает настройки из объекта Settings."""
        enabled = self.settings.get('google_keep.enabled', False)
        email = self.settings.get('google_keep.email', '')
        password = self.settings.get('google_keep.password', '')
        
        self.enabled_checkbox.setChecked(enabled)
        self.email_input.setText(email)
        self.password_input.setText(password)
        
        # Обновляем состояние полей
        self.on_enabled_changed(enabled)
    
    def test_connection(self):
        """Тестирует соединение с Google Keep."""
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if not email or not password:
            QMessageBox.warning(self, "Ошибка", "Введите email и токен приложения")
            return
        
        # Убираем пробелы из токена (Google выдает с пробелами, но нужен без них)
        password_clean = password.replace(' ', '').strip()
        
        # Логируем для отладки (без показа пароля)
        logger.info(f"Тест соединения для email: {email}, длина токена: {len(password_clean)}")
        
        # Блокируем кнопку во время теста
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Проверка...")
        
        try:
            from services.google_keep_sync import GoogleKeepSync
            from storage.database import DatabaseManager
            
            # Создаем временный экземпляр для теста (используем очищенный токен)
            db_manager = DatabaseManager()
            sync = GoogleKeepSync(db_manager, email, password_clean)
            
            if sync.authenticate():
                QMessageBox.information(self, "Успех", "Соединение с Google Keep установлено успешно")
            else:
                QMessageBox.critical(
                    self, "Ошибка",
                    "Не удалось подключиться к Google Keep.\n\n"
                    "Убедитесь, что:\n"
                    "1. Используете токен приложения (не обычный пароль)\n"
                    "2. Токен состоит из 16 символов (без пробелов)\n"
                    "3. Включена двухфакторная аутентификация\n\n"
                    "Как получить токен:\n"
                    "https://myaccount.google.com/apppasswords"
                )
        except ImportError:
            QMessageBox.critical(self, "Ошибка", "Библиотека gkeepapi не установлена.\n\nУстановите: pip install gkeepapi")
        except Exception as e:
            logger.error(f"Ошибка при тестировании соединения: {e}", exc_info=True)
            error_msg = str(e)
            if "BadAuthentication" in error_msg or "auth" in error_msg.lower():
                error_msg = (
                    f"Ошибка аутентификации: {error_msg}\n\n"
                    "Используйте токен приложения, а не обычный пароль!\n\n"
                    "Как получить токен:\n"
                    "1. Включите двухфакторную аутентификацию\n"
                    "2. Перейдите: https://myaccount.google.com/apppasswords\n"
                    "3. Создайте токен для 'Mail' или 'Other'\n"
                    "4. Используйте 16-символьный токен (без пробелов)"
                )
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения:\n{error_msg}")
        finally:
            # Восстанавливаем кнопку
            self.test_btn.setText("Тест соединения")
            self._update_test_button_state()
    
    def accept(self):
        """Сохраняет настройки и закрывает диалог."""
        enabled = self.enabled_checkbox.isChecked()
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        
        if enabled and (not email or not password):
            QMessageBox.warning(self, "Ошибка", "Для включения синхронизации необходимо указать email и пароль")
            return
        
        # Сохраняем настройки
        self.settings.set('google_keep.enabled', enabled)
        self.settings.set('google_keep.email', email)
        self.settings.set('google_keep.password', password)
        
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
    

