# ui.py - Interface principal do Vox Imago
# Contém DriveFileGalleryApp e FileDetailsPanel.
# Gerencia a interface gráfica, eventos, filtros, autenticação e integração com os módulos do projeto.

import os
import time
import sqlite3
import webbrowser

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from workers import AuthWorker, ThumbnailWorker, LocalScanWorker, DriveSyncWorker

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QFrame, QSizePolicy, QSpacerItem, QFileDialog,
    QDialog, QCheckBox, QDialogButtonBox, QProgressBar, QComboBox, QCompleter,
    QFormLayout, QSplitter, QDateEdit, QVBoxLayout, QScrollArea, QProgressDialog, QListView, QSystemTrayIcon, QMenu,
    QToolButton, QAbstractItemView
)
from PyQt6.QtGui import QPixmap, QFont, QIcon, QAction, QDrag, QCursor
from PyQt6.QtCore import Qt, QTimer, QStringListModel, QDate, QThread, pyqtSignal, QThreadPool, QRect, QUrl, QMimeData

from database import FileIndexer
from widgets import OptionsDialog
from utils import format_size, get_generic_thumbnail, load_settings, save_settings
from utils import SETTINGS_FILE as TOKEN_FILE

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


class FileListView(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_start_position = None

    def mousePressEvent(self, event):
        self.drag_start_position = event.pos()
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                self.setCurrentIndex(index)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start_position is not None and (event.pos() - self.drag_start_position).manhattanLength() > QApplication.startDragDistance():
            self.startDrag(Qt.DropAction.CopyAction)
            self.drag_start_position = None
        super().mouseMoveEvent(event)

    def startDrag(self, supportedActions):
        indexes = self.selectedIndexes()
        if not indexes:
            index = self.indexAt(self.mapFromGlobal(QCursor.pos()))
            if index.isValid():
                self.setCurrentIndex(index)
        indexes = self.selectedIndexes()
        if not indexes:
            return

        mime_data = QMimeData()
        urls = []
        for index in indexes:
            file_item = index.data(Qt.ItemDataRole.UserRole)
            if file_item.get('source') == 'local' and file_item.get('path'):
                urls.append(QUrl.fromLocalFile(file_item['path']))
            elif file_item.get('source') == 'drive' and file_item.get('webViewLink'):
                urls.append(QUrl(file_item['webViewLink']))
        mime_data.setUrls(urls)

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)


