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


class GoogleKeepOAuth:
    """Класс для OAuth 2.0 аутентификации с Google Keep."""
    
    def __init__(
        self, 
        credentials_file: Optional[str] = None, 
        token_file: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        project_id: Optional[str] = None
    ):
        """
        Инициализация OAuth аутентификации.
        
        Args:
            credentials_file: Путь к файлу с OAuth credentials (приоритет над client_id/secret)
            token_file: Путь к файлу для сохранения токена (по умолчанию: ~/.notes-google-keep/token.json)
            client_id: OAuth 2.0 Client ID (если не указан credentials_file)
            client_secret: OAuth 2.0 Client Secret (если не указан credentials_file)
            project_id: Project ID (опционально, если не указан credentials_file)
        """
        if not HAS_GOOGLE_AUTH:
            raise ImportError("google-auth не установлен. Установите: pip install google-auth google-auth-oauthlib")
        
        self.token_file = token_file or self._get_default_token_path()
        self.creds: Optional[Credentials] = None
        
        # Создаем директории, если их нет
        token_dir = Path(self.token_file).parent
        token_dir.mkdir(parents=True, exist_ok=True)
        
        # Определяем источник credentials: файл или поля ввода
        self.credentials_file = credentials_file
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_id = project_id
        
        # Проверяем наличие credentials
        if not self._has_credentials():
            raise ValueError(
                "OAuth credentials не найдены!\n\n"
                "Укажите один из вариантов:\n"
                "1. Путь к файлу credentials.json (credentials_file)\n"
                "2. Client ID и Client Secret (client_id, client_secret)\n\n"
                "Создайте OAuth 2.0 credentials в Google Cloud Console:\n"
                "https://console.cloud.google.com/apis/credentials\n\n"
                "См. README.md для подробных инструкций."
            )
    
    def _has_credentials(self) -> bool:
        """Проверяет наличие credentials (файл или поля ввода)."""
        # Проверяем файл
        if self.credentials_file:
            expanded_path = os.path.expanduser(self.credentials_file)
            if os.path.exists(expanded_path):
                return True
        
        # Проверяем поля ввода
        if self.client_id and self.client_secret:
            return True
        
        return False
    
    def _get_default_token_path(self) -> str:
        """Возвращает путь к файлу токена по умолчанию."""
        home = Path.home()
        return str(home / ".notes-google-keep" / "token.json")
    
    def _get_default_credentials_path(self) -> str:
        """Возвращает путь к файлу credentials по умолчанию."""
        home = Path.home()
        return str(home / ".notes-google-keep" / "credentials.json")
    
    def _load_client_config(self) -> Dict[str, Any]:
        """
        Загружает конфигурацию OAuth клиента из файла или полей ввода.
        
        Returns:
            Словарь с конфигурацией OAuth клиента
        """
        # Приоритет: файл > поля ввода
        if self.credentials_file:
            expanded_path = os.path.expanduser(self.credentials_file)
            if os.path.exists(expanded_path):
                try:
                    with open(expanded_path, 'r') as f:
                        config = json.load(f)
                    
                    # Проверяем формат файла
                    if 'installed' in config:
                        return config
                    elif 'web' in config:
                        # Если это web credentials, конвертируем в installed формат
                        web_config = config['web']
                        return {
                            "installed": {
                                "client_id": web_config.get('client_id'),
                                "client_secret": web_config.get('client_secret'),
                                "auth_uri": web_config.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth'),
                                "token_uri": web_config.get('token_uri', 'https://oauth2.googleapis.com/token'),
                                "auth_provider_x509_cert_url": web_config.get('auth_provider_x509_cert_url', 'https://www.googleapis.com/oauth2/v1/certs'),
                                "redirect_uris": ["http://localhost"]
                            }
                        }
                    else:
                        raise ValueError("Неверный формат credentials файла. Ожидается 'installed' или 'web' секция.")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Ошибка при чтении credentials файла (неверный JSON): {e}")
                except Exception as e:
                    raise ValueError(f"Ошибка при загрузке credentials файла: {e}")
        
        # Используем поля ввода
        if self.client_id and self.client_secret:
            config = {
                "installed": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost"]
                }
            }
            if self.project_id:
                config["installed"]["project_id"] = self.project_id
            return config
        
        raise ValueError("OAuth credentials не найдены. Укажите файл или client_id/client_secret.")
    
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
                    client_config = self._load_client_config()
                    flow = InstalledAppFlow.from_client_config(
                        client_config,
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

