"""
Модуль для управления темами приложения.
"""
from typing import Dict

# Светлая тема (в стиле macOS Notes)
LIGHT_THEME = """
QMainWindow {
    background-color: #f5f5f5;
}
QWidget {
    background-color: #f5f5f5;
    color: #212121;
}
QWidget#left_panel {
    background-color: #f5f5f5;
}
QWidget#right_panel {
    background-color: white;
}
QWidget#top_bar {
    background-color: white;
    border-bottom: 1px solid #e0e0e0;
}
QPushButton {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 8px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #45a049;
}
QPushButton:pressed {
    background-color: #3d8b40;
}
QPushButton#icon_button {
    background-color: transparent;
    border: none;
    padding: 4px;
    border-radius: 6px;
    font-size: 14pt;
}
QPushButton#icon_button:hover {
    background-color: rgba(0, 0, 0, 0.05);
}
QPushButton#icon_button:pressed {
    background-color: rgba(0, 0, 0, 0.1);
}
QPushButton#delete_button {
    background-color: #f44336;
    color: white;
    border: none;
    border-radius: 14px;
    font-size: 18pt;
    font-weight: bold;
    padding: 0px;
}
QPushButton#delete_button:hover {
    background-color: #d32f2f;
}
QPushButton#delete_button:pressed {
    background-color: #b71c1c;
}
QPushButton#format_button {
    background-color: transparent;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px;
    font-size: 11pt;
}
QPushButton#format_button:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: #777;
}
QPushButton#format_button:pressed {
    background-color: rgba(255, 255, 255, 0.15);
}
QWidget#format_toolbar {
    background-color: #1e1e1e;
    border-bottom: 1px solid #2a2a2a;
}
QListWidget {
    background-color: #f5f5f5;
    border: none;
    border-radius: 0px;
    color: #212121;
    outline: none;
}
QScrollBar:vertical {
    background-color: transparent;
    width: 12px;
    border: none;
    border-radius: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #999999;
    min-height: 30px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #777777;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background-color: transparent;
}
QScrollBar:horizontal {
    background-color: transparent;
    height: 12px;
    border: none;
    border-radius: 6px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #999999;
    min-width: 30px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #777777;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background-color: transparent;
}
QListWidget::item {
    padding: 0px;
    border-bottom: 1px solid #e8e8e8;
    background-color: transparent;
    min-height: 60px;
    border-left: 3px solid transparent;
}
QListWidget::item:hover {
    background-color: #f8f8f8;
}
QListWidget::item:selected {
    background-color: #f0f0f0;
    color: #212121;
    border-left: 3px solid {button_color};
    font-weight: 500;
}
QListWidget::item QWidget {
    background-color: transparent;
}
QListWidget::item {
    color: #212121;
}
QLineEdit, QTextEdit {
    background-color: white;
    border: none;
    border-radius: 0px;
    padding: 15px;
    color: #212121;
    font-size: 14pt;
}
QLineEdit {
    font-size: 20pt;
    font-weight: 500;
    padding: 20px 30px;
}
QTextEdit {
    font-size: 14pt;
    line-height: 1.6;
    padding: 20px 30px;
}
QLabel {
    color: #212121;
}
QLabel#info_label {
    color: #999;
    font-size: 9pt;
    padding: 5px;
}
QLineEdit#search_input {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 8px 12px;
    background-color: white;
    font-size: 12pt;
}
QMenuBar {
    background-color: #f5f5f5;
    color: #212121;
}
QMenuBar::item {
    background-color: transparent;
    padding: 4px 8px;
}
QMenuBar::item:selected {
    background-color: #e0e0e0;
}
QMenu {
    background-color: white;
    color: #212121;
    border: 1px solid #ddd;
}
QMenu::item:selected {
    background-color: #e3f2fd;
}
"""

