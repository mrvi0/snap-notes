"""
Диалог для разрешения конфликтов при синхронизации.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox
)

from models import Note


class ConflictDialog(QDialog):
    """Диалог для разрешения конфликтов при синхронизации."""
    
    def __init__(self, local_note: Note, remote_note: Note, parent=None):
        super().__init__(parent)
        self.local_note = local_note
        self.remote_note = remote_note
        self.action = None
        self.init_ui()
    
    def init_ui(self):
        """Инициализирует интерфейс диалога."""
        self.setWindowTitle("Разрешение конфликта")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        # Информация о конфликте
        info_label = QLabel(
            f"Обнаружен конфликт для заметки '{self.local_note.title}':\n"
            f"Локальная версия изменена: {self.local_note.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"Удаленная версия изменена: {self.remote_note.updated_at.strftime('%Y-%m-%d %H:%M')}"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Кнопки
        button_box = QDialogButtonBox()
        replace_btn = button_box.addButton("Заменить локальную", QDialogButtonBox.ButtonRole.AcceptRole)
        keep_btn = button_box.addButton("Сохранить локально", QDialogButtonBox.ButtonRole.RejectRole)
        cancel_btn = button_box.addButton("Отмена", QDialogButtonBox.ButtonRole.DestructiveRole)
        
        replace_btn.clicked.connect(lambda: self.set_action("replace"))
        keep_btn.clicked.connect(lambda: self.set_action("keep"))
        cancel_btn.clicked.connect(self.reject)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def set_action(self, action: str):
        """Устанавливает выбранное действие и закрывает диалог."""
        self.action = action
        self.accept()

