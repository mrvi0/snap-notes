"""
Утилиты для работы с Markdown форматированием.
"""
import re
from typing import Tuple
from html import escape, unescape


def convert_plain_to_markdown(text: str) -> str:
    """
    Конвертирует обычный текст в Markdown.
    
    Args:
        text: Обычный текст
        
    Returns:
        Текст в формате Markdown
    """
    if not text:
        return text
    
    lines = text.split('\n')
    result = []
    
    for line in lines:
        # Определяем тип строки
        stripped = line.strip()
        
        if not stripped:
            result.append('')
            continue
        
        # Проверяем на заголовки (если строка короткая и в верхнем регистре)
        if len(stripped) < 50 and stripped.isupper() and len(stripped) > 3:
            result.append(f"## {stripped}")
            continue
        
        # Проверяем на списки (если начинается с цифры или дефиса)
        if re.match(r'^\d+[\.\)]\s', stripped) or stripped.startswith('- ') or stripped.startswith('* '):
            result.append(line)
            continue
        
        # Обычный текст
        result.append(line)
    
    return '\n'.join(result)


def convert_markdown_to_plain(text: str) -> str:
    """
    Конвертирует Markdown в обычный текст.
    
    Args:
        text: Текст в формате Markdown
        
    Returns:
        Обычный текст без Markdown разметки
    """
    if not text:
        return text
    
    # Убираем заголовки
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Убираем жирный текст
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    
    # Убираем курсив
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    
    # Убираем зачеркнутый текст
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    
    # Убираем код
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Убираем ссылки
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Убираем маркеры списков
    text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+[\.\)]\s+', '', text, flags=re.MULTILINE)
    
    return text


def apply_markdown_formatting(text: str, format_type: str, selection_start: int = None, 
                              selection_end: int = None) -> Tuple[str, int, int]:
    """
    Применяет Markdown форматирование к выделенному тексту.
    
    Args:
        text: Текст для форматирования
        format_type: Тип форматирования ('bold', 'italic', 'strikethrough', 'header1', 'header2', 'list')
        selection_start: Начало выделения
        selection_end: Конец выделения
        
    Returns:
        Кортеж (новый текст, новое начало выделения, новый конец выделения)
    """
    if selection_start is None or selection_end is None:
        return text, 0, len(text)
    
    if selection_start == selection_end:
        # Нет выделения, применяем к текущей позиции или строке
        lines = text.split('\n')
        cursor_line = text[:selection_start].count('\n')
        line_text = lines[cursor_line]
        
        if format_type == 'header1':
            lines[cursor_line] = f"# {line_text}"
        elif format_type == 'header2':
            lines[cursor_line] = f"## {line_text}"
        elif format_type == 'list':
            lines[cursor_line] = f"- {line_text}"
        else:
            return text, selection_start, selection_end
        
        new_text = '\n'.join(lines)
        new_start = selection_start + (len(lines[cursor_line]) - len(line_text))
        return new_text, new_start, new_start
    
    # Есть выделение
    selected_text = text[selection_start:selection_end]
    
    if format_type == 'bold':
        new_text = text[:selection_start] + f"**{selected_text}**" + text[selection_end:]
        new_start = selection_start
        new_end = selection_end + 4
    elif format_type == 'italic':
        new_text = text[:selection_start] + f"*{selected_text}*" + text[selection_end:]
        new_start = selection_start
        new_end = selection_end + 2
    elif format_type == 'strikethrough':
        new_text = text[:selection_start] + f"~~{selected_text}~~" + text[selection_end:]
        new_start = selection_start
        new_end = selection_end + 4
    else:
        return text, selection_start, selection_end
    
    return new_text, new_start, new_end


def extract_body_content(html: str) -> str:
    """
    Извлекает только содержимое body из HTML, убирая CSS стили и метаданные.
    
    Args:
        html: Полный HTML текст
        
    Returns:
        Только содержимое body без стилей
    """
    if not html:
        return html
    
    # Убираем style теги и их содержимое
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Извлекаем содержимое body, если есть
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, flags=re.DOTALL | re.IGNORECASE)
    if body_match:
        html = body_match.group(1)
    else:
        # Если нет body, ищем содержимое после head
        html_match = re.search(r'</head>(.*?)(?:</html>|$)', html, flags=re.DOTALL | re.IGNORECASE)
        if html_match:
            html = html_match.group(1)
    
    return html


