"""
Графический интерфейс приложения заметок на PyQt6.

Markdown - единственный канонический формат.
HTML не используется.
"""
import logging
from datetime import datetime
from typing import Optional, List, Tuple

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QTextEdit, QLineEdit, QPushButton, QLabel, QMessageBox, QDialog,
    QDialogButtonBox, QListWidgetItem, QMenuBar, QMenu, QToolBar
)
from PyQt6.QtGui import (
    QFont, QIcon, QTextCursor, QKeyEvent, QAction, QResizeEvent
)
from PyQt6.QtCore import Qt, QTimer

from models import Note
from storage import DatabaseManager
from services import SyncManager
from utils import Settings, get_theme
from settings_dialog import SettingsDialog
from components import MarkdownEditor, EditorMode
from ui import LinkIconTextEdit, ConflictDialog
from ui.google_keep_settings_dialog import GoogleKeepSettingsDialog
from ui.google_drive_settings_dialog import GoogleDriveSettingsDialog

logger = logging.getLogger(__name__)

# Попытка импортировать QMarkdownTextEdit
try:
    from QMarkdownTextEdit import QMarkdownTextEdit
except ImportError:
    # Fallback: используем QTextEdit с поддержкой markdown (PyQt6 имеет setMarkdown/toMarkdown)
    QMarkdownTextEdit = QTextEdit
    logger.warning("QMarkdownTextEdit не найден, используется QTextEdit с поддержкой Markdown")


# Удалены классы LinkIconTextEdit и ConflictDialog - перенесены в ui/


