"""
Модуль для работы с Google Drive API.

Использует официальный Google Drive API для хранения заметок как .md файлов.
"""
import logging
import io
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import Note
from storage.database import DatabaseManager
from services.google_drive_auth import GoogleDriveAuth

logger = logging.getLogger(__name__)

# ID папки для заметок в Google Drive
NOTES_FOLDER_NAME = "Notes App"


class GoogleDriveAPI:
    """Класс для работы с Google Drive через официальный API."""
    
    def __init__(self, db_manager: DatabaseManager, auth: GoogleDriveAuth):
        """
        Инициализация API клиента.
        
        Args:
            db_manager: Менеджер базы данных
            auth: Экземпляр GoogleDriveAuth для аутентификации
        """
        self.db_manager = db_manager
        self.auth = auth
        self.creds = None
        self.service = None
        self.notes_folder_id = None
        self._authenticated = False
    
    def authenticate(self) -> bool:
        """
        Аутентифицируется через OAuth 2.0.
        
        Returns:
            True если успешно
        """
        if not self.auth.is_authenticated():
            if not self.auth.authenticate():
                return False
        
        try:
            from googleapiclient.discovery import build
            from googleapiclient.errors import HttpError
            
            self.creds = self.auth.get_credentials()
            self.service = build('drive', 'v3', credentials=self.creds)
            
            # Получаем или создаем папку для заметок
            self.notes_folder_id = self._get_or_create_notes_folder()
            
            self._authenticated = True
            logger.info("Аутентификация в Google Drive API успешна")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при аутентификации в Google Drive API: {e}")
            return False
    
    def _get_or_create_notes_folder(self) -> str:
        """
        Получает или создает папку для заметок в Google Drive.
        
        Returns:
            ID папки
        """
        try:
            # Ищем существующую папку
            query = f"name='{NOTES_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                folder_id = items[0]['id']
                logger.info(f"Найдена папка '{NOTES_FOLDER_NAME}' с ID: {folder_id}")
                return folder_id
            
            # Создаем новую папку
            file_metadata = {
                'name': NOTES_FOLDER_NAME,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            logger.info(f"Создана папка '{NOTES_FOLDER_NAME}' с ID: {folder_id}")
            return folder_id
            
        except Exception as e:
            logger.error(f"Ошибка при получении/создании папки: {e}")
            raise
    
    def fetch_notes(self) -> List[Note]:
        """
        Загружает заметки из Google Drive.
        
        Returns:
            Список заметок
        """
        if not self._authenticated:
            if not self.authenticate():
                raise Exception("Не удалось аутентифицироваться")
        
        try:
            # Получаем все .md файлы из папки заметок
            # Используем поиск по расширению файла
            query = f"'{self.notes_folder_id}' in parents and name contains '.md' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name, modifiedTime)'
            ).execute()
            
            items = results.get('files', [])
            notes = []
            
            for item in items:
                file_id = item['id']
                file_name = item['name']
                
                # Пропускаем файлы, которые не заканчиваются на .md
                if not file_name.endswith('.md'):
                    continue
                
                # Получаем содержимое файла
                try:
                    from googleapiclient.http import MediaIoBaseDownload
                    import io
                    
                    request = self.service.files().get_media(fileId=file_id)
                    file_content = io.BytesIO()
                    downloader = MediaIoBaseDownload(file_content, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                    
                    file_content.seek(0)
                    content = file_content.read().decode('utf-8')
                    
                    # Извлекаем название заметки из имени файла (без .md)
                    title = file_name[:-3] if file_name.endswith('.md') else file_name
                    
                    # Парсим дату изменения
                    modified_time = item.get('modifiedTime', '')
                    updated_at = None
                    if modified_time:
                        try:
                            from dateutil import parser
                            updated_at = parser.parse(modified_time)
                        except:
                            updated_at = datetime.now()
                    
                    note = Note(
                        id=None,  # Будет установлен при синхронизации
                        title=title,
                        markdown_content=content,
                        created_at=updated_at or datetime.now(),
                        updated_at=updated_at or datetime.now()
                    )
                    
                    # Сохраняем file_id для будущих обновлений
                    # Можно добавить поле drive_file_id в модель Note
                    notes.append(note)
                    
                except Exception as e:
                    logger.error(f"Ошибка при загрузке файла {file_name}: {e}")
                    continue
            
            logger.info(f"Загружено {len(notes)} заметок из Google Drive")
            return notes
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке заметок из Google Drive: {e}", exc_info=True)
            raise
    
    def push_note(self, note: Note) -> bool:
        """
        Отправляет заметку в Google Drive.
        
        Args:
            note: Заметка для отправки
            
        Returns:
            True если успешно
        """
        if not self._authenticated:
            if not self.authenticate():
                raise Exception("Не удалось аутентифицироваться")
        
        try:
            file_name = f"{note.title}.md"
            
            # Ищем существующий файл
            query = f"'{self.notes_folder_id}' in parents and name='{file_name}' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id)'
            ).execute()
            
            items = results.get('files', [])
            
            # Подготавливаем содержимое файла
            from googleapiclient.http import MediaIoBaseUpload
            
            file_content = note.markdown_content.encode('utf-8')
            media_body = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype='text/plain',
                resumable=True
            )
            
            if items:
                # Обновляем существующий файл
                file_id = items[0]['id']
                self.service.files().update(
                    fileId=file_id,
                    media_body=media_body
                ).execute()
                logger.info(f"Заметка '{note.title}' обновлена в Google Drive")
            else:
                # Создаем новый файл
                file_metadata = {
                    'name': file_name,
                    'parents': [self.notes_folder_id]
                }
                self.service.files().create(
                    body=file_metadata,
                    media_body=media_body,
                    fields='id'
                ).execute()
                logger.info(f"Заметка '{note.title}' создана в Google Drive")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке заметки в Google Drive: {e}", exc_info=True)
            raise
    
    def push_notes(self, notes: List[Note]) -> bool:
        """
        Отправляет несколько заметок в Google Drive.
        
        Args:
            notes: Список заметок
            
        Returns:
            True если успешно
        """
        for note in notes:
            self.push_note(note)
        
        logger.info(f"Отправлено {len(notes)} заметок в Google Drive")
        return True