def convert_html_to_markdown(html: str) -> str:
    """
    Конвертирует HTML в Markdown.
    
    Args:
        html: HTML текст
        
    Returns:
        Текст в формате Markdown
    """
    if not html:
        return html
    
    # Извлекаем только содержимое body, убирая CSS
    html = extract_body_content(html)
    
    # Убираем обертки параграфов
    html = re.sub(r'<p[^>]*>', '', html)
    html = re.sub(r'</p>', '\n', html)
    html = re.sub(r'<br\s*/?>', '\n', html)
    
    # Заголовки
    html = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', html, flags=re.DOTALL)
    html = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', html, flags=re.DOTALL)
    html = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', html, flags=re.DOTALL)
    
    # Обрабатываем форматирование итеративно до тех пор, пока есть изменения
    # Это позволяет обрабатывать вложенные теги любого уровня
    max_iterations = 20
    for iteration in range(max_iterations):
        original_html = html
        
        # Зачеркнутый (обрабатываем первым, так как обычно самый внутренний)
        html = re.sub(r'<span[^>]*style="[^"]*text-decoration:\s*line-through[^"]*"[^>]*>(.*?)</span>', r'~~\1~~', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<s[^>]*>(.*?)</s>', r'~~\1~~', html, flags=re.DOTALL)
        html = re.sub(r'<strike[^>]*>(.*?)</strike>', r'~~\1~~', html, flags=re.DOTALL)
        html = re.sub(r'<del[^>]*>(.*?)</del>', r'~~\1~~', html, flags=re.DOTALL)
        
        # Курсив
        html = re.sub(r'<span[^>]*style="[^"]*font-style:\s*italic[^"]*"[^>]*>(.*?)</span>', r'*\1*', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', html, flags=re.DOTALL)
        html = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', html, flags=re.DOTALL)
        
        # Жирный
        html = re.sub(r'<span[^>]*style="[^"]*font-weight:\s*(?:600|bold|700|800|900)[^"]*"[^>]*>(.*?)</span>', r'**\1**', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', html, flags=re.DOTALL)
        html = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', html, flags=re.DOTALL)
        
        # Если изменений не было, выходим
        if html == original_html:
            break
    
    # Списки
    html = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', html, flags=re.DOTALL)
    html = re.sub(r'<ul[^>]*>|</ul>|<ol[^>]*>|</ol>', '', html)
    
    # Убираем остальные HTML теги
    html = re.sub(r'<[^>]+>', '', html)
    
    # Декодируем HTML entities
    html = unescape(html)
    
    # Очищаем лишние переносы
    html = re.sub(r'\n{3,}', '\n\n', html)
    
    return html.strip()


def convert_markdown_to_html(markdown: str) -> str:
    """
    Конвертирует Markdown в HTML.
    
    Args:
        markdown: Текст в формате Markdown
        
    Returns:
        HTML текст
    """
    if not markdown:
        return ""
    
    # Экранируем HTML
    html = escape(markdown)
    
    # Заголовки
    html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    
    # Жирный
    html = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', html)
    html = re.sub(r'__(.+?)__', r'<b>\1</b>', html)
    
    # Курсив (после жирного, чтобы не конфликтовать)
    html = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<i>\1</i>', html)
    html = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'<i>\1</i>', html)
    
    # Зачеркнутый
    html = re.sub(r'~~(.+?)~~', r'<s>\1</s>', html)
    
    # Списки
    html = re.sub(r'^[\*\-\+]\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
    
    # Переносы строк
    html = re.sub(r'\n', '<br/>', html)
    
    # Обертываем в параграфы
    if not html.startswith('<h') and not html.startswith('<ul'):
        html = f'<p>{html}</p>'
    
    return html


def strip_markdown_and_html(text: str) -> str:
    """
    Убирает Markdown разметку и HTML теги, оставляя только чистый текст.
    
    Args:
        text: Текст с Markdown или HTML разметкой
        
    Returns:
        Чистый текст без разметки
    """
    if not text:
        return text
    
    # Сначала убираем HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Убираем HTML entities
    text = unescape(text)
    
    # Убираем Markdown разметку
    # Заголовки
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Жирный
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    
    # Курсив
    text = re.sub(r'(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_(?!_)(.*?)(?<!_)_(?!_)', r'\1', text)
    
    # Зачеркнутый
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    
    # Код
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Ссылки
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # Списки
    text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+[\.\)]\s+', '', text, flags=re.MULTILINE)
    
    return text.strip()

