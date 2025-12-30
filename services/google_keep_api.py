"""
Модуль для работы с Google Keep через неофициальный REST API.

Использует Master Token для аутентификации и прямые HTTP запросы к Google Keep API.
"""
import logging
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import Note
from storage.database import DatabaseManager
from services.google_keep_auth import GoogleKeepAuth

logger = logging.getLogger(__name__)

# Базовый URL для Google Keep API (неофициальный)
KEEP_API_BASE = "https://keep.google.com"


class GoogleKeepAPI:
    """Класс для работы с Google Keep через REST API."""
    
    def __init__(self, db_manager: DatabaseManager, auth: GoogleKeepAuth):
        """
        Инициализация API клиента.
        
        Args:
            db_manager: Менеджер базы данных
            auth: Экземпляр GoogleKeepAuth для аутентификации
        """
        self.db_manager = db_manager
        self.auth = auth
        self.session = auth.get_session()
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """
        Аутентифицируется через Master Token.
        
        Returns:
            True если успешно
        """
        if not self.auth.is_authenticated():
            if not self.auth.authenticate():
                return False
        
        self._authenticated = True
        logger.info("Аутентификация в Google Keep API успешна")
        return True
    
    def fetch_notes(self) -> List[Note]:
        """
        Загружает заметки из Google Keep.
        
        Returns:
            Список заметок
        """
        if not self._authenticated:
            if not self.authenticate():
                raise Exception("Не удалось аутентифицироваться")
        
        try:
            # Получаем список заметок через неофициальный Google Keep API
            # Используем endpoint, который использует gkeepapi
            url = f"{KEEP_API_BASE}/api/v1/notes"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 401:
                raise Exception("Master Token недействителен. Получите новый токен.")
            
            response.raise_for_status()
            data = response.json()
            
            notes = []
            # Обрабатываем ответ API
            # Структура ответа может варьироваться, адаптируем под реальный формат
            if 'notes' in data:
                for keep_note in data['notes']:
                    title = keep_note.get('title', 'Без названия')
                    text = keep_note.get('text', '')
                    # Конвертируем timestamp в datetime
                    created_timestamp = keep_note.get('createdTimestampUsec', 0)
                    updated_timestamp = keep_note.get('userEditedTimestampUsec', 0) or created_timestamp
                    
                    if created_timestamp:
                        created = datetime.fromtimestamp(created_timestamp / 1000000)
                    else:
                        created = datetime.now()
                    
                    if updated_timestamp:
                        updated = datetime.fromtimestamp(updated_timestamp / 1000000)
                    else:
                        updated = created
                    
                    note = Note(
                        id=None,  # Будет создан в БД
                        title=title,
                        markdown_content=text,  # Google Keep хранит plain text, мы используем как markdown
                        created_at=created,
                        updated_at=updated
                    )
                    notes.append(note)
            
            logger.info(f"Загружено {len(notes)} заметок из Google Keep")
            return notes
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке заметок из Google Keep: {e}", exc_info=True)
            raise
    
    def push_note(self, note: Note) -> bool:
        """
        Отправляет заметку в Google Keep.
        
        Args:
            note: Заметка для отправки
            
        Returns:
            True если успешно
        """
        if not self._authenticated:
            if not self.authenticate():
                raise Exception("Не удалось аутентифицироваться")
        
        try:
            # Создаем заметку через неофициальный Google Keep API
            url = f"{KEEP_API_BASE}/api/v1/notes"
            payload = {
                'title': note.title,
                'text': note.markdown_content,  # Отправляем markdown как есть
            }
            
            response = self.session.post(
                url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 401:
                raise Exception("Master Token недействителен. Получите новый токен.")
            
            response.raise_for_status()
            logger.info(f"Заметка '{note.title}' отправлена в Google Keep")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке заметки в Google Keep: {e}", exc_info=True)
            raise
    
    def push_notes(self, notes: List[Note]) -> bool:
        """
        Отправляет несколько заметок в Google Keep.
        
        Args:
            notes: Список заметок
            
        Returns:
            True если успешно
        """
        for note in notes:
            self.push_note(note)
        
        logger.info(f"Отправлено {len(notes)} заметок в Google Keep")
        return True
