"""
Графический интерфейс приложения заметок на PyQt5.
"""
import logging
from datetime import datetime
from typing import Optional

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QTextEdit, QLineEdit, QPushButton, QLabel, QMessageBox, QDialog,
    QDialogButtonBox, QListWidgetItem, QMenuBar, QMenu, QAction
)
from PyQt5.QtGui import QFont, QIcon, QTextDocument, QTextCursor
from PyQt5.QtCore import Qt, QTimer

from models import Note
from database import DatabaseManager
from sync_manager import SyncManager
from settings import Settings
from themes import get_theme
from settings_dialog import SettingsDialog
from sync_settings_dialog import SyncSettingsDialog
from markdown_utils import (
    convert_plain_to_markdown, convert_markdown_to_plain, apply_markdown_formatting,
    convert_html_to_markdown, convert_markdown_to_html
)

logger = logging.getLogger(__name__)


class ConflictDialog(QDialog):
    """Диалог для разрешения конфликтов при синхронизации."""
    
    def __init__(self, local_note: Note, remote_note: Note, parent=None):
        super().__init__(parent)
        self.local_note = local_note
        self.remote_note = remote_note
        self.action = None
        self.init_ui()
    
    def init_ui(self):
        """Инициализирует интерфейс диалога."""
        self.setWindowTitle("Разрешение конфликта")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        # Информация о конфликте
        info_label = QLabel(
            f"Обнаружен конфликт для заметки '{self.local_note.title}':\n"
            f"Локальная версия изменена: {self.local_note.updated_at.strftime('%Y-%m-%d %H:%M')}\n"
            f"Удаленная версия изменена: {self.remote_note.updated_at.strftime('%Y-%m-%d %H:%M')}"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Кнопки
        button_box = QDialogButtonBox()
        replace_btn = button_box.addButton("Заменить локальную", QDialogButtonBox.ButtonRole.AcceptRole)
        keep_btn = button_box.addButton("Сохранить локально", QDialogButtonBox.ButtonRole.RejectRole)
        cancel_btn = button_box.addButton("Отмена", QDialogButtonBox.ButtonRole.DestructiveRole)
        
        replace_btn.clicked.connect(lambda: self.set_action("replace"))
        keep_btn.clicked.connect(lambda: self.set_action("keep"))
        cancel_btn.clicked.connect(self.reject)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
    
    def set_action(self, action: str):
        """Устанавливает выбранное действие и закрывает диалог."""
        self.action = action
        self.accept()


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
        self.is_markdown_mode = False  # Режим Markdown
        
        self.init_ui()
        self.apply_theme()
        self.update_markdown_toggle_style()  # Устанавливаем начальный стиль кнопки
        self.load_notes()
    
    def init_ui(self):
        """Инициализирует интерфейс главного окна."""
        self.setWindowTitle("Заметки")
        self.setGeometry(100, 100, 1200, 700)
        
        # Меню
        self.create_menu()
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Левая панель: список заметок (узкая)
        left_panel = QWidget()
        left_panel.setObjectName("left_panel")
        left_panel.setMaximumWidth(280)
        left_panel.setMinimumWidth(250)
        left_panel.setFixedWidth(250)  # Фиксированная ширина для стабильности
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        
        # Верхняя панель с кнопками
        top_bar = QWidget()
        top_bar.setObjectName("top_bar")
        top_bar_layout = QVBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(10, 15, 10, 10)  # Увеличили верхний отступ
        top_bar_layout.setSpacing(5)
        
        # Верхняя панель с кнопками
        top_buttons_layout = QHBoxLayout()
        
        # Кнопка добавления (плюсик)
        self.add_btn = QPushButton("+")
        self.add_btn.setObjectName("icon_button")
        self.add_btn.setFixedSize(36, 36)  # Увеличили размер кнопки
        self.add_btn.setFont(QFont("Arial", 16, QFont.Bold))  # Немного уменьшили размер иконки
        self.add_btn.clicked.connect(self.on_add_note)
        top_buttons_layout.addWidget(self.add_btn)
        
        # Кнопка сортировки
        self.sort_btn = QPushButton("⇅")
        self.sort_btn.setObjectName("icon_button")
        self.sort_btn.setFixedSize(36, 36)
        self.sort_btn.setFont(QFont("Arial", 14))
        self.sort_btn.setToolTip("Сортировка")
        self.sort_btn.clicked.connect(self.show_sort_menu)
        top_buttons_layout.addWidget(self.sort_btn)
        
        top_buttons_layout.addStretch()
        top_bar_layout.addLayout(top_buttons_layout)
        
        # Поле поиска (всегда видимо)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("search_input")
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.textChanged.connect(self.on_search)
        top_bar_layout.addWidget(self.search_input)
        
        left_layout.addWidget(top_bar)
        
        # Список заметок
        self.notes_list = QListWidget()
        self.notes_list.itemClicked.connect(self.on_note_selected)
        left_layout.addWidget(self.notes_list)
        
        # Правая панель: редактирование
        right_panel = QWidget()
        right_panel.setObjectName("right_panel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        # Панель инструментов форматирования (всегда видна)
        self.format_toolbar = QWidget()
        self.format_toolbar.setObjectName("format_toolbar")
        format_layout = QHBoxLayout(self.format_toolbar)
        format_layout.setContentsMargins(10, 5, 10, 5)
        format_layout.setSpacing(5)
        
        # Кнопки форматирования
        self.bold_btn = QPushButton("B")
        self.bold_btn.setObjectName("format_button")
        self.bold_btn.setFixedSize(30, 30)
        self.bold_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.bold_btn.setToolTip("Жирный")
        self.bold_btn.clicked.connect(lambda: self.apply_format('bold'))
        format_layout.addWidget(self.bold_btn)
        
        self.italic_btn = QPushButton("I")
        self.italic_btn.setObjectName("format_button")
        self.italic_btn.setFixedSize(30, 30)
        self.italic_btn.setFont(QFont("Arial", 12))
        self.italic_btn.setStyleSheet("font-style: italic;")
        self.italic_btn.setToolTip("Курсив")
        self.italic_btn.clicked.connect(lambda: self.apply_format('italic'))
        format_layout.addWidget(self.italic_btn)
        
        self.strikethrough_btn = QPushButton("S")
        self.strikethrough_btn.setObjectName("format_button")
        self.strikethrough_btn.setFixedSize(30, 30)
        self.strikethrough_btn.setFont(QFont("Arial", 12))
        self.strikethrough_btn.setToolTip("Зачеркнутый")
        self.strikethrough_btn.clicked.connect(lambda: self.apply_format('strikethrough'))
        format_layout.addWidget(self.strikethrough_btn)
        
        self.header1_btn = QPushButton("H1")
        self.header1_btn.setObjectName("format_button")
        self.header1_btn.setFixedSize(35, 30)
        self.header1_btn.setToolTip("Заголовок 1")
        self.header1_btn.clicked.connect(lambda: self.apply_format('header1'))
        format_layout.addWidget(self.header1_btn)
        
        self.header2_btn = QPushButton("H2")
        self.header2_btn.setObjectName("format_button")
        self.header2_btn.setFixedSize(35, 30)
        self.header2_btn.setToolTip("Заголовок 2")
        self.header2_btn.clicked.connect(lambda: self.apply_format('header2'))
        format_layout.addWidget(self.header2_btn)
        
        self.list_btn = QPushButton("•")
        self.list_btn.setObjectName("format_button")
        self.list_btn.setFixedSize(30, 30)
        self.list_btn.setFont(QFont("Arial", 14))
        self.list_btn.setToolTip("Список")
        self.list_btn.clicked.connect(lambda: self.apply_format('list'))
        format_layout.addWidget(self.list_btn)
        
        format_layout.addStretch()
        
        # Переключатель Markdown (toggle с визуальной индикацией)
        self.markdown_toggle = QPushButton("Markdown")
        self.markdown_toggle.setObjectName("markdown_toggle")
        self.markdown_toggle.setCheckable(True)
        self.markdown_toggle.setToolTip("Переключить режим Markdown")
        self.markdown_toggle.clicked.connect(self.toggle_markdown_mode)
        format_layout.addWidget(self.markdown_toggle)
        
        right_layout.addWidget(self.format_toolbar)
        
        # Заголовок
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Заголовок заметки...")
        self.title_input.textChanged.connect(self.on_content_changed)
        right_layout.addWidget(self.title_input)
        
        # Содержимое
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Содержимое заметки...")
        self.content_input.textChanged.connect(self.on_content_changed)
        right_layout.addWidget(self.content_input, 1)
        
        # Информация о заметке и кнопка удаления
        # Используем контейнер для абсолютного позиционирования кнопки
        self.info_container = QWidget()
        self.info_container.setMinimumHeight(50)  # Минимальная высота для размещения кнопки
        info_container_layout = QVBoxLayout(self.info_container)
        info_container_layout.setContentsMargins(5, 5, 5, 5)
        
        # Информация о заметке
        self.info_label = QLabel("")
        self.info_label.setObjectName("info_label")
        self.info_label.setWordWrap(True)
        self.info_label.hide()  # Скрываем по умолчанию
        self.info_container.hide()  # Скрываем весь контейнер по умолчанию
        info_container_layout.addWidget(self.info_label)
        
        # Кнопка удаления - позиционируем абсолютно поверх контейнера
        self.delete_btn = QPushButton("×")
        self.delete_btn.setObjectName("delete_button")
        self.delete_btn.setFixedSize(28, 28)
        self.delete_btn.setToolTip("Удалить заметку")
        self.delete_btn.clicked.connect(self.on_delete_note)
        self.delete_btn.hide()  # Показываем только когда выбрана заметка
        self.delete_btn.setParent(self.info_container)  # Устанавливаем родителя для абсолютного позиционирования
        self.delete_btn.raise_()  # Поднимаем кнопку поверх других элементов
        
        # Обработчик изменения размера контейнера для обновления позиции кнопки
        def update_delete_btn_position():
            if self.delete_btn.isVisible():
                # Центрируем кнопку по вертикали
                btn_height = 28
                container_height = self.info_container.height()
                y_pos = max(5, (container_height - btn_height) // 2)
                self.delete_btn.move(self.info_container.width() - 33, y_pos)
                self.delete_btn.raise_()
        
        # Переопределяем resizeEvent для контейнера
        original_resize = self.info_container.resizeEvent
        def resize_with_btn_positioning(event):
            original_resize(event)
            update_delete_btn_position()
        self.info_container.resizeEvent = resize_with_btn_positioning
        
        right_layout.addWidget(self.info_container)
        
        # Разделение на панели
        main_layout.addWidget(left_panel, 0)
        main_layout.addWidget(right_panel, 1)
        
        # Применяем тему
        self.apply_theme()
    
    def create_menu(self):
        """Создает меню приложения."""
        menubar = self.menuBar()
        
        # Меню "Файл"
        file_menu = menubar.addMenu("Файл")
        
        new_action = QAction("Новая заметка", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.on_add_note)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        sync_action = QAction("Синхронизация", self)
        sync_action.setShortcut("Ctrl+S")
        sync_action.triggered.connect(self.on_sync)
        file_menu.addAction(sync_action)
        
        # Меню "Настройки"
        settings_menu = menubar.addMenu("Настройки")
        
        appearance_action = QAction("Внешний вид", self)
        appearance_action.triggered.connect(self.show_settings)
        settings_menu.addAction(appearance_action)
        
        sync_settings_action = QAction("Синхронизация", self)
        sync_settings_action.triggered.connect(self.show_sync_settings)
        settings_menu.addAction(sync_settings_action)
    
    def apply_theme(self):
        """Применяет выбранную тему."""
        theme_name = self.settings.get("theme", "system")
        button_color = self.settings.get("button_color", "#4CAF50")
        theme_style = get_theme(theme_name, button_color)
        self.setStyleSheet(theme_style)
    
    def show_sort_menu(self):
        """Показывает меню сортировки."""
        from PyQt5.QtWidgets import QMenu
        
        menu = QMenu(self)
        
        alphabet_action = menu.addAction("По алфавиту")
        alphabet_action.triggered.connect(lambda: self.set_sort_order("alphabet"))
        
        created_action = menu.addAction("По дате создания")
        created_action.triggered.connect(lambda: self.set_sort_order("created"))
        
        updated_action = menu.addAction("По дате изменения")
        updated_action.triggered.connect(lambda: self.set_sort_order("updated"))
        
        # Показываем меню под кнопкой
        button_pos = self.sort_btn.mapToGlobal(self.sort_btn.rect().bottomLeft())
        menu.exec_(button_pos)
    
    def set_sort_order(self, order: str):
        """Устанавливает порядок сортировки."""
        self.sort_order = order
        self.load_notes()
    
    def on_content_changed(self):
        """Обработчик изменения содержимого заметки."""
        self.has_unsaved_changes = True
        # Запускаем таймер автосохранения
        delay = self.settings.get("auto_save.delay", 1000)
        self.auto_save_timer.stop()
        self.auto_save_timer.start(delay)
    
    def auto_save_note(self):
        """Автоматически сохраняет заметку."""
        if not self.has_unsaved_changes:
            return
        
        title = self.title_input.text().strip()
        # Получаем содержимое в зависимости от режима
        if self.is_markdown_mode:
            content = self.content_input.toPlainText().strip()
        else:
            # В режиме HTML получаем HTML и конвертируем в markdown для хранения
            html_content = self.content_input.toHtml()
            content = convert_html_to_markdown(html_content) if html_content else ""
        
        # Не сохраняем пустые заметки
        if not title and not content:
            return
        
        try:
            if self.current_note:
                # Обновление существующей заметки
                if self.db_manager.update_note(self.current_note.id, title or "Без названия", content, self.is_markdown_mode):
                    self.current_note = self.db_manager.get_note(self.current_note.id)
                    if self.current_note:
                        self.info_label.setText(
                            f"Создано: {self.current_note.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                            f"Изменено: {self.current_note.updated_at.strftime('%Y-%m-%d %H:%M')}"
                        )
                        self.info_label.show()  # Убеждаемся, что видно
                        # Обновляем позицию кнопки удаления (с небольшой задержкой для правильного размера)
                        if self.delete_btn.isVisible():
                            def position_delete_btn():
                                btn_height = 28
                                container_height = self.info_container.height()
                                y_pos = max(5, (container_height - btn_height) // 2)
                                self.delete_btn.move(self.info_container.width() - 33, y_pos)
                                self.delete_btn.raise_()
                            QTimer.singleShot(10, position_delete_btn)
                    self.load_notes()
                    self.has_unsaved_changes = False
                    logger.info("Заметка автоматически сохранена")
            else:
                # Создание новой заметки
                if title or content:
                    note = self.db_manager.create_note(title or "Без названия", content, self.is_markdown_mode)
                    self.current_note = note
                    self.load_notes()
                    # НЕ показываем info_label при создании новой заметки
                    self.info_label.hide()
                    self.info_container.hide()  # Скрываем контейнер
                    self.delete_btn.show()  # Показываем кнопку удаления
                    # Позиционируем кнопку в правом верхнем углу (с небольшой задержкой для правильного размера)
                    def position_delete_btn():
                        btn_height = 28
                        container_height = self.info_container.height()
                        y_pos = max(5, (container_height - btn_height) // 2)
                        self.delete_btn.move(self.info_container.width() - 33, y_pos)
                        self.delete_btn.raise_()
                    QTimer.singleShot(10, position_delete_btn)
                    self.has_unsaved_changes = False
                    logger.info("Новая заметка автоматически создана")
        except Exception as e:
            logger.error(f"Ошибка при автосохранении заметки: {e}")
    
    def load_notes(self, notes: Optional[list] = None):
        """Загружает заметки в список."""
        if notes is None:
            notes = self.db_manager.get_all_notes()
            
            # Применяем сортировку
            if self.sort_order == "alphabet":
                notes = sorted(notes, key=lambda n: n.title.lower())
            elif self.sort_order == "created":
                notes = sorted(notes, key=lambda n: n.created_at, reverse=True)
            else:  # updated (по умолчанию)
                notes = sorted(notes, key=lambda n: n.updated_at, reverse=True)
        
        self.notes_list.clear()
        for note in notes:
            # Форматируем заметку: жирное название, потом часть заметки
            title = note.title if note.title else "Без названия"
            # Обрезаем название до 25 символов (с учетом ширины сайдбара ~220px)
            if len(title) > 25:
                title = title[:25] + "..."
            
            # Берем первые 25 символов содержимого для превью (короткое описание)
            preview = note.content[:25].replace('\n', ' ').replace('\r', '') if note.content else ""
            if len(note.content) > 25:
                preview += "..."
            
            # Фиксированная ширина сайдбара (250px) минус отступы и скроллбар
            sidebar_width = 220  # 250px ширина панели, минус padding (15px с каждой стороны) и скроллбар
            
            # Создаем виджет для элемента списка с форматированием
            item_widget = QWidget()
            item_widget.setMaximumWidth(sidebar_width)  # Ограничиваем ширину сайдбаром
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(15, 12, 15, 12)
            item_layout.setSpacing(6)
            item_layout.setAlignment(Qt.AlignTop)
            
            # Название жирным
            title_label = QLabel(title)
            title_font = QFont()
            title_font.setBold(True)
            title_font.setPointSize(11)
            title_label.setFont(title_font)
            title_label.setWordWrap(False)
            title_label.setFixedHeight(20)  # Фиксированная высота для названия
            title_label.setMaximumWidth(sidebar_width)  # Ограничиваем ширину
            item_layout.addWidget(title_label)
            
            # Превью обычным текстом
            if preview:
                preview_label = QLabel(preview)
                preview_label.setStyleSheet("color: #666; font-size: 10pt;")
                preview_label.setWordWrap(False)
                preview_label.setFixedHeight(18)  # Фиксированная высота для превью
                preview_label.setMaximumWidth(sidebar_width)  # Ограничиваем ширину
                item_layout.addWidget(preview_label)
            
            item = QListWidgetItem()
            item.setData(Qt.UserRole, note.id)
            # Устанавливаем фиксированную высоту для элемента
            item.setSizeHint(item_widget.sizeHint())
            self.notes_list.addItem(item)
            self.notes_list.setItemWidget(item, item_widget)
        
        logger.info(f"Загружено заметок: {len(notes)}")
    
    def on_search(self, text: str):
        """Обработчик поиска заметок."""
        if text.strip():
            notes = self.db_manager.search_notes(text)
            self.load_notes(notes)
        else:
            self.load_notes()
    
    def on_note_selected(self, item: QListWidgetItem):
        """Обработчик выбора заметки из списка."""
        # Сохраняем текущие изменения перед переключением
        if self.has_unsaved_changes:
            self.auto_save_timer.stop()
            self.auto_save_note()
        
        note_id = item.data(Qt.UserRole)
        if note_id:
            note = self.db_manager.get_note(note_id)
            if note:
                self.current_note = note
                self.title_input.setText(note.title)
                
                # Устанавливаем режим Markdown
                self.is_markdown_mode = note.is_markdown
                self.markdown_toggle.setChecked(note.is_markdown)
                
                # Показываем/скрываем кнопки форматирования
                if note.is_markdown:
                    self.bold_btn.hide()
                    self.italic_btn.hide()
                    self.strikethrough_btn.hide()
                    self.header1_btn.hide()
                    self.header2_btn.hide()
                    self.list_btn.hide()
                    self.content_input.setPlainText(note.content)
                else:
                    self.bold_btn.show()
                    self.italic_btn.show()
                    self.strikethrough_btn.show()
                    self.header1_btn.show()
                    self.header2_btn.show()
                    self.list_btn.show()
                    # Конвертируем markdown в HTML для отображения (если был markdown)
                    if note.content:
                        html_content = convert_markdown_to_html(note.content)
                        self.content_input.setHtml(html_content)
                    else:
                        self.content_input.clear()
                
                self.update_markdown_toggle_style()
                
                self.info_label.setText(
                    f"Создано: {note.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Изменено: {note.updated_at.strftime('%Y-%m-%d %H:%M')}"
                )
                self.info_label.show()  # Показываем при выборе заметки
                self.info_container.show()  # Показываем контейнер
                self.delete_btn.show()  # Показываем кнопку удаления
                # Позиционируем кнопку в правом верхнем углу контейнера (с небольшой задержкой для правильного размера)
                def position_delete_btn():
                    btn_height = 28
                    container_height = self.info_container.height()
                    y_pos = max(5, (container_height - btn_height) // 2)
                    self.delete_btn.move(self.info_container.width() - 33, y_pos)
                    self.delete_btn.raise_()
                QTimer.singleShot(10, position_delete_btn)
                self.has_unsaved_changes = False
    
    def on_add_note(self):
        """Обработчик добавления новой заметки."""
        # Сохраняем текущие изменения
        if self.has_unsaved_changes:
            self.auto_save_timer.stop()
            self.auto_save_note()
        
        self.current_note = None
        self.title_input.clear()
        self.content_input.clear()
        self.info_label.clear()
        self.info_label.hide()  # Скрываем при создании новой заметки
        self.info_container.hide()  # Скрываем контейнер
        self.delete_btn.hide()
        
        # Сбрасываем режим Markdown
        self.is_markdown_mode = False
        self.markdown_toggle.setChecked(False)
        # Показываем кнопки форматирования
        self.bold_btn.show()
        self.italic_btn.show()
        self.strikethrough_btn.show()
        self.header1_btn.show()
        self.header2_btn.show()
        self.list_btn.show()
        self.update_markdown_toggle_style()
        
        self.has_unsaved_changes = False
        self.title_input.setFocus()
    
    def on_delete_note(self):
        """Обработчик удаления заметки."""
        if not self.current_note:
            return
        
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.NoIcon)  # Убираем иконку
        msg_box.setWindowTitle("Подтверждение")
        msg_box.setText(f"Вы уверены, что хотите удалить заметку '{self.current_note.title}'?")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.db_manager.delete_note(self.current_note.id):
                self.current_note = None
                self.title_input.clear()
                self.content_input.clear()
                self.info_label.clear()
                self.info_label.hide()  # Скрываем при удалении
                self.info_container.hide()  # Скрываем контейнер
                self.delete_btn.hide()
                self.has_unsaved_changes = False
                self.load_notes()
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.NoIcon)  # Убираем иконку
                msg_box.setWindowTitle("Успех")
                msg_box.setText("Заметка удалена")
                msg_box.exec()
            else:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.NoIcon)  # Убираем иконку
                msg_box.setWindowTitle("Ошибка")
                msg_box.setText("Не удалось удалить заметку")
                msg_box.exec()
    
    def show_settings(self):
        """Показывает диалог настроек."""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == QDialog.Accepted:
            theme = dialog.get_theme()
            button_color = dialog.get_button_color()
            self.settings.set("theme", theme)
            self.settings.set("button_color", button_color)
            self.apply_theme()
    
    def show_sync_settings(self):
        """Показывает диалог настроек синхронизации."""
        dialog = SyncSettingsDialog(self, self.db_manager)
        if dialog.exec() == QDialog.Accepted:
            # Обновляем список заметок после синхронизации
            self.load_notes()
    
    def on_sync(self):
        """Обработчик синхронизации."""
        # Сохраняем текущие изменения
        if self.has_unsaved_changes:
            self.auto_save_timer.stop()
            self.auto_save_note()
        
        try:
            success, conflicts = self.sync_manager.sync(use_server=False)
            
            if success:
                # Обрабатываем конфликты
                for local_note, remote_note, conflict_type in conflicts:
                    dialog = ConflictDialog(local_note, remote_note, self)
                    if dialog.exec() == QDialog.Accepted and dialog.action:
                        self.sync_manager.resolve_conflict(local_note, remote_note, dialog.action)
                
                # Обновляем список заметок
                self.load_notes()
                # Уведомление убрано по запросу пользователя
            else:
                msg_box = QMessageBox(self)
                msg_box.setIcon(QMessageBox.NoIcon)  # Убираем иконку
                msg_box.setWindowTitle("Ошибка")
                msg_box.setText("Ошибка при синхронизации")
                msg_box.exec()
        except Exception as e:
            logger.error(f"Ошибка при синхронизации: {e}")
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.NoIcon)  # Убираем иконку
            msg_box.setWindowTitle("Ошибка")
            msg_box.setText(f"Ошибка при синхронизации: {str(e)}")
            msg_box.exec()
    
    def toggle_markdown_mode(self, checked: bool):
        """Переключает режим Markdown."""
        if self.has_unsaved_changes:
            self.auto_save_timer.stop()
            self.auto_save_note()
        
        current_content = self.content_input.toPlainText()
        
        if checked:
            # Переключаемся на Markdown
            self.is_markdown_mode = True
            # Конвертируем обычный текст в Markdown
            if current_content:
                markdown_content = convert_plain_to_markdown(current_content)
                self.content_input.setPlainText(markdown_content)
        else:
            # Переключаемся на обычный текст
            self.is_markdown_mode = False
            # Конвертируем Markdown в обычный текст и сохраняем
            if current_content:
                plain_content = convert_markdown_to_plain(current_content)
                self.content_input.setPlainText(plain_content)
                # Сохраняем конвертированный текст сразу
                if self.current_note:
                    title = self.title_input.text().strip()
                    self.db_manager.update_note(
                        self.current_note.id, 
                        title or "Без названия", 
                        plain_content, 
                        False  # is_markdown = False
                    )
                    self.current_note = self.db_manager.get_note(self.current_note.id)
                    self.load_notes()
        
        # Обновляем стиль кнопки
        self.update_markdown_toggle_style()
        
        # Обновляем заметку в базе данных
        if self.current_note:
            self.has_unsaved_changes = True
            self.auto_save_timer.start(1000)
    
    def apply_format(self, format_type: str):
        """Применяет форматирование к выделенному тексту."""
        if self.is_markdown_mode:
            # В режиме markdown применяем markdown форматирование
            cursor = self.content_input.textCursor()
            selection_start = cursor.selectionStart()
            selection_end = cursor.selectionEnd()
            
            current_text = self.content_input.toPlainText()
            new_text, new_start, new_end = apply_markdown_formatting(
                current_text, format_type, selection_start, selection_end
            )
            
            self.content_input.setPlainText(new_text)
            
            # Восстанавливаем выделение
            new_cursor = QTextCursor(self.content_input.document())
            new_cursor.setPosition(new_start)
            new_cursor.setPosition(new_end, QTextCursor.KeepAnchor)
            self.content_input.setTextCursor(new_cursor)
        else:
            # В режиме HTML применяем визуальное форматирование
            cursor = self.content_input.textCursor()
            format = cursor.charFormat()
            
            if format_type == 'bold':
                format.setFontWeight(QFont.Bold if format.fontWeight() != QFont.Bold else QFont.Normal)
            elif format_type == 'italic':
                format.setFontItalic(not format.fontItalic())
            elif format_type == 'strikethrough':
                format.setFontStrikeOut(not format.fontStrikeOut())
            elif format_type == 'header1':
                format.setFontPointSize(18)
                format.setFontWeight(QFont.Bold)
            elif format_type == 'header2':
                format.setFontPointSize(16)
                format.setFontWeight(QFont.Bold)
            elif format_type == 'list':
                # Для списков нужно добавить маркер в начало строки
                cursor.insertText("• ")
                return
            
            cursor.setCharFormat(format)
            self.content_input.setTextCursor(cursor)
        
        self.on_content_changed()
    
    def update_markdown_toggle_style(self):
        """Обновляет стиль кнопки переключения Markdown в зависимости от состояния."""
        if self.markdown_toggle.isChecked():
            self.markdown_toggle.setStyleSheet("""
                QPushButton#markdown_toggle {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton#markdown_toggle:hover {
                    background-color: #45a049;
                }
                QPushButton#markdown_toggle:pressed {
                    background-color: #3d8b40;
                }
            """)
        else:
            self.markdown_toggle.setStyleSheet("""
                QPushButton#markdown_toggle {
                    background-color: transparent;
                    color: #666;
                    border: 1px solid #ddd;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton#markdown_toggle:hover {
                    background-color: #f0f0f0;
                    border-color: #bbb;
                }
                QPushButton#markdown_toggle:pressed {
                    background-color: #e0e0e0;
                }
            """)
