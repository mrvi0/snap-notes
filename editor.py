"""
Логика редактора Markdown.

Поддерживает два режима:
- Visual Markdown mode: визуальное форматирование через toolbar
- Raw Markdown mode: чистый markdown-текст

Markdown - единственный канонический формат хранения.
HTML используется только для визуализации в Visual режиме.
"""
import logging
from typing import Optional
from enum import Enum
import html as html_module
import markdown as markdown_lib

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
        self.mode = EditorMode.RAW  # По умолчанию RAW режим
        self.is_dark_theme = is_dark_theme
        self._current_markdown = ""  # Храним оригинальный Markdown текст
        self._setup_editor()
        
        # Инициализируем Markdown конвертер
        try:
            import markdown
            self.md = markdown.Markdown(extensions=['fenced_code', 'codehilite'])
        except ImportError:
            self.md = None
            logger.warning("Библиотека markdown не установлена, используется встроенный setMarkdown")
    
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
        
        # Получаем текущий markdown-текст из хранимого значения или из редактора
        if self.mode == EditorMode.RAW:
            # В RAW режиме берем текст напрямую из редактора и обновляем сохраненное значение
            current_markdown = self.text_edit.toPlainText()
            self._current_markdown = current_markdown
        else:
            # В VISUAL режиме используем сохраненный Markdown
            current_markdown = self._current_markdown
        
        cursor_position = self.text_edit.textCursor().position()
        
        self.mode = mode
        
        if mode == EditorMode.VISUAL:
            # Сохраняем оригинальный Markdown перед конвертацией
            self._current_markdown = current_markdown
            # В визуальном режиме конвертируем Markdown в HTML с правильными стилями
            html_content = self._markdown_to_html(current_markdown)
            # В VISUAL режиме делаем редактор read-only, чтобы предотвратить редактирование HTML
            # Редактирование должно происходить только в RAW режиме для сохранения целостности Markdown
            self.text_edit.setReadOnly(True)
            self.text_edit.setHtml(html_content)
        else:
            # В raw режиме показываем сохраненный Markdown текст
            # Разрешаем редактирование в RAW режиме
            self.text_edit.setReadOnly(False)
            self.text_edit.setPlainText(self._current_markdown)
            
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
            # В RAW режиме берем текст напрямую и обновляем сохраненное значение
            markdown_text = self.text_edit.toPlainText()
            self._current_markdown = markdown_text
            return markdown_text
        else:
            # В VISUAL режиме возвращаем сохраненный Markdown
            # НЕ используем toMarkdown(), так как это может исказить текст
            return self._current_markdown
    
    def set_markdown(self, markdown_text: str) -> None:
        """
        Устанавливает markdown-текст в редактор.
        
        Args:
            markdown_text: Текст в формате Markdown
        """
        # Всегда сохраняем оригинальный Markdown
        self._current_markdown = markdown_text
        
        if self.mode == EditorMode.VISUAL:
            # В визуальном режиме конвертируем Markdown в HTML с правильными стилями
            html_content = self._markdown_to_html(markdown_text)
            self.text_edit.setHtml(html_content)
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
    
    def _markdown_to_html(self, markdown_text: str) -> str:
        """
        Конвертирует Markdown в HTML с правильными стилями для кода.
        
        Работает как VS Code и другие Markdown визуализаторы:
        - Inline code: фон только на сам текст с padding
        - Code blocks: один фон на весь блок
        """
        # Определяем цвета в зависимости от темы
        if self.is_dark_theme:
            code_bg = "#2a2a2a"
            code_border = "#444"
            text_color = "#e0e0e0"
        else:
            code_bg = "#f5f5f5"
            code_border = "#ddd"
            text_color = "#212121"
        
        # Конвертируем Markdown в HTML
        if hasattr(self, 'md') and self.md:
            try:
                # Сбрасываем состояние конвертера
                self.md.reset()
                html = self.md.convert(markdown_text)
            except Exception as e:
                logger.error(f"Ошибка конвертации Markdown: {e}")
                # Fallback на встроенный метод PyQt6
                self.text_edit.setMarkdown(markdown_text)
                html = self.text_edit.toHtml()
        else:
            # Fallback на встроенный метод PyQt6
            self.text_edit.setMarkdown(markdown_text)
            html = self.text_edit.toHtml()
        
        # Добавляем inline стили для кода
        # Заменяем <code> на <code> с inline стилями (только для inline, не внутри pre)
        code_style = f'background-color: {code_bg}; padding: 2px 4px; border-radius: 3px; font-family: "Courier New", monospace;'
        
        # Сначала обрабатываем блоки <pre><code>
        pre_code_style = f'background-color: {code_bg}; padding: 12px; border-radius: 4px; border-left: 3px solid {code_border}; font-family: "Courier New", monospace; white-space: pre-wrap; overflow-x: auto; display: block;'
        html = re.sub(
            r'<pre><code[^>]*>(.*?)</code></pre>',
            lambda m: f'<pre style="{pre_code_style}"><code>{m.group(1)}</code></pre>',
            html,
            flags=re.DOTALL
        )
        
        # Затем обрабатываем inline <code> (не внутри pre)
        # Находим все <code> которые не внутри <pre>
        def replace_inline_code(match):
            # Проверяем, не находится ли этот code внутри pre
            start = match.start()
            # Ищем ближайший <pre> перед этим кодом
            before = html[:start]
            pre_open_count = before.count('<pre')
            pre_close_count = before.count('</pre>')
            if pre_open_count > pre_close_count:
                # Мы внутри pre, не заменяем
                return match.group(0)
            return f'<code style="{code_style}">{match.group(1)}</code>'
        
        html = re.sub(
            r'<code[^>]*>(.*?)</code>',
            replace_inline_code,
            html,
            flags=re.DOTALL
        )
        
        # Обертываем в базовый HTML
        full_html = f'''<html><head><style>
        body {{ color: {text_color}; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        code {{ background-color: {code_bg}; padding: 2px 4px; border-radius: 3px; font-family: "Courier New", monospace; }}
        pre {{ background-color: {code_bg}; padding: 12px; border-radius: 4px; border-left: 3px solid {code_border}; font-family: "Courier New", monospace; white-space: pre-wrap; overflow-x: auto; }}
        pre code {{ background-color: transparent; padding: 0; border-radius: 0; }}
        </style></head><body>{html}</body></html>'''
        
        return full_html
    
    def _apply_code_styling(self) -> None:
        """
        Применяет стили к блокам кода и inline коду программно.
        
        Работает как VS Code preview:
        - Inline code: фон только на сам текст с небольшими отступами
        - Code blocks: один фон на все строки блока, по ширине текста
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
        
        # Получаем HTML представление для точного поиска тегов
        html_content = self.text_edit.toHtml()
        
        # Находим все теги <pre> (блоки кода) - они могут содержать <code> внутри
        pre_pattern = re.compile(r'<pre[^>]*>(.*?)</pre>', re.DOTALL)
        pre_matches = list(pre_pattern.finditer(html_content))
        
        # Находим все теги <code> которые НЕ внутри <pre>
        code_pattern = re.compile(r'<code[^>]*>(.*?)</code>', re.DOTALL)
        code_matches = list(code_pattern.finditer(html_content))
        
        # Фильтруем inline code (исключаем те, что внутри pre)
        inline_code_matches = []
        for code_match in code_matches:
            code_start = code_match.start()
            code_end = code_match.end()
            # Проверяем, не находится ли этот code внутри pre
            is_inside_pre = False
            for pre_match in pre_matches:
                if pre_match.start() < code_start < pre_match.end():
                    is_inside_pre = True
                    break
            if not is_inside_pre:
                inline_code_matches.append(code_match)
        
        # Применяем стили к inline коду
        for code_match in inline_code_matches:
            code_text = html_module.unescape(code_match.group(1))
            if not code_text.strip():
                continue
            
            # Ищем этот текст в документе
            cursor = QTextCursor(document)
            cursor.setPosition(0)
            found = False
            while True:
                cursor = document.find(code_text, cursor)
                if cursor.isNull():
                    break
                
                # Применяем стили только к найденному тексту (не ко всей строке)
                start_pos = cursor.selectionStart()
                end_pos = cursor.selectionEnd()
                cursor.setPosition(start_pos)
                cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
                
                char_format = cursor.charFormat()
                new_format = QTextCharFormat(char_format)
                new_format.setFont(monospace_font)
                new_format.setBackground(code_bg)
                new_format.setFontFixedPitch(True)
                new_format.setFontFamily("Courier New")
                # Добавляем небольшой padding через изменение формата
                # В QTextCharFormat нет прямого padding, но можно использовать свойства
                cursor.setCharFormat(new_format)
                found = True
                break
        
        # Применяем стили к блокам кода (pre)
        for pre_match in pre_matches:
            pre_content = pre_match.group(1)
            # Убираем внутренние теги <code> если есть
            pre_content = re.sub(r'<code[^>]*>|</code>', '', pre_content)
            pre_content = html_module.unescape(pre_content)
            
            if not pre_content.strip():
                continue
            
            # Берем первую непустую строку для поиска
            lines = pre_content.split('\n')
            first_line = None
            for line in lines:
                if line.strip():
                    first_line = line.strip()
                    break
            
            if not first_line:
                continue
            
            # Ищем эту строку в документе
            cursor = QTextCursor(document)
            cursor.setPosition(0)
            found = False
            while True:
                cursor = document.find(first_line, cursor)
                if cursor.isNull():
                    break
                
                # Нашли начало блока, применяем стили ко всем строкам блока
                block_start = cursor.block()
                block = block_start
                
                # Собираем все блоки кода
                code_blocks = []
                for _ in range(min(len(lines), 200)):  # Ограничение для безопасности
                    if not block.isValid():
                        break
                    code_blocks.append(block)
                    block = block.next()
                
                # Применяем стили ко всем блокам как к одному целому
                # Используем QTextBlockFormat для фона, но только на ширину текста
                for block in code_blocks:
                    block_cursor = QTextCursor(block)
                    block_cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                    
                    # Применяем формат блока с фоном и отступами
                    block_format = block.blockFormat()
                    new_block_format = QTextBlockFormat(block_format)
                    new_block_format.setBackground(code_bg)
                    # Отступы: слева 12px, сверху/снизу 6px
                    new_block_format.setLeftMargin(12)
                    new_block_format.setRightMargin(12)
                    new_block_format.setTopMargin(6)
                    new_block_format.setBottomMargin(6)
                    block_cursor.setBlockFormat(new_block_format)
                    
                    # Применяем моноширинный шрифт ко всему блоку
                    block_cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
                    char_format = block_cursor.charFormat()
                    new_char_format = QTextCharFormat(char_format)
                    new_char_format.setFont(monospace_font)
                    new_char_format.setFontFixedPitch(True)
                    new_char_format.setFontFamily("Courier New")
                    block_cursor.setCharFormat(new_char_format)
                    block_cursor.clearSelection()
                
                found = True
                break
        
        logger.debug("Применение стилей кода выполнено")
