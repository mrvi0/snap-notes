"""
Менеджер базы данных SQLite для заметок.
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
    
    def _get_connection(self) -> sqlite3.Connection:
        """Создает и возвращает соединение с базой данных."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self) -> None:
        """Инициализирует таблицу заметок в базе данных."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_markdown INTEGER DEFAULT 0
                )
            """)
            
            # Добавляем колонку is_markdown если её нет (для существующих БД)
            try:
                cursor.execute("ALTER TABLE notes ADD COLUMN is_markdown INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Колонка уже существует
            conn.commit()
            conn.close()
            logger.info("База данных инициализирована успешно")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise
    
    def create_note(self, title: str, content: str, is_markdown: bool = False) -> Note:
        """
        Создает новую заметку.
        
        Args:
            title: Заголовок заметки
            content: Содержимое заметки
            is_markdown: Использовать ли Markdown форматирование
            
        Returns:
            Созданная заметка с присвоенным ID
        """
        now = datetime.now().isoformat()
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notes (title, content, created_at, updated_at, is_markdown)
                VALUES (?, ?, ?, ?, ?)
            """, (title, content, now, now, 1 if is_markdown else 0))
            note_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Заметка создана с ID: {note_id}")
            return Note(
                id=note_id,
                title=title,
                content=content,
                created_at=datetime.fromisoformat(now),
                updated_at=datetime.fromisoformat(now),
                is_markdown=is_markdown
            )
        except sqlite3.Error as e:
            logger.error(f"Ошибка при создании заметки: {e}")
            raise
    
    def get_note(self, note_id: int) -> Optional[Note]:
        """
        Получает заметку по ID.
        
        Args:
            note_id: ID заметки
            
        Returns:
            Заметка или None, если не найдена
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return Note(
                    id=row['id'],
                    title=row['title'],
                    content=row['content'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    is_markdown=bool(row.get('is_markdown', 0))
                )
            return None
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении заметки: {e}")
            raise
    
    def get_all_notes(self) -> List[Note]:
        """
        Получает все заметки из базы данных.
        
        Returns:
            Список всех заметок
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notes ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            conn.close()
            
            notes = []
            for row in rows:
                notes.append(Note(
                    id=row['id'],
                    title=row['title'],
                    content=row['content'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            return notes
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении всех заметок: {e}")
            raise
    
    def update_note(self, note_id: int, title: str, content: str, is_markdown: bool = None) -> bool:
        """
        Обновляет заметку.
        
        Args:
            note_id: ID заметки
            title: Новый заголовок
            content: Новое содержимое
            is_markdown: Использовать ли Markdown форматирование (None - не менять)
            
        Returns:
            True, если обновление успешно, False иначе
        """
        now = datetime.now().isoformat()
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if is_markdown is not None:
                cursor.execute("""
                    UPDATE notes 
                    SET title = ?, content = ?, updated_at = ?, is_markdown = ?
                    WHERE id = ?
                """, (title, content, now, 1 if is_markdown else 0, note_id))
            else:
                cursor.execute("""
                    UPDATE notes 
                    SET title = ?, content = ?, updated_at = ?
                    WHERE id = ?
                """, (title, content, now, note_id))
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
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if success:
                logger.info(f"Заметка {note_id} удалена")
            else:
                logger.warning(f"Заметка {note_id} не найдена для удаления")
            return success
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении заметки: {e}")
            raise
    
    def search_notes(self, query: str) -> List[Note]:
        """
        Ищет заметки по заголовку и содержимому.
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список найденных заметок
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            cursor.execute("""
                SELECT * FROM notes 
                WHERE title LIKE ? OR content LIKE ?
                ORDER BY updated_at DESC
            """, (search_pattern, search_pattern))
            rows = cursor.fetchall()
            conn.close()
            
            notes = []
            for row in rows:
                notes.append(Note(
                    id=row['id'],
                    title=row['title'],
                    content=row['content'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at']),
                    is_markdown=bool(row.get('is_markdown', 0))
                ))
            return notes
        except sqlite3.Error as e:
            logger.error(f"Ошибка при поиске заметок: {e}")
            raise
    
    def sync_note(self, note: Note) -> Note:
        """
        Синхронизирует заметку (создает или обновляет) с сохранением оригинальных дат.
        
        Args:
            note: Заметка для синхронизации
            
        Returns:
            Синхронизированная заметка
        """
        if note.id is None:
            return self.create_note(note.title, note.content, note.is_markdown)
        else:
            # Проверяем, существует ли заметка
            existing = self.get_note(note.id)
            if existing:
                # Обновляем с сохранением оригинальных дат
                try:
                    conn = self._get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE notes 
                        SET title = ?, content = ?, created_at = ?, updated_at = ?, is_markdown = ?
                        WHERE id = ?
                    """, (
                        note.title,
                        note.content,
                        note.created_at.isoformat(),
                        note.updated_at.isoformat(),
                        1 if note.is_markdown else 0,
                        note.id
                    ))
                    conn.commit()
                    conn.close()
                    logger.info(f"Заметка {note.id} синхронизирована")
                    return self.get_note(note.id) or note
                except sqlite3.Error as e:
                    logger.error(f"Ошибка при синхронизации заметки: {e}")
                    raise
            else:
                # Если ID есть, но заметки нет, создаем новую с сохранением ID и дат
                # Используем INSERT OR REPLACE для избежания конфликтов
                try:
                    conn = self._get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO notes (id, title, content, created_at, updated_at, is_markdown)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        note.id,
                        note.title,
                        note.content,
                        note.created_at.isoformat(),
                        note.updated_at.isoformat(),
                        1 if note.is_markdown else 0
                    ))
                    conn.commit()
                    conn.close()
                    logger.info(f"Заметка {note.id} создана при синхронизации")
                    return self.get_note(note.id) or note
                except sqlite3.Error as e:
                    logger.error(f"Ошибка при создании заметки при синхронизации: {e}")
                    raise

