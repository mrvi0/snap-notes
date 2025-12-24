"""
Кастомный QTextEdit с поддержкой иконок ссылок.
"""
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import (
    QTextCursor, QPainter, QPixmap, QMouseEvent, QPen
)
from PyQt6.QtCore import Qt, QUrl, QRect
from PyQt6.QtGui import QColor, QDesktopServices


class LinkIconTextEdit(QTextEdit):
    """QTextEdit с поддержкой иконок ссылок, которые не копируются."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.link_icons = {}  # {link_url: icon_rect}
        self.icon_size = 16
        self.icon_padding = 4
        self._is_visual_mode = False  # По умолчанию Raw режим
        
        # Создаем иконку для ссылки (стрелка в новую вкладку)
        self.link_icon = self._create_link_icon()
    
    def _create_link_icon(self) -> QPixmap:
        """Создает иконку для ссылки (открыть в новой вкладке)."""
        pixmap = QPixmap(self.icon_size, self.icon_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Рисуем иконку "открыть в новой вкладке" (квадрат со стрелкой)
        # Используем синий цвет для ссылок
        link_color = QColor("#2196F3")
        painter.setPen(link_color)
        painter.setBrush(link_color)
        
        # Рисуем квадрат
        square_size = self.icon_size - 4
        painter.drawRect(2, 2, square_size, square_size)
        
        # Рисуем стрелку (диагональ из левого нижнего в правый верхний угол)
        white_pen = QPen(QColor("white"), 2)
        painter.setPen(white_pen)
        painter.setBrush(QColor("white"))
        # Стрелка: линия от (4, icon_size-4) до (icon_size-4, 4)
        painter.drawLine(4, self.icon_size - 4, self.icon_size - 4, 4)
        # Наконечник стрелки вверх
        painter.drawLine(self.icon_size - 4, 4, self.icon_size - 6, 4)
        painter.drawLine(self.icon_size - 4, 4, self.icon_size - 4, 6)
        
        painter.end()
        return pixmap
    
    def paintEvent(self, event):
        """Переопределяем отрисовку для добавления иконок ссылок."""
        super().paintEvent(event)
        
        # Отрисовываем иконки только в Visual режиме
        if not self._is_visual_mode:
            return
        
        painter = QPainter(self.viewport())
        self.link_icons.clear()
        
        # Находим все ссылки в документе
        document = self.document()
        cursor = QTextCursor(document)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        
        # Проходим по всему документу и ищем ссылки
        processed_positions = set()
        while not cursor.atEnd():
            char_format = cursor.charFormat()
            anchor = char_format.anchorHref()
            
            if anchor and cursor.position() not in processed_positions:
                # Нашли ссылку, получаем её границы
                start_pos = cursor.position()
                # Ищем конец ссылки (пока формат не изменится)
                end_cursor = QTextCursor(cursor)
                while not end_cursor.atEnd():
                    pos = end_cursor.position()
                    if pos in processed_positions:
                        break
                    end_char_format = end_cursor.charFormat()
                    if end_char_format.anchorHref() != anchor:
                        break
                    processed_positions.add(pos)
                    end_cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
                
                end_pos = end_cursor.position()
                
                # Получаем прямоугольник для конца ссылки
                end_cursor.setPosition(end_pos)
                rect = self.cursorRect(end_cursor)
                
                # Позиция иконки справа от ссылки
                icon_x = rect.right() + self.icon_padding
                icon_y = rect.top() + (rect.height() - self.icon_size) // 2
                icon_rect = QRect(icon_x, icon_y, self.icon_size, self.icon_size)
                
                # Сохраняем позицию иконки для обработки кликов
                self.link_icons[anchor] = icon_rect
                
                # Рисуем иконку
                painter.drawPixmap(icon_rect, self.link_icon)
                
                # Переходим к следующей позиции после ссылки
                cursor.setPosition(end_pos)
            else:
                processed_positions.add(cursor.position())
                cursor.movePosition(QTextCursor.MoveOperation.NextCharacter)
        
        painter.end()
    
    def mousePressEvent(self, event: QMouseEvent):
        """Обрабатывает клики по иконкам ссылок."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.pos()
            # Проверяем, кликнули ли по иконке
            for url, icon_rect in self.link_icons.items():
                if icon_rect.contains(pos):
                    QDesktopServices.openUrl(QUrl(url))
                    return
        
        super().mousePressEvent(event)
    
    def set_visual_mode(self, is_visual: bool):
        """Устанавливает режим отображения (Visual или Raw)."""
        self._is_visual_mode = is_visual
        if is_visual:
            self.update()  # Перерисовываем для показа иконок

