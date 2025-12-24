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
    
    def __init__(self, db_manager: DatabaseManager, email: str, password: str, master_token: Optional[str] = None):
        """
        Инициализация синхронизации с Google Keep.
        
        Args:
            db_manager: Менеджер базы данных
            email: Email для входа в Google Keep
            password: Пароль или токен приложения (может быть None, если используется master_token)
            master_token: Master token для аутентификации (альтернатива паролю)
        """
        if not HAS_GKEEPAPI:
            raise ImportError("gkeepapi не установлен. Установите: pip install gkeepapi")
        
        self.db_manager = db_manager
        self.email = email
        self.password = password
        self.master_token = master_token
        self.keep = gkeepapi.Keep()
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """
        Аутентифицируется в Google Keep.
        
        Пробует несколько методов аутентификации:
        1. Master token (если предоставлен)
        2. App Password через authenticate()
        3. App Password через login() (fallback)
        
        Примечание: Google может не принимать app passwords для некоторых аккаунтов.
        В этом случае рекомендуется использовать master token.
        
        Returns:
            True если аутентификация успешна
        """
        try:
            # Если есть master token, используем его
            if self.master_token:
                logger.info("Попытка аутентификации через master token")
                try:
                    self.keep.resume(self.email, self.master_token)
                    self._authenticated = True
                    logger.info("Успешная аутентификация в Google Keep через master token")
                    return True
                except Exception as token_error:
                    logger.warning(f"Master token не сработал: {token_error}, пробуем app password")
            
            # Если нет master token или он не сработал, пробуем app password
            if not self.password:
                logger.error("Нет ни master token, ни пароля для аутентификации")
                self._authenticated = False
                return False
            
            # Убираем все пробелы из токена (Google выдает токен с пробелами, но нужен без них)
            password_clean = self.password.replace(' ', '').strip()
            
            logger.info(f"Попытка аутентификации для email: {self.email}")
            logger.debug(f"Длина токена: {len(password_clean)} символов")
            
            # Пробуем сначала authenticate (новый метод)
            try:
                self.keep.authenticate(self.email, password_clean)
                self._authenticated = True
                logger.info("Успешная аутентификация в Google Keep через authenticate()")
                return True
            except Exception as auth_error:
                logger.warning(f"authenticate() не сработал: {auth_error}, пробуем login()")
                # Если authenticate не работает, пробуем старый метод login
                try:
                    self.keep.login(self.email, password_clean)
                    self._authenticated = True
                    logger.info("Успешная аутентификация в Google Keep через login()")
                    return True
                except Exception as login_error:
                    logger.error(f"login() также не сработал: {login_error}")
                    raise auth_error  # Выбрасываем оригинальную ошибку
                    
        except Exception as e:
            # Проверяем, является ли это ошибкой аутентификации
            error_str = str(e).lower()
            error_code = e.code if hasattr(e, 'code') else None
            if 'badauthentication' in error_str or 'login' in error_str or 'auth' in error_str:
                logger.error(f"Ошибка аутентификации в Google Keep: {e}, код: {error_code}")
                logger.error(
                    "Возможные причины:\n"
                    "1. Google больше не принимает app passwords для этого аккаунта\n"
                    "2. Токен приложения неверный или устарел\n"
                    "3. Нужно использовать master token (получить через gkeepapi CLI или скрипт)\n"
                    "4. Требуется OAuth 2.0 аутентификация"
                )
            else:
                logger.error(f"Неожиданная ошибка при аутентификации в Google Keep: {e}", exc_info=True)
            self._authenticated = False
            return False
    
    def get_master_token(self) -> Optional[str]:
        """
        Получает master token после успешной аутентификации.
        
        Master token можно использовать для последующих аутентификаций
        без необходимости вводить пароль.
        
        Returns:
            Master token или None, если не аутентифицирован
        """
        if not self._authenticated:
            return None
        try:
            return self.keep.getMasterToken()
        except Exception as e:
            logger.error(f"Ошибка при получении master token: {e}")
            return None
    
    def _markdown_to_keep_text(self, markdown_text: str) -> str:
        """
        Возвращает Markdown текст для Google Keep без изменений.
        
        Синхронизация полностью копирует все теги Markdown в том виде, в котором они есть,
        без переформатирования и прочего.
        
        Args:
            markdown_text: Текст в формате Markdown
            
        Returns:
            Markdown текст для Google Keep (без изменений)
        """
        # Возвращаем Markdown как есть, без каких-либо изменений
        return markdown_text
    
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
            for note in notes:
                # Отправляем Markdown как есть, без изменений
                keep_text = self._markdown_to_keep_text(note.markdown_content)
                
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

