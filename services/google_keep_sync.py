"""
Модуль для синхронизации заметок с Google Keep.

Использует Master Token для аутентификации и прямые HTTP запросы к неофициальному Google Keep API.
"""
import logging
from typing import List, Optional, Tuple
from datetime import datetime

from models import Note
from storage.database import DatabaseManager
from services.google_keep_auth import GoogleKeepAuth
from services.google_keep_api import GoogleKeepAPI

logger = logging.getLogger(__name__)


class GoogleKeepSync:
    """Класс для синхронизации заметок с Google Keep через Master Token."""
    
    def __init__(self, db_manager: DatabaseManager, settings=None, parent_widget=None):
        """
        Инициализация синхронизации с Google Keep.
        
        Args:
            db_manager: Менеджер базы данных
            settings: Объект Settings для получения Master Token (опционально)
            parent_widget: Родительский виджет (опционально)
        """
        self.db_manager = db_manager
        self.settings = settings
        self.parent_widget = parent_widget
        
        # Получаем credentials из настроек
        master_token = None
        email = None
        app_password = None
        
        if settings:
            master_token = settings.get('google_keep.master_token', '')
            if master_token:
                master_token = master_token.strip()
            email = settings.get('google_keep.email', '')
            if email:
                email = email.strip()
            app_password = settings.get('google_keep.app_password', '')
            if app_password:
                app_password = app_password.strip()
        
        # Создаем auth клиент с Master Token или email/app_password
        self.auth = GoogleKeepAuth(
            master_token=master_token if master_token else None,
            email=email if email else None,
            app_password=app_password if app_password else None
        )
        self.api = GoogleKeepAPI(db_manager, self.auth)
        self._authenticated = False
    
    def authenticate(self, parent_widget=None) -> bool:
        """
        Аутентифицируется в Google Keep через Master Token.
        
        Args:
            parent_widget: Родительский виджет (опционально)
            
        Returns:
            True если аутентификация успешна
        """
        try:
            # Аутентифицируемся через Master Token
            if not self.auth.authenticate():
                logger.error("Аутентификация с Master Token не удалась")
                return False
            
            # Аутентифицируемся в API
            if not self.api.authenticate():
                logger.error("API аутентификация не удалась")
                return False
            
            self._authenticated = True
            logger.info("Успешная аутентификация в Google Keep через Master Token")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при аутентификации: {e}", exc_info=True)
            self._authenticated = False
            return False
    
    def fetch_notes(self) -> List[Note]:
        """
        Загружает заметки из Google Keep.
        
        Returns:
            Список заметок в формате приложения
        """
        if not self._authenticated:
            if not self.authenticate():
                raise Exception("Не удалось аутентифицироваться в Google Keep")
        
        try:
            return self.api.fetch_notes()
        except Exception as e:
            logger.error(f"Ошибка при загрузке заметок из Google Keep: {e}")
            raise
    
    def push_notes(self, notes: List[Note]) -> bool:
        """
        Отправляет заметки в Google Keep.
        
        Синхронизация полностью копирует все теги Markdown без изменений.
        
        Args:
            notes: Список заметок для отправки
            
        Returns:
            True если успешно
        """
        if not self._authenticated:
            if not self.authenticate():
                raise Exception("Не удалось аутентифицироваться в Google Keep")
        
        try:
            return self.api.push_notes(notes)
        except Exception as e:
            logger.error(f"Ошибка при отправке заметок в Google Keep: {e}")
            raise
    
    def sync(self) -> Tuple[bool, List[Tuple[Note, Note, str]]]:
        """
        Синхронизирует заметки с Google Keep (двусторонняя синхронизация).
        
        Синхронизация полностью копирует все теги Markdown без изменений.
        
        Returns:
            Кортеж (успех, список конфликтов)
        """
        try:
            # Аутентифицируемся
            if not self.authenticate():
                return False, []
            
            # Получаем локальные заметки
            local_notes = self.db_manager.get_all_notes()
            local_dict = {note.id: note for note in local_notes if note.id is not None}
            
            # Получаем заметки из Google Keep
            keep_notes = self.fetch_notes()
            keep_dict = {}  # TODO: использовать keep_id для mapping
            
            conflicts = []
            
            # Обрабатываем заметки из Google Keep
            for keep_note in keep_notes:
                # TODO: реализовать mapping по keep_id
                # Пока просто создаем новые заметки
                if keep_note.title not in [n.title for n in local_notes]:
                    # Новая заметка из Keep
                    self.db_manager.create_note(keep_note.title, keep_note.markdown_content)
            
            # Отправляем локальные заметки в Keep (Markdown как есть)
            self.push_notes(local_notes)
            
            logger.info("Синхронизация с Google Keep завершена успешно")
            return True, conflicts
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации с Google Keep: {e}")
            return False, []