class ServiceStatusDialog(QDialog):
    def __init__(self, status_text, show_progress=False, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle("Status dos Serviços")
        self.setModal(True)
        self.resize(400, 200)

        layout = QVBoxLayout(self)

        self.text_label = QLabel(status_text)
        self.text_label.setWordWrap(True)
        layout.addWidget(self.text_label)

        self.progress_bar = QProgressBar(self)
        if show_progress:
            self.progress_bar.setRange(0, 0)
            layout.addWidget(self.progress_bar)
        else:
            self.progress_bar.hide()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

    def update_status(self, new_text):
        self.text_label.setText(new_text)


class DriveFileGalleryApp(QMainWindow):
    def _reindex_local_files(self):
        settings = load_settings()
        scan_paths = settings.get('scan_paths')
        if scan_paths and len(scan_paths) > 0:
            self._start_local_scan(scan_paths)
            self.status_bar.showMessage("Reindexando arquivos locais...", 5000)
        else:
            self.status_bar.showMessage(
                "Nenhuma pasta local configurada para reindexação.", 5000)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoxImago - Galeria de Arquivos")
        self.setMinimumSize(600, 400)

        self.scroll_loading = False

        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(8)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("VMico.png"))
        self.tray_icon.setToolTip("Vox Imago - Galeria de Arquivos")

        self.tray_menu = QMenu()
        self.show_action = QAction("Mostrar Janela", self)
        self.show_action.triggered.connect(self.show)
        self.tray_menu.addAction(self.show_action)

        self.tray_menu.addSeparator()

        self.status_action = QAction("Status dos Serviços", self)
        self.status_action.triggered.connect(self.show_service_status)
        self.tray_menu.addAction(self.status_action)

        self.tray_menu.addSeparator()

        self.quit_action = QAction("Sair", self)
        self.quit_action.triggered.connect(self.close)
        self.tray_menu.addAction(self.quit_action)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        self.tray_icon.show()

        self.service = None
        self.indexer = FileIndexer()
        self.current_view = 'local'
        self.current_page = 0
        self.page_size = 50
        self.search_term = ""
        self.current_filter = "all"
        self.current_sort = "name_asc"
        self.current_folder_id = None
        self.advanced_filters = {}
        self.explorer_special_active = False
        self.is_loading = False
        self.all_files_loaded = False
        self.is_authenticated = False

        self.auth_thread = None
        self.auth_worker = None
        self.local_scan_thread = None
        self.local_scan_worker = None
        self.drive_sync_thread = None
        self.drive_sync_worker = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.handle_search_request)

        self.token_check_timer = QTimer()
        self.token_check_timer.timeout.connect(self._check_token_refresh)
        self.token_check_timer.start(30 * 60 * 1000)

        self.suggestion_timer = QTimer()
        self.suggestion_timer.setSingleShot(True)
        self.suggestion_timer.timeout.connect(self.update_search_suggestions)

        self.completer_model = QStringListModel()

        self._setup_ui()
        self.show()

        settings = load_settings()
        self.show_drive_metadata = settings.get('show_drive_metadata', True)
        scan_paths = settings.get('scan_paths')
        if scan_paths and len(scan_paths) > 0:
            self._start_local_scan(scan_paths)
        else:
            self.indexer.cursor.execute(
                "DELETE FROM files WHERE source='local'")
            self.indexer.cursor.execute(
                "DELETE FROM search_index WHERE source='local'")
            self.indexer.conn.commit()
            self.current_view = 'local'
            self.current_folder_id = None
            self.clear_display()
            self.all_files_loaded = True
            self.loading_label.setText("Nenhum arquivo encontrado.")
            self.loading_label.show()

        self._check_initial_auth()
        self.extension_combo.setCurrentIndex(0)

    def closeEvent(self, event):
        threads_to_wait = []
        if hasattr(self, 'auth_thread') and self.auth_thread and self.auth_thread.isRunning():
            self.auth_thread.quit()
            threads_to_wait.append(self.auth_thread)
        if hasattr(self, 'drive_sync_thread') and self.drive_sync_thread and self.drive_sync_thread.isRunning():
            self.drive_sync_thread.quit()
            threads_to_wait.append(self.drive_sync_thread)
        if hasattr(self, 'local_scan_thread') and self.local_scan_thread and self.local_scan_thread.isRunning():
            self.local_scan_thread.quit()
            threads_to_wait.append(self.local_scan_thread)

        for thread in threads_to_wait:
            if not thread.wait(5000):
                print(
                    f"Aviso: Thread {thread.objectName()} não terminou no tempo esperado.")

        if hasattr(self, 'auth_worker') and self.auth_worker:
            self.auth_worker.deleteLater()
        if hasattr(self, 'drive_sync_worker') and self.drive_sync_worker:
            self.drive_sync_worker.deleteLater()
        if hasattr(self, 'local_scan_worker') and self.local_scan_worker:
            self.local_scan_worker.deleteLater()

        if hasattr(self.details_panel, 'thumbnail_thread') and self.details_panel.thumbnail_thread:
            if self.details_panel.thumbnail_thread.isRunning():
                self.details_panel.thumbnail_thread.quit()
                if not self.details_panel.thumbnail_thread.wait(3000):
                    print("Aviso: Thumbnail thread do painel não terminou.")
            self.details_panel.thumbnail_thread.deleteLater()
        if hasattr(self.details_panel, 'thumbnail_worker') and self.details_panel.thumbnail_worker:
            self.details_panel.thumbnail_worker.deleteLater()

        if hasattr(self, 'indexer') and self.indexer.conn:
            self.indexer.conn.close()

        if hasattr(self, 'tray_icon'):
            self.tray_icon.hide()

        event.accept()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isMinimized() or not self.isVisible():
                self.showNormal()
                self.raise_()
                self.activateWindow()
            else:
                self.showMinimized()

    def show_service_status(self):
        status_lines = []

        if self.is_authenticated:
            status_lines.append("✓ Autenticado no Google Drive")
        else:
            status_lines.append("✗ Não autenticado no Google Drive")

        if self.local_scan_thread and self.local_scan_thread.isRunning():
            status_lines.append("⟳ Escaneamento local em andamento...")
        else:
            try:
                local_count = self.indexer.get_file_count(source='local')
                status_lines.append(
                    f"✓ Arquivos locais indexados: {local_count}")
            except:
                status_lines.append("✗ Erro ao acessar arquivos locais")

        if self.drive_sync_thread and self.drive_sync_thread.isRunning():
            status_lines.append("⟳ Sincronização do Drive em andamento...")
        else:
            try:
                drive_count = self.indexer.get_file_count(source='drive')
                status_lines.append(
                    f"✓ Arquivos do Drive indexados: {drive_count}")
            except:
                status_lines.append("✗ Erro ao acessar arquivos do Drive")

        if self.is_loading:
            status_lines.append("⟳ Carregando arquivos...")

        if self.current_view == 'local':
            status_lines.append("👁️ Visualizando: Arquivos Locais")
        elif self.current_view == 'drive':
            status_lines.append("👁️ Visualizando: Google Drive")
        else:
            status_lines.append("👁️ Visualizando: Unificado")

        if self.search_term:
            status_lines.append(f"🔍 Pesquisa ativa: '{self.search_term}'")

        if self.explorer_special_active:
            status_lines.append("🏠 Modo Explorer Local ativo")

        status_text = "\n".join(status_lines)
        show_progress = (self.local_scan_thread and self.local_scan_thread.isRunning()) or (
            self.drive_sync_thread and self.drive_sync_thread.isRunning())
        dialog = ServiceStatusDialog(status_text, show_progress, self)
        dialog.exec()

    def _check_token_refresh(self):
        try:
            creds = None
            if os.path.exists(TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(
                    TOKEN_FILE, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                self.service = build('drive', 'v3', credentials=creds)
        except Exception as e:
            print(f"Erro ao atualizar token: {e}")

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        unified_bar = QFrame()
        unified_bar.setFrameShape(QFrame.Shape.StyledPanel)
        unified_bar.setFrameShadow(QFrame.Shadow.Raised)
        unified_bar.setFixedHeight(50)

        unified_layout = QHBoxLayout(unified_bar)
        unified_layout.setContentsMargins(15, 8, 15, 8)

        self.app_title_label = QLabel("VI-MB")
        self.app_title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        unified_layout.addWidget(self.app_title_label)
        unified_layout.addSpacing(15)

        unified_layout.addStretch()

        self.tools_menu = QMenu("Ferramentas", self)

        self.tools_menu.addAction("Pastas Locais", self._show_scan_options)
        self.tools_menu.addAction("Atualizar Drive", self._start_drive_sync)
        self.tools_menu.addAction(
            "Reindexar Arquivos Locais", self._reindex_local_files)
        self.tools_menu.addAction("Limpar Cache", self.clear_thumbnail_cache)
        self.explorer_action = QAction("Explorer Local", self)
        self.explorer_action.setCheckable(True)
        self.explorer_action.setChecked(self.explorer_special_active)
        self.explorer_action.triggered.connect(self.toggle_explorer_special)
        self.tools_menu.addAction(self.explorer_action)

        self.tools_button = QToolButton(self)
        self.tools_button.setText("🛠️ Ferramentas")
        self.tools_button.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup)
        self.tools_button.setMenu(self.tools_menu)

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Pesquisar...")
        self.search_entry.setFixedWidth(250)
        self.search_entry.textChanged.connect(self.handle_search_input)
        unified_layout.addWidget(self.search_entry)
        unified_layout.addStretch()

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Todos os Tipos", "all")
        self.filter_combo.addItem("Imagens", "image")
        self.filter_combo.addItem("Documentos", "document")
        self.filter_combo.addItem("Planilhas", "spreadsheet")
        self.filter_combo.addItem("Apresentações", "presentation")
        self.filter_combo.addItem("Pastas", "folder")
        self.filter_combo.activated.connect(self.change_filter_type_combo)
        self.filter_combo.setEnabled(False)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Nome (A-Z)", "name_asc")
        self.sort_combo.addItem("Nome (Z-A)", "name_desc")
        self.sort_combo.addItem("Tamanho (Menor)", "size_asc")
        self.sort_combo.addItem("Tamanho (Maior)", "size_desc")
        self.sort_combo.activated.connect(self.change_sort_order)
        self.sort_combo.setEnabled(False)

        filter_label = QLabel("Filtrar:")
        filter_label.setFixedWidth(50)
        unified_layout.addWidget(filter_label)
        unified_layout.addWidget(self.filter_combo)
        unified_layout.addSpacing(5)
        sort_label = QLabel("Ordenar por:")
        sort_label.setFixedWidth(70)
        unified_layout.addWidget(sort_label)
        unified_layout.addWidget(self.sort_combo)

        unified_layout.addSpacing(5)
        self.more_filters_button = QPushButton("Mais Filtros ▼")
        self.more_filters_button.setCheckable(True)
        self.more_filters_button.clicked.connect(self.toggle_advanced_filters)
        unified_layout.addWidget(self.more_filters_button)

        self.extension_combo = QComboBox()
        self.extension_combo.setEditable(False)
        self.extension_combo.setPlaceholderText("Selecione a extensão")
        self._populate_extension_combo()

        self.modified_after_date = QDateEdit()
        self.modified_after_date.setDate(QDate.currentDate().addDays(-7))
        self.modified_after_date.setCalendarPopup(True)

        self.created_after_date = QDateEdit()
        self.created_after_date.setDate(QDate.currentDate().addDays(-7))
        self.created_after_date.setCalendarPopup(True)

        self.created_before_date = QDateEdit()
        self.created_before_date.setDate(QDate.currentDate())
        self.created_before_date.setCalendarPopup(True)

        self.starred_checkbox = QCheckBox("Favoritos")

        self.apply_advanced_filter_button = QPushButton("Aplicar Filtros")
        self.apply_advanced_filter_button.clicked.connect(
            self.apply_advanced_filters)

        self.clear_advanced_filter_button = QPushButton("Limpar Filtros")
        self.clear_advanced_filter_button.clicked.connect(
            self.clear_advanced_filters)

        self.advanced_filter_layout = QHBoxLayout()

        self.ext_label = QLabel("Extensão:")
        self.ext_label.setFixedWidth(80)
        self.ext_label.setFixedHeight(30)
        self.ext_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.advanced_filter_layout.addWidget(self.ext_label)
        self.advanced_filter_layout.addWidget(self.extension_combo)

        self.mod_label = QLabel("Modificado após:")
        self.mod_label.setFixedWidth(100)
        self.mod_label.setFixedHeight(30)
        self.mod_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.advanced_filter_layout.addWidget(self.mod_label)
        self.advanced_filter_layout.addWidget(self.modified_after_date)

        self.created_after_label = QLabel("Criado após:")
        self.created_after_label.setFixedWidth(80)
        self.created_after_label.setFixedHeight(30)
        self.created_after_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.advanced_filter_layout.addWidget(self.created_after_label)
        self.advanced_filter_layout.addWidget(self.created_after_date)

        self.created_before_label = QLabel("Criado antes:")
        self.created_before_label.setFixedWidth(90)
        self.created_before_label.setFixedHeight(30)
        self.created_before_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.advanced_filter_layout.addWidget(self.created_before_label)
        self.advanced_filter_layout.addWidget(self.created_before_date)

        self.advanced_filter_layout.addWidget(self.starred_checkbox)
        self.advanced_filter_layout.addWidget(
            self.apply_advanced_filter_button)
        self.advanced_filter_layout.addWidget(
            self.clear_advanced_filter_button)

        self.advanced_filter_layout.setSpacing(15)
        self.advanced_filter_layout.setContentsMargins(5, 5, 5, 5)
        self.advanced_filter_layout.setSpacing(5)
        self.advanced_filters_widget = QWidget()
        self.advanced_filters_widget.setLayout(self.advanced_filter_layout)
        self.advanced_filters_widget.setObjectName("advanced_filters_widget")
        self.advanced_filters_widget.hide()

        main_layout.addWidget(self.advanced_filters_widget)

        unified_layout.addStretch()

        self.scan_options_button = QPushButton("Pastas Locais")
        self.scan_options_button.clicked.connect(self._show_scan_options)
        self.sync_drive_button = QPushButton("Atualizar Drive")
        self.sync_drive_button.clicked.connect(self._start_drive_sync)
        self.reindex_button = QPushButton("Reindexar arquivos locais")
        self.reindex_button.clicked.connect(self._reindex_local_files)
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self._start_auth)
        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.handle_logout)
        self.auth_status_label = QLabel("Verificando...")
        self.auth_status_label.setFixedWidth(150)
        self.clear_cache_button = QPushButton("Limpar Cache")
        self.clear_cache_button.clicked.connect(self.clear_thumbnail_cache)
        self.explorer_button = QPushButton("Explorer Local")
        self.explorer_button.clicked.connect(self.toggle_explorer_special)

        unified_layout.addWidget(self.tools_button)
        unified_layout.addWidget(self.auth_status_label)
        unified_layout.addWidget(self.login_button)
        unified_layout.addWidget(self.logout_button)

        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.search_entry.setCompleter(self.completer)

        main_layout.addWidget(unified_bar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        from file_list_model import FileListModel
        from file_list_delegate import FileListDelegate

        self.file_list_view = FileListView()
        self.file_list_model = FileListModel([])
        self.file_list_view.setModel(self.file_list_model)
        self.file_list_view.setSelectionMode(
            QListView.SelectionMode.SingleSelection)
        self.file_list_view.setItemDelegate(FileListDelegate(
            self.file_list_view, indexer=self.indexer))
        self.file_list_view.setUniformItemSizes(True)
        self.file_list_view.setMinimumHeight(400)
        self.file_list_view.setMinimumWidth(500)
        self.file_list_view.clicked.connect(self.on_file_selected)
        self.file_list_view.doubleClicked.connect(self.on_double_click)
        self.file_list_view.verticalScrollBar().valueChanged.connect(self.on_scroll)

        self.file_list_view.setDragEnabled(True)
        self.file_list_view.setAcceptDrops(False)
        self.file_list_view.setDropIndicatorShown(False)
        self.file_list_view.setDragDropMode(
            QAbstractItemView.DragDropMode.DragOnly)

        self.details_panel = FileDetailsPanel(self)

        self.splitter.addWidget(self.file_list_view)
        self.splitter.addWidget(self.details_panel)
        self.details_panel.setMinimumWidth(320)
        self.details_panel.setMaximumWidth(340)
        self.splitter.setSizes([900, 340])

        main_layout.addWidget(self.splitter)

        self.loading_label = QLabel("Carregando...")
        self.loading_label.setFixedHeight(30)
        self.loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading_label.hide()
        main_layout.addWidget(self.loading_label)

        self.status_bar = self.statusBar()
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.status_bar.addWidget(self.progress_bar, 1)

        self.all_loaded_label = QLabel("Todos os arquivos foram carregados.")
        self.all_loaded_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.all_loaded_label.setFixedHeight(30)
        self.all_loaded_label.hide()
        main_layout.addWidget(self.all_loaded_label)

        self.update_ui_for_auth_state(False)
        self.update_filter_buttons()

        self.extension_combo.currentIndexChanged.connect(
            self.apply_advanced_filters)
        self.modified_after_date.dateChanged.connect(
            self.apply_advanced_filters)
        self.created_after_date.dateChanged.connect(
            self.apply_advanced_filters)
        self.created_before_date.dateChanged.connect(
            self.apply_advanced_filters)
        self.starred_checkbox.stateChanged.connect(self.apply_advanced_filters)

        self.setStyleSheet("""
            /* Fundo principal escuro */
            QMainWindow {
                background-color: #121212;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                color: #ffffff;
            }

    /* Barra unificada: fundo escuro com sombra sutil */
    QFrame {
        background-color: #1e1e1e;
        border: 1px solid #333333;
        border-radius: 10px;
    }            /* Botões: menores e consistentes */
            QPushButton {
                background-color: #1976d2;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;  /* Reduzido de 10px 16px para 6px 12px */
                font-weight: 500;
                font-size: 12px;  /* Tamanho de fonte menor */
            }
            QPushButton:hover {
                background-color: #1565c0;
            }
            QPushButton:pressed {
                background-color: #0d47a1;
            }
            QPushButton:disabled {
                background-color: #424242;
                color: #9e9e9e;
            }

            QPushButton{
                font-weight: bold;  /* Destaque o botão */
            }

            QPushButton#more_filters_button:checked {
                background-color: #0d47a1;  /* Azul mais escuro quando ativo */
            }

            /* QToolButton (botão "Ferramentas"): mesmo estilo dos QPushButton */
            QToolButton {
                background-color: #1976d2;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;  /* Mesmo padding reduzido */
                font-weight: 500;
                font-size: 12px;
            }
            QToolButton:hover {
                background-color: #1565c0;
            }
            QToolButton:pressed {
                background-color: #0d47a1;
            }
            QToolButton:disabled {
                background-color: #424242;
                color: #9e9e9e;
            }
            QToolButton::menu-indicator {
                image: none;  /* Remove ícone padrão do menu */
            }

            /* Combos: estilo escuro */
            QComboBox {
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 4px 8px;  /* Padding menor */
                background-color: #2c2c2c;
                color: #ffffff;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #1976d2;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow_dark.png);
                width: 12px;
                height: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #2c2c2c;
                color: #ffffff;
                selection-background-color: #1976d2;
            }

            /* Labels: texto branco */
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QLabel#title {
                font-weight: bold;
                font-size: 14px;
                color: #1976d2;
            }

            #advanced_filters_widget QLabel {
                margin: 0px;
                padding: 0px;
                font-size: 12px;
            }
            #advanced_filters_widget QComboBox,
            #advanced_filters_widget QDateEdit,
            #advanced_filters_widget QCheckBox,
            #advanced_filters_widget QPushButton {
                margin: 0px;
                padding: 2px 4px;
            }
            #advanced_filters_widget {
                max-height: 40px;
            }
            /* Lista de arquivos: fundo alternado escuro */
            QListView {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 8px;
                alternate-background-color: #2c2c2c;
            }
            QListView::item {
                padding: 6px;  /* Padding menor */
                border-bottom: 1px solid #333333;
                color: #ffffff;
                border: 1px solid transparent;
            }
            QListView::item:selected {
                background-color: #1976d2;
                color: #ffffff;
                border-color: #1976d2;
            }

            /* Painel de detalhes: card escuro */
            FileDetailsPanel {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                border-radius: 10px;
            }
            FileDetailsPanel QLabel {
                font-size: 12px;
                margin: 3px 0;  /* Margem menor */
                color: #ffffff;
            }

            /* Barra de progresso: azul para sucesso */
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                background-color: #2c2c2c;
            }
            QProgressBar::chunk {
                background-color: #1976d2;
                border-radius: 4px;
            }

            /* Status bar: fundo escuro */
            QStatusBar {
                background-color: #1e1e1e;
                border-top: 1px solid #333333;
                color: #ffffff;
            }

            /* Entradas de texto: fundo escuro */
            QLineEdit {
                background-color: #2c2c2c;
                border: 1px solid #555555;
                border-radius: 6px;
                padding: 4px;  /* Padding menor */
                color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #1976d2;
            }
        """)

    def _populate_extension_combo(self):
        self.indexer.ensure_conn()
        self.extension_combo.clear()
        self.extension_combo.addItem("Todas", "")
        self.indexer.cursor.execute("SELECT DISTINCT name FROM files")
        extensions = set()
        for row in self.indexer.cursor.fetchall():
            name = row[0]
            ext = os.path.splitext(name)[1].lower()
            if ext:
                extensions.add(ext)
        for ext in sorted(extensions):
            self.extension_combo.addItem(ext, ext)

    def apply_advanced_filters(self):
        filters = {}

        extension_value = self.extension_combo.currentData()
        if extension_value not in [None, '']:
            filters['extension'] = extension_value

        default_modified = QDate.currentDate().addDays(-7)
        if self.modified_after_date.date() != default_modified:
            filters['modified_after'] = self.modified_after_date.date().toPyDate()

        default_created_after = QDate.currentDate().addDays(-7)
        if self.created_after_date.date() != default_created_after:
            filters['created_after'] = self.created_after_date.date().toPyDate()

        default_created_before = QDate.currentDate()
        if self.created_before_date.date() != default_created_before:
            filters['created_before'] = self.created_before_date.date().toPyDate()

        if self.starred_checkbox.isChecked():
            filters['is_starred'] = True

        self.advanced_filters = filters
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def clear_advanced_filters(self):
        self.extension_combo.setCurrentIndex(0)
        self.modified_after_date.setDate(QDate.currentDate().addDays(-7))
        self.created_after_date.setDate(QDate.currentDate().addDays(-7))
        self.created_before_date.setDate(QDate.currentDate())
        self.advanced_filters = {}
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()
        self.starred_checkbox.setChecked(False)

    def clear_thumbnail_cache(self):
        self.indexer.clear_cache()
        self.status_bar.showMessage("Cache de miniaturas limpo.", 5000)
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def navigate_to_root(self, source):
        self.current_view = None
        self.current_folder_id = None
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def navigate_to_folder(self, folder_id):
        self.search_term = ""
        self.search_entry.clear()
        self.current_folder_id = folder_id
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def update_filter_buttons(self):
        is_searching = bool(self.search_term)
        self.filter_combo.setEnabled(not is_searching)
        self.sort_combo.setEnabled(not is_searching)

    def change_filter_type_combo(self, index):
        self.current_filter = self.filter_combo.itemData(index)
        print(f"DEBUG: Filtro alterado para: {self.current_filter}")
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def change_sort_order(self, index):
        self.current_sort = self.sort_combo.itemData(index)
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def toggle_explorer_special(self):
        self.explorer_special_active = not self.explorer_special_active
        self.explorer_action.setChecked(self.explorer_special_active)
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()

    def toggle_advanced_filters(self):
        if self.advanced_filters_widget.isVisible():
            self.advanced_filters_widget.hide()
            self.more_filters_button.setText("Mais Filtros ▼")
            self.more_filters_button.setChecked(False)
        else:
            self.advanced_filters_widget.show()
            self.more_filters_button.setText("Menos Filtros ▲")
            self.more_filters_button.setChecked(True)
            self.apply_advanced_filters()

    def handle_search_input(self, text):
        if text:
            self.search_timer.stop()
            self.search_timer.start(500)
            self.update_search_suggestions()
        else:
            self.search_timer.stop()
            self.search_term = ""
            self.completer_model.setStringList([])
            self.current_page = 0
            self.all_files_loaded = False
            self.current_folder_id = None
            self.clear_display()
            self.load_next_batch()

        self.update_filter_buttons()

    def update_search_suggestions(self):
        text = self.search_entry.text().strip()
        if not text:
            self.completer_model.setStringList([])
            return

        suggestions = self.indexer.get_search_suggestions(
            text, self.is_authenticated)
        self.completer_model.setStringList(suggestions)

    def handle_search_request(self):
        self.search_term = self.search_entry.text().strip().lower()
        self.current_page = 0
        self.all_files_loaded = False
        self.current_folder_id = None
        self.clear_display()
        self.load_next_batch()

    def update_ui_for_auth_state(self, is_authenticated):
        self.is_authenticated = is_authenticated
        self.login_button.setVisible(not is_authenticated)
        self.logout_button.setVisible(is_authenticated)

    def on_scroll(self, value):
        scroll_bar = self.file_list_view.verticalScrollBar()
        threshold = scroll_bar.maximum() * 0.2
        if value >= scroll_bar.maximum() - threshold and not self.is_loading and not self.all_files_loaded:
            self.scroll_loading = True
            self.load_next_batch()

    def _show_scan_options(self):
        if self.local_scan_thread and self.local_scan_thread.isRunning():
            QMessageBox.warning(
                self, "Aviso", "Aguarde a conclusão do escaneamento local.")
            return

        dialog = OptionsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_paths = dialog.get_selected_paths()
            show_drive_metadata = dialog.get_show_drive_metadata()
            settings = load_settings()
            settings['scan_paths'] = selected_paths
            settings['show_drive_metadata'] = show_drive_metadata
            save_settings(settings)

            self.show_drive_metadata = show_drive_metadata

            if show_drive_metadata and self.is_authenticated:
                self._start_drive_sync()

            self.current_view = 'local'
            self.current_folder_id = None
            self.clear_display()
            self.all_files_loaded = False
            self.current_page = 0

            if selected_paths:
                self._start_local_scan(selected_paths)
            else:
                self.indexer.cursor.execute(
                    "DELETE FROM files WHERE source='local'")
                self.indexer.cursor.execute(
                    "DELETE FROM search_index WHERE source='local'")
                self.indexer.conn.commit()
                self.loading_label.setText("Nenhum arquivo encontrado.")
                self.loading_label.show()
                self.all_files_loaded = True

            self.load_next_batch()

    def _start_local_scan(self, paths_to_scan):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.all_loaded_label.hide()

        self.local_scan_thread = QThread()
        self.local_scan_worker = LocalScanWorker(
            db_name=self.indexer.db_name, scan_path=paths_to_scan)
        self.local_scan_worker.moveToThread(self.local_scan_thread)

        self.local_scan_worker.finished.connect(self.on_local_scan_finished)
        self.local_scan_worker.update_status_signal.connect(
            self.status_bar.showMessage)
        self.local_scan_worker.progress_update.connect(
            self.update_local_scan_progress)

        self.local_scan_thread.started.connect(self.local_scan_worker.run)
        self.local_scan_thread.start()

    def on_local_scan_finished(self):
        try:
            file_count = self.indexer.get_file_count(source='local')
            self.tray_icon.showMessage("Sincronização Local Concluída",
                                       f"Escaneamento concluido. {file_count} arquivos locais indexados", QSystemTrayIcon.MessageIcon.Information, 3000)
        except Exception as e:
            print(f"Erro ao acessar banco em on_local_scan_finished: {e}")
            self.tray_icon.showMessage("Sincronização Local Concluída",
                                       "Escaneamento concluido.", QSystemTrayIcon.MessageIcon.Information, 3000)

        self.status_bar.showMessage("Escaneamento local concluído.", 5000)
        self.progress_bar.setVisible(False)
        self.local_scan_thread.quit()
        self.local_scan_thread.wait()
        self.local_scan_worker.deleteLater()
        self.local_scan_thread.deleteLater()
        self.local_scan_worker = None
        self.local_scan_thread = None

        self.current_view = 'local'
        self.advanced_filters = {}
        self.extension_combo.setCurrentIndex(0)
        self._populate_extension_combo()
        self.clear_display()
        self.load_next_batch()

        self.apply_advanced_filters()

    def update_local_scan_progress(self, files_processed):
        self.status_bar.showMessage(
            f"Escaneando arquivos locais... {files_processed} arquivos processados.")

    def _check_initial_auth(self):
        self.update_ui_for_auth_state(False)
        self.auth_status_label.setText("Verificando credenciais...")

        creds = None
        TOKEN_FILE = 'token.json'
        CREDENTIALS_FILE = 'credentials.json'
        from google_auth_oauthlib.flow import InstalledAppFlow

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                print("Token atualizado com sucesso.")
            except Exception as e:
                print(f"Falha ao atualizar token: {e}")
                creds = None

        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(
                    TOKEN_FILE, SCOPES)
                if not creds or not creds.valid or not creds.refresh_token or not creds.client_id or not creds.client_secret:
                    raise ValueError("Token inválido ou incompleto.")
            except Exception:
                creds = None

        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                self.auth_status_label.setText(
                    "Arquivo credentials.json não encontrado.")
                self.load_next_batch()
                return
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

        if creds and creds.valid:
            self.service = build('drive', 'v3', credentials=creds)
            self.update_ui_for_auth_state(True)
            self.auth_status_label.setText("Logado com Google")
            self._start_drive_sync()
        else:
            self.auth_status_label.setText("Não Autenticado")
            self.load_next_batch()

    def _start_auth(self):
        if self.auth_thread and self.auth_thread.isRunning():
            self.status_bar.showMessage(
                "Processo de login já em andamento...", 5000)
            return

        self.status_bar.showMessage(
            "Abrindo navegador para autenticação...", 5000)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.login_button.setEnabled(False)

        self.auth_thread = QThread()
        self.auth_worker = AuthWorker()
        self.auth_worker.moveToThread(self.auth_thread)

        self.auth_worker.authenticated.connect(self.on_auth_success)
        self.auth_worker.auth_failed.connect(self.on_auth_fail)

        self.auth_thread.started.connect(self.auth_worker.run)
        self.auth_thread.start()

    def on_auth_success(self, creds):
        self.progress_bar.setVisible(False)
        self.login_button.setEnabled(True)
        self.status_bar.showMessage(
            "Login bem-sucedido. Sincronizando arquivos...", 5000)
        self.auth_status_label.setText("Logado com Google")
        self.service = build('drive', 'v3', credentials=creds)
        self.update_ui_for_auth_state(True)
        self._start_drive_sync()

        self.auth_thread.quit()
        self.auth_thread.wait()
        self.auth_worker.deleteLater()
        self.auth_thread.deleteLater()
        self.auth_worker = None
        self.auth_thread = None

    def on_auth_fail(self, error_message):
        self.progress_bar.setVisible(False)
        self.login_button.setEnabled(True)
        QMessageBox.critical(self, "Erro de Autenticação", error_message)
        self.status_bar.showMessage("Login falhou.", 5000)
        self.auth_status_label.setText("Não Autenticado")

        self.auth_thread.quit()
        self.auth_thread.wait()
        self.auth_worker.deleteLater()
        self.auth_thread.deleteLater()
        self.auth_worker = None
        self.auth_thread = None

    def handle_logout(self):
        try:
            TOKEN_FILE = 'token.json'
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
            self.status_bar.showMessage("Logout bem-sucedido.", 5000)
            self.service = None
            self.indexer.ensure_conn()
            self.indexer.cursor.execute(
                "DELETE FROM files WHERE source='drive'")
            self.indexer.cursor.execute(
                "DELETE FROM search_index WHERE source='drive'")
            self.indexer.conn.commit()
            self.clear_display()
            self.update_ui_for_auth_state(False)
            self.auth_status_label.setText("Não Autenticado")
            self.current_view = 'local'
            self.current_folder_id = None
            self.load_next_batch()
        except Exception as e:
            print(f"Erro ao fazer logout: {e}")
            QMessageBox.warning(self, "Erro", f"Falha ao fazer logout: {e}")

    def _start_drive_sync(self):
        if self.drive_sync_thread and self.drive_sync_thread.isRunning():
            self.status_bar.showMessage(
                "Sincronização do Drive já em andamento...", 5000)
            return
        if not self.service:
            QMessageBox.warning(
                self, "Erro", "Não autenticado no Google Drive.")
            return

        try:
            self.indexer.ensure_conn()
            file_count = self.indexer.get_file_count(source='drive')
        except Exception as e:
            print(f"Erro ao verificar contagem de arquivos: {e}")
            file_count = 0

        if file_count == 0:
            progress = QProgressDialog(
                "Sincronizando arquivos...", "Cancelar", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setAutoClose(True)
            progress.setAutoReset(True)
            progress.setFixedSize(400, 150)
            progress.setStyleSheet("""
        QProgressBar {
            min-height: 25px;  /* Barra mais grossa */
            border: 1px solid #ccc;
            border-radius: 5px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;  /* Cor verde para progresso */
            border-radius: 5px;
        }
    """)

            self.drive_sync_thread = QThread()
            self.drive_sync_worker = DriveSyncWorker(
                self.service, db_name=self.indexer.db_name)
            self.drive_sync_worker.moveToThread(self.drive_sync_thread)

            self.drive_sync_worker.progress_update.connect(
                lambda value, msg: (progress.setValue(value), progress.setLabelText(msg)))
            self.drive_sync_worker.sync_finished.connect(
                lambda: progress.close())
            self.drive_sync_worker.sync_failed.connect(
                lambda: progress.close())
            progress.canceled.connect(self.drive_sync_worker.terminate)

            self.drive_sync_thread.started.connect(self.drive_sync_worker.run)
            self.drive_sync_thread.start()
            progress.exec()

            self.drive_sync_thread.quit()
            self.drive_sync_thread.wait()
            self.drive_sync_worker.deleteLater()
            self.drive_sync_thread.deleteLater()
            self.drive_sync_worker = None
            self.drive_sync_thread = None
        else:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)

            self.drive_sync_thread = QThread()
            self.drive_sync_worker = DriveSyncWorker(
                self.service, db_name=self.indexer.db_name)
            self.drive_sync_worker.moveToThread(self.drive_sync_thread)

            self.drive_sync_worker.sync_finished.connect(
                self.on_drive_sync_finished)
            self.drive_sync_worker.sync_failed.connect(
                self.on_drive_sync_failed)
            self.drive_sync_worker.update_status.connect(
                self.status_bar.showMessage)
            self.drive_sync_worker.progress_update.connect(
                self.update_drive_sync_progress)

            self.drive_sync_thread.started.connect(self.drive_sync_worker.run)
            self.drive_sync_thread.start()

    def on_drive_sync_finished(self):
        self.status_bar.showMessage("Sincronização do Drive concluída.", 5000)
        self.progress_bar.setVisible(False)
        self.drive_sync_thread.quit()
        self.drive_sync_thread.wait()
        self.drive_sync_worker.deleteLater()
        self.drive_sync_thread.deleteLater()
        self.drive_sync_worker = None
        self.drive_sync_thread = None

        self.current_view = None
        self.current_folder_id = None
        self.advanced_filters = {}
        self.extension_combo.setCurrentIndex(0)
        self._populate_extension_combo()
        self.clear_display()
        self.load_next_batch()

        self.apply_advanced_filters()

    def on_drive_sync_failed(self, error_message):
        self.status_bar.showMessage(error_message, 5000)
        self.tray_icon.showMessage(
            "Erro de Sincronização", f"Falha na sincronização do Google Drive: {error_message}", QSystemTrayIcon.MessageIcon.Critical, 5000)
        self.progress_bar.setVisible(False)
        self.drive_sync_thread.quit()
        self.drive_sync_thread.wait()
        self.drive_sync_worker.deleteLater()
        self.drive_sync_thread.deleteLater()
        self.drive_sync_worker = None
        self.drive_sync_thread = None
        self.update_ui_for_auth_state(False)

    def update_drive_sync_progress(self, value, msg):
        self.status_bar.showMessage(msg)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)

    def clear_display(self):
        self.all_loaded_label.hide()
        self.file_list_model.setFiles([])

        if hasattr(self.details_panel, 'thumbnail_thread') and self.details_panel.thumbnail_thread:
            try:
                if self.details_panel.thumbnail_thread.isRunning():
                    self.details_panel.thumbnail_thread.quit()
                    if not self.details_panel.thumbnail_thread.wait(2000):
                        print(
                            "Aviso: Thumbnail thread não terminou ao limpar display.")
                self.details_panel.thumbnail_thread.deleteLater()
            except Exception as e:
                print(f"Erro ao limpar thumbnail thread: {e}")
        if hasattr(self.details_panel, 'thumbnail_worker') and self.details_panel.thumbnail_worker:
            try:
                self.details_panel.thumbnail_worker.deleteLater()
            except Exception as e:
                print(f"Erro ao limpar thumbnail worker: {e}")

        self.details_panel.thumbnail_worker = None
        self.details_panel.thumbnail_thread = None
        self.details_panel.hide()

    def load_next_batch(self):
        if self.is_loading or self.all_files_loaded:
            return

        self.is_loading = True
        self.loading_label.show()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage("Carregando arquivos...", 0)

        try:
            self.indexer.ensure_conn()
            search_all_sources = bool(
                self.search_term and self.is_authenticated)
            source = self.current_view if not search_all_sources else None

            files_to_add = self._load_files_for_filters(source)
            print(
                f"DEBUG: Carregados {len(files_to_add)} arquivos para filtro '{self.current_filter}', source='{source}'")

            if not files_to_add:
                self.all_files_loaded = True
                if not self.file_list_model.rowCount():
                    self.loading_label.setText("Nenhum arquivo encontrado.")
                    self.loading_label.show()
                else:
                    self.loading_label.hide()
                    self.all_loaded_label.show()
            else:
                self._add_thumbnail_widgets(files_to_add)
                if len(files_to_add) < self.page_size:
                    self.all_files_loaded = True
                    self.all_loaded_label.show()
                self.current_page += 1
                self.loading_label.hide()

        except Exception as e:
            print(f"Erro ao carregar arquivos: {e}")
            self.loading_label.setText("Erro ao carregar arquivos.")
            self.loading_label.show()
        finally:
            self.is_loading = False
            self.scroll_loading = False
            self.progress_bar.setVisible(False)
            self.status_bar.showMessage("Arquivos carregados.", 3000)

    def _load_files_for_filters(self, source):
        print(
            f"DEBUG: _load_files_for_filters chamado com source='{source}', current_filter='{self.current_filter}', advanced_filters='{self.advanced_filters}'")
        folder_id = self.current_folder_id
        filter_type = self.current_filter

        if not self.search_term and folder_id is None:
            if self.advanced_filters.get('is_starred') or self.advanced_filters.get('extension') not in [None, '']:
                filter_type = 'all'
                local_files = self.indexer.load_files_paged(
                    'local', self.current_page, self.page_size, None, self.current_sort, filter_type, None, self.advanced_filters, explorer_special=self.explorer_special_active
                )
                drive_files = []
                if self.is_authenticated and self.show_drive_metadata:
                    drive_files = self.indexer.load_files_paged(
                        'drive', self.current_page, self.page_size, None, self.current_sort, filter_type, None, self.advanced_filters, explorer_special=self.explorer_special_active
                    )
                return local_files + drive_files
            else:
                local_files = self.indexer.load_files_paged(
                    'local', self.current_page, self.page_size, None, self.current_sort, filter_type, None, self.advanced_filters, explorer_special=self.explorer_special_active
                )
                drive_files = []
                if self.is_authenticated and self.show_drive_metadata:
                    drive_files = self.indexer.load_files_paged(
                        'drive', self.current_page, self.page_size, None, self.current_sort, filter_type, None, self.advanced_filters, explorer_special=self.explorer_special_active
                    )
                return local_files + drive_files
        else:
            if self.advanced_filters.get('extension'):
                filter_type = 'all'
            files = self.indexer.load_files_paged(
                source, self.current_page, self.page_size, self.search_term,
                self.current_sort, filter_type, folder_id, self.advanced_filters, explorer_special=self.explorer_special_active
            )
            if not self.show_drive_metadata:
                files = [f for f in files if not (
                    f.get('source') == 'drive' and not f.get('path'))]
            return files

    def _add_thumbnail_widgets(self, files_to_add):
        if self.current_page == 0:
            self.file_list_model.setFiles(files_to_add)
        else:
            self.file_list_model.addFiles(files_to_add)

    def on_file_selected(self, index):
        file_item = self.file_list_model.data(index, Qt.ItemDataRole.UserRole)
        if file_item:
            self.details_panel.update_details(file_item)

    def on_double_click(self, index):
        file_item = self.file_list_model.data(index, Qt.ItemDataRole.UserRole)
        if file_item and file_item.get('mimeType') in ['application/vnd.google-apps.folder', 'folder']:
            self.current_page = 0
            self.all_files_loaded = False
            self.clear_display()
            self.current_folder_id = file_item['id']
            self.load_next_batch()
        elif file_item:
            if file_item.get('source') == 'local' and file_item.get('path'):
                try:
                    os.startfile(file_item['path'])
                    print(f"Abrindo arquivo local: {file_item['path']}")
                except Exception as e:
                    print(f"Erro ao abrir arquivo local: {e}")
            elif file_item.get('source') == 'drive' and file_item.get('webViewLink'):
                webbrowser.open(file_item['webViewLink'])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace:
            if self.current_folder_id:
                self.go_to_parent_folder()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            selected_indexes = self.file_list_view.selectedIndexes()
            if selected_indexes:
                self.on_double_click(selected_indexes[0])
        else:
            super().keyPressEvent(event)

    def go_to_parent_folder(self):
        self.indexer.cursor.execute(
            "SELECT parentId FROM files WHERE file_id = ?", (self.current_folder_id,))
        row = self.indexer.cursor.fetchone()
        parent_id = row[0] if row else None
        self.navigate_to_folder(parent_id)


