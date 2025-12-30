"""
Диалог настроек синхронизации с Google Keep.
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFormLayout, QMessageBox, QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer

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
        
        # Информация о Master Token
        info_label = QLabel(
            "Google Keep API недоступен через OAuth 2.0 для личных аккаунтов.\n"
            "Используется Master Token для доступа к неофициальному API Google Keep.\n\n"
            "Вариант 1 - Master Token (рекомендуется):\n"
            "Введите Master Token напрямую (получите через gkeepapi CLI или другой способ).\n\n"
            "Вариант 2 - Email + App Password:\n"
            "Введите email и App Password (16-символьный токен приложения).\n"
            "Приложение автоматически получит Master Token при первом подключении.\n\n"
            "См. README.md для подробных инструкций."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 10pt; color: #666; padding: 10px;")
        keep_layout.addRow(info_label)
        
        # Master Token (приоритетный способ)
        master_token_label = QLabel("Master Token:")
        master_token_label.setStyleSheet("font-size: 11pt;")
        self.master_token_input = QLineEdit()
        self.master_token_input.setPlaceholderText("Вставьте Master Token здесь")
        self.master_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.master_token_input.setFixedWidth(350)
        self.master_token_input.setFixedHeight(28)
        self.master_token_input.setStyleSheet("font-size: 10pt;")
        self.master_token_input.setToolTip(
            "Master Token для доступа к Google Keep.\n"
            "Получите через: gkeepapi -e <email> -p <app_password> gettoken\n"
            "Или оставьте пустым и используйте Email + App Password ниже."
        )
        keep_layout.addRow(master_token_label, self.master_token_input)
        
        # Разделитель
        separator_label = QLabel("─ или ─")
        separator_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        separator_label.setStyleSheet("font-size: 10pt; color: #999; padding: 10px 0;")
        keep_layout.addRow(separator_label)
        
        # Email
        email_label = QLabel("Email:")
        email_label.setStyleSheet("font-size: 11pt;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your.email@gmail.com")
        self.email_input.setFixedWidth(350)
        self.email_input.setFixedHeight(28)
        self.email_input.setStyleSheet("font-size: 10pt;")
        keep_layout.addRow(email_label, self.email_input)
        
        # App Password
        app_password_label = QLabel("App Password:")
        app_password_label.setStyleSheet("font-size: 11pt;")
        self.app_password_input = QLineEdit()
        self.app_password_input.setPlaceholderText("16-символьный токен приложения")
        self.app_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.app_password_input.setFixedWidth(350)
        self.app_password_input.setFixedHeight(28)
        self.app_password_input.setStyleSheet("font-size: 10pt;")
        self.app_password_input.setToolTip(
            "Токен приложения (App Password) из Google Account.\n"
            "1. Включите двухфакторную аутентификацию\n"
            "2. Перейдите: https://myaccount.google.com/apppasswords\n"
            "3. Создайте токен для 'Mail' или 'Other'\n"
            "4. Используйте 16-символьный токен (без пробелов)"
        )
        keep_layout.addRow(app_password_label, self.app_password_input)
        
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
        self.master_token_input.textChanged.connect(self._update_test_button_state)
        self.email_input.textChanged.connect(self._on_credentials_changed)
        self.app_password_input.textChanged.connect(self._on_credentials_changed)
        
        # Флаг для предотвращения рекурсии при программной вставке токена
        self._is_auto_filling_token = False
    
    def _update_test_button_state(self):
        """Обновляет состояние кнопки теста соединения."""
        # Кнопка активна, если есть Master Token ИЛИ (Email + App Password)
        has_credentials = bool(
            self.master_token_input.text().strip() or
            (self.email_input.text().strip() and self.app_password_input.text().strip())
        )
        self.test_btn.setEnabled(has_credentials)
    
    def on_enabled_changed(self, enabled: bool):
        """Обрабатывает изменение состояния чекбокса включения."""
        # Кнопка теста не зависит от чекбокса, только от наличия credentials
        pass
    
    def _get_master_token_async(self):
        """Асинхронно получает Master Token через gkeepapi."""
        # Проверяем еще раз, что поля заполнены и токен еще не получен
        if self.master_token_input.text().strip():
            return
        
        email = self.email_input.text().strip()
        app_password = self.app_password_input.text().strip()
        
        if not email or not app_password:
            return
        
        # Показываем индикатор загрузки
        self.master_token_input.setPlaceholderText("Получение Master Token...")
        self.master_token_input.setEnabled(False)
        self.email_input.setEnabled(False)
        self.app_password_input.setEnabled(False)
        
        try:
            from services.google_keep_auth import GoogleKeepAuth
            
            # Создаем временный экземпляр для получения токена
            auth = GoogleKeepAuth(email=email, app_password=app_password)
            
            # Пытаемся получить токен
            master_token = auth._get_master_token_from_credentials()
            
            if master_token:
                # Вставляем токен в поле
                self._is_auto_filling_token = True
                self.master_token_input.setText(master_token)
                self.master_token_input.setPlaceholderText("Вставьте Master Token здесь")
                self._is_auto_filling_token = False
                
                # Показываем сообщение об успехе
                QMessageBox.information(
                    self,
                    "Успех",
                    "Master Token успешно получен и вставлен в форму!"
                )
            else:
                raise ValueError("Не удалось получить Master Token")
                
        except ImportError:
            # gkeepapi не установлен
            self.master_token_input.setPlaceholderText("Установите gkeepapi: pip install gkeepapi")
            QMessageBox.warning(
                self,
                "gkeepapi не установлен",
                "Для автоматического получения Master Token требуется gkeepapi.\n\n"
                "Установите: pip install gkeepapi\n\n"
                "Или получите Master Token вручную:\n"
                "gkeepapi -e <email> -p <app_password> gettoken"
            )
        except Exception as e:
            logger.error(f"Ошибка при получении Master Token: {e}", exc_info=True)
            self.master_token_input.setPlaceholderText("Ошибка получения токена. Введите вручную.")
            QMessageBox.warning(
                self,
                "Ошибка",
                f"Не удалось получить Master Token автоматически:\n{str(e)}\n\n"
                "Попробуйте получить токен вручную:\n"
                "gkeepapi -e <email> -p <app_password> gettoken"
            )
        finally:
            # Восстанавливаем поля
            self.master_token_input.setEnabled(True)
            self.email_input.setEnabled(True)
            self.app_password_input.setEnabled(True)
            if not self.master_token_input.text().strip():
                self.master_token_input.setPlaceholderText("Вставьте Master Token здесь")
    
    def load_settings(self):
        """Загружает настройки из объекта Settings."""
        enabled = self.settings.get('google_keep.enabled', False)
        master_token = self.settings.get('google_keep.master_token', '')
        email = self.settings.get('google_keep.email', '')
        app_password = self.settings.get('google_keep.app_password', '')
        
        self.enabled_checkbox.setChecked(enabled)
        self.master_token_input.setText(master_token)
        self.email_input.setText(email)
        self.app_password_input.setText(app_password)
        
        # Обновляем состояние кнопки теста после загрузки настроек
        self._update_test_button_state()
    
    def test_connection(self):
        """Тестирует соединение с Google Keep через Master Token."""
        # Сначала сохраняем текущие настройки (чтобы credentials были доступны)
        master_token = self.master_token_input.text().strip()
        email = self.email_input.text().strip()
        app_password = self.app_password_input.text().strip()
        
        # Временно сохраняем в settings для теста
        self.settings.set('google_keep.master_token', master_token)
        self.settings.set('google_keep.email', email)
        self.settings.set('google_keep.app_password', app_password)
        
        # Блокируем кнопку во время теста
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Проверка...")
        
        try:
            from services.google_keep_sync import GoogleKeepSync
            from storage.database import DatabaseManager
            
            # Создаем временный экземпляр для теста с обновленными настройками
            db_manager = DatabaseManager()
            sync = GoogleKeepSync(db_manager, settings=self.settings, parent_widget=self)
            
            if sync.authenticate(parent_widget=self):
                QMessageBox.information(
                    self, 
                    "Успех", 
                    "Соединение с Google Keep установлено успешно!\n\n"
                    "Master Token сохранен локально для будущих использований."
                )
            else:
                QMessageBox.critical(
                    self, 
                    "Ошибка", 
                    "Не удалось подключиться к Google Keep.\n\n"
                    "Убедитесь, что:\n"
                    "1. Master Token корректен (если используете)\n"
                    "2. Email и App Password правильные (если используете)\n"
                    "3. У вас есть доступ к интернету\n"
                    "4. Проверьте логи приложения для деталей"
                )
        except ImportError as e:
            QMessageBox.critical(
                self, 
                "Ошибка", 
                f"Не установлены необходимые библиотеки.\n\n"
                f"Установите: pip install requests\n\n"
                f"Ошибка: {e}"
            )
        except Exception as e:
            logger.error(f"Ошибка при тестировании соединения: {e}", exc_info=True)
            error_msg = str(e)
            
            # Улучшаем сообщение об ошибке
            if "gkeepapi" in error_msg.lower() or "import" in error_msg.lower():
                # Ошибка импорта gkeepapi
                error_msg = (
                    f"{error_msg}\n\n"
                    "Для получения Master Token через email/app_password требуется gkeepapi.\n\n"
                    "Установите: pip install gkeepapi\n\n"
                    "Или получите Master Token вручную и вставьте его в поле 'Master Token'."
                )
            elif "token" in error_msg.lower() or "credentials" in error_msg.lower() or "authentication" in error_msg.lower():
                # Ошибка аутентификации
                error_msg = (
                    f"{error_msg}\n\n"
                    "Убедитесь, что вы ввели:\n"
                    "1. Master Token (рекомендуется) ИЛИ\n"
                    "2. Email и App Password (16-символьный токен приложения)\n\n"
                    "Для получения Master Token:\n"
                    "gkeepapi -e <email> -p <app_password> gettoken"
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
        master_token = self.master_token_input.text().strip()
        email = self.email_input.text().strip()
        app_password = self.app_password_input.text().strip()
        
        # Сохраняем настройки
        self.settings.set('google_keep.enabled', enabled)
        self.settings.set('google_keep.master_token', master_token)
        self.settings.set('google_keep.email', email)
        self.settings.set('google_keep.app_password', app_password)
        
        super().accept()
    
    def get_enabled(self) -> bool:
        """Возвращает, включена ли синхронизация."""
        return self.enabled_checkbox.isChecked()
    

