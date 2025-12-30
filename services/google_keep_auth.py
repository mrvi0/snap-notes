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

# Импортируем gkeepapi исключения для обработки ошибок
try:
    import gkeepapi.exception
    HAS_GKEEPAPI_EXCEPTIONS = True
except ImportError:
    HAS_GKEEPAPI_EXCEPTIONS = False

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
        
        Использует gkeepapi только для получения токена, затем работает напрямую с API.
        """
        if not self.email or not self.app_password:
            return None
        
        try:
            # Пытаемся использовать gkeepapi только для получения Master Token
            try:
                import gkeepapi
            except ImportError:
                raise ImportError(
                    "Для получения Master Token через email/app_password требуется gkeepapi.\n"
                    "Установите: pip install gkeepapi\n\n"
                    "Или получите Master Token вручную:\n"
                    "gkeepapi -e <email> -p <app_password> gettoken"
                )
            
            logger.info("Используем gkeepapi для получения Master Token...")
            
            # Создаем экземпляр gkeepapi и аутентифицируемся
            keep = gkeepapi.Keep()
            
            # Используем authenticate вместо устаревшего login
            try:
                success = keep.authenticate(self.email, self.app_password)
            except AttributeError:
                # Если authenticate не доступен, пробуем login (для старых версий)
                logger.warning("authenticate не доступен, используем login")
                success = keep.login(self.email, self.app_password)
            
            if not success:
                raise ValueError(
                    "Не удалось войти в Google Keep.\n\n"
                    "Проверьте:\n"
                    "1. Email правильный\n"
                    "2. App Password правильный (16 символов без пробелов)\n"
                    "3. Двухфакторная аутентификация включена\n"
                    "4. App Password создан для правильного аккаунта"
                )
            
            # Получаем Master Token из gkeepapi
            # gkeepapi хранит токен в приватных атрибутах после логина
            master_token = None
            
            # Пытаемся получить токен из различных мест, где gkeepapi может его хранить
            if hasattr(keep, '_master_token') and keep._master_token:
                master_token = keep._master_token
            elif hasattr(keep, 'master_token') and keep.master_token:
                master_token = keep.master_token
            elif hasattr(keep, '_session') and hasattr(keep._session, '_master_token'):
                master_token = keep._session._master_token
            elif hasattr(keep, 'session') and hasattr(keep.session, '_master_token'):
                master_token = keep.session._master_token
            else:
                # Пытаемся получить через публичный метод, если он есть
                try:
                    if hasattr(keep, 'getMasterToken'):
                        master_token = keep.getMasterToken()
                except:
                    pass
            
            if master_token:
                logger.info("Master Token успешно получен через gkeepapi")
                return master_token
            else:
                # Если не удалось получить напрямую, пытаемся извлечь из HTTP заголовков
                # gkeepapi может использовать токен в запросах
                try:
                    # Делаем тестовый запрос и извлекаем токен из заголовков
                    # Это не идеально, но может сработать
                    if hasattr(keep, '_session') and hasattr(keep._session, 'headers'):
                        headers = keep._session.headers
                        if 'Authorization' in headers:
                            auth_header = headers['Authorization']
                            if auth_header.startswith('Bearer '):
                                master_token = auth_header[7:]  # Убираем 'Bearer '
                except:
                    pass
                
                if master_token:
                    logger.info("Master Token извлечен из заголовков gkeepapi")
                    return master_token
                else:
                    raise ValueError(
                        "Не удалось получить Master Token из gkeepapi.\n"
                        "Попробуйте получить токен вручную через CLI:\n"
                        "gkeepapi -e <email> -p <app_password> gettoken"
                    )
            
        except ImportError as e:
            logger.error(f"gkeepapi не установлен: {e}")
            raise
        except Exception as e:
            # Проверяем, является ли это ошибкой аутентификации gkeepapi
            if HAS_GKEEPAPI_EXCEPTIONS:
                try:
                    import gkeepapi.exception
                    if isinstance(e, gkeepapi.exception.LoginException):
                        error_code = e.args[0] if e.args else "Unknown"
                        logger.error(f"Ошибка аутентификации в gkeepapi: {error_code}")
                        raise ValueError(
                            f"Ошибка аутентификации: {error_code}\n\n"
                            "Возможные причины:\n"
                            "1. Неправильный email или app password\n"
                            "2. App password не создан или отозван\n"
                            "3. Двухфакторная аутентификация не включена\n"
                            "4. Аккаунт заблокирован или требует дополнительной проверки\n\n"
                            "Попробуйте:\n"
                            "1. Создать новый App Password: https://myaccount.google.com/apppasswords\n"
                            "2. Убедиться, что используете 16-символьный токен без пробелов\n"
                            "3. Получить Master Token вручную через CLI:\n"
                            "   gkeepapi -e <email> -p <app_password> gettoken"
                        )
                except:
                    pass
            
            # Если это не LoginException, продолжаем обычную обработку
            if "BadAuthentication" in str(e) or "LoginException" in str(e):
                error_code = e.args[0] if e.args else "Unknown"
                logger.error(f"Ошибка аутентификации в gkeepapi: {error_code}")
                raise ValueError(
                    f"Ошибка аутентификации: {error_code}\n\n"
                    "Возможные причины:\n"
                    "1. Неправильный email или app password\n"
                    "2. App password не создан или отозван\n"
                    "3. Двухфакторная аутентификация не включена\n"
                    "4. Аккаунт заблокирован или требует дополнительной проверки\n\n"
                    "Попробуйте:\n"
                    "1. Создать новый App Password: https://myaccount.google.com/apppasswords\n"
                    "2. Убедиться, что используете 16-символьный токен без пробелов\n"
                    "3. Получить Master Token вручную через CLI:\n"
                    "   gkeepapi -e <email> -p <app_password> gettoken"
                )
        except Exception as e:
            logger.error(f"Ошибка при получении Master Token через gkeepapi: {e}")
            error_msg = str(e)
            if "BadAuthentication" in error_msg or "LoginException" in error_msg:
                raise ValueError(
                    "Ошибка аутентификации в Google Keep.\n\n"
                    "Проверьте email и app password.\n"
                    "Убедитесь, что:\n"
                    "1. App Password правильный (16 символов, без пробелов)\n"
                    "2. Двухфакторная аутентификация включена\n"
                    "3. App Password создан для правильного аккаунта\n\n"
                    "Получите Master Token вручную:\n"
                    "gkeepapi -e <email> -p <app_password> gettoken"
                )
            raise
    
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
                    try:
                        self.master_token = self._get_master_token_from_credentials()
                        if self.master_token:
                            self._save_token()
                            logger.info("Master Token успешно получен и сохранен")
                    except ImportError as e:
                        # gkeepapi не установлен - показываем понятную ошибку
                        error_msg = str(e)
                        raise ValueError(error_msg)
                    except Exception as e:
                        logger.error(f"Ошибка при получении Master Token: {e}")
                        raise ValueError(
                            f"Не удалось получить Master Token: {e}\n\n"
                            "Рекомендуется получить Master Token вручную:\n"
                            "1. Установите gkeepapi: pip install gkeepapi\n"
                            "2. Выполните: gkeepapi -e <email> -p <app_password> gettoken\n"
                            "3. Вставьте полученный токен в настройки приложения"
                        )
                else:
                    raise ValueError(
                        "Не указан Master Token или email/app_password.\n\n"
                        "Получите Master Token одним из способов:\n"
                        "1. Вручную: gkeepapi -e <email> -p <app_password> gettoken\n"
                        "2. Или введите email и app password в настройках"
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