class FileDetailsPanel(QFrame):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_loading = False

        self.content_widget = QWidget()
        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.title_label = QLabel("Detalhes do Arquivo")
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.title_label)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(192, 192)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.thumbnail_label)

        self.separator = QFrame()
        self.separator.setFrameShape(QFrame.Shape.HLine)
        self.separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(self.separator)

        self.form_layout = QFormLayout()
        self.name_label = QLabel("N/A")
        self.source_label = QLabel("N/A")
        self.size_label = QLabel("N/A")
        self.path_label = QLabel("N/A")
        self.path_label.setWordWrap(True)
        self.description_label = QLabel("N/A")
        self.description_label.setWordWrap(True)

        self.form_layout.addRow(QLabel("<b>Nome:</b>"), self.name_label)
        self.form_layout.addRow(QLabel("<b>Fonte:</b>"), self.source_label)
        self.form_layout.addRow(QLabel("<b>Tamanho:</b>"), self.size_label)
        self.form_layout.addRow(
            QLabel("<b>Caminho/Link:</b>"), self.path_label)
        self.form_layout.addRow(
            QLabel("<b>Descrição:</b>"), self.description_label)

        self.open_folder_button = QPushButton("Abrir pasta")
        self.open_folder_button.setVisible(False)
        self.open_folder_button.clicked.connect(self.open_folder)
        self.form_layout.addRow(QLabel(""), self.open_folder_button)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll_area)

        self.current_file_item = None
        self.parent_app = parent
        self.temp_download_widget = None

        self.hide()

    def update_details(self, file_item):
        if hasattr(self, 'thumbnail_thread') and self.thumbnail_thread:
            try:
                if self.thumbnail_thread.isRunning():
                    self.thumbnail_thread.quit()
                    self.thumbnail_thread.wait()
                self.thumbnail_worker.deleteLater()
                self.thumbnail_thread.deleteLater()
            except Exception:
                pass
            self.thumbnail_worker = None
            self.thumbnail_thread = None

        self.title_label.setText("Detalhes do Arquivo")
        self.name_label.setText(file_item.get('name', 'N/A'))
        self.source_label.setText("Google Drive" if file_item.get(
            'source') == 'drive' else "Local")
        self.size_label.setText(format_size(file_item.get('size', 0)) if file_item.get(
            'mimeType') not in ['application/vnd.google-apps.folder', 'folder'] else "N/A")
        self.path_label.setText(file_item.get(
            'path', file_item.get('webViewLink', 'N/A')))
        self.description_label.setText(file_item.get('description', 'N/A'))
        self.current_file_item = file_item

        self.thumbnail_label.setPixmap(get_generic_thumbnail(
            file_item.get('mimeType'), size=(96, 96)))

        thumbnail_path = file_item.get('thumbnailPath')
        thumbnail_link = file_item.get('thumbnailLink')
        mime = file_item.get('mimeType', '')
        local_path = file_item.get('path')

        shown = False
        if local_path and os.path.exists(local_path):
            if mime.startswith('image/'):
                pixmap = QPixmap(local_path)
                if not pixmap.isNull():
                    self.thumbnail_label.setPixmap(pixmap.scaled(
                        self.thumbnail_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                    self.show()
                    shown = True
            elif mime == 'application/pdf' and self.parent_app.thread_pool.activeThreadCount() < 5:
                try:
                    import fitz
                    doc = fitz.open(local_path)
                    page = doc.load_page(0)
                    pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                    img_data = pix.tobytes('ppm')
                    from PyQt6.QtGui import QImage
                    qimg = QImage()
                    qimg.loadFromData(img_data)
                    pixmap = QPixmap.fromImage(qimg)
                    if not pixmap.isNull():
                        self.thumbnail_label.setPixmap(pixmap.scaled(
                            self.thumbnail_label.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        ))
                        self.show()
                        shown = True
                except Exception:
                    pass
            elif mime.startswith('video/') and self.parent_app.thread_pool.activeThreadCount() < 5:
                try:
                    import cv2
                    cap = cv2.VideoCapture(local_path)
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        import numpy as np
                        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = frame.shape
                        bytes_per_line = ch * w
                        from PyQt6.QtGui import QImage
                        qimg = QImage(frame.data, w, h, bytes_per_line,
                                      QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(qimg)
                        if not pixmap.isNull():
                            self.thumbnail_label.setPixmap(pixmap.scaled(
                                self.thumbnail_label.size(),
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation
                            ))
                            self.show()
                            shown = True
                except Exception:
                    pass
            else:
                self.thumbnail_label.setPixmap(
                    get_generic_thumbnail(mime, size=(96, 96)))
                self.show()
                shown = True
        else:
            if file_item.get('source') == 'drive' and thumbnail_link:
                self.thumbnail_thread = QThread()
                self.thumbnail_worker = ThumbnailWorker(
                    thumbnail_link, file_item)
                self.thumbnail_worker.moveToThread(self.thumbnail_thread)
                self.thumbnail_thread.started.connect(
                    self.thumbnail_worker.run)
                self.thumbnail_worker.finished.connect(
                    self.on_thumbnail_loaded)
                self.thumbnail_thread.start()
            self.show()

        if file_item.get('source') == 'local' and file_item.get('path') and os.path.exists(file_item.get('path')):
            self.open_folder_button.setVisible(True)
        else:
            self.open_folder_button.setVisible(False)

    def open_folder(self):
        import os
        import sys
        from PyQt6.QtWidgets import QMessageBox
        file_path = self.current_file_item.get('path')
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Arquivo não encontrado",
                                "O caminho do arquivo não existe.")
            return
        folder = os.path.dirname(file_path)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", folder])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", folder])
        except Exception as e:
            QMessageBox.critical(self, "Erro ao abrir pasta",
                                 f"Não foi possível abrir a pasta: {e}")
        self.show()

    def on_thumbnail_loaded(self, image_data, thumbnail_path):

        if image_data and thumbnail_path:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                self.thumbnail_label.setPixmap(pixmap.scaled(
                    self.thumbnail_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                conn = sqlite3.connect('file_index.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE files SET thumbnailPath = ? WHERE file_id = ?",
                               (thumbnail_path, self.current_file_item.get('id')))
                conn.commit()
                conn.close()
            else:
                self.thumbnail_label.setPixmap(get_generic_thumbnail(
                    self.current_file_item.get('mimeType'), size=(96, 96)))
        else:
            self.thumbnail_label.setPixmap(get_generic_thumbnail(
                self.current_file_item.get('mimeType'), size=(96, 96)))

        if self.thumbnail_worker and self.thumbnail_thread:
            self.thumbnail_thread.quit()
            self.thumbnail_thread.wait()
            self.thumbnail_worker.deleteLater()
            self.thumbnail_thread.deleteLater()
            self.thumbnail_worker = None
            self.thumbnail_thread = None


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
