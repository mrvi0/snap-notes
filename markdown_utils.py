"""
Утилиты для работы с Markdown форматированием.
"""
import re
from typing import Tuple


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

