# ui.py - Interface principal do Vox Imago
# Contém DriveFileGalleryApp e FileDetailsPanel.
# Gerencia a interface gráfica, eventos, filtros, autenticação e integração com os módulos do projeto.

import os
import time
import sqlite3

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from workers import AuthWorker, ThumbnailWorker, LocalScanWorker, DriveSyncWorker

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QMessageBox, QFrame, QSizePolicy, QSpacerItem, QFileDialog,
    QDialog, QCheckBox, QDialogButtonBox, QProgressBar, QComboBox, QCompleter,
    QFormLayout, QSplitter, QDateEdit
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QTimer, QStringListModel, QDate, QThread, pyqtSignal, QThreadPool

from database import FileIndexer
from widgets import OptionsDialog, FileItemWidget
from utils import format_size, get_generic_thumbnail, load_settings, save_settings
from utils import SETTINGS_FILE as TOKEN_FILE


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

        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(8)

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
        for i in range(self.files_layout.count()):
            item = self.files_layout.itemAt(i)
            widget = item.widget()
            if isinstance(widget, FileItemWidget):
                widget.cleanup()

        if self.local_scan_thread and self.local_scan_thread.isRunning():
            self.local_scan_worker.stop()
            self.local_scan_thread.quit()
            self.local_scan_thread.wait()

        if self.drive_sync_thread and self.drive_sync_thread.isRunning():
            self.drive_sync_thread.quit()
            self.drive_sync_thread.wait()

        self.indexer.close()
        event.accept()

    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        unified_bar = QFrame()
        unified_bar.setFrameShape(QFrame.Shape.StyledPanel)
        unified_bar.setFrameShadow(QFrame.Shadow.Raised)
        unified_bar.setFixedHeight(50)

        unified_layout = QHBoxLayout(unified_bar)
        unified_layout.setContentsMargins(10, 5, 10, 5)

        self.app_title_label = QLabel("VI-MB")
        self.app_title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        unified_layout.addWidget(self.app_title_label)
        unified_layout.addSpacing(15)

        self.view_label = QLabel("Visualizando: Local")
        self.view_label.setFixedWidth(150)
        unified_layout.addWidget(self.view_label)

        unified_layout.addStretch()

        self.breadcrumb_layout = QHBoxLayout()
        self.breadcrumb_widget = QWidget()
        self.breadcrumb_widget.setLayout(self.breadcrumb_layout)
        unified_layout.addWidget(self.breadcrumb_widget)

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

        unified_layout.addWidget(QLabel("Filtrar:"))
        unified_layout.addWidget(self.filter_combo)
        unified_layout.addSpacing(10)
        unified_layout.addWidget(QLabel("Ordenar por:"))
        unified_layout.addWidget(self.sort_combo)

        self.advanced_filter_layout = QHBoxLayout()
        self.extension_combo = QComboBox()
        self.extension_combo.setEditable(False)
        self.extension_combo.setPlaceholderText("Selecione a extensão")
        self._populate_extension_combo()
        self.modified_after_date = QDateEdit()
        self.modified_after_date.setDate(QDate.currentDate().addDays(-7))
        self.modified_after_date.setCalendarPopup(True)
        self.apply_advanced_filter_button = QPushButton("Aplicar Filtros")
        self.apply_advanced_filter_button.clicked.connect(
            self.apply_advanced_filters)
        self.created_after_date = QDateEdit()
        self.created_after_date.setDate(QDate.currentDate().addDays(-7))
        self.created_after_date.setCalendarPopup(True)
        self.created_before_date = QDateEdit()
        self.created_before_date.setDate(QDate.currentDate())
        self.created_before_date.setCalendarPopup(True)

        self.clear_advanced_filter_button = QPushButton("Limpar Filtros")
        self.clear_advanced_filter_button.clicked.connect(
            self.clear_advanced_filters)

        self.advanced_filter_layout.addWidget(QLabel("Extensão:"))
        self.advanced_filter_layout.addWidget(self.extension_combo)
        self.advanced_filter_layout.addWidget(QLabel("Criado antes:"))
        self.advanced_filter_layout.addWidget(self.created_before_date)
        self.advanced_filter_layout.addWidget(QLabel("Criado após:"))
        self.advanced_filter_layout.addWidget(self.created_after_date)
        self.advanced_filter_layout.addWidget(QLabel("Modificado após:"))
        self.advanced_filter_layout.addWidget(self.modified_after_date)
        self.starred_checkbox = QCheckBox("Favoritos")
        self.advanced_filter_layout.addWidget(self.starred_checkbox)
        self.advanced_filter_layout.addWidget(
            self.apply_advanced_filter_button)
        self.advanced_filter_layout.addWidget(
            self.clear_advanced_filter_button)

        main_layout.addLayout(self.advanced_filter_layout)

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

        unified_layout.addWidget(self.scan_options_button)
        unified_layout.addWidget(self.sync_drive_button)
        unified_layout.addWidget(self.reindex_button)
        unified_layout.addWidget(self.auth_status_label)
        unified_layout.addWidget(self.login_button)
        unified_layout.addWidget(self.logout_button)
        unified_layout.addWidget(self.clear_cache_button)

        self.completer = QCompleter(self.completer_model, self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.search_entry.setCompleter(self.completer)

        main_layout.addWidget(unified_bar)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()

        self.files_layout = QVBoxLayout(self.scroll_content)
        self.files_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_content.setLayout(self.files_layout)
        self.scroll_area.setWidget(self.scroll_content)

        self.details_panel = FileDetailsPanel(self)

        self.splitter.addWidget(self.scroll_area)
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

        self.scroll_area.verticalScrollBar().valueChanged.connect(self.on_scroll)

        self.all_loaded_label = QLabel("Todos os arquivos foram carregados.")
        self.all_loaded_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.all_loaded_label.setFixedHeight(30)
        self.all_loaded_label.hide()
        main_layout.addWidget(self.all_loaded_label)

        self.update_ui_for_auth_state(False)
        self.update_ui_for_view()
        self.update_filter_buttons()
        self.update_breadcrumb()

        self.extension_combo.currentIndexChanged.connect(
            self.apply_advanced_filters)
        self.modified_after_date.dateChanged.connect(
            self.apply_advanced_filters)
        self.created_after_date.dateChanged.connect(
            self.apply_advanced_filters)
        self.created_before_date.dateChanged.connect(
            self.apply_advanced_filters)
        self.starred_checkbox.stateChanged.connect(self.apply_advanced_filters)

    def _populate_extension_combo(self):
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

    def update_breadcrumb(self):
        for i in reversed(range(self.breadcrumb_layout.count())):
            item = self.breadcrumb_layout.itemAt(i)
            if item and item.widget():
                item.widget().deleteLater()

        breadcrumb = self.indexer.get_breadcrumb(
            self.current_folder_id, self.current_view)
        for i, crumb in enumerate(breadcrumb):
            label = ClickableLabel(crumb['name'])
            label.setStyleSheet(
                "font-weight: bold; text-decoration: underline;")
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            label.clicked.connect(lambda checked=False,
                                  fid=crumb['id']: self.navigate_to_folder(fid))
            self.breadcrumb_layout.addWidget(label)
            if i < len(breadcrumb) - 1:
                self.breadcrumb_layout.addWidget(QLabel(" > "))
        self.breadcrumb_layout.addStretch()

    def navigate_to_root(self, source):
        self.current_view = None
        self.current_folder_id = None
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()
        self.update_breadcrumb()

    def navigate_to_folder(self, folder_id):
        self.search_term = ""
        self.search_entry.clear()
        self.current_folder_id = folder_id
        self.current_page = 0
        self.all_files_loaded = False
        self.clear_display()
        self.load_next_batch()
        self.update_breadcrumb()

    def update_filter_buttons(self):
        is_searching = bool(self.search_term)
        self.filter_combo.setEnabled(not is_searching)
        self.sort_combo.setEnabled(not is_searching)

    def update_ui_for_view(self):
        if self.current_view is None:
            view_name = "Unificado"
        elif self.current_view == 'local':
            view_name = "Local"
        else:
            view_name = "Google Drive"
        if self.search_term:
            view_name = "Pesquisa Unificada"
        self.view_label.setText(f"Visualizando: {view_name}")
        self.update_breadcrumb()

    def change_filter_type_combo(self, index):
        self.current_filter = self.filter_combo.itemData(index)
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
        self.update_ui_for_view()

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
        scroll_bar = self.scroll_area.verticalScrollBar()
        if value > 0 and value == scroll_bar.maximum() and not self.is_loading and not self.all_files_loaded:
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
        self.status_bar.showMessage("Escaneamento local concluído.", 5000)
        self.progress_bar.setVisible(False)
        self.local_scan_thread.quit()
        self.local_scan_thread.wait()
        self.local_scan_worker.deleteLater()
        self.local_scan_thread.deleteLater()
        self.local_scan_worker = None
        self.local_scan_thread = None

        self.current_view = 'local'
        self.advenced_filters = {}
        self.extension_combo.setCurrentIndex(0)
        self._populate_extension_combo()
        self.clear_display()
        self.load_next_batch()

        self.apply_advanced_filters()

    def update_local_scan_progress(self, files_found):
        self.status_bar.showMessage(
            f"Escaneando... {files_found} arquivos encontrados.")

    def _check_initial_auth(self):
        self.update_ui_for_auth_state(False)
        self.auth_status_label.setText("Verificando credenciais...")

        creds = None
        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        TOKEN_FILE = 'token.json'
        CREDENTIALS_FILE = 'credentials.json'
        from google_auth_oauthlib.flow import InstalledAppFlow

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
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            self.status_bar.showMessage("Logout bem-sucedido.", 5000)
            self.service = None
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

    def _start_drive_sync(self):
        if self.drive_sync_thread and self.drive_sync_thread.isRunning():
            self.status_bar.showMessage(
                "Sincronização do Drive já em andamento...", 5000)
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.drive_sync_thread = QThread()
        self.drive_sync_worker = DriveSyncWorker(
            self.service, db_name=self.indexer.db_name)
        self.drive_sync_worker.moveToThread(self.drive_sync_thread)

        self.drive_sync_worker.sync_finished.connect(
            self.on_drive_sync_finished)
        self.drive_sync_worker.sync_failed.connect(self.on_drive_sync_failed)
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
        self.progress_bar.setVisible(False)
        self.drive_sync_thread.quit()
        self.drive_sync_thread.wait()
        self.drive_sync_worker.deleteLater()
        self.drive_sync_thread.deleteLater()
        self.drive_sync_worker = None
        self.drive_sync_thread = None
        self.update_ui_for_auth_state(False)

    def update_drive_sync_progress(self, current_value):
        self.status_bar.showMessage(
            f"Sincronizando... {current_value} arquivos encontrados.")
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setValue(current_value)

    def clear_display(self):
        self.all_loaded_label.hide()
        for i in reversed(range(self.files_layout.count())):
            item = self.files_layout.itemAt(i)
            widget = item.widget()
            if widget:
                if hasattr(widget, 'cleanup'):
                    widget.cleanup()
                widget.deleteLater()

        if hasattr(self.details_panel, 'thumbnail_thread') and self.details_panel.thumbnail_thread:
            try:
                if self.details_panel.thumbnail_thread.isRunning():
                    self.details_panel.thumbnail_thread.quit()
                    self.details_panel.thumbnail_thread.wait()
                self.details_panel.thumbnail_worker.deleteLater()
                self.details_panel.thumbnail_thread.deleteLater()
            except Exception:
                pass
            self.details_panel.thumbnail_worker = None
            self.details_panel.thumbnail_thread = None
        self.details_panel.hide()

    def load_next_batch(self):
        if self.is_loading or self.all_files_loaded:
            return

        self.is_loading = True
        self.loading_label.show()
        QApplication.processEvents()

        if not hasattr(self, 'show_drive_metadata'):
            self.show_drive_metadata = load_settings().get('show_drive_metadata', True)

        search_all_sources = bool(self.search_term and self.is_authenticated)
        source = self.current_view if not search_all_sources else None

        start_time = time.time()

        folder_id = self.current_folder_id
        filter_type = self.current_filter

        if not self.search_term and folder_id is None:
            if self.advanced_filters.get('is_starred'):
                filter_type = 'all'
                local_files = self.indexer.load_files_paged(
                    'local', self.current_page, self.page_size, None, self.current_sort, filter_type, None, self.advanced_filters
                )
                drive_files = []
                if self.is_authenticated and self.show_drive_metadata:
                    drive_files = self.indexer.load_files_paged(
                        'drive', self.current_page, self.page_size, None, self.current_sort, filter_type, None, self.advanced_filters
                    )
                files_to_add = local_files + drive_files
            elif self.advanced_filters.get('extension') not in [None, '']:
                filter_type = 'all'
                local_files = self.indexer.load_files_paged(
                    'local', self.current_page, self.page_size, None, self.current_sort, filter_type, None, self.advanced_filters
                )
                drive_files = []
                if self.is_authenticated and self.show_drive_metadata:
                    drive_files = self.indexer.load_files_paged(
                        'drive', self.current_page, self.page_size, None, self.current_sort, filter_type, None, self.advanced_filters
                    )
                files_to_add = local_files + drive_files

            else:
                filter_type = 'all'
                local_files = self.indexer.load_files_paged(
                    'local', self.current_page, self.page_size, None, self.current_sort, filter_type, None, self.advanced_filters
                )
                drive_files = []
                if self.is_authenticated and self.show_drive_metadata:
                    drive_files = self.indexer.load_files_paged(
                        'drive', self.current_page, self.page_size, None, self.current_sort, filter_type, None, self.advanced_filters
                    )
                files_to_add = local_files + drive_files
        else:
            if self.advanced_filters.get('extension'):
                filter_type = 'all'
            files_to_add = self.indexer.load_files_paged(
                source, self.current_page, self.page_size, self.search_term,
                self.current_sort, filter_type, folder_id, self.advanced_filters
            )

        elapsed_time = time.time() - start_time
        print(
            f"Tempo para carregar {len(files_to_add)} arquivos do banco de dados: {elapsed_time:.4f}s")

        if not files_to_add:
            self.all_files_loaded = True
            if self.files_layout.count() == 0:
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

        self.is_loading = False

    def _add_thumbnail_widgets(self, files_to_add):
        for item in files_to_add:
            item_widget = FileItemWidget(
                self, item, self.service, self.status_bar.showMessage)
            item_widget.selected.connect(self.details_panel.update_details)
            item_widget.folder_clicked.connect(self.navigate_to_folder)
            self.files_layout.addWidget(item_widget)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace:
            if self.current_folder_id:
                self.go_to_parent_folder()
            else:
                pass
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

        if local_path and os.path.exists(local_path):
            pixmap = QPixmap(local_path)
            if not pixmap.isNull():
                self.thumbnail_label.setPixmap(pixmap.scaled(
                    self.thumbnail_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                self.show()
                return
            if mime == 'application/pdf':
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
                        return
                except Exception:
                    pass
            if mime.startswith('video/'):
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
                            return
                except Exception:
                    pass
            try:
                from PyQt6.QtGui import QIcon
                icon = QIcon(local_path)
                pixmap = icon.pixmap(self.thumbnail_label.size())
                if not pixmap.isNull():
                    self.thumbnail_label.setPixmap(pixmap)
                    self.show()
                    return
            except Exception:
                pass

        if file_item.get('source') == 'drive' and thumbnail_link:
            self.thumbnail_thread = QThread()
            self.thumbnail_worker = ThumbnailWorker(thumbnail_link, file_item)
            self.thumbnail_worker.moveToThread(self.thumbnail_thread)
            self.thumbnail_thread.started.connect(self.thumbnail_worker.run)
            self.thumbnail_worker.finished.connect(self.on_thumbnail_loaded)
            self.thumbnail_thread.start()

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
                # verificar se funciona no windows????
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
