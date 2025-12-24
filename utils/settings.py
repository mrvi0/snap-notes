"""
Модуль для управления настройками приложения.
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class Settings:
    """Класс для управления настройками приложения."""
    
    def __init__(self, config_file: str = "settings.json"):
        """
        Инициализация настроек.
        
        Args:
            config_file: Путь к файлу настроек
        """
        self.config_file = config_file
        self.settings: Dict[str, Any] = {
            "theme": "light",  # "light", "dark"
            "button_color": "#4CAF50",  # Цвет кнопок
            "font_size": 12,  # Размер шрифта в пунктах
            "auto_save": {
                "enabled": True,
                "delay": 1000  # миллисекунды
            },
            "google_keep": {
                "enabled": False,
                "email": "",
                "password": ""
            }
        }
        self.load()
    
    def load(self) -> None:
        """Загружает настройки из файла."""
        try:
            if Path(self.config_file).exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
                logger.info("Настройки загружены")
        except Exception as e:
            logger.error(f"Ошибка при загрузке настроек: {e}")
    
    def save(self) -> None:
        """Сохраняет настройки в файл."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            logger.info("Настройки сохранены")
        except Exception as e:
            logger.error(f"Ошибка при сохранении настроек: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Получает значение настройки.
        
        Args:
            key: Ключ настройки (можно использовать точечную нотацию, например "google_keep.enabled")
            default: Значение по умолчанию
            
        Returns:
            Значение настройки
        """
        keys = key.split('.')
        value = self.settings
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Устанавливает значение настройки.
        
        Args:
            key: Ключ настройки (можно использовать точечную нотацию)
            value: Значение для установки
        """
        keys = key.split('.')
        settings = self.settings
        for k in keys[:-1]:
            if k not in settings:
                settings[k] = {}
            settings = settings[k]
        settings[keys[-1]] = value
        self.save()

