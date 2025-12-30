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
        
        # Информация об OAuth
        info_label = QLabel(
            "Синхронизация использует OAuth 2.0 для безопасной авторизации.\n\n"
            "Введите OAuth credentials из Google Cloud Console или укажите путь к файлу credentials.json.\n\n"
            "При первом подключении откроется браузер для авторизации.\n"
            "Токен будет сохранен локально для последующих использований.\n\n"
            "См. README.md для подробных инструкций по созданию credentials."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 10pt; color: #666; padding: 10px;")
        keep_layout.addRow(info_label)
        
        # Client ID
        client_id_label = QLabel("Client ID:")
        client_id_label.setStyleSheet("font-size: 11pt;")
        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("xxxxx.apps.googleusercontent.com")
        self.client_id_input.setFixedWidth(350)
        self.client_id_input.setFixedHeight(28)
        self.client_id_input.setStyleSheet("font-size: 10pt;")
        self.client_id_input.setToolTip("OAuth 2.0 Client ID из Google Cloud Console")
        keep_layout.addRow(client_id_label, self.client_id_input)
        
        # Client Secret
        client_secret_label = QLabel("Client Secret:")
        client_secret_label.setStyleSheet("font-size: 11pt;")
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setPlaceholderText("GOCSPX-xxxxxxxxxxxxx")
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.client_secret_input.setFixedWidth(350)
        self.client_secret_input.setFixedHeight(28)
        self.client_secret_input.setStyleSheet("font-size: 10pt;")
        self.client_secret_input.setToolTip("OAuth 2.0 Client Secret из Google Cloud Console")
        keep_layout.addRow(client_secret_label, self.client_secret_input)
        
        # Project ID (опционально)
        project_id_label = QLabel("Project ID (опционально):")
        project_id_label.setStyleSheet("font-size: 11pt;")
        self.project_id_input = QLineEdit()
        self.project_id_input.setPlaceholderText("your-project-id")
        self.project_id_input.setFixedWidth(350)
        self.project_id_input.setFixedHeight(28)
        self.project_id_input.setStyleSheet("font-size: 10pt;")
        self.project_id_input.setToolTip("Project ID из Google Cloud Console (необязательно)")
        keep_layout.addRow(project_id_label, self.project_id_input)
        
        # Разделитель
        separator_label = QLabel("─ или ─")
        separator_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator_label.setStyleSheet("font-size: 10pt; color: #999; padding: 10px 0;")
        keep_layout.addRow(separator_label)
        
        # Путь к файлу credentials.json (альтернатива)
        credentials_file_label = QLabel("Путь к credentials.json:")
        credentials_file_label.setStyleSheet("font-size: 11pt;")
        self.credentials_file_input = QLineEdit()
        self.credentials_file_input.setPlaceholderText("~/.notes-google-keep/credentials.json")
        self.credentials_file_input.setFixedWidth(350)
        self.credentials_file_input.setFixedHeight(28)
        self.credentials_file_input.setStyleSheet("font-size: 10pt;")
        self.credentials_file_input.setToolTip(
            "Альтернатива: путь к файлу credentials.json из Google Cloud Console.\n"
            "Если указан, будет использован файл вместо полей выше."
        )
        keep_layout.addRow(credentials_file_label, self.credentials_file_input)
        
        keep_group.setLayout(keep_layout)
        layout.addWidget(keep_group)
        
        # Кнопка тестирования соединения
        self.test_btn = QPushButton("Тест соединения")
        self.test_btn.setEnabled(False)  # Будет активирована при наличии credentials
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
        self.client_id_input.textChanged.connect(self._update_test_button_state)
        self.client_secret_input.textChanged.connect(self._update_test_button_state)
        self.credentials_file_input.textChanged.connect(self._update_test_button_state)
    
    def _update_test_button_state(self):
        """Обновляет состояние кнопки теста соединения."""
        # Кнопка активна, если есть credentials (независимо от чекбокса включения)
        has_credentials = (
            (self.client_id_input.text().strip() and self.client_secret_input.text().strip()) or
            self.credentials_file_input.text().strip()
        )
        self.test_btn.setEnabled(has_credentials)
    
    def on_enabled_changed(self, enabled: bool):
        """Обрабатывает изменение состояния чекбокса включения."""
        # Кнопка теста не зависит от чекбокса, только от наличия credentials
        pass
    
    def load_settings(self):
        """Загружает настройки из объекта Settings."""
        enabled = self.settings.get('google_keep.enabled', False)
        client_id = self.settings.get('google_keep.client_id', '')
        client_secret = self.settings.get('google_keep.client_secret', '')
        project_id = self.settings.get('google_keep.project_id', '')
        credentials_file = self.settings.get('google_keep.credentials_file', '')
        
        self.enabled_checkbox.setChecked(enabled)
        self.client_id_input.setText(client_id)
        self.client_secret_input.setText(client_secret)
        self.project_id_input.setText(project_id)
        self.credentials_file_input.setText(credentials_file)
        
        # Обновляем состояние кнопки теста после загрузки настроек
        self._update_test_button_state()
    
    def test_connection(self):
        """Тестирует соединение с Google Keep через OAuth 2.0."""
        # Сначала сохраняем текущие настройки (чтобы credentials были доступны)
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()
        project_id = self.project_id_input.text().strip()
        credentials_file = self.credentials_file_input.text().strip()
        
        # Временно сохраняем в settings для теста
        self.settings.set('google_keep.client_id', client_id)
        self.settings.set('google_keep.client_secret', client_secret)
        self.settings.set('google_keep.project_id', project_id)
        self.settings.set('google_keep.credentials_file', credentials_file)
        
        # Блокируем кнопку во время теста
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Проверка...")
        
        try:
            from services.google_keep_sync import GoogleKeepSync
            from storage.database import DatabaseManager
            
            # Создаем временный экземпляр для теста с обновленными настройками
            db_manager = DatabaseManager()
            sync = GoogleKeepSync(db_manager, settings=self.settings, parent_widget=self)
            
            # Показываем сообщение о том, что откроется браузер
            QMessageBox.information(
                self, 
                "Авторизация", 
                "Сейчас откроется браузер для авторизации в Google.\n\n"
                "Разрешите доступ к Google Keep и дождитесь завершения."
            )
            
            if sync.authenticate(parent_widget=self):
                QMessageBox.information(
                    self, 
                    "Успех", 
                    "Соединение с Google Keep установлено успешно!\n\n"
                    "Токен сохранен локально для будущих использований."
                )
            else:
                QMessageBox.critical(
                    self, 
                    "Ошибка", 
                    "Не удалось подключиться к Google Keep.\n\n"
                    "Убедитесь, что:\n"
                    "1. Вы разрешили доступ к Google Keep в браузере\n"
                    "2. У вас есть доступ к интернету\n"
                    "3. Проверьте логи приложения для деталей"
                )
        except ImportError as e:
            QMessageBox.critical(
                self, 
                "Ошибка", 
                f"Не установлены необходимые библиотеки.\n\n"
                f"Установите: pip install google-auth google-auth-oauthlib google-auth-httplib2\n\n"
                f"Ошибка: {e}"
            )
        except Exception as e:
            logger.error(f"Ошибка при тестировании соединения: {e}", exc_info=True)
            error_msg = str(e)
            # Улучшаем сообщение об ошибке для отсутствующих credentials
            if "credentials" in error_msg.lower() or "client_id" in error_msg.lower():
                error_msg = (
                    f"{error_msg}\n\n"
                    "Убедитесь, что вы ввели:\n"
                    "1. Client ID и Client Secret ИЛИ\n"
                    "2. Путь к файлу credentials.json"
                )
            QMessageBox.critical(
                self, 
                "Ошибка", 
                f"Ошибка подключения:\n{error_msg}\n\n"
                "Проверьте логи приложения для деталей."
            )
        finally:
            # Восстанавливаем кнопку
            self.test_btn.setText("Тест соединения")
            self._update_test_button_state()
    
    def accept(self):
        """Сохраняет настройки и закрывает диалог."""
        enabled = self.enabled_checkbox.isChecked()
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()
        project_id = self.project_id_input.text().strip()
        credentials_file = self.credentials_file_input.text().strip()
        
        # Сохраняем настройки
        self.settings.set('google_keep.enabled', enabled)
        self.settings.set('google_keep.client_id', client_id)
        self.settings.set('google_keep.client_secret', client_secret)
        self.settings.set('google_keep.project_id', project_id)
        self.settings.set('google_keep.credentials_file', credentials_file)
        
        super().accept()
    
    def get_enabled(self) -> bool:
        """Возвращает, включена ли синхронизация."""
        return self.enabled_checkbox.isChecked()
    

