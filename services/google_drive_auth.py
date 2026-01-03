"""
Модуль для аутентификации с Google Drive через OAuth 2.0.

Использует официальный Google Drive API с OAuth 2.0 для безопасной аутентификации.
"""
import logging
import os
import json
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Google Drive API scope
SCOPES = ['https://www.googleapis.com/auth/drive.file']


class GoogleDriveAuth:
    """Класс для аутентификации с Google Drive через OAuth 2.0."""
    
    def __init__(self, credentials_file: Optional[str] = None, 
                 token_file: Optional[str] = None):
        """
        Инициализация аутентификации.
        
        Args:
            credentials_file: Путь к файлу credentials.json (OAuth 2.0)
            token_file: Путь к файлу для сохранения токена
        """
        self.credentials_file = credentials_file or self._get_default_credentials_path()
        self.token_file = token_file or self._get_default_token_path()
        self.creds = None
        
        # Создаем директорию для токена, если её нет
        token_dir = Path(self.token_file).parent
        token_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_default_credentials_path(self) -> str:
        """Возвращает путь к файлу credentials по умолчанию."""
        home = Path.home()
        return str(home / ".notes-google-keep" / "credentials.json")
    
    def _get_default_token_path(self) -> str:
        """Возвращает путь к файлу токена по умолчанию."""
        home = Path.home()
        return str(home / ".notes-google-keep" / "token.json")
    
    def authenticate(self, parent_widget=None) -> bool:
        """
        Выполняет аутентификацию с Google Drive через OAuth 2.0.
        
        Args:
            parent_widget: Родительский виджет для показа диалога (опционально)
            
        Returns:
            True если аутентификация успешна
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            
            # Загружаем сохраненный токен, если есть
            if os.path.exists(self.token_file):
                self.creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
            
            # Если токен недействителен, обновляем или получаем новый
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    # Обновляем токен
                    self.creds.refresh(Request())
                else:
                    # Получаем новый токен через OAuth flow
                    if not os.path.exists(self.credentials_file):
                        raise FileNotFoundError(
                            f"Файл credentials.json не найден: {self.credentials_file}\n\n"
                            "Для получения credentials.json:\n"
                            "1. Перейдите на https://console.cloud.google.com/\n"
                            "2. Создайте проект (или выберите существующий)\n"
                            "3. Включите Google Drive API\n"
                            "4. Создайте OAuth 2.0 credentials (Desktop app)\n"
                            "5. Скачайте credentials.json\n"
                            "6. Сохраните в ~/.notes-google-keep/credentials.json"
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    # Запускаем OAuth flow
                    # Если есть parent_widget, можно использовать его для показа браузера
                    self.creds = flow.run_local_server(port=0)
                
                # Сохраняем токен для будущего использования
                self._save_token()
            
            logger.info("Аутентификация с Google Drive успешна")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Файл credentials.json не найден: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при аутентификации с Google Drive: {e}")
            raise
    
    def _save_token(self):
        """Сохраняет токен в файл."""
        if self.creds:
            try:
                with open(self.token_file, 'w') as token:
                    token.write(self.creds.to_json())
                logger.info("Токен сохранен в файл")
            except Exception as e:
                logger.error(f"Ошибка при сохранении токена: {e}")
    
    def get_credentials(self):
        """Возвращает credentials для использования в API."""
        if not self.creds:
            raise Exception("Не аутентифицирован. Вызовите authenticate() сначала.")
        return self.creds
    
    def is_authenticated(self) -> bool:
        """Проверяет, аутентифицирован ли пользователь."""
        return self.creds is not None and self.creds.valid

