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
import html as html_module

from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QTextBlockFormat, QFont, QColor
from PyQt6.QtCore import Qt
import re

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
    
    def __init__(self, text_edit: QMarkdownTextEdit, is_dark_theme: bool = False):
        """
        Инициализация редактора.
        
        Args:
            text_edit: Виджет QMarkdownTextEdit для редактирования
            is_dark_theme: True если используется темная тема
        """
        self.text_edit = text_edit
        self.mode = EditorMode.VISUAL
        self.is_dark_theme = is_dark_theme
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
            # Применяем стили к блокам кода и inline коду программно
            # Используем QTimer для отложенного применения, так как setMarkdown асинхронный
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(10, self._apply_code_styling)
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
            # Применяем стили к блокам кода и inline коду программно
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(10, self._apply_code_styling)
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
    
    def _apply_code_styling(self) -> None:
        """
        Применяет стили к блокам кода и inline коду программно.
        
        ВАЖНО: Этот метод НЕ должен изменять содержимое документа или добавлять
        новые элементы. Он только применяет визуальные стили к уже существующим
        элементам кода, которые были созданы через setMarkdown().
        """
        # Определяем цвета в зависимости от темы
        if self.is_dark_theme:
            code_bg = QColor("#2a2a2a")
            code_border = QColor("#444")
        else:
            code_bg = QColor("#f5f5f5")
            code_border = QColor("#ddd")
        
        document = self.text_edit.document()
        
        # Моноширинный шрифт
        default_font = document.defaultFont()
        font_size = default_font.pointSize() if default_font.pointSize() > 0 else 10
        
        monospace_font = QFont("Courier New", font_size)
        monospace_font.setStyleHint(QFont.StyleHint.Monospace)
        monospace_font.setFixedPitch(True)
        
        # Проходим по всем блокам документа и проверяем их форматирование
        # Блоки кода обычно имеют моноширинный шрифт или определенные характеристики
        block = document.firstBlock()
        in_code_block = False
        code_block_start = None
        
        while block.isValid():
            block_text = block.text()
            block_format = block.blockFormat()
            char_format = block.charFormat()
            
            # Проверяем, является ли блок частью блока кода
            # Блоки кода обычно имеют несколько пустых строк подряд или определенный формат
            # Более надежный способ - проверить, есть ли в блоке моноширинный шрифт
            # или проверить HTML представление
            
            # Простой эвристический подход: если блок содержит только код-подобный контент
            # (много пробелов, специальных символов) и имеет моноширинный шрифт
            
            # Проверяем формат символов в блоке
            cursor = QTextCursor(block)
            cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
            
            # Если блок выглядит как код (содержит много пробелов/табов в начале)
            # или имеет определенные характеристики
            is_code_like = (
                block_text.startswith('    ') or  # 4+ пробела в начале
                block_text.startswith('\t') or    # Таб в начале
                (len(block_text.strip()) > 0 and 
                 all(c in ' \t\n' or ord(c) < 128 for c in block_text))  # Только ASCII
            )
            
            # Применяем стили только если блок действительно выглядит как код
            # и не является частью обычного текста
            if is_code_like and len(block_text.strip()) > 0:
                # Применяем формат блока с фоном и отступами
                new_block_format = QTextBlockFormat(block_format)
                new_block_format.setBackground(code_bg)
                new_block_format.setLeftMargin(12)
                new_block_format.setRightMargin(12)
                new_block_format.setTopMargin(6)
                new_block_format.setBottomMargin(6)
                cursor.setBlockFormat(new_block_format)
                
                # Применяем моноширинный шрифт
                new_char_format = QTextCharFormat(char_format)
                new_char_format.setFont(monospace_font)
                new_char_format.setFontFixedPitch(True)
                new_char_format.setFontFamily("Courier New")
                cursor.setCharFormat(new_char_format)
            
            block = block.next()
        
        logger.debug("Применение стилей кода выполнено")
