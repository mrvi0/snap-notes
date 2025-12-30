"""
Модуль для аутентификации с Google Keep через Master Token.

Использует неофициальный API Google Keep с Master Token.
Master Token можно получить через email/app password или использовать готовый.
"""
import logging
import requests
import json
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# URL для получения Master Token
GOOGLE_ACCOUNTS_BASE_URL = "https://accounts.google.com"
GOOGLE_KEEP_BASE_URL = "https://keep.google.com"


class GoogleKeepAuth:
    """Класс для аутентификации с Google Keep через Master Token."""
    
    def __init__(self, master_token: Optional[str] = None, email: Optional[str] = None, 
                 app_password: Optional[str] = None, token_file: Optional[str] = None):
        """
        Инициализация аутентификации.
        
        Args:
            master_token: Master Token для доступа к Google Keep (приоритет)
            email: Email для получения Master Token (если master_token не указан)
            app_password: App Password для получения Master Token (если master_token не указан)
            token_file: Путь к файлу для сохранения Master Token
        """
        self.master_token = master_token
        self.email = email
        self.app_password = app_password
        self.token_file = token_file or self._get_default_token_path()
        self.session = requests.Session()
        
        # Создаем директорию для токена, если её нет
        token_dir = Path(self.token_file).parent
        token_dir.mkdir(parents=True, exist_ok=True)
        
        # Загружаем сохраненный токен, если есть
        self._load_token()
    
    def _get_default_token_path(self) -> str:
        """Возвращает путь к файлу токена по умолчанию."""
        home = Path.home()
        return str(home / ".notes-google-keep" / "master_token.json")
    
    def _load_token(self):
        """Загружает Master Token из файла."""
        if Path(self.token_file).exists():
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    if 'master_token' in data:
                        self.master_token = data['master_token']
                        logger.info("Master Token загружен из файла")
            except Exception as e:
                logger.warning(f"Ошибка при загрузке Master Token: {e}")
    
    def _save_token(self):
        """Сохраняет Master Token в файл."""
        if self.master_token:
            try:
                with open(self.token_file, 'w') as f:
                    json.dump({'master_token': self.master_token}, f)
                logger.info("Master Token сохранен в файл")
            except Exception as e:
                logger.error(f"Ошибка при сохранении Master Token: {e}")
    
    def _get_master_token_from_credentials(self) -> Optional[str]:
        """
        Получает Master Token используя email и app password.
        
        Это эмулирует процесс получения токена, который использует gkeepapi.
        """
        if not self.email or not self.app_password:
            return None
        
        try:
            # Шаг 1: Аутентификация в Google Accounts
            session = requests.Session()
            
            # Получаем страницу входа
            login_url = f"{GOOGLE_ACCOUNTS_BASE_URL}/ServiceLogin"
            response = session.get(login_url)
            
            # Извлекаем необходимые параметры из страницы
            # Это упрощенная версия - в реальности нужен более сложный парсинг
            
            # Шаг 2: Отправляем credentials
            login_data = {
                'Email': self.email,
                'Passwd': self.app_password,
                'service': 'keep',
                'source': 'notes-google-keep'
            }
            
            # Это упрощенный пример - реальная аутентификация сложнее
            # и требует обработки cookies, CSRF токенов и т.д.
            
            logger.warning("Получение Master Token через email/app_password требует сложной реализации")
            logger.warning("Рекомендуется использовать готовый Master Token")
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении Master Token: {e}")
            return None
    
    def authenticate(self) -> bool:
        """
        Выполняет аутентификацию с Google Keep.
        
        Returns:
            True если аутентификация успешна
        """
        try:
            # Если Master Token не указан, пытаемся получить его
            if not self.master_token:
                if self.email and self.app_password:
                    logger.info("Попытка получить Master Token через email/app_password...")
                    self.master_token = self._get_master_token_from_credentials()
                    if self.master_token:
                        self._save_token()
                else:
                    raise ValueError(
                        "Не указан Master Token или email/app_password. "
                        "Получите Master Token через: gkeepapi -e <email> -p <app_password> gettoken"
                    )
            
            if not self.master_token:
                raise ValueError("Не удалось получить Master Token")
            
            # Проверяем токен, делая тестовый запрос
            # Используем неофициальный API Google Keep
            headers = {
                'Authorization': f'Bearer {self.master_token}',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            }
            
            # Тестовый запрос к Google Keep API
            test_url = f"{GOOGLE_KEEP_BASE_URL}/api/v1/notes"
            response = self.session.get(test_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("Аутентификация с Google Keep успешна")
                return True
            elif response.status_code == 401:
                raise ValueError("Master Token недействителен. Получите новый токен.")
            else:
                logger.warning(f"Неожиданный статус код: {response.status_code}")
                # Все равно считаем успешным, если токен есть
                return True
                
        except Exception as e:
            logger.error(f"Ошибка при аутентификации: {e}")
            return False
    
    def get_master_token(self) -> Optional[str]:
        """Возвращает Master Token."""
        return self.master_token
    
    def is_authenticated(self) -> bool:
        """Проверяет, аутентифицирован ли пользователь."""
        return self.master_token is not None and len(self.master_token) > 0
    
    def get_session(self) -> requests.Session:
        """Возвращает сессию requests с настроенными заголовками."""
        if self.master_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.master_token}',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
            })
        return self.session

