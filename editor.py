"""
Логика редактора Markdown.

Поддерживает два режима:
- Visual Markdown mode: визуальное форматирование через toolbar
- Raw Markdown mode: чистый markdown-текст

Markdown - единственный канонический формат, HTML не используется.
"""
import logging
from typing import Optional
from enum import Enum

from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QFont
from PyQt6.QtCore import Qt

try:
    from QMarkdownTextEdit import QMarkdownTextEdit
    HAS_QMARKDOWN = True
except ImportError:
    # Fallback: PyQt6 QTextEdit имеет встроенную поддержку Markdown
    QMarkdownTextEdit = QTextEdit
    HAS_QMARKDOWN = False
    logging.warning("QMarkdownTextEdit не найден, используется QTextEdit с поддержкой Markdown (PyQt6)")

logger = logging.getLogger(__name__)


class EditorMode(Enum):
    """Режимы работы редактора."""
    VISUAL = "visual"  # Визуальное форматирование
    RAW = "raw"        # Чистый markdown-текст


class MarkdownEditor:
    """
    Класс для управления редактором Markdown.
    
    Обеспечивает работу в двух режимах без изменения содержимого markdown-текста.
    """
    
    def __init__(self, text_edit: QMarkdownTextEdit):
        """
        Инициализация редактора.
        
        Args:
            text_edit: Виджет QMarkdownTextEdit для редактирования
        """
        self.text_edit = text_edit
        self.mode = EditorMode.VISUAL
        self._setup_editor()
    
    def _setup_editor(self) -> None:
        """Настраивает редактор."""
        # Настройки по умолчанию
        self.text_edit.setAcceptRichText(False)  # Только plain text
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
    
    def set_mode(self, mode: EditorMode) -> None:
        """
        Переключает режим редактора.
        
        Args:
            mode: Новый режим (VISUAL или RAW)
        
        Важно: переключение режимов НЕ должно менять содержимое markdown-текста.
        """
        if self.mode == mode:
            return
        
        # Получаем текущий markdown-текст
        current_markdown = self.get_markdown()
        cursor_position = self.text_edit.textCursor().position()
        
        self.mode = mode
        
        if mode == EditorMode.VISUAL:
            # В визуальном режиме рендерим markdown
            # PyQt6 QTextEdit имеет встроенный метод setMarkdown
            self.text_edit.setMarkdown(current_markdown)
        else:
            # В raw режиме показываем чистый markdown-текст
            # Сбрасываем все форматирование, чтобы текст был обычным
            self.text_edit.setPlainText(current_markdown)
            
            # Устанавливаем обычный шрифт для всего текста в RAW режиме
            cursor = self.text_edit.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            char_format = QTextCharFormat()
            char_format.setFontWeight(QFont.Weight.Normal)  # Обычный вес, не жирный
            char_format.setFontItalic(False)  # Не курсив
            cursor.setCharFormat(char_format)
            cursor.clearSelection()
        
        # Восстанавливаем позицию курсора
        cursor = self.text_edit.textCursor()
        cursor.setPosition(min(cursor_position, len(current_markdown)))
        self.text_edit.setTextCursor(cursor)
        
        logger.info(f"Режим редактора изменен на: {mode.value}")
    
    def get_markdown(self) -> str:
        """
        Получает текущий markdown-текст.
        
        Returns:
            Текст в формате Markdown
        """
        if self.mode == EditorMode.RAW:
            return self.text_edit.toPlainText()
        else:
            # В визуальном режиме получаем markdown
            # PyQt6 QTextEdit имеет встроенный метод toMarkdown
            return self.text_edit.toMarkdown()
    
    def set_markdown(self, markdown_text: str) -> None:
        """
        Устанавливает markdown-текст в редактор.
        
        Args:
            markdown_text: Текст в формате Markdown
        """
        if self.mode == EditorMode.VISUAL:
            # PyQt6 QTextEdit имеет встроенный метод setMarkdown
            self.text_edit.setMarkdown(markdown_text)
        else:
            # В RAW режиме устанавливаем как plain text и сбрасываем форматирование
            self.text_edit.setPlainText(markdown_text)
            
            # Устанавливаем обычный шрифт для всего текста
            cursor = self.text_edit.textCursor()
            cursor.select(QTextCursor.SelectionType.Document)
            char_format = QTextCharFormat()
            char_format.setFontWeight(QFont.Weight.Normal)  # Обычный вес, не жирный
            char_format.setFontItalic(False)  # Не курсив
            cursor.setCharFormat(char_format)
            cursor.clearSelection()
    
    def apply_format(self, format_type: str) -> None:
        """
        Применяет форматирование к выделенному тексту.
        
        Args:
            format_type: Тип форматирования:
                - 'bold': жирный (**text**)
                - 'italic': курсив (*text*)
                - 'header1': заголовок H1 (# text)
                - 'header2': заголовок H2 (## text)
                - 'header3': заголовок H3 (### text)
                - 'list': маркированный список (- item)
                - 'quote': цитата (> text)
                - 'code': inline код (`text`)
        """
        cursor = self.text_edit.textCursor()
        
        if not cursor.hasSelection():
            # Если нет выделения, применяем форматирование к текущей позиции
            # или создаем новый элемент
            if format_type in ['header1', 'header2', 'header3', 'list', 'quote']:
                self._apply_block_format(cursor, format_type)
            return
        
        selected_text = cursor.selectedText()
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()
        
        # Получаем текущий markdown
        markdown = self.get_markdown()
        
        # Применяем форматирование
        if format_type == 'bold':
            formatted = f"**{selected_text}**"
        elif format_type == 'italic':
            formatted = f"*{selected_text}*"
        elif format_type == 'code':
            formatted = f"`{selected_text}`"
        else:
            # Для блочных элементов используем отдельный метод
            self._apply_block_format(cursor, format_type)
            return
        
        # Заменяем выделенный текст
        new_markdown = markdown[:start_pos] + formatted + markdown[end_pos:]
        self.set_markdown(new_markdown)
        
        # Восстанавливаем выделение
        new_cursor = self.text_edit.textCursor()
        new_cursor.setPosition(start_pos)
        new_cursor.setPosition(start_pos + len(formatted), QTextCursor.MoveMode.KeepAnchor)
        self.text_edit.setTextCursor(new_cursor)
    
    def _apply_block_format(self, cursor: QTextCursor, format_type: str) -> None:
        """
        Применяет блочное форматирование к текущей строке.
        
        Args:
            cursor: Текущий курсор
            format_type: Тип форматирования
        """
        # Получаем текущую строку
        cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
        line_text = cursor.selectedText()
        
        # Убираем существующее форматирование строки
        line_text = line_text.lstrip('#').lstrip('>').lstrip('-').lstrip('*').lstrip(' ').lstrip('\t')
        
        # Применяем новое форматирование
        if format_type == 'header1':
            formatted_line = f"# {line_text}"
        elif format_type == 'header2':
            formatted_line = f"## {line_text}"
        elif format_type == 'header3':
            formatted_line = f"### {line_text}"
        elif format_type == 'quote':
            formatted_line = f"> {line_text}"
        elif format_type == 'list':
            formatted_line = f"- {line_text}"
        else:
            formatted_line = line_text
        
        # Заменяем строку
        markdown = self.get_markdown()
        line_start = cursor.selectionStart()
        line_end = cursor.selectionEnd()
        
        new_markdown = markdown[:line_start] + formatted_line + markdown[line_end:]
        self.set_markdown(new_markdown)
        
        # Перемещаем курсор в конец строки
        new_cursor = self.text_edit.textCursor()
        new_cursor.setPosition(line_start + len(formatted_line))
        self.text_edit.setTextCursor(new_cursor)

