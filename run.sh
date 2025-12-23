#!/bin/bash
# Скрипт для запуска приложения заметок

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "Ошибка: Python3 не установлен"
    exit 1
fi

# Установка зависимостей, если нужно
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Запуск приложения
python3 main.py

