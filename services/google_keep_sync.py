"""
Модуль для синхронизации заметок с Google Keep.

Использует библиотеку gkeepapi для работы с Google Keep API.
"""
import logging
from typing import List, Optional, Tuple
from datetime import datetime

try:
    import gkeepapi
    from gkeepapi.node import Note as KeepNote, NodeType
    HAS_GKEEPAPI = True
except ImportError:
    HAS_GKEEPAPI = False
    logging.warning("gkeepapi не установлен, синхронизация с Google Keep недоступна")

from models import Note
from storage.database import DatabaseManager
from services.sync_manager import MarkdownLevel

logger = logging.getLogger(__name__)


class GoogleKeepSync:
    """Класс для синхронизации заметок с Google Keep."""
    
    def __init__(self, db_manager: DatabaseManager, email: str, password: str):
        """
        Инициализация синхронизации с Google Keep.
        
        Args:
            db_manager: Менеджер базы данных
            email: Email для входа в Google Keep
            password: Пароль или токен приложения
        """
        if not HAS_GKEEPAPI:
            raise ImportError("gkeepapi не установлен. Установите: pip install gkeepapi")
        
        self.db_manager = db_manager
        self.email = email
        self.password = password
        self.keep = gkeepapi.Keep()
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """
        Аутентифицируется в Google Keep.
        
        Returns:
            True если аутентификация успешна
        """
        try:
            self.keep.login(self.email, self.password)
            self._authenticated = True
            logger.info("Успешная аутентификация в Google Keep")
            return True
        except Exception as e:
            logger.error(f"Ошибка аутентификации в Google Keep: {e}")
            self._authenticated = False
            return False
    
    def _markdown_to_keep_text(self, markdown_text: str, downgrade_extended: bool = False) -> str:
        """
        Конвертирует Markdown в простой текст для Google Keep.
        
        Google Keep не поддерживает Markdown, поэтому конвертируем в plain text.
        Если есть расширенный Markdown, можно понизить до safe-уровня или предупредить.
        
        Args:
            markdown_text: Текст в формате Markdown
            downgrade_extended: Понижать ли расширенный markdown до safe-уровня
            
        Returns:
            Plain text для Google Keep
        """
        if downgrade_extended and MarkdownLevel.contains_extended_markdown(markdown_text):
            markdown_text = MarkdownLevel.downgrade_to_safe(markdown_text)
            logger.info("Markdown понижен до safe-уровня для Google Keep")
        
        # Простая конвертация Markdown в plain text
        import re
        
        # Убираем заголовки (оставляем только текст)
        text = re.sub(r'^#{1,6}\s+(.+)$', r'\1', markdown_text, flags=re.MULTILINE)
        
        # Убираем жирный (**text** -> text)
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        
        # Убираем курсив (*text* -> text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        
        # Убираем зачеркнутый (~~text~~ -> text)
        text = re.sub(r'~~([^~]+)~~', r'\1', text)
        
        # Убираем списки (оставляем только текст с отступом)
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Убираем цитаты (оставляем только текст)
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
        
        # Убираем inline код (оставляем только текст)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Убираем ссылки (оставляем только текст)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Убираем изображения (оставляем только alt-текст)
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', text)
        
        return text.strip()
    
    def _keep_text_to_markdown(self, keep_text: str) -> str:
        """
        Конвертирует текст из Google Keep в Markdown.
        
        Google Keep хранит только plain text, поэтому просто возвращаем текст.
        В будущем можно добавить эвристики для определения форматирования.
        
        Args:
            keep_text: Текст из Google Keep
            
        Returns:
            Markdown текст (пока просто plain text)
        """
        # Пока просто возвращаем текст как есть
        # В будущем можно добавить эвристики для определения заголовков, списков и т.д.
        return keep_text
    
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
            keep_notes = self.keep.all()
            notes = []
            
            for keep_note in keep_notes:
                if keep_note.type != NodeType.Note:
                    continue
                
                # Конвертируем Google Keep заметку в нашу модель
                title = keep_note.title or ""
                text = keep_note.text or ""
                
                # Конвертируем текст в Markdown
                markdown_content = self._keep_text_to_markdown(text)
                
                # Используем ID из Google Keep как внешний идентификатор
                # В нашей БД нужно будет хранить mapping между нашими ID и Keep ID
                note = Note(
                    id=None,  # Будет создан при сохранении
                    title=title,
                    markdown_content=markdown_content,
                    created_at=keep_note.timestamps.created if hasattr(keep_note.timestamps, 'created') else datetime.now(),
                    updated_at=keep_note.timestamps.updated if hasattr(keep_note.timestamps, 'updated') else datetime.now()
                )
                
                # Сохраняем Keep ID для будущей синхронизации
                # TODO: добавить поле keep_id в модель Note или создать mapping таблицу
                notes.append(note)
            
            logger.info(f"Загружено {len(notes)} заметок из Google Keep")
            return notes
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке заметок из Google Keep: {e}")
            raise
    
    def push_notes(self, notes: List[Note], downgrade_extended: bool = False) -> bool:
        """
        Отправляет заметки в Google Keep.
        
        Args:
            notes: Список заметок для отправки
            downgrade_extended: Понижать ли расширенный markdown до safe-уровня
            
        Returns:
            True если успешно
        """
        if not self._authenticated:
            if not self.authenticate():
                raise Exception("Не удалось аутентифицироваться в Google Keep")
        
        try:
            for note in notes:
                # Конвертируем Markdown в plain text
                keep_text = self._markdown_to_keep_text(note.markdown_content, downgrade_extended)
                
                # Создаем или обновляем заметку в Google Keep
                # TODO: реализовать обновление существующих заметок по keep_id
                keep_note = self.keep.createNote(note.title, keep_text)
                logger.info(f"Заметка '{note.title}' отправлена в Google Keep")
            
            # Синхронизируем изменения
            self.keep.sync()
            logger.info(f"Отправлено {len(notes)} заметок в Google Keep")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке заметок в Google Keep: {e}")
            raise
    
    def sync(self, downgrade_extended: bool = False) -> Tuple[bool, List[Tuple[Note, Note, str]]]:
        """
        Синхронизирует заметки с Google Keep (двусторонняя синхронизация).
        
        Args:
            downgrade_extended: Понижать ли расширенный markdown до safe-уровня
            
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
            
            # Отправляем локальные заметки в Keep
            self.push_notes(local_notes, downgrade_extended)
            
            logger.info("Синхронизация с Google Keep завершена успешно")
            return True, conflicts
            
        except Exception as e:
            logger.error(f"Ошибка при синхронизации с Google Keep: {e}")
            return False, []

