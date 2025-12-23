"""
Модуль для синхронизации с Google Keep.
"""
import logging
from typing import List, Optional, Tuple
from datetime import datetime

from models import Note
from database import DatabaseManager

logger = logging.getLogger(__name__)

try:
    import gkeepapi
    KEEPAPI_AVAILABLE = True
except ImportError:
    KEEPAPI_AVAILABLE = False
    logger.warning("gkeepapi не установлен. Установите: pip install gkeepapi")


class GoogleKeepSync:
    """Класс для синхронизации с Google Keep."""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Инициализация синхронизации с Google Keep.
        
        Args:
            db_manager: Менеджер базы данных
        """
        self.db_manager = db_manager
        self.keep = None
        self.authenticated = False
    
    def login(self, email: str, password: str) -> bool:
        """
        Авторизация в Google Keep.
        
        Args:
            email: Email аккаунта Google
            password: Пароль или токен приложения
            
        Returns:
            True, если авторизация успешна
        """
        if not KEEPAPI_AVAILABLE:
            logger.error("gkeepapi не установлен")
            return False
        
        try:
            self.keep = gkeepapi.Keep()
            success = self.keep.login(email, password)
            if success:
                self.authenticated = True
                logger.info("Успешная авторизация в Google Keep")
            else:
                logger.error("Ошибка авторизации в Google Keep")
            return success
        except Exception as e:
            logger.error(f"Ошибка при авторизации в Google Keep: {e}")
            return False
    
    def sync_from_keep(self) -> Tuple[bool, List[Tuple[Note, Note, str]]]:
        """
        Синхронизирует заметки из Google Keep в локальную базу.
        
        Returns:
            Кортеж (успех, список конфликтов)
        """
        if not self.authenticated or not self.keep:
            logger.error("Не авторизован в Google Keep")
            return False, []
        
        try:
            local_notes = self.db_manager.get_all_notes()
            local_dict = {note.id: note for note in local_notes if note.id is not None}
            
            # Получаем заметки из Google Keep
            keep_notes = self.keep.all()
            conflicts = []
            synced_count = 0
            
            for gnote in keep_notes:
                # Преобразуем заметку Google Keep в нашу модель
                note = self._keep_note_to_note(gnote)
                
                # Ищем по заголовку (так как ID в Google Keep другой)
                matching_local = None
                for local_note in local_notes:
                    if local_note.title == note.title and abs(
                        (local_note.updated_at - note.updated_at).total_seconds()
                    ) < 60:  # Примерно одинаковое время
                        matching_local = local_note
                        break
                
                if matching_local:
                    # Проверяем конфликт
                    if note.updated_at > matching_local.updated_at:
                        conflicts.append((matching_local, note, "keep_newer"))
                    elif note.updated_at < matching_local.updated_at:
                        # Локальная версия новее
                        synced_count += 1
                else:
                    # Новая заметка из Keep
                    self.db_manager.sync_note(note)
                    synced_count += 1
            
            logger.info(f"Синхронизация из Keep завершена. Синхронизировано: {synced_count}, конфликтов: {len(conflicts)}")
            return True, conflicts
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации из Google Keep: {e}")
            return False, []
    
    def sync_to_keep(self) -> bool:
        """
        Синхронизирует заметки из локальной базы в Google Keep.
        
        Returns:
            True, если синхронизация успешна
        """
        if not self.authenticated or not self.keep:
            logger.error("Не авторизован в Google Keep")
            return False
        
        try:
            local_notes = self.db_manager.get_all_notes()
            keep_notes = {note.title: note for note in self.keep.all()}
            
            synced_count = 0
            for local_note in local_notes:
                if local_note.title not in keep_notes:
                    # Создаем новую заметку в Keep
                    gnote = self.keep.createNote(local_note.title, local_note.content)
                    synced_count += 1
                else:
                    # Обновляем существующую
                    gnote = keep_notes[local_note.title]
                    gnote.title = local_note.title
                    gnote.text = local_note.content
                    gnote.save()
                    synced_count += 1
            
            self.keep.sync()
            logger.info(f"Синхронизация в Keep завершена. Синхронизировано: {synced_count}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации в Google Keep: {e}")
            return False
    
    def _keep_note_to_note(self, gnote) -> Note:
        """
        Преобразует заметку Google Keep в нашу модель Note.
        
        Args:
            gnote: Заметка из Google Keep
            
        Returns:
            Объект Note
        """
        # Используем timestamp из Google Keep или текущее время
        updated_at = datetime.fromtimestamp(gnote.timestamps.updated / 1000000) if hasattr(gnote, 'timestamps') else datetime.now()
        created_at = datetime.fromtimestamp(gnote.timestamps.created / 1000000) if hasattr(gnote, 'timestamps') else datetime.now()
        
        return Note(
            id=None,  # ID будет присвоен при сохранении в БД
            title=gnote.title or "Без названия",
            content=gnote.text or "",
            created_at=created_at,
            updated_at=updated_at
        )

