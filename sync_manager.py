"""
Менеджер синхронизации заметок с сервером.

Поддерживает понятия Safe Markdown и Extended Markdown для синхронизации
с сервисами, которые могут не поддерживать все возможности Markdown.
"""
import json
import logging
import requests
import re
from typing import List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from models import Note
from database import DatabaseManager

logger = logging.getLogger(__name__)


class MarkdownLevel:
    """
    Уровни поддержки Markdown при синхронизации.
    
    Safe Markdown: базовые элементы, поддерживаемые большинством сервисов
    Extended Markdown: расширенные элементы, которые могут теряться при синхронизации
    """
    
    # Элементы Safe Markdown (заголовки, жирный, курсив, простые списки)
    SAFE_PATTERNS = [
        r'^#{1,6}\s+',  # Заголовки
        r'\*\*.*?\*\*',  # Жирный
        r'\*.*?\*',      # Курсив
        r'^\s*[-*+]\s+',  # Маркированные списки
        r'^\s*\d+\.\s+',  # Нумерованные списки
        r'^>\s+',        # Цитаты
    ]
    
    # Элементы Extended Markdown (код, таблицы, сложные конструкции)
    EXTENDED_PATTERNS = [
        r'```.*?```',    # Блоки кода
        r'`.*?`',        # Inline код
        r'\|.*?\|',      # Таблицы
        r'\[.*?\]\(.*?\)',  # Ссылки с форматированием
        r'!\[.*?\]\(.*?\)',  # Изображения
    ]
    
    @staticmethod
    def contains_extended_markdown(markdown_text: str) -> bool:
        """
        Проверяет, содержит ли markdown расширенные элементы.
        
        Args:
            markdown_text: Текст в формате Markdown
            
        Returns:
            True, если содержит расширенные элементы
        """
        for pattern in MarkdownLevel.EXTENDED_PATTERNS:
            if re.search(pattern, markdown_text, re.MULTILINE | re.DOTALL):
                return True
        return False
    
    @staticmethod
    def downgrade_to_safe(markdown_text: str) -> str:
        """
        Понижает markdown до safe-уровня, удаляя расширенные элементы.
        
        Args:
            markdown_text: Исходный markdown
            
        Returns:
            Markdown на safe-уровне
        """
        text = markdown_text
        
        # Удаляем блоки кода (заменяем на plain text)
        text = re.sub(r'```[\s\S]*?```', lambda m: m.group(0).replace('```', '').strip(), text)
        
        # Удаляем inline код (заменяем на plain text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Удаляем таблицы (заменяем на plain text)
        text = re.sub(r'\|.*?\|', lambda m: m.group(0).replace('|', ' ').strip(), text)
        
        # Упрощаем ссылки (оставляем только текст)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Удаляем изображения
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
        
        return text


