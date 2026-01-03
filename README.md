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

## Синхронизация

Приложение поддерживает синхронизацию заметок с **Google Drive** (рекомендуется) и **Google Keep**.

### Google Drive (рекомендуется)

**Преимущества:**
- ✅ Официальный API Google (OAuth 2.0)
- ✅ Работает на Linux и Android
- ✅ Заметки хранятся как `.md` файлы
- ✅ Доступ с любого устройства через Google Drive
- ✅ Один аккаунт Google для всех устройств

**Настройка:**

1. **Создайте проект в Google Cloud Console:**
   - Перейдите на https://console.cloud.google.com/
   - Создайте новый проект (или выберите существующий)
   - Назовите проект, например "Notes App"

2. **Включите Google Drive API:**
   - В меню слева выберите "APIs & Services" → "Library"
   - Найдите "Google Drive API"
   - Нажмите "Enable"

3. **Создайте OAuth 2.0 credentials:**
   - Перейдите в "APIs & Services" → "Credentials"
   - Нажмите "Create Credentials" → "OAuth client ID"
   - Если появится запрос, настройте OAuth consent screen:
     - User Type: External
     - App name: Notes App
     - User support email: ваш email
     - Developer contact: ваш email
     - Нажмите "Save and Continue"
     - Scopes: оставьте по умолчанию, нажмите "Save and Continue"
     - Test users: добавьте ваш email, нажмите "Save and Continue"
   - Application type: **Desktop app**
   - Name: Notes App
   - Нажмите "Create"

4. **Скачайте credentials.json:**
   - Нажмите на созданный OAuth client
   - Нажмите "Download JSON"
   - Сохраните файл как `credentials.json`

5. **Настройте приложение:**
   - Откройте "Настройки" → "Синхронизация Google Drive"
   - Укажите путь к `credentials.json`
   - Нажмите "Тест соединения"
   - При первом подключении откроется браузер для авторизации
   - После успешной авторизации нажмите "OK"

**Использование на Android:**
- Заметки будут храниться в папке "Notes App" в Google Drive
- Вы можете открывать и редактировать `.md` файлы через любое приложение для работы с Google Drive
- Или создать простое Android приложение для синхронизации

### Google Keep

Приложение поддерживает синхронизацию заметок с Google Keep через **Master Token**.

**Важно:** Google Keep API недоступен через OAuth 2.0 для личных аккаунтов (только для Google Workspace). Поэтому используется неофициальный API Google Keep с Master Token.

### Настройка Master Token

Есть два способа получить Master Token:

#### Вариант 1: Использовать готовый Master Token (рекомендуется)

1. **Получите Master Token через gkeepapi CLI**:
   ```bash
   pip install gkeepapi
   gkeepapi -e your.email@gmail.com -p your_app_password gettoken
   ```
   
   Команда выведет Master Token, который можно скопировать.

2. **Введите Master Token в приложении**:
   - Откройте "Настройки" → "Синхронизация Google Keep"
   - Вставьте Master Token в поле "Master Token"
   - Нажмите "Тест соединения"

#### Вариант 2: Использовать Email + App Password

1. **Создайте App Password**:
   - Включите двухфакторную аутентификацию в вашем Google аккаунте
   - Перейдите на [Токены приложений](https://myaccount.google.com/apppasswords)
   - Выберите приложение: "Mail" или "Other (Custom name)"
   - Введите имя (например, "Notes App")
   - Нажмите "Создать"
   - Google покажет 16-символьный токен (например: `abcd efgh ijkl mnop`)

2. **Введите данные в приложении**:
   - Откройте "Настройки" → "Синхронизация Google Keep"
   - Введите ваш email в поле "Email"
   - Введите 16-символьный токен **без пробелов** в поле "App Password"
   - Нажмите "Тест соединения"
   - Приложение автоматически получит Master Token при первом подключении

**Безопасность:**
- Master Token хранится только на вашем компьютере в `~/.notes-google-keep/master_token.json`
- Никакие данные не передаются разработчикам приложения
- Вы полностью контролируете свой Master Token
- Master Token можно отозвать в настройках Google Account

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
