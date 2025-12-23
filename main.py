#!/usr/bin/env python3
"""
Главный файл для запуска приложения заметок.
"""
import sys
import logging
from PyQt5.QtWidgets import QApplication

from gui import NotesMainWindow

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('notes_app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Точка входа в приложение."""
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Заметки")
        
        window = NotesMainWindow()
        window.show()
        
        logger.info("Приложение запущено")
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске приложения: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