class NotesMainWindow(QMainWindow):
    """Главное окно приложения заметок."""
    
    def __init__(self):
        super().__init__()
        self.db_manager = DatabaseManager()
        self.sync_manager = SyncManager(self.db_manager)
        self.settings = Settings()
        self.current_note: Optional[Note] = None
        self.auto_save_timer = QTimer()
        self.auto_save_timer.setSingleShot(True)
        self.auto_save_timer.timeout.connect(self.auto_save_note)
        self.has_unsaved_changes = False
        self.sort_order = "updated"  # По умолчанию по дате изменения
        
        self.init_ui()
        self.apply_theme()
        self.load_notes()
    
    def resizeEvent(self, event: QResizeEvent):
        """Обрабатывает изменение размера окна."""
        super().resizeEvent(event)
        # Обновляем ширину элементов списка при изменении размера окна
        if hasattr(self, 'notes_list') and self.notes_list.count() > 0:
            self._update_list_items_width()
    
    def init_ui(self):
        """Инициализирует интерфейс главного окна."""
        self.setWindowTitle("Заметки")
        self.setGeometry(100, 100, 1200, 700)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Левая панель (список заметок)
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel)
        
        # Правая панель (редактор)
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel, 1)
        
        # Меню
        self._create_menu_bar()
    
    def _create_left_panel(self) -> QWidget:
        """Создает левую панель со списком заметок."""
        panel = QWidget()
        panel.setObjectName("left_panel")
        panel.setMaximumWidth(250)
        panel.setMinimumWidth(200)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Верхняя панель с кнопками
        top_bar = QWidget()
        top_bar.setObjectName("top_bar")
        top_bar.setFixedHeight(50)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(10, 5, 10, 5)
        
        # Кнопка добавления
        self.add_btn = QPushButton("+")
        self.add_btn.setObjectName("icon_button")
        self.add_btn.setFixedSize(36, 36)
        self.add_btn.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.add_btn.clicked.connect(self.on_add_note)
        top_layout.addWidget(self.add_btn)
        
        # Кнопка сортировки
        self.sort_btn = QPushButton("⇅")
        self.sort_btn.setObjectName("icon_button")
        self.sort_btn.setFixedSize(36, 36)
        self.sort_btn.setFont(QFont("Arial", 14))
        self.sort_btn.setToolTip("Сортировка")
        self.sort_btn.clicked.connect(self.show_sort_menu)
        top_layout.addWidget(self.sort_btn)
        
        top_layout.addStretch()
        layout.addWidget(top_bar)
        
        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setObjectName("search_input")
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.textChanged.connect(self.on_search_changed)
        layout.addWidget(self.search_input)
        
        # Список заметок
        self.notes_list = QListWidget()
        self.notes_list.itemClicked.connect(self.on_note_selected)
        # Отключаем горизонтальный скролл
        self.notes_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # Устанавливаем режим переноса текста
        self.notes_list.setWordWrap(True)
        layout.addWidget(self.notes_list)
        
        return panel
    
    def _create_right_panel(self) -> QWidget:
        """Создает правую панель с редактором."""
        panel = QWidget()
        panel.setObjectName("right_panel")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar для форматирования
        self.format_toolbar = QWidget()
        self.format_toolbar.setObjectName("format_toolbar")
        self.format_toolbar.setFixedHeight(50)
        toolbar_layout = QHBoxLayout(self.format_toolbar)
        toolbar_layout.setContentsMargins(15, 5, 15, 5)
        
        # Кнопки форматирования
        self.bold_btn = QPushButton("B")
        self.bold_btn.setObjectName("format_button")
        self.bold_btn.setToolTip("Жирный")
        self.bold_btn.clicked.connect(lambda: self.editor.apply_format('bold'))
        toolbar_layout.addWidget(self.bold_btn)
        
        self.italic_btn = QPushButton("I")
        self.italic_btn.setObjectName("format_button")
        self.italic_btn.setToolTip("Курсив")
        self.italic_btn.clicked.connect(lambda: self.editor.apply_format('italic'))
        toolbar_layout.addWidget(self.italic_btn)
        
        self.h1_btn = QPushButton("H1")
        self.h1_btn.setObjectName("format_button")
        self.h1_btn.setToolTip("Заголовок 1")
        self.h1_btn.clicked.connect(lambda: self.editor.apply_format('header1'))
        toolbar_layout.addWidget(self.h1_btn)
        
        self.h2_btn = QPushButton("H2")
        self.h2_btn.setObjectName("format_button")
        self.h2_btn.setToolTip("Заголовок 2")
        self.h2_btn.clicked.connect(lambda: self.editor.apply_format('header2'))
        toolbar_layout.addWidget(self.h2_btn)
        
        self.h3_btn = QPushButton("H3")
        self.h3_btn.setObjectName("format_button")
        self.h3_btn.setToolTip("Заголовок 3")
        self.h3_btn.clicked.connect(lambda: self.editor.apply_format('header3'))
        toolbar_layout.addWidget(self.h3_btn)
        
        self.list_btn = QPushButton("•")
        self.list_btn.setObjectName("format_button")
        self.list_btn.setToolTip("Список")
        self.list_btn.clicked.connect(lambda: self.editor.apply_format('list'))
        toolbar_layout.addWidget(self.list_btn)
        
        self.quote_btn = QPushButton(">")
        self.quote_btn.setObjectName("format_button")
        self.quote_btn.setToolTip("Цитата")
        self.quote_btn.clicked.connect(lambda: self.editor.apply_format('quote'))
        toolbar_layout.addWidget(self.quote_btn)
        
        self.code_btn = QPushButton("`")
        self.code_btn.setObjectName("format_button")
        self.code_btn.setToolTip("Inline код")
        self.code_btn.clicked.connect(lambda: self.editor.apply_format('code'))
        toolbar_layout.addWidget(self.code_btn)
        
        toolbar_layout.addStretch()
        
        # Переключатель режимов
        self.mode_toggle = QPushButton("MD")
        self.mode_toggle.setObjectName("format_button")
        self.mode_toggle.setCheckable(True)
        self.mode_toggle.setChecked(False)  # По умолчанию Raw режим
        self.mode_toggle.setToolTip("Переключить режим (Visual/Raw Markdown)")
        self.mode_toggle.clicked.connect(self.toggle_editor_mode)
        toolbar_layout.addWidget(self.mode_toggle)
        
        layout.addWidget(self.format_toolbar)
        
        # Заголовок
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Заголовок заметки...")
        self.title_input.textChanged.connect(self.on_content_changed)
        layout.addWidget(self.title_input)
        
        # Редактор Markdown с поддержкой иконок ссылок
        if QMarkdownTextEdit == QTextEdit:
            # Используем кастомный QTextEdit с иконками ссылок
            self.content_input = LinkIconTextEdit()
        else:
            # Если есть QMarkdownTextEdit, используем его, но без иконок
            self.content_input = QMarkdownTextEdit()
        
        self.content_input.setPlaceholderText("Содержимое заметки...")
        self.content_input.textChanged.connect(self.on_content_changed)
        
        # Инициализируем редактор
        # Определяем, какая тема используется
        theme_name = self.settings.get('theme', 'light')
        is_dark = (theme_name == 'dark')
        self.editor = MarkdownEditor(self.content_input, is_dark_theme=is_dark)
        # Редактор по умолчанию в RAW режиме
        
        # Устанавливаем режим для отображения иконок (по умолчанию Raw, иконки не показываются)
        if hasattr(self.content_input, 'set_visual_mode'):
            self.content_input.set_visual_mode(False)
        
        layout.addWidget(self.content_input, 1)
        
        # Информация о заметке и кнопка удаления
        self.info_container = QWidget()
        self.info_container.setMinimumHeight(50)
        info_layout = QHBoxLayout(self.info_container)
        info_layout.setContentsMargins(30, 5, 30, 5)
        
        self.info_label = QLabel()
        self.info_label.setObjectName("info_label")
        info_layout.addWidget(self.info_label)
        
        info_layout.addStretch()
        
        # Кнопка удаления
        self.delete_btn = QPushButton("×")
        self.delete_btn.setObjectName("delete_button")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.clicked.connect(self.on_delete_note)
        self.delete_btn.hide()
        info_layout.addWidget(self.delete_btn)
        
        layout.addWidget(self.info_container)
        self.info_container.hide()
        
        return panel
    
    def _create_menu_bar(self):
        """Создает меню приложения."""
        menubar = self.menuBar()
        
        # Файл
        file_menu = menubar.addMenu("Файл")
        
        new_action = QAction("Новая заметка", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.on_add_note)
        file_menu.addAction(new_action)
        
        save_action = QAction("Сохранить", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.auto_save_note)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        sync_action = QAction("Синхронизировать", self)
        sync_action.triggered.connect(self.on_sync)
        file_menu.addAction(sync_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Настройки
        settings_menu = menubar.addMenu("Настройки")
        
        appearance_action = QAction("Внешний вид", self)
        appearance_action.triggered.connect(self.show_settings)
        settings_menu.addAction(appearance_action)
        
        keep_sync_action = QAction("Синхронизация Google Keep", self)
        keep_sync_action.triggered.connect(self.show_google_keep_settings)
        settings_menu.addAction(keep_sync_action)
        
        drive_sync_action = QAction("Синхронизация Google Drive", self)
        drive_sync_action.triggered.connect(self.show_google_drive_settings)
        settings_menu.addAction(drive_sync_action)
    
    def _darken_color(self, hex_color: str, factor: float = 0.9) -> str:
        """Затемняет цвет для hover эффекта."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = int(r * factor)
        g = int(g * factor)
        b = int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def toggle_editor_mode(self, checked: bool):
        """
        Переключает режим редактора между Visual и Raw Markdown.
        
        Args:
            checked: True для Visual режима, False для Raw
        """
        if checked:
            self.editor.set_mode(EditorMode.VISUAL)
            # В визуальном режиме применяем обычные стили из темы
            self.apply_theme()  # Переприменяем тему для восстановления стилей
            # Обновляем режим для отображения иконок ссылок
            if hasattr(self.content_input, 'set_visual_mode'):
                self.content_input.set_visual_mode(True)
        else:
            self.editor.set_mode(EditorMode.RAW)
            # В RAW режиме применяем стиль для обычного текста (не жирный, обычный размер)
            font_size = self.settings.get('font_size', 12)
            self.content_input.setStyleSheet(f"""
                QTextEdit {{
                    font-weight: normal !important;
                    font-size: {font_size}pt !important;
                }}
            """)
            # Отключаем иконки ссылок в RAW режиме
            if hasattr(self.content_input, 'set_visual_mode'):
                self.content_input.set_visual_mode(False)
            # Обновляем стиль кнопки MD
            self.apply_theme()
    
    def on_add_note(self):
        """Создает новую заметку."""
        self.current_note = None
        self.title_input.clear()
        self.content_input.clear()
        self.info_container.hide()
        self.delete_btn.hide()
        self.has_unsaved_changes = False
    
    def on_delete_note(self):
        """Удаляет текущую заметку."""
        if not self.current_note:
            return
        
        reply = QMessageBox.question(
            self, "Удаление заметки",
            f"Вы уверены, что хотите удалить заметку '{self.current_note.title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_note(self.current_note.id):
                self.current_note = None
                self.title_input.clear()
                self.content_input.clear()
                self.info_container.hide()
                self.delete_btn.hide()
                self.load_notes()
                logger.info("Заметка удалена")
    
    def on_note_selected(self, item: QListWidgetItem):
        """Обрабатывает выбор заметки из списка."""
        # Получаем ID заметки из данных элемента
        note_id = item.data(Qt.ItemDataRole.UserRole)
        if note_id is None:
            return
        note = self.db_manager.get_note(note_id)
        
        if note:
            self.current_note = note
            self.title_input.setText(note.title)
            self.editor.set_markdown(note.markdown_content)
            
            # Показываем информацию о заметке
            created = note.created_at.strftime("%Y-%m-%d %H:%M")
            updated = note.updated_at.strftime("%Y-%m-%d %H:%M")
            self.info_label.setText(f"Создано: {created} | Изменено: {updated}")
            self.info_container.show()
            self.delete_btn.show()
            
            self.has_unsaved_changes = False
    
    def on_content_changed(self):
        """Обрабатывает изменение содержимого."""
        self.has_unsaved_changes = True
        self.auto_save_timer.start(1000)  # Автосохранение через 1 секунду
    
    def auto_save_note(self):
        """Автоматически сохраняет текущую заметку."""
        if not self.has_unsaved_changes:
            return
        
        title = self.title_input.text().strip()
        if not title:
            return
        
        markdown_content = self.editor.get_markdown()
        
        if self.current_note:
            # Обновляем существующую заметку
            self.db_manager.update_note(
                self.current_note.id,
                title,
                markdown_content
            )
            self.current_note = self.db_manager.get_note(self.current_note.id)
        else:
            # Создаем новую заметку
            self.current_note = self.db_manager.create_note(title, markdown_content)
        
        self.has_unsaved_changes = False
        self.load_notes()
        logger.info("Заметка сохранена")
    
    def on_search_changed(self, text: str):
        """Обрабатывает изменение поискового запроса."""
        if text.strip():
            notes = self.db_manager.search_notes(text)
        else:
            notes = self.db_manager.get_all_notes()
        
        self._populate_notes_list(notes)
    
    def load_notes(self):
        """Загружает список заметок."""
        notes = self.db_manager.get_all_notes()
        
        # Сортировка
        if self.sort_order == "alphabetical":
            notes.sort(key=lambda n: n.title.lower())
        elif self.sort_order == "created":
            notes.sort(key=lambda n: n.created_at, reverse=True)
        else:  # updated
            notes.sort(key=lambda n: n.updated_at, reverse=True)
        
        self._populate_notes_list(notes)
    
    def _update_list_items_width(self):
        """Обновляет ширину всех элементов списка при изменении размера."""
        list_width = self.notes_list.width()
        if list_width <= 0:
            return
        
        max_item_width = max(list_width - 30, 180)  # Минимум 180px
        
        for i in range(self.notes_list.count()):
            item = self.notes_list.item(i)
            item_widget = self.notes_list.itemWidget(item)
            if item_widget:
                item_widget.setMaximumWidth(max_item_width)
                # Обновляем ширину всех QLabel внутри
                for child in item_widget.findChildren(QLabel):
                    child.setMaximumWidth(max_item_width - 20)
    
    def _populate_notes_list(self, notes):
        """Заполняет список заметок."""
        self.notes_list.clear()
        
        # Получаем ширину списка для ограничения элементов
        list_width = self.notes_list.width()
        if list_width <= 0:
            # Если список еще не отображен, используем ширину панели
            list_width = self.notes_list.parent().width() if self.notes_list.parent() else 230
        
        # Вычисляем максимальную ширину для элементов (учитываем отступы и скроллбар)
        max_item_width = max(list_width - 30, 180)  # Минимум 180px
        
        for note in notes:
            # Создаем кастомный виджет для элемента списка
            item_widget = QWidget()
            item_widget.setMaximumWidth(max_item_width)
            
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(10, 8, 10, 8)
            item_layout.setSpacing(4)
            
            # Заголовок (жирный)
            title_label = QLabel(note.title)
            title_font = QFont()
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setWordWrap(True)
            # Ограничиваем ширину заголовка
            title_label.setMaximumWidth(max_item_width - 20)  # Учитываем отступы layout
            # Ограничиваем высоту заголовка до 1-2 строк
            title_font_metrics = title_label.fontMetrics()
            title_line_height = title_font_metrics.lineSpacing()
            title_label.setMaximumHeight(title_line_height * 2)  # Максимум 2 строки для заголовка
            item_layout.addWidget(title_label)
            
            # Предпросмотр (короткое описание) - строго 2 строки
            preview = self._strip_markdown_preview(note.markdown_content)
            
            # Создаем временный QLabel для измерения текста
            temp_label = QLabel()
            temp_label.setWordWrap(True)
            temp_label.setStyleSheet("color: #666; font-size: 11pt;")
            temp_label.setMaximumWidth(max_item_width - 20)
            temp_font_metrics = temp_label.fontMetrics()
            line_height = temp_font_metrics.lineSpacing()
            
            # Ограничиваем текст так, чтобы он помещался ровно в 2 строки
            # Вычисляем максимальное количество символов для 2 строк
            max_chars_per_line = (max_item_width - 20) // temp_font_metrics.averageCharWidth()
            max_chars = max_chars_per_line * 2  # 2 строки
            
            if len(preview) > max_chars:
                # Обрезаем до нужной длины и добавляем многоточие
                preview = preview[:max_chars - 3] + "..."
            
            preview_label = QLabel(preview)
            preview_label.setWordWrap(True)
            preview_label.setStyleSheet("color: #666; font-size: 11pt;")
            # Ограничиваем ширину предпросмотра
            preview_label.setMaximumWidth(max_item_width - 20)  # Учитываем отступы layout
            # Строго ограничиваем высоту до 2 строк
            preview_label.setMaximumHeight(line_height * 2)
            preview_label.setMinimumHeight(line_height * 2)  # Фиксируем высоту
            preview_label.setTextFormat(Qt.TextFormat.PlainText)
            item_layout.addWidget(preview_label)
            
            # Создаем QListWidgetItem
            item = QListWidgetItem()
            # Устанавливаем размер элемента
            item.setSizeHint(item_widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            
            # Устанавливаем виджет в элемент списка
            self.notes_list.addItem(item)
            self.notes_list.setItemWidget(item, item_widget)
    
    def _strip_markdown_preview(self, markdown_text: str) -> str:
        """
        Убирает markdown синтаксис для предпросмотра в списке.
        
        Args:
            markdown_text: Текст в формате Markdown
            
        Returns:
            Plain text без markdown синтаксиса
        """
        import re
        # Убираем заголовки
        text = re.sub(r'^#{1,6}\s+', '', markdown_text, flags=re.MULTILINE)
        # Убираем жирный и курсив
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        # Убираем списки
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        # Убираем цитаты
        text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
        # Убираем inline код
        text = re.sub(r'`([^`]+)`', r'\1', text)
        return text.strip()
    
    def show_sort_menu(self):
        """Показывает меню сортировки."""
        from PyQt6.QtWidgets import QMenu
        
        menu = QMenu(self)
        
        alphabetical_action = QAction("По алфавиту", self)
        alphabetical_action.triggered.connect(lambda: self.set_sort_order("alphabetical"))
        menu.addAction(alphabetical_action)
        
        created_action = QAction("По дате создания", self)
        created_action.triggered.connect(lambda: self.set_sort_order("created"))
        menu.addAction(created_action)
        
        updated_action = QAction("По дате изменения", self)
        updated_action.triggered.connect(lambda: self.set_sort_order("updated"))
        menu.addAction(updated_action)
        
        menu.exec(self.sort_btn.mapToGlobal(self.sort_btn.rect().bottomLeft()))
    
    def set_sort_order(self, order: str):
        """Устанавливает порядок сортировки."""
        self.sort_order = order
        self.load_notes()
    
    def on_sync(self):
        """Обрабатывает синхронизацию."""
        # Проверяем, включена ли синхронизация с Google Drive (приоритет)
        if self.settings.get('google_drive.enabled', False):
            self._sync_google_drive()
        # Проверяем, включена ли синхронизация с Google Keep
        elif self.settings.get('google_keep.enabled', False):
            self._sync_google_keep()
        else:
            # Используем стандартную синхронизацию (локальный файл)
            try:
                self.sync_manager.sync()
                QMessageBox.information(self, "Синхронизация", "Синхронизация завершена успешно")
                self.load_notes()
            except Exception as e:
                logger.error(f"Ошибка при синхронизации: {e}")
                QMessageBox.critical(self, "Ошибка", f"Ошибка при синхронизации: {e}")
    
    def _sync_google_keep(self):
        """Синхронизирует заметки с Google Keep через OAuth 2.0."""
        try:
            from services.google_keep_sync import GoogleKeepSync
            
            # Создаем экземпляр синхронизатора (OAuth не требует email/password)
            keep_sync = GoogleKeepSync(self.db_manager, settings=self.settings, parent_widget=self)
            
            # Выполняем синхронизацию (Markdown копируется как есть)
            success, conflicts = keep_sync.sync()
            
            if success:
                if conflicts:
                    # Обрабатываем конфликты
                    self._handle_sync_conflicts(conflicts)
                else:
                    QMessageBox.information(self, "Синхронизация", "Синхронизация с Google Keep завершена успешно")
                self.load_notes()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось синхронизировать с Google Keep")
                
        except ImportError:
            QMessageBox.critical(
                self, 
                "Ошибка", 
                "Не установлены необходимые библиотеки.\n\n"
                "Установите: pip install google-auth google-auth-oauthlib google-auth-httplib2"
            )
        except Exception as e:
            logger.error(f"Ошибка при синхронизации с Google Keep: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при синхронизации с Google Keep: {str(e)}")
    
    def _handle_sync_conflicts(self, conflicts: List[Tuple[Note, Note, str]]):
        """Обрабатывает конфликты при синхронизации."""
        for local_note, remote_note, conflict_type in conflicts:
            dialog = ConflictDialog(local_note, remote_note, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                if dialog.action == "replace":
                    # Заменяем локальную версию удаленной
                    self.db_manager.sync_note(remote_note)
                elif dialog.action == "keep":
                    # Сохраняем локальную версию
                    pass  # Локальная версия уже сохранена
    
    def show_google_keep_settings(self):
        """Показывает диалог настроек синхронизации Google Keep."""
        dialog = GoogleKeepSettingsDialog(self.settings, self)
        dialog.exec()
    
    def _sync_google_drive(self):
        """Синхронизирует заметки с Google Drive через OAuth 2.0."""
        try:
            from services.google_drive_sync import GoogleDriveSync
            
            # Создаем экземпляр синхронизатора
            drive_sync = GoogleDriveSync(self.db_manager, settings=self.settings, parent_widget=self)
            
            # Выполняем синхронизацию (Markdown копируется как есть)
            success, conflicts = drive_sync.sync()
            
            if success:
                if conflicts:
                    # Обрабатываем конфликты
                    self._handle_sync_conflicts(conflicts)
                else:
                    QMessageBox.information(self, "Синхронизация", "Синхронизация с Google Drive завершена успешно")
                self.load_notes()
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось синхронизировать с Google Drive")
                
        except ImportError:
            QMessageBox.critical(
                self, 
                "Ошибка", 
                "Не установлены необходимые библиотеки.\n\n"
                "Установите: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dateutil"
            )
        except Exception as e:
            logger.error(f"Ошибка при синхронизации с Google Drive: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при синхронизации с Google Drive: {str(e)}")
    
    def show_google_drive_settings(self):
        """Показывает диалог настроек синхронизации Google Drive."""
        dialog = GoogleDriveSettingsDialog(self.settings, self)
        dialog.exec()
    
    def show_settings(self):
        """Показывает диалог настроек."""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Сохраняем настройки из диалога
            theme = dialog.get_theme()
            button_color = dialog.get_button_color()
            font_size = dialog.get_font_size()
            self.settings.set("theme", theme)
            self.settings.set("button_color", button_color)
            self.settings.set("font_size", font_size)
            self.apply_theme()
    
    def apply_theme(self):
        """Применяет тему к приложению."""
        theme_name = self.settings.get('theme', 'light')
        button_color = self.settings.get('button_color', '#4CAF50')
        font_size = self.settings.get('font_size', 12)
        theme_css = get_theme(theme_name, button_color, font_size)
        self.setStyleSheet(theme_css)
        
        # Обновляем стиль кнопки MD в зависимости от режима
        if hasattr(self, 'mode_toggle'):
            if not self.mode_toggle.isChecked():
                # Raw режим - окрашиваем в выбранный цвет
                self.mode_toggle.setStyleSheet(f"""
                    QPushButton#format_button {{
                        background-color: {button_color};
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 6px 8px;
                        font-size: 11pt;
                        min-width: 32px;
                        min-height: 32px;
                        max-width: 32px;
                        max-height: 32px;
                    }}
                    QPushButton#format_button:hover {{
                        background-color: {self._darken_color(button_color)};
                    }}
                    QPushButton#format_button:pressed {{
                        background-color: {self._darken_color(button_color, 0.85)};
                    }}
                """)
            else:
                # Visual режим - прозрачная кнопка
                self.mode_toggle.setStyleSheet("")
        
        # Обновляем тему в редакторе
        if hasattr(self, 'editor'):
            is_dark = (theme_name == 'dark')
            self.editor.is_dark_theme = is_dark
            # Переприменяем стили кода, если редактор в визуальном режиме
            if self.editor.mode == EditorMode.VISUAL:
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(50, self.editor._apply_code_styling)
