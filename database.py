"""
Менеджер базы данных SQLite для заметок.

Все заметки хранятся в формате Markdown.
HTML не используется.
"""
import sqlite3
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from models import Note

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Класс для управления базой данных заметок."""
    
    def __init__(self, db_path: str = "notes.db"):
        """
        Инициализация менеджера базы данных.
        
        Args:
            db_path: Путь к файлу базы данных SQLite
        """
        self.db_path = db_path
        self._init_database()
        self._migrate_old_schema()
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Создает и возвращает соединение с базой данных.
        
        Использует timeout для предотвращения блокировок.
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Включаем WAL режим для лучшей производительности и предотвращения блокировок
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass  # Игнорируем ошибки при установке WAL
        return conn
    
    def _init_database(self) -> None:
        """
        Инициализирует таблицу заметок в базе данных.
        
        Все заметки хранятся в формате Markdown в поле markdown_content.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    markdown_content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()
            conn.close()
            logger.info("База данных инициализирована успешно")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise
    
    def _migrate_old_schema(self) -> None:
        """
        Мигрирует старую схему БД (content, is_markdown) в новую (markdown_content).
        
        Это одноразовая миграция для совместимости со старыми базами данных.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Проверяем структуру таблицы
            cursor.execute("PRAGMA table_info(notes)")
            columns_info = cursor.fetchall()
            columns = [col[1] for col in columns_info]
            
            # Если есть старая колонка content, но нет markdown_content
            if 'content' in columns and 'markdown_content' not in columns:
                logger.info("Миграция: добавление колонки markdown_content")
                cursor.execute("ALTER TABLE notes ADD COLUMN markdown_content TEXT")
                
                # Копируем данные из content в markdown_content
                cursor.execute("UPDATE notes SET markdown_content = content WHERE markdown_content IS NULL OR markdown_content = ''")
                cursor.execute("UPDATE notes SET markdown_content = '' WHERE markdown_content IS NULL")
                
                conn.commit()
                logger.info("Миграция завершена: данные скопированы в markdown_content")
            
            # Если есть обе колонки, убеждаемся что markdown_content заполнена
            if 'content' in columns and 'markdown_content' in columns:
                cursor.execute("UPDATE notes SET markdown_content = content WHERE markdown_content IS NULL OR markdown_content = ''")
                conn.commit()
            
            conn.close()
        except sqlite3.Error as e:
            logger.warning(f"Ошибка при миграции схемы (можно игнорировать): {e}")
    
    def create_note(self, title: str, markdown_content: str) -> Note:
        """
        Создает новую заметку.
        
        Args:
            title: Заголовок заметки
            markdown_content: Содержимое заметки в формате Markdown
            
        Returns:
            Созданная заметка с присвоенным ID
        """
        now = datetime.now().isoformat()
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Проверяем, есть ли старая колонка content
            cursor.execute("PRAGMA table_info(notes)")
            columns = [col[1] for col in cursor.fetchall()]
            has_old_content = 'content' in columns
            
            if has_old_content:
                # Если есть старая колонка, заполняем её тоже (для совместимости)
                cursor.execute("""
                    INSERT INTO notes (title, markdown_content, content, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (title, markdown_content, markdown_content, now, now))
            else:
                # Новая схема - только markdown_content
                cursor.execute("""
                    INSERT INTO notes (title, markdown_content, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (title, markdown_content, now, now))
            
            note_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Заметка создана с ID: {note_id}")
            return Note(
                id=note_id,
                title=title,
                markdown_content=markdown_content,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now)
            )
        except sqlite3.Error as e:
            logger.error(f"Ошибка при создании заметки: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_note(self, note_id: int) -> Optional[Note]:
        """
        Получает заметку по ID.
        
        Args:
            note_id: ID заметки
            
        Returns:
            Заметка или None, если не найдена
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            
            if row:
                # Поддержка старой схемы для обратной совместимости
                if 'markdown_content' in row.keys():
                    content = row['markdown_content']
                elif 'content' in row.keys():
                    content = row['content']
                else:
                    content = ''
                return Note(
                    id=row['id'],
                    title=row['title'],
                    markdown_content=content,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                )
            return None
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении заметки: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_all_notes(self) -> List[Note]:
        """
        Получает все заметки из базы данных.
        
        Returns:
            Список всех заметок
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            
            notes = []
            for row in rows:
                # Поддержка старой схемы для обратной совместимости
                if 'markdown_content' in row.keys():
                    content = row['markdown_content']
                elif 'content' in row.keys():
                    content = row['content']
                else:
                    content = ''
                notes.append(Note(
                    id=row['id'],
                    title=row['title'],
                    markdown_content=content,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            return notes
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении всех заметок: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def update_note(self, note_id: int, title: str, markdown_content: str) -> bool:
        """
        Обновляет заметку.
        
        Args:
            note_id: ID заметки
            title: Новый заголовок
            markdown_content: Новое содержимое в формате Markdown
            
        Returns:
            True, если обновление успешно, False иначе
        """
        now = datetime.now().isoformat()
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE notes 
                SET title = ?, markdown_content = ?, updated_at = ?
                WHERE id = ?
            """, (title, markdown_content, now, note_id))
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                logger.info(f"Заметка {note_id} обновлена")
            else:
                logger.warning(f"Заметка {note_id} не найдена для обновления")
            return success
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении заметки: {e}")
            raise
    
    def delete_note(self, note_id: int) -> bool:
        """
        Удаляет заметку.
        
        Args:
            note_id: ID заметки
            
        Returns:
            True, если удаление успешно, False иначе
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                logger.info(f"Заметка {note_id} удалена")
            else:
                logger.warning(f"Заметка {note_id} не найдена для удаления")
            return success
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении заметки: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def search_notes(self, query: str) -> List[Note]:
        """
        Ищет заметки по заголовку и содержимому.
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список найденных заметок
        """
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT * FROM notes 
                WHERE title LIKE ? OR markdown_content LIKE ?
                ORDER BY updated_at DESC
            """, (search_pattern, search_pattern))
            rows = cursor.fetchall()
            
            notes = []
            for row in rows:
                # Поддержка старой схемы для обратной совместимости
                if 'markdown_content' in row.keys():
                    content = row['markdown_content']
                elif 'content' in row.keys():
                    content = row['content']
                else:
                    content = ''
                notes.append(Note(
                    id=row['id'],
                    title=row['title'],
                    markdown_content=content,
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            return notes
        except sqlite3.Error as e:
            logger.error(f"Ошибка при поиске заметок: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def sync_note(self, note: Note) -> Note:
        """
        Синхронизирует заметку (создает или обновляет) с сохранением оригинальных дат.
        
        Args:
            note: Заметка для синхронизации
            
        Returns:
            Синхронизированная заметка
        """
        if note.id is None:
            return self.create_note(note.title, note.markdown_content)
        else:
            # Проверяем, существует ли заметка
            existing = self.get_note(note.id)
            if existing:
                # Обновляем с сохранением оригинальных дат
                conn = None
                try:
                    conn = self._get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE notes 
                        SET title = ?, markdown_content = ?, created_at = ?, updated_at = ?
                        WHERE id = ?
                    """, (
                        note.title,
                        note.markdown_content,
                        note.created_at.isoformat(),
                        note.updated_at.isoformat(),
                        note.id
                    ))
                    conn.commit()
                    logger.info(f"Заметка {note.id} синхронизирована")
                    return self.get_note(note.id) or note
                except sqlite3.Error as e:
                    logger.error(f"Ошибка при синхронизации заметки: {e}")
                    raise
                finally:
                    if conn:
                        conn.close()
            else:
                # Если ID есть, но заметки нет, создаем новую с сохранением ID и дат
                conn = None
                try:
                    conn = self._get_connection()
                    cursor = conn.cursor()
                    
                    # Проверяем, есть ли старая колонка content
                    cursor.execute("PRAGMA table_info(notes)")
                    columns = [col[1] for col in cursor.fetchall()]
                    has_old_content = 'content' in columns
                    
                    if has_old_content:
                        # Если есть старая колонка, указываем её тоже (для совместимости)
                        cursor.execute("""
                            INSERT OR REPLACE INTO notes (id, title, markdown_content, content, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            note.id,
                            note.title,
                            note.markdown_content,
                            note.markdown_content,  # Дублируем в content для совместимости
                            note.created_at.isoformat(),
                            note.updated_at.isoformat()
                        ))
                    else:
                        # Новая схема - только markdown_content
                        cursor.execute("""
                            INSERT OR REPLACE INTO notes (id, title, markdown_content, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            note.id,
                            note.title,
                            note.markdown_content,
                            note.created_at.isoformat(),
                            note.updated_at.isoformat()
                        ))
                    
                    conn.commit()
                    logger.info(f"Заметка {note.id} создана при синхронизации")
                    return self.get_note(note.id) or note
                except sqlite3.Error as e:
                    logger.error(f"Ошибка при создании заметки при синхронизации: {e}")
                    raise
                finally:
                    if conn:
                        conn.close()
