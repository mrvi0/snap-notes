"""
Менеджер синхронизации заметок с сервером.
"""
import json
import logging
import requests
from typing import List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from models import Note
from database import DatabaseManager

logger = logging.getLogger(__name__)


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
                return [Note.from_dict(note_data) for note_data in data]
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
            return [Note.from_dict(note_data) for note_data in data]
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при загрузке с сервера: {e}")
            raise
    
    def _push_to_server(self, notes: List[Note]) -> bool:
        """Отправляет заметки на сервер через REST API."""
        if not self.sync_url:
            raise ValueError("URL синхронизации не указан")
        
        try:
            data = [note.to_dict() for note in notes]
            response = requests.post(self.sync_url, json=data, timeout=10)
            response.raise_for_status()
            logger.info("Заметки успешно отправлены на сервер")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при отправке на сервер: {e}")
            raise
    
    def sync(self, use_server: bool = False) -> Tuple[bool, List[Tuple[Note, Note, str]]]:
        """
        Синхронизирует заметки.
        
        Args:
            use_server: Использовать сервер (True) или локальный файл (False)
            
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
            synced_count = 0
            
            # Обрабатываем удаленные заметки
            # Важно: не добавляем обратно заметки, которые были удалены локально
            # Если заметка есть в файле, но не в локальной БД - значит она была удалена намеренно
            for remote_note in remote_notes:
                if remote_note.id and remote_note.id in local_dict:
                    local_note = local_dict[remote_note.id]
                    # Проверяем конфликт: удаленная версия новее
                    if remote_note.updated_at > local_note.updated_at:
                        conflicts.append((local_note, remote_note, "remote_newer"))
                    elif remote_note.updated_at < local_note.updated_at:
                        # Локальная версия новее - обновляем локальную базу (она уже актуальна)
                        # Просто увеличиваем счетчик
                        synced_count += 1
                # НЕ добавляем заметки, которых нет локально - они были удалены намеренно
            
            # Сохраняем все локальные заметки в файл синхронизации
            # Это перезапишет файл, удалив из него заметки, которые были удалены локально
            all_local_notes = self.db_manager.get_all_notes()
            self._save_to_local_file(all_local_notes)
            
            logger.info(f"Синхронизация завершена. Синхронизировано: {synced_count}, конфликтов: {len(conflicts)}")
            return True, conflicts
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации: {e}")
            return False, []
    
    def resolve_conflict(self, local_note: Note, remote_note: Note, 
                       action: str) -> None:
        """
        Разрешает конфликт между локальной и удаленной версией.
        
        Args:
            local_note: Локальная версия заметки
            remote_note: Удаленная версия заметки
            action: Действие ('replace' - заменить локальную, 'keep' - сохранить локальную)
        """
        if action == "replace":
            # Заменяем локальную версию удаленной
            self.db_manager.update_note(
                remote_note.id,
                remote_note.title,
                remote_note.content
            )
            logger.info(f"Конфликт разрешен: локальная заметка {remote_note.id} заменена удаленной")
        elif action == "keep":
            # Сохраняем локальную версию (ничего не делаем)
            logger.info(f"Конфликт разрешен: локальная версия заметки {local_note.id} сохранена")
        else:
            raise ValueError(f"Неизвестное действие: {action}")