class SyncManager:
    """Класс для синхронизации заметок с сервером или локальным файлом."""
    
    def __init__(self, db_manager: DatabaseManager, sync_url: Optional[str] = None, 
                 local_sync_file: str = "notes_sync.json"):
        """
        Инициализация менеджера синхронизации.
        
        Args:
            db_manager: Менеджер базы данных
            sync_url: URL REST API для синхронизации (опционально)
            local_sync_file: Путь к локальному файлу для синхронизации
        """
        self.db_manager = db_manager
        self.sync_url = sync_url
        self.local_sync_file = local_sync_file
    
    def _load_from_local_file(self) -> List[Note]:
        """Загружает заметки из локального JSON файла."""
        try:
            if not Path(self.local_sync_file).exists():
                return []
            
            with open(self.local_sync_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                notes = []
                for note_data in data:
                    # Поддержка старого формата (content -> markdown_content)
                    if 'markdown_content' not in note_data and 'content' in note_data:
                        note_data['markdown_content'] = note_data.pop('content')
                    notes.append(Note.from_dict(note_data))
                return notes
        except Exception as e:
            logger.error(f"Ошибка при загрузке из локального файла: {e}")
            return []
    
    def _save_to_local_file(self, notes: List[Note]) -> None:
        """Сохраняет заметки в локальный JSON файл."""
        try:
            with open(self.local_sync_file, 'w', encoding='utf-8') as f:
                json.dump([note.to_dict() for note in notes], f, ensure_ascii=False, indent=2)
            logger.info(f"Заметки сохранены в {self.local_sync_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении в локальный файл: {e}")
            raise
    
    def _fetch_from_server(self) -> List[Note]:
        """Загружает заметки с сервера через REST API."""
        if not self.sync_url:
            raise ValueError("URL синхронизации не указан")
        
        try:
            response = requests.get(self.sync_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            notes = []
            for note_data in data:
                # Поддержка старого формата
                if 'markdown_content' not in note_data and 'content' in note_data:
                    note_data['markdown_content'] = note_data.pop('content')
                notes.append(Note.from_dict(note_data))
            return notes
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при загрузке с сервера: {e}")
            raise
    
    def _push_to_server(self, notes: List[Note], downgrade_extended: bool = False) -> bool:
        """
        Отправляет заметки на сервер через REST API.
        
        Args:
            notes: Список заметок для отправки
            downgrade_extended: Понижать ли расширенный markdown до safe-уровня
        """
        if not self.sync_url:
            raise ValueError("URL синхронизации не указан")
        
        try:
            data = []
            for note in notes:
                note_dict = note.to_dict()
                # Если требуется, понижаем markdown до safe-уровня
                if downgrade_extended and MarkdownLevel.contains_extended_markdown(note.markdown_content):
                    note_dict['markdown_content'] = MarkdownLevel.downgrade_to_safe(note.markdown_content)
                    logger.info(f"Markdown понижен до safe-уровня для заметки {note.id}")
                data.append(note_dict)
            
            response = requests.post(self.sync_url, json=data, timeout=10)
            response.raise_for_status()
            logger.info("Заметки успешно отправлены на сервер")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке на сервер: {e}")
            raise
    
    def sync(self, use_server: bool = False, downgrade_extended: bool = False) -> Tuple[bool, List[Tuple[Note, Note, str]]]:
        """
        Синхронизирует заметки.
        
        Args:
            use_server: Использовать сервер (True) или локальный файл (False)
            downgrade_extended: Понижать ли расширенный markdown до safe-уровня
            
        Returns:
            Кортеж (успех, список конфликтов)
            Конфликт: (локальная_заметка, серверная_заметка, тип_конфликта)
        """
        try:
            # Получаем локальные заметки
            local_notes = self.db_manager.get_all_notes()
            local_dict = {note.id: note for note in local_notes if note.id is not None}
            
            # Получаем удаленные заметки
            if use_server:
                remote_notes = self._fetch_from_server()
            else:
                remote_notes = self._load_from_local_file()
            
            remote_dict = {note.id: note for note in remote_notes if note.id is not None}
            
            conflicts = []
            
            # Обрабатываем удаленные заметки
            for remote_note in remote_notes:
                if remote_note.id in local_dict:
                    local_note = local_dict[remote_note.id]
                    # Проверяем конфликты
                    if local_note.updated_at != remote_note.updated_at:
                        if local_note.updated_at > remote_note.updated_at:
                            conflicts.append((local_note, remote_note, "local_newer"))
                        else:
                            conflicts.append((local_note, remote_note, "remote_newer"))
                else:
                    # Новая заметка с сервера
                    # Проверяем, содержит ли она расширенный markdown
                    if MarkdownLevel.contains_extended_markdown(remote_note.markdown_content):
                        if not downgrade_extended:
                            logger.warning(f"Заметка {remote_note.id} содержит расширенный markdown")
                    self.db_manager.sync_note(remote_note)
            
            # Отправляем локальные заметки
            if use_server:
                self._push_to_server(local_notes, downgrade_extended)
            else:
                # Сохраняем все локальные заметки в файл
                self._save_to_local_file(local_notes)
            
            logger.info("Синхронизация завершена успешно")
            return True, conflicts
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации: {e}")
            return False, []
