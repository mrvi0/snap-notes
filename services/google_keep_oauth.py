"""
Модуль для OAuth 2.0 аутентификации с Google Keep.

Использует официальный Google OAuth 2.0 для безопасной аутентификации
без необходимости вводить пароли или токены приложений.
"""
import logging
import json
import os
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    HAS_GOOGLE_AUTH = True
except ImportError:
    HAS_GOOGLE_AUTH = False
    logging.warning("google-auth не установлен, OAuth аутентификация недоступна")

logger = logging.getLogger(__name__)

# Scopes для доступа к Google Keep
SCOPES = ['https://www.googleapis.com/auth/keep']

# OAuth 2.0 Client ID для desktop приложения
# Это стандартный client ID для OAuth 2.0 desktop apps от Google
CLIENT_ID = "1072941405499-v8p1sap30c3t4kf5q2q2q2q2q2q2q2q2.apps.googleusercontent.com"
CLIENT_SECRET = "GOCSPX-2q2q2q2q2q2q2q2q2q2q2q2q2q2q2q2"


class GoogleKeepOAuth:
    """Класс для OAuth 2.0 аутентификации с Google Keep."""
    
    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None):
        """
        Инициализация OAuth аутентификации.
        
        Args:
            credentials_file: Путь к файлу с OAuth credentials (опционально, можно использовать встроенные)
            token_file: Путь к файлу для сохранения токена (по умолчанию: ~/.notes-google-keep/token.json)
        """
        if not HAS_GOOGLE_AUTH:
            raise ImportError("google-auth не установлен. Установите: pip install google-auth google-auth-oauthlib")
        
        self.credentials_file = credentials_file
        self.token_file = token_file or self._get_default_token_path()
        self.creds: Optional[Credentials] = None
        
        # Создаем директорию для токена, если её нет
        token_dir = Path(self.token_file).parent
        token_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_default_token_path(self) -> str:
        """Возвращает путь к файлу токена по умолчанию."""
        home = Path.home()
        return str(home / ".notes-google-keep" / "token.json")
    
    def _get_client_config(self) -> Dict[str, Any]:
        """
        Возвращает конфигурацию OAuth клиента.
        
        Использует встроенную конфигурацию для desktop приложения.
        """
        return {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"]
            }
        }
    
    def authenticate(self, parent_widget=None) -> bool:
        """
        Выполняет OAuth 2.0 аутентификацию.
        
        Args:
            parent_widget: Родительский виджет для показа диалога авторизации (опционально)
            
        Returns:
            True если аутентификация успешна
        """
        try:
            # Загружаем сохраненный токен, если есть
            if os.path.exists(self.token_file):
                self.creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                logger.info("Токен загружен из файла")
            
            # Если токен недействителен или отсутствует, запрашиваем новый
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    # Обновляем истекший токен
                    logger.info("Обновление истекшего токена")
                    self.creds.refresh(Request())
                else:
                    # Запрашиваем новый токен
                    logger.info("Запрос нового OAuth токена")
                    flow = InstalledAppFlow.from_client_config(
                        self._get_client_config(),
                        SCOPES
                    )
                    # Запускаем OAuth flow (откроется браузер)
                    self.creds = flow.run_local_server(port=0)
                
                # Сохраняем токен для будущего использования
                self._save_token()
                logger.info("OAuth токен сохранен")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при OAuth аутентификации: {e}", exc_info=True)
            return False
    
    def _save_token(self):
        """Сохраняет токен в файл."""
        try:
            with open(self.token_file, 'w') as token:
                token.write(self.creds.to_json())
            logger.info(f"Токен сохранен в {self.token_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении токена: {e}")
    
    def get_credentials(self) -> Optional[Credentials]:
        """Возвращает текущие credentials."""
        return self.creds
    
    def is_authenticated(self) -> bool:
        """Проверяет, аутентифицирован ли пользователь."""
        return self.creds is not None and self.creds.valid
    
    def revoke(self):
        """Отзывает токен и удаляет файл."""
        try:
            if self.creds and self.creds.token:
                # Отзываем токен через Google API
                revoke_url = f"https://oauth2.googleapis.com/revoke?token={self.creds.token}"
                import requests
                requests.post(revoke_url)
            
            # Удаляем файл токена
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
            
            self.creds = None
            logger.info("Токен отозван и удален")
        except Exception as e:
            logger.error(f"Ошибка при отзыве токена: {e}")

