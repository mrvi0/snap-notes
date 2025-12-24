"""
Модуль для работы с Google Keep через REST API.

Использует OAuth 2.0 для аутентификации и прямые HTTP запросы к Google Keep API.
"""
import logging
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import Note
from storage.database import DatabaseManager
from services.google_keep_oauth import GoogleKeepOAuth, HAS_GOOGLE_AUTH

logger = logging.getLogger(__name__)

# Базовый URL для Google Keep API (неофициальный, но стабильный)
KEEP_API_BASE = "https://keep.google.com"
KEEP_API_URL = f"{KEEP_API_BASE}/media"


class GoogleKeepAPI:
    """Класс для работы с Google Keep через REST API."""
    
    def __init__(self, db_manager: DatabaseManager, oauth: GoogleKeepOAuth):
        """
        Инициализация API клиента.
        
        Args:
            db_manager: Менеджер базы данных
            oauth: Экземпляр GoogleKeepOAuth для аутентификации
        """
        if not HAS_GOOGLE_AUTH:
            raise ImportError("google-auth не установлен")
        
        self.db_manager = db_manager
        self.oauth = oauth
        self.session = requests.Session()
        self._authenticated = False
    
    def _get_headers(self) -> Dict[str, str]:
        """Возвращает заголовки для HTTP запросов."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
        }
        
        # Добавляем OAuth токен
        if self.oauth.creds and self.oauth.creds.token:
            headers['Authorization'] = f'Bearer {self.oauth.creds.token}'
        
        return headers
    
    def authenticate(self) -> bool:
        """
        Аутентифицируется через OAuth.
        
        Returns:
            True если успешно
        """
        if not self.oauth.is_authenticated():
            if not self.oauth.authenticate():
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
            # Получаем список заметок через Google Keep API
            # Используем неофициальный endpoint для получения заметок
            url = f"{KEEP_API_BASE}/api/v1/notes"
            response = self.session.get(url, headers=self._get_headers())
            
            if response.status_code == 401:
                # Токен истек, обновляем
                logger.warning("Токен истек, обновляем...")
                if self.oauth.creds and self.oauth.creds.refresh_token:
                    from google.auth.transport.requests import Request
                    self.oauth.creds.refresh(Request())
                    self.oauth._save_token()
                    response = self.session.get(url, headers=self._get_headers())
            
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
                    created = datetime.fromtimestamp(keep_note.get('createdTimestampUsec', 0) / 1000000)
                    updated = datetime.fromtimestamp(keep_note.get('userEditedTimestampUsec', 0) / 1000000)
                    
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
            # Создаем заметку через Google Keep API
            url = f"{KEEP_API_BASE}/api/v1/notes"
            payload = {
                'title': note.title,
                'text': note.markdown_content,  # Отправляем markdown как есть
            }
            
            response = self.session.post(
                url,
                headers=self._get_headers(),
                json=payload
            )
            
            if response.status_code == 401:
                # Токен истек, обновляем
                logger.warning("Токен истек, обновляем...")
                if self.oauth.creds and self.oauth.creds.refresh_token:
                    from google.auth.transport.requests import Request
                    self.oauth.creds.refresh(Request())
                    self.oauth._save_token()
                    response = self.session.post(
                        url,
                        headers=self._get_headers(),
                        json=payload
                    )
            
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

