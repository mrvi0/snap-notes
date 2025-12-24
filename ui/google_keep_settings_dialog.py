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
            "Синхронизация использует OAuth 2.0 для безопасной авторизации.\n"
            "При первом подключении откроется браузер для авторизации.\n"
            "Токен будет сохранен локально для последующих использований."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 10pt; color: #666; padding: 10px;")
        keep_layout.addRow(info_label)
        
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
    
    def _update_test_button_state(self):
        """Обновляет состояние кнопки теста соединения."""
        # Кнопка активна, если синхронизация включена
        self.test_btn.setEnabled(self.enabled_checkbox.isChecked())
    
    def on_enabled_changed(self, enabled: bool):
        """Обрабатывает изменение состояния чекбокса включения."""
        # Поля ввода всегда активны, только кнопка теста зависит от включения
        self._update_test_button_state()
    
    def load_settings(self):
        """Загружает настройки из объекта Settings."""
        enabled = self.settings.get('google_keep.enabled', False)
        
        self.enabled_checkbox.setChecked(enabled)
        
        # Обновляем состояние полей
        self.on_enabled_changed(enabled)
    
    def test_connection(self):
        """Тестирует соединение с Google Keep через OAuth 2.0."""
        # Блокируем кнопку во время теста
        self.test_btn.setEnabled(False)
        self.test_btn.setText("Проверка...")
        
        try:
            from services.google_keep_sync import GoogleKeepSync
            from storage.database import DatabaseManager
            
            # Создаем временный экземпляр для теста
            db_manager = DatabaseManager()
            sync = GoogleKeepSync(db_manager, parent_widget=self)
            
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
            QMessageBox.critical(
                self, 
                "Ошибка", 
                f"Ошибка подключения:\n{str(e)}\n\n"
                "Проверьте логи приложения для деталей."
            )
        finally:
            # Восстанавливаем кнопку
            self.test_btn.setText("Тест соединения")
            self._update_test_button_state()
    
    def accept(self):
        """Сохраняет настройки и закрывает диалог."""
        enabled = self.enabled_checkbox.isChecked()
        
        # Сохраняем настройки
        self.settings.set('google_keep.enabled', enabled)
        
        super().accept()
    
    def get_enabled(self) -> bool:
        """Возвращает, включена ли синхронизация."""
        return self.enabled_checkbox.isChecked()
    

