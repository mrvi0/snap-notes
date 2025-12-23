"""
Диалог настроек синхронизации с Google Keep.
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QFormLayout, QMessageBox, QTextEdit
)

logger = logging.getLogger(__name__)


class SyncSettingsDialog(QDialog):
    """Диалог настроек синхронизации."""
    
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.keep_sync = None
        self.init_ui()
    
    def init_ui(self):
        """Инициализирует интерфейс диалога."""
        self.setWindowTitle("Настройки синхронизации")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Информация
        info_label = QLabel(
            "Для синхронизации с Google Keep необходимо:\n"
            "1. Войти в аккаунт Google\n"
            "2. Создать токен приложения (рекомендуется) или использовать пароль\n"
            "3. Настроить синхронизацию"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Настройки Google Keep
        keep_group = QGroupBox("Google Keep")
        keep_layout = QFormLayout()
        
        self.keep_email_input = QLineEdit()
        self.keep_email_input.setPlaceholderText("email@gmail.com")
        keep_layout.addRow("Email:", self.keep_email_input)
        
        self.keep_password_input = QLineEdit()
        self.keep_password_input.setPlaceholderText("Пароль или токен приложения")
        self.keep_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        keep_layout.addRow("Пароль/Токен:", self.keep_password_input)
        
        self.keep_test_btn = QPushButton("Проверить подключение")
        self.keep_test_btn.clicked.connect(self.test_connection)
        keep_layout.addRow("", self.keep_test_btn)
        
        keep_group.setLayout(keep_layout)
        layout.addWidget(keep_group)
        
        # Кнопка синхронизации
        self.sync_btn = QPushButton("Синхронизировать с Google Keep")
        self.sync_btn.clicked.connect(self.sync_both)
        layout.addWidget(self.sync_btn)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def test_connection(self):
        """Проверяет подключение к Google Keep."""
        email = self.keep_email_input.text().strip()
        password = self.keep_password_input.text().strip()
        
        if not email or not password:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.NoIcon)
            msg_box.setWindowTitle("Предупреждение")
            msg_box.setText("Введите email и пароль")
            msg_box.exec()
            return
        
        try:
            from google_keep_sync import GoogleKeepSync
            from database import DatabaseManager
            
            if not self.db_manager:
                self.db_manager = DatabaseManager()
            self.keep_sync = GoogleKeepSync(self.db_manager)
            success = self.keep_sync.login(email, password)
            
            if success:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.NoIcon)
                msg_box.setWindowTitle("Успех")
                msg_box.setText("Подключение к Google Keep успешно!")
                msg_box.exec()
            else:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.NoIcon)
                msg_box.setWindowTitle("Ошибка")
                msg_box.setText("Не удалось подключиться к Google Keep")
                msg_box.exec()
        except Exception as e:
            logger.error(f"Ошибка при проверке подключения: {e}")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.NoIcon)
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText(f"Ошибка: {str(e)}")
            msg_box.exec()
    
    def sync_from_keep(self):
        """Синхронизирует заметки из Google Keep."""
        if not self.keep_sync or not self.keep_sync.authenticated:
            self.test_connection()
            if not self.keep_sync or not self.keep_sync.authenticated:
                return
        
        try:
            success, conflicts = self.keep_sync.sync_from_keep()
            if success:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.NoIcon)
                msg_box.setWindowTitle("Успех")
                msg_box.setText("Синхронизация из Google Keep завершена")
                msg_box.exec()
                if conflicts:
                    msg_box = QMessageBox(self)
                    msg_box.setIcon(QMessageBox.Icon.NoIcon)
                    msg_box.setWindowTitle("Конфликты")
                    msg_box.setText(f"Обнаружено конфликтов: {len(conflicts)}")
                    msg_box.exec()
            else:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.NoIcon)
                msg_box.setWindowTitle("Ошибка")
                msg_box.setText("Ошибка при синхронизации")
                msg_box.exec()
        except Exception as e:
            logger.error(f"Ошибка при синхронизации: {e}")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.NoIcon)
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText(f"Ошибка: {str(e)}")
            msg_box.exec()
    
    def sync_to_keep(self):
        """Синхронизирует заметки в Google Keep."""
        if not self.keep_sync or not self.keep_sync.authenticated:
            self.test_connection()
            if not self.keep_sync or not self.keep_sync.authenticated:
                return
        
        try:
            success = self.keep_sync.sync_to_keep()
            if success:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.NoIcon)
                msg_box.setWindowTitle("Успех")
                msg_box.setText("Синхронизация в Google Keep завершена")
                msg_box.exec()
            else:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.NoIcon)
                msg_box.setWindowTitle("Ошибка")
                msg_box.setText("Ошибка при синхронизации")
                msg_box.exec()
        except Exception as e:
            logger.error(f"Ошибка при синхронизации: {e}")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.NoIcon)
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText(f"Ошибка: {str(e)}")
            msg_box.exec()
    
    def sync_both(self):
        """Двусторонняя синхронизация."""
        if not self.keep_sync or not self.keep_sync.authenticated:
            self.test_connection()
            if not self.keep_sync or not self.keep_sync.authenticated:
                return
        
        try:
            # Синхронизируем из Keep
            success_from, conflicts = self.keep_sync.sync_from_keep()
            if not success_from:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.NoIcon)
                msg_box.setWindowTitle("Ошибка")
                msg_box.setText("Ошибка при синхронизации из Google Keep")
                msg_box.exec()
                return
            
            # Синхронизируем в Keep
            success_to = self.keep_sync.sync_to_keep()
            if not success_to:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.Icon.NoIcon)
                msg_box.setWindowTitle("Ошибка")
                msg_box.setText("Ошибка при синхронизации в Google Keep")
                msg_box.exec()
                return
            
            # Уведомляем об успехе
            conflict_msg = f"\nОбнаружено конфликтов: {len(conflicts)}" if conflicts else ""
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.NoIcon)
            msg_box.setWindowTitle("Успех")
            msg_box.setText(f"Синхронизация завершена успешно!{conflict_msg}")
            msg_box.exec()
            
            # Закрываем диалог
            self.accept()
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации: {e}")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.NoIcon)
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText(f"Ошибка: {str(e)}")
            msg_box.exec()