# Темная тема
DARK_THEME = """
QMainWindow {
    background-color: #121212;
}
QWidget {
    background-color: #121212;
    color: #e0e0e0;
}
QWidget#left_panel {
    background-color: #121212;
}
QWidget#right_panel {
    background-color: #1e1e1e;
}
QWidget#top_bar {
    background-color: #1e1e1e;
    border-bottom: 1px solid #2a2a2a;
}
QPushButton {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 8px;
    border-radius: 4px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #45a049;
}
QPushButton:pressed {
    background-color: #3d8b40;
}
QPushButton#icon_button {
    background-color: transparent;
    border: none;
    padding: 4px;
    border-radius: 6px;
    font-size: 16pt;
}
QPushButton#icon_button:hover {
    background-color: rgba(255, 255, 255, 0.1);
}
QPushButton#icon_button:pressed {
    background-color: rgba(255, 255, 255, 0.15);
}
QPushButton#delete_button {
    background-color: #f44336;
    color: white;
    border: none;
    border-radius: 14px;
    font-size: 18pt;
    font-weight: bold;
    padding: 0px;
}
QPushButton#delete_button:hover {
    background-color: #d32f2f;
}
QPushButton#delete_button:pressed {
    background-color: #b71c1c;
}
QPushButton#format_button {
    background-color: transparent;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 4px;
    font-size: 11pt;
}
QPushButton#format_button:hover {
    background-color: rgba(255, 255, 255, 0.1);
    border-color: #777;
}
QPushButton#format_button:pressed {
    background-color: rgba(255, 255, 255, 0.15);
}
QWidget#format_toolbar {
    background-color: #1e1e1e;
    border-bottom: 1px solid #2a2a2a;
}
QListWidget {
    background-color: #1e1e1e;
    border: none;
    border-radius: 0px;
    color: #e0e0e0;
    outline: none;
}
QScrollBar:vertical {
    background-color: transparent;
    width: 12px;
    border: none;
    border-radius: 6px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #666666;
    min-height: 30px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical:hover {
    background-color: #888888;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background-color: transparent;
}
QScrollBar:horizontal {
    background-color: transparent;
    height: 12px;
    border: none;
    border-radius: 6px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #666666;
    min-width: 30px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #888888;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    background-color: transparent;
}
QListWidget::item {
    padding: 0px;
    border-bottom: 1px solid #2a2a2a;
    background-color: transparent;
    min-height: 60px;
    border-left: 3px solid transparent;
}
QListWidget::item:hover {
    background-color: #252525;
}
QListWidget::item:selected {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border-left: 3px solid {button_color};
    font-weight: 500;
}
QListWidget::item QWidget {
    background-color: transparent;
}
QLineEdit, QTextEdit {
    background-color: #1e1e1e;
    border: none;
    border-radius: 0px;
    padding: 15px;
    color: #e0e0e0;
    font-size: 14pt;
}
QLineEdit {
    font-size: 20pt;
    font-weight: 500;
    padding: 20px 30px;
}
QTextEdit {
    font-size: 14pt;
    line-height: 1.6;
    padding: 20px 30px;
}
QLabel {
    color: #e0e0e0;
}
QLabel#info_label {
    color: #888;
    font-size: 9pt;
    padding: 5px;
}
QLineEdit#search_input {
    border: 1px solid #444;
    border-radius: 8px;
    padding: 8px 12px;
    background-color: #2a2a2a;
    font-size: 12pt;
}
QMenuBar {
    background-color: #121212;
    color: #e0e0e0;
}
QMenuBar::item {
    background-color: transparent;
    padding: 4px 8px;
}
QMenuBar::item:selected {
    background-color: #2d2d2d;
}
QMenu {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #333;
}
QMenu::item:selected {
    background-color: #2d4a5e;
}
"""


def get_theme(theme_name: str, button_color: str = "#4CAF50") -> str:
    """
    Получает стиль темы.
    
    Args:
        theme_name: Название темы ("light", "dark", "system")
        button_color: Цвет кнопок в формате HEX
        
    Returns:
        Строка со стилями CSS
    """
    # Вычисляем более темный оттенок для hover
    def darken_color(hex_color: str, factor: float = 0.9) -> str:
        """Затемняет цвет."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    hover_color = darken_color(button_color, 0.9)
    pressed_color = darken_color(button_color, 0.8)
    
    button_style = f"""
QPushButton {{
    background-color: {button_color};
    color: white;
    border: none;
    padding: 8px;
    border-radius: 4px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {hover_color};
}}
QPushButton:pressed {{
    background-color: {pressed_color};
}}
"""
    
    # Выбираем базовую тему
    if theme_name == "dark":
        base_theme = DARK_THEME
    elif theme_name == "light":
        base_theme = LIGHT_THEME
    else:  # system или по умолчанию
        base_theme = LIGHT_THEME
    
    # Заменяем стили кнопок (ищем блок QPushButton и заменяем его)
    import re
    # Удаляем старые стили QPushButton (но не QPushButton#icon_button)
    pattern = r'QPushButton \{[^}]*background-color:[^}]*\}'
    base_theme = re.sub(pattern, '', base_theme, flags=re.DOTALL)
    
    # Удаляем старые стили hover и pressed для QPushButton
    pattern = r'QPushButton:hover \{[^}]*\}'
    base_theme = re.sub(pattern, '', base_theme, flags=re.DOTALL)
    pattern = r'QPushButton:pressed \{[^}]*\}'
    base_theme = re.sub(pattern, '', base_theme, flags=re.DOTALL)
    
    # Вставляем новые стили кнопок перед QPushButton#icon_button
    if 'QPushButton#icon_button' in base_theme:
        base_theme = base_theme.replace('QPushButton#icon_button', button_style + 'QPushButton#icon_button')
    else:
        base_theme = button_style + base_theme
    
    # Заменяем {button_color} в стилях (для границы выбранной заметки)
    base_theme = base_theme.replace('{button_color}', button_color)
    
    return base_theme

