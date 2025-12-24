# Notes Application - Markdown Editor

Полнофункциональное desktop-приложение для заметок на Python + PyQt6 с поддержкой Markdown.

## Архитектурные принципы

- **Markdown - единственный канонический формат хранения заметок**
- HTML не используется ни для хранения, ни как промежуточный формат
- Любое форматирование обратимо без деградации Markdown

## Возможности

### Редактор

- **Визуальное форматирование** через toolbar:
  - Bold (**)
  - Italic (*)
  - Heading (H1–H3 через #)
  - Bullet list (-)
  - Quote (>)
  - Inline code (`)

- **Два режима работы**:
  1. **Visual Markdown mode**: визуальное представление с форматированием
  2. **Raw Markdown mode**: чистый markdown-текст без визуальных элементов

- Переключение режимов **НЕ меняет** содержимое markdown-текста

### Хранение

- Локальное хранение через SQLite
- Каждая заметка содержит:
  - `id`
  - `title`
  - `markdown_content` (TEXT) - **только Markdown**
  - `created_at`
  - `updated_at`

### Настройки внешнего вида

- Выбор темы: светлая, темная, системная
- Выбор цвета кнопок из палитры
- Настройка размера шрифта (8-24pt):
  - Размер применяется ко всем элементам интерфейса
  - Заголовки автоматически на 6pt больше основного размера
  - Обычный текст использует выбранный размер

## Установка и запуск

### Требования

- Python 3.8+
- PyQt6
- Ubuntu (или другая Linux система)

### Установка зависимостей

```bash
# Создайте виртуальное окружение (рекомендуется)
python3 -m venv venv
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

**Примечание**: QMarkdownTextEdit не является стандартным пакетом. Приложение использует встроенную поддержку Markdown в PyQt6 QTextEdit через методы `setMarkdown()` и `toMarkdown()`. Если требуется использовать библиотеку QMarkdownTextEdit от pbek, установите её вручную из [репозитория](https://github.com/pbek/QMarkdownTextEdit).

### Запуск

```bash
python3 main.py
```

Или используйте скрипт:

```bash
./run.sh
```

## Синхронизация с Google Keep

Приложение поддерживает синхронизацию заметок с Google Keep через **OAuth 2.0**.

### Настройка OAuth 2.0 credentials

**Важно:** Для безопасности и приватности каждый пользователь должен создать свои собственные OAuth credentials в Google Cloud Console. Это гарантирует, что только вы имеете доступ к своим данным.

#### Шаг 1: Создание OAuth credentials в Google Cloud Console

1. **Перейдите в Google Cloud Console**:
   - Откройте [Google Cloud Console](https://console.cloud.google.com/)
   - Войдите в свой Google аккаунт

2. **Создайте новый проект** (или выберите существующий):
   - Нажмите на выпадающий список проектов вверху
   - Нажмите "New Project"
   - Введите имя проекта (например, "Notes App")
   - Нажмите "Create"

3. **Включите Google Keep API**:
   - Перейдите в [API Library](https://console.cloud.google.com/apis/library)
   - Найдите "Google Keep API" (если доступен) или используйте общий Google API
   - Нажмите "Enable"

4. **Создайте OAuth 2.0 Client ID**:
   - Перейдите в [Credentials](https://console.cloud.google.com/apis/credentials)
   - Нажмите "Create Credentials" → "OAuth client ID"
   - Если появится запрос, настройте OAuth consent screen:
     - Выберите "External" (для личного использования)
     - Заполните обязательные поля (App name, User support email)
     - Добавьте свой email в "Developer contact information"
     - Нажмите "Save and Continue"
     - В "Scopes" нажмите "Add or Remove Scopes"
     - Найдите и добавьте: `https://www.googleapis.com/auth/keep` (если доступен)
     - Или используйте: `https://www.googleapis.com/auth/drive` (для общего доступа)
     - Нажмите "Save and Continue"
     - В "Test users" добавьте свой email
     - Нажмите "Save and Continue"
   - Выберите тип приложения: **"Desktop app"**
   - Введите имя (например, "Notes App")
   - Нажмите "Create"

5. **Скачайте credentials**:
   - После создания вы увидите Client ID и Client Secret
   - Нажмите на иконку скачивания (Download JSON)
   - Сохраните файл как `credentials.json`

#### Шаг 2: Установка credentials в приложении

1. **Создайте директорию для конфигурации**:
   ```bash
   mkdir -p ~/.notes-google-keep
   ```

2. **Скопируйте credentials файл**:
   ```bash
   cp ~/Downloads/credentials.json ~/.notes-google-keep/credentials.json
   ```
   
   Или вручную переместите скачанный файл в `~/.notes-google-keep/credentials.json`

3. **Проверьте формат файла**:
   Файл должен содержать структуру вида:
   ```json
   {
     "installed": {
       "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
       "client_secret": "YOUR_CLIENT_SECRET",
       ...
     }
   }
   ```
   
   Если файл содержит секцию `"web"` вместо `"installed"`, приложение автоматически конвертирует его.

#### Шаг 3: Первая авторизация

1. Откройте приложение
2. Перейдите в "Настройки" → "Синхронизация Google Keep"
3. Включите синхронизацию
4. Нажмите "Тест соединения"
5. Откроется браузер для авторизации
6. Разрешите доступ к Google Keep
7. Токен будет сохранен локально в `~/.notes-google-keep/token.json`

**Безопасность:**
- Credentials файл хранится только на вашем компьютере
- Токен доступа также хранится только локально
- Никакие данные не передаются разработчикам приложения
- Вы полностью контролируете свои OAuth credentials

## Структура проекта

```
notes-google-keep/
├── main.py                 # Точка входа
├── gui.py                  # GUI слой (PyQt6)
├── editor.py               # Логика редактора (Visual/Raw режимы)
├── models.py               # Модели данных (Note)
├── database.py             # Database layer (SQLite)
├── sync_manager.py         # Sync layer (Safe/Extended Markdown)
├── settings.py             # Управление настройками
├── themes.py               # Темы оформления
├── settings_dialog.py      # Диалог настроек
└── requirements.txt        # Зависимости
```

## Архитектура

### Разделение слоев

- **GUI**: `gui.py` - интерфейс пользователя
- **Editor logic**: `editor.py` - логика редактора с двумя режимами
- **Database layer**: `database.py` - работа с SQLite
- **Sync layer**: `sync_manager.py` - синхронизация с поддержкой Safe/Extended Markdown

### Классы

- `Note`: модель заметки (dataclass)
- `DatabaseManager`: управление базой данных
- `MarkdownEditor`: управление редактором (Visual/Raw режимы)
- `SyncManager`: синхронизация заметок
- `MarkdownLevel`: определение Safe/Extended Markdown

## Использование

1. **Создание заметки**: Нажмите кнопку "+" или используйте Ctrl+N
2. **Редактирование**: Выберите заметку из списка и начните редактировать
3. **Форматирование**: Используйте кнопки на toolbar для применения форматирования
4. **Переключение режимов**: Нажмите кнопку "Visual"/"Raw" для переключения между визуальным и текстовым режимами
5. **Автосохранение**: Заметки сохраняются автоматически через 1 секунду после изменения
6. **Настройки**: Используйте меню "Настройки" → "Внешний вид" для изменения темы, цвета кнопок и размера шрифта

## Лицензия

MIT
