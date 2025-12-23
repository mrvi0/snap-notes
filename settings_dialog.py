"""
Диалог настроек приложения.
"""
import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QMessageBox,
    QGridLayout, QSpinBox
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from settings import Settings
from themes import get_theme

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Диалог настроек приложения."""
    
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Инициализирует интерфейс диалога."""
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Настройки темы
        theme_group = QGroupBox("Внешний вид")
        theme_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Светлая", "Темная", "Системная"])
        theme_layout.addRow("Тема:", self.theme_combo)
        
        # Выбор цвета кнопок
        color_label = QLabel("Цвет кнопок:")
        theme_layout.addRow(color_label)
        
        # Палитра цветов
        self.color_buttons = []
        color_palette_layout = QGridLayout()
        
        # Дефолтная палитра цветов
        default_colors = [
            ("#4CAF50", "Зеленый"),
            ("#2196F3", "Синий"),
            ("#FF9800", "Оранжевый"),
            ("#F44336", "Красный"),
            ("#9C27B0", "Фиолетовый"),
            ("#00BCD4", "Голубой"),
            ("#FFC107", "Желтый"),
            ("#795548", "Коричневый"),
            ("#607D8B", "Серо-синий"),
            ("#E91E63", "Розовый"),
        ]
        
        self.selected_color = None
        row = 0
        col = 0
        for color_hex, color_name in default_colors:
            color_btn = QPushButton()
            color_btn.setFixedSize(40, 40)
            color_btn.setStyleSheet(f"background-color: {color_hex}; border: 2px solid #ccc; border-radius: 4px;")
            color_btn.setToolTip(color_name)
            color_btn.clicked.connect(lambda checked, c=color_hex: self.select_color(c))
            color_palette_layout.addWidget(color_btn, row, col)
            self.color_buttons.append((color_btn, color_hex))
            
            col += 1
            if col >= 5:  # 5 цветов в ряд
                col = 0
                row += 1
        
        theme_layout.addRow("", color_palette_layout)
        
        # Размер шрифта
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setMinimum(8)
        self.font_size_spin.setMaximum(24)
        self.font_size_spin.setSuffix(" pt")
        theme_layout.addRow("Размер шрифта:", self.font_size_spin)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addWidget(ok_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def load_settings(self):
        """Загружает настройки в форму."""
        theme = self.settings.get("theme", "system")
        if theme == "light":
            self.theme_combo.setCurrentIndex(0)
        elif theme == "dark":
            self.theme_combo.setCurrentIndex(1)
        else:
            self.theme_combo.setCurrentIndex(2)
        
        # Загружаем цвет кнопок
        button_color = self.settings.get("button_color", "#4CAF50")
        self.select_color(button_color, update_settings=False)
        
        # Загружаем размер шрифта
        font_size = self.settings.get("font_size", 12)
        self.font_size_spin.setValue(font_size)
    
    def select_color(self, color_hex: str, update_settings: bool = True):
        """Выбирает цвет кнопок."""
        self.selected_color = color_hex
        
        # Обновляем визуальное выделение
        for btn, btn_color in self.color_buttons:
            if btn_color == color_hex:
                btn.setStyleSheet(
                    f"background-color: {btn_color}; "
                    f"border: 3px solid #000; "
                    f"border-radius: 4px;"
                )
            else:
                btn.setStyleSheet(
                    f"background-color: {btn_color}; "
                    f"border: 2px solid #ccc; "
                    f"border-radius: 4px;"
                )
        
        if update_settings:
            self.settings.set("button_color", color_hex)
    
    def get_theme(self) -> str:
        """Возвращает выбранную тему."""
        index = self.theme_combo.currentIndex()
        if index == 0:
            return "light"
        elif index == 1:
            return "dark"
        else:
            return "system"
    
    def get_button_color(self) -> str:
        """Возвращает выбранный цвет кнопок."""
        return self.selected_color or self.settings.get("button_color", "#4CAF50")
    
    def get_font_size(self) -> int:
        """Возвращает выбранный размер шрифта."""
        return self.font_size_spin.value()
    
    def accept(self):
        """Сохраняет настройки при нажатии OK."""
        # Сохраняем тему
        theme = self.get_theme()
        self.settings.set("theme", theme)
        
        # Сохраняем цвет кнопок
        button_color = self.get_button_color()
        self.settings.set("button_color", button_color)
        
        # Сохраняем размер шрифта
        font_size = self.get_font_size()
        self.settings.set("font_size", font_size)
        
        super().accept()
