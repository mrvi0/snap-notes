"""
Модуль для синхронизации заметок с Google Drive.

Использует официальный Google Drive API для хранения заметок как .md файлов.
Работает на Linux и Android (через Google Drive приложение).
"""
import logging
from typing import List, Optional, Tuple
from datetime import datetime

from models import Note
from storage.database import DatabaseManager
from services.google_drive_auth import GoogleDriveAuth
from services.google_drive_api import GoogleDriveAPI

logger = logging.getLogger(__name__)


class GoogleDriveSync:
    """Класс для синхронизации заметок с Google Drive."""
    
    def __init__(self, db_manager: DatabaseManager, settings=None, parent_widget=None):
        """
        Инициализация синхронизации с Google Drive.
        
        Args:
            db_manager: Менеджер базы данных
            settings: Объект Settings для получения настроек (опционально)
            parent_widget: Родительский виджет (опционально)
        """
        self.db_manager = db_manager
        self.settings = settings
        self.parent_widget = parent_widget
        
        # Получаем путь к credentials из настроек
        credentials_file = None
        if settings:
            credentials_file = settings.get('google_drive.credentials_file', '')
            if credentials_file:
                credentials_file = credentials_file.strip()
        
        # Создаем auth клиент
        self.auth = GoogleDriveAuth(credentials_file=credentials_file)
        self.api = GoogleDriveAPI(db_manager, self.auth)
        self._authenticated = False
    
    def authenticate(self, parent_widget=None) -> bool:
        """
        Аутентифицируется в Google Drive через OAuth 2.0.
        
        Args:
            parent_widget: Родительский виджет (опционально)
            
        Returns:
            True если аутентификация успешна
        """
        try:
            # Аутентифицируемся через OAuth 2.0
            if not self.auth.authenticate(parent_widget=parent_widget or self.parent_widget):
                logger.error("Аутентификация с Google Drive не удалась")
                return False
            
            # Аутентифицируемся в API
            if not self.api.authenticate():
                logger.error("API аутентификация не удалась")
                return False
            
            self._authenticated = True
            logger.info("Успешная аутентификация в Google Drive")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при аутентификации: {e}", exc_info=True)
            self._authenticated = False
            return False
    
    def fetch_notes(self) -> List[Note]:
        """
        Загружает заметки из Google Drive.
        
        Returns:
            Список заметок
        """
        if not self._authenticated:
            if not self.authenticate():
                raise Exception("Не удалось аутентифицироваться в Google Drive")
        
        try:
            return self.api.fetch_notes()
        except Exception as e:
            logger.error(f"Ошибка при загрузке заметок из Google Drive: {e}")
            raise
    
    def push_notes(self, notes: List[Note]) -> bool:
        """
        Отправляет заметки в Google Drive.
        
        Args:
            notes: Список заметок для отправки
            
        Returns:
            True если успешно
        """
        if not self._authenticated:
            if not self.authenticate():
                raise Exception("Не удалось аутентифицироваться в Google Drive")
        
        try:
            return self.api.push_notes(notes)
        except Exception as e:
            logger.error(f"Ошибка при отправке заметок в Google Drive: {e}")
            raise
    
    def sync(self) -> Tuple[bool, List[Tuple[Note, Note, str]]]:
        """
        Синхронизирует заметки с Google Drive (двусторонняя синхронизация).
        
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
            
            # Получаем заметки из Google Drive
            drive_notes = self.fetch_notes()
            drive_dict = {note.title: note for note in drive_notes}
            
            conflicts = []
            
            # Обрабатываем заметки из Google Drive
            for drive_note in drive_notes:
                # Ищем соответствующую локальную заметку по названию
                local_note = None
                for ln in local_notes:
                    if ln.title == drive_note.title:
                        local_note = ln
                        break
                
                if local_note:
                    # Проверяем конфликты
                    if local_note.updated_at and drive_note.updated_at:
                        if local_note.updated_at > drive_note.updated_at:
                            conflicts.append((local_note, drive_note, "local_newer"))
                        elif drive_note.updated_at > local_note.updated_at:
                            # Обновляем локальную заметку
                            if local_note.id:
                                self.db_manager.update_note(
                                    local_note.id,
                                    local_note.title,
                                    drive_note.markdown_content
                                )
                else:
                    # Новая заметка из Google Drive
                    self.db_manager.create_note(drive_note.title, drive_note.markdown_content)
            
            # Отправляем локальные заметки в Google Drive
            self.push_notes(local_notes)
            
            logger.info("Синхронизация с Google Drive завершена успешно")
            return True, conflicts
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации с Google Drive: {e}")
            return False, []



