'''
 ui.py - Interface principal do Vox Imago
 Contém DriveFileGalleryApp e FileDetailsPanel.
 Gerencia a interface gráfica, eventos, filtros, autenticação e integração com os módulos do projeto.
'''

import os
import webbrowser
from src.authentication import AuthWorker
from src.services.local_scan import LocalScan
from src.drive.processing import start_drive_folder_processing

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QMessageBox, QDialog, QDialogButtonBox, QProgressBar, QSplitter, QVBoxLayout, QProgressDialog, QListView, QSystemTrayIcon, QMenu,
    QAbstractItemView
)

from PyQt6.QtGui import QIcon, QAction
from src.ui.details_panel import FileDetailsPanel
from PyQt6.QtCore import Qt, QTimer, QStringListModel, QDate, QThread, pyqtSignal, QThreadPool, QRunnable, QMetaObject, QSize, QItemSelectionModel
from src.ui.list_view import FileListView
from src.database.database import FileIndexer
from src.database.search import SearchEngine
from src.ui.local_dialog import OptionsDialog
from src.drive.drive_dialog import DriveFolderDialog
from src.utils.utils import load_settings, save_settings, filter_existing_files
from src.ui.thumbnails import ThumbnailCache, ThumbnailManager, FileListDelegate
from src.ui.main_bar import MainBar
from src.ui.list_model import FileListModel
from src.ui.list_update import list_update


SCOPES = ['https://www.googleapis.com/auth/drive.readonly']


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
    thumbnail_generated = pyqtSignal(str)

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
        print('DEBUG: DriveFileGalleryApp.__init__ INICIO')
        super().__init__()
        self.setWindowTitle("VoxImago - Galeria de Arquivos")
        self.setMinimumSize(1260, 660)

        self.scroll_loading = False

        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(8)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("assets/VMico.png"))
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
        self.search_engine = SearchEngine(self.indexer)
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
        self.drive_sync_after_local_scan = False
        self.drive_sync_running = False

        self.auth_thread = None
        self.auth_worker = None
        self.local_scan_thread = None
        self.local_scan_worker = None
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

        self.thumbnail_generated.connect(self.refresh_details_panel_thumbnail)

        settings = load_settings()
        self.show_drive_metadata = settings.get('show_drive_metadata', True)
        scan_paths = settings.get('scan_paths')

        has_saved_config = bool(scan_paths and len(scan_paths) > 0)
        self.auth_worker = AuthWorker()
        has_saved_auth = self.auth_worker.is_authenticated() if self.auth_worker else False
        refreshed_service = None
        if self.auth_worker:
            refreshed_service = self.auth_worker.refresh_token()
            if refreshed_service:
                self.service = refreshed_service
                has_saved_auth = True
        if has_saved_auth:
            self._start_auth(auto=True)
        else:
            self.update_ui_for_auth_state(False)
            list_update.load_next_batch(self)

        if not has_saved_config:
            self.current_view = 'local'
            self.current_folder_id = None
            try:
                existing_count = self.indexer.conn.execute(
                    "SELECT COUNT(*) FROM files WHERE source='local'").fetchone()[0]
                if existing_count == 0:
                    list_update.clear_display(self)
                    self.all_files_loaded = True
                    self.loading_label.setText("Nenhum arquivo encontrado.")
                else:
                    print(
                        f"📁 {existing_count} arquivos locais encontrados no banco")
                    list_update.load_next_batch(self)
            except Exception as e:
                print(f"⚠️ Erro ao verificar arquivos existentes: {e}")
                list_update.clear_display(self)
                self.all_files_loaded = True
                self.loading_label.setText("Nenhum arquivo encontrado.")
            self.loading_label.show()

    def close(self):
        try:
            super().close()
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Ocorreu um erro ao fechar o aplicativo:\n{e}")

    def set_view_mode(self, mode=None):
        if mode is None:
            if self.action_grid_view.isChecked():
                mode = "grid"
            elif self.action_list_view.isChecked():
                mode = "list"
            else:
                mode = "grid"

        if mode == "grid":
            self.file_list_view.setViewMode(QListView.ViewMode.IconMode)
            self.file_list_view.setIconSize(QSize(200, 200))
            self.file_list_view.setGridSize(QSize(240, 280))
            self.file_list_view.setSpacing(8)
            self.action_grid_view.setChecked(True)
            self.action_list_view.setChecked(False)
            self.file_list_view.verticalScrollBar().setSingleStep(60)
            self.file_list_view.verticalScrollBar().setPageStep(240)
        else:
            self.file_list_view.setViewMode(QListView.ViewMode.ListMode)
            self.file_list_view.setIconSize(QSize(48, 48))
            self.file_list_view.setGridSize(QSize(60, 60))
            self.file_list_view.setSpacing(4)
            self.action_grid_view.setChecked(False)
            self.action_list_view.setChecked(True)
            self.file_list_view.verticalScrollBar().setSingleStep(20)
            self.file_list_view.verticalScrollBar().setPageStep(60)

    def on_tray_icon_activated(self, reason):
        try:
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                if self.isMinimized() or not self.isVisible():
                    self.showNormal()
                    self.raise_()
                    self.activateWindow()
                else:
                    self.showMinimized()
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Ocorreu um erro ao ativar o ícone da bandeja:\n{e}")

    def show_service_status(self):
        try:
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
            show_progress = (
                self.local_scan_thread and self.local_scan_thread.isRunning())
            dialog = ServiceStatusDialog(status_text, show_progress, self)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Ocorreu um erro ao exibir o status dos serviços:\n{e}")

    def _check_token_refresh(self):
        if not self.is_authenticated or not self.auth_worker:
            return
        try:
            service = self.auth_worker.refresh_token()
            if service:
                self.service = service
        except Exception as e:
            print(f"Erro ao atualizar token: {e}")

    def _setup_ui(self):
        print('DEBUG: _setup_ui chamado')
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.main_bar = MainBar(self)
        main_layout.addWidget(self.main_bar)
        self.action_grid_view = self.main_bar.action_grid_view
        self.action_list_view = self.main_bar.action_list_view

        self.main_bar.action_scan_options.triggered.connect(
            self._show_scan_options)
        self.main_bar.action_sync_drive.triggered.connect(
            self._start_drive_sync)
        self.main_bar.action_reindex.triggered.connect(
            self._reindex_local_files)
        self.main_bar.action_clear_cache.triggered.connect(
            self.clear_thumbnail_cache)
        self.main_bar.action_explorer.triggered.connect(
            self.toggle_explorer_special)
        self.main_bar.action_grid_view.triggered.connect(
            lambda: self.set_view_mode(None))
        self.main_bar.action_list_view.triggered.connect(
            lambda: self.set_view_mode(None))
        self.main_bar.login_button.clicked.connect(self._start_auth)
        self.main_bar.logout_button.clicked.connect(self.handle_logout)
        self.main_bar.search_entry.textChanged.connect(
            self.handle_search_input)
        self.main_bar.sort_combo.activated.connect(self.change_sort_order)
        self.main_bar.category_combo.activated.connect(
            self.change_filter_type_combo)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.file_list_view = FileListView()
        self.file_list_model = FileListModel([])
        self.file_list_view.setModel(self.file_list_model)
        self.file_list_view.setSelectionMode(
            QListView.SelectionMode.SingleSelection)
        self.file_list_delegate = FileListDelegate(
            self.file_list_view, indexer=self.indexer)
        self.file_list_delegate.requestThumbnail.connect(
            self.handle_request_thumbnail)
        self.file_list_view.setItemDelegate(self.file_list_delegate)
        self.file_list_view.setUniformItemSizes(True)
        self.file_list_view.setMinimumHeight(400)
        self.file_list_view.setMinimumWidth(500)
        self.file_list_view.fileSelected.connect(self.on_file_selected)
        self.file_list_view.fileDoubleClicked.connect(self.on_double_click)
        self.file_list_view.verticalScrollBar().valueChanged.connect(self.on_scroll)

        self.set_view_mode("grid")
        self.file_list_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.file_list_view.setDragEnabled(True)
        self.file_list_view.setAcceptDrops(False)
        self.file_list_view.setDropIndicatorShown(False)
        self.file_list_view.setDragDropMode(
            QAbstractItemView.DragDropMode.DragOnly)

        self.details_panel = FileDetailsPanel(self)

        self.splitter.addWidget(self.file_list_view)
        self.splitter.addWidget(self.details_panel)
        self.details_panel.setMinimumWidth(400)
        self.details_panel.setMaximumWidth(600)
        self.splitter.setSizes([900, 400])

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

        self._pending_thumbs = set()

    def handle_request_thumbnail(self, file_item):
        try:
            if not file_item:
                return
            if ThumbnailCache.is_thumbnail_cached(file_item):
                return
            key = file_item.get('id') or file_item.get('path')
            if not key or key in self._pending_thumbs:
                return
            self._pending_thumbs.add(key)

            class _ThumbRunnable(QRunnable):
                def __init__(self, app_ref, item, key):
                    super().__init__()
                    self.app_ref = app_ref
                    self.item = item
                    self.key = key

                def run(self):
                    try:
                        src = (self.item.get('source') or '').lower()
                        if src == 'local':
                            ThumbnailManager.generate_local_thumbnail(
                                self.item, size=(256, 256))
                    except Exception:
                        pass
                    finally:
                        try:
                            QMetaObject.invokeMethod(
                                self.app_ref.file_list_view.viewport(),
                                "update",
                                Qt.ConnectionType.QueuedConnection
                            )
                        except Exception:
                            pass
                        try:
                            self.app_ref.thumbnail_generated.emit(self.key)
                        except Exception:
                            pass
                        try:
                            self.app_ref._pending_thumbs.discard(self.key)
                        except Exception:
                            pass

            self.thread_pool.start(_ThumbRunnable(self, file_item, key))
        except Exception:
            pass

    def refresh_details_panel_thumbnail(self, file_key: str):
        try:
            curr = getattr(self.details_panel, 'current_file_item', None)
            if not curr:
                return
            curr_key = curr.get('id') or curr.get('path')
            if curr_key != file_key:
                return
            if ThumbnailCache.is_thumbnail_cached(curr):
                self.details_panel.update_details(curr)
        except Exception:
            pass

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

    def _get_file_category(self, filename):
        if not filename:
            return "others"

        ext = os.path.splitext(filename)[1].lower()

        image_extencions = {'.jpg', '.jpeg', '.png',
                            '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff'}
        video_extensions = {'.mp4', '.avi', '.mov', '.wmv',
                            '.flv', '.mkv', '.webm', '.m4v', '.3gp'}
        document_extensions = {'.pdf', '.doc', '.docx', '.txt',
                               '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'}
        audio_extensions = {'.mp3', '.wav',
                            '.flac', '.aac', '.ogg', '.wma', '.m4a'}

        if ext in image_extencions:
            return "images"
        elif ext in video_extensions:
            return "videos"
        elif ext in document_extensions:
            return "documents"
        elif ext in audio_extensions:
            return "audios"
        else:
            return "others"

    def apply_advanced_filters(self):
        filters = {}

        extension_value = self.extension_combo.currentData()
        if extension_value not in [None, '']:
            filters['extension'] = extension_value

        category_value = self.main_bar.category_combo.currentData()
        if category_value not in [None, '']:
            filters['category'] = category_value

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
        list_update.clear_display(self)
        print(f"🔍 Filtros aplicados: {filters}")
        list_update.load_next_batch(self)

    def clear_advanced_filters(self):
        self.extension_combo.setCurrentIndex(0)
        self.modified_after_date.setDate(QDate.currentDate().addDays(-7))
        self.created_after_date.setDate(QDate.currentDate().addDays(-7))
        self.created_before_date.setDate(QDate.currentDate())
        self.advanced_filters = {}
        self.current_page = 0
        self.all_files_loaded = False
        list_update.clear_display(self)
        list_update.load_next_batch(self)
        self.starred_checkbox.setChecked(False)

    def clear_thumbnail_cache(self):
        self.indexer.clear_cache()
        self.status_bar.showMessage("Cache de miniaturas limpo.", 5000)
        self.current_page = 0
        self.all_files_loaded = False
        list_update.clear_display(self)
        list_update.load_next_batch(self)

    def navigate_to_root(self, source):
        self.current_view = None
        self.current_folder_id = None
        self.current_page = 0
        self.all_files_loaded = False
        list_update.clear_display(self)
        list_update.load_next_batch(self)

    def navigate_to_folder(self, folder_id):
        self.search_term = ""
        self.search_entry.clear()
        self.current_folder_id = folder_id
        self.current_page = 0
        self.all_files_loaded = False
        list_update.clear_display(self)
        list_update.load_next_batch(self)

    def update_filter_buttons(self):
        self.main_bar.category_combo.setEnabled(True)
        self.main_bar.sort_combo.setEnabled(True)

    def change_filter_type_combo(self, index):
        selected_category = self.main_bar.category_combo.itemData(index)
        self.current_filter = selected_category
        print(f"DEBUG: Filtro alterado para: {self.current_filter}")
        if selected_category:
            self.advanced_filters['category'] = selected_category
        else:
            self.advanced_filters.pop('category', None)
        self.current_page = 0
        self.all_files_loaded = False
        list_update.clear_display(self)
        list_update.load_next_batch(self)

    def change_sort_order(self, index):
        self.current_sort = self.main_bar.sort_combo.itemData(index)
        self.current_page = 0
        self.all_files_loaded = False
        list_update.clear_display(self)
        list_update.load_next_batch(self)

    def toggle_explorer_special(self):
        self.explorer_special_active = self.main_bar.action_explorer.isChecked()
        self.current_page = 0
        self.all_files_loaded = False
        list_update.clear_display(self)
        list_update.load_next_batch(self)

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
            list_update.clear_display(self)
            list_update.load_next_batch(self)

        self.update_filter_buttons()

    def update_search_suggestions(self):
        try:
            text = self.main_bar.search_entry.text().strip()
            if not text:
                self.completer_model.setStringList([])
                return

            suggestions = self.search_engine.get_search_suggestions(
                text, self.is_authenticated)

            normalized_text = self.search_engine.normalize_text(text)
            if normalized_text != text.lower():
                normalized_suggestions = self.search_engine.get_search_suggestions(
                    normalized_text, self.is_authenticated)
                suggestions = list(set(suggestions + normalized_suggestions))

            self.completer_model.setStringList(suggestions[:10])
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Ocorreu um erro ao atualizar sugestões de busca:\n{e}")

    def handle_search_request(self):
        try:
            original_term = self.main_bar.search_entry.text().strip()
            self.search_term = original_term.lower()

            if self.search_term:
                normalized_term = self.search_engine.normalize_text(
                    self.search_term)
                print(
                    f"🔍 Busca: '{original_term}' → Normalizado: '{normalized_term}'")

            self.current_page = 0
            self.all_files_loaded = False
            self.current_folder_id = None
            list_update.clear_display(self)
            list_update.load_next_batch(self)
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Ocorreu um erro ao buscar arquivos:\n{e}")

    def update_ui_for_auth_state(self, is_authenticated):
        self.is_authenticated = is_authenticated
        self.main_bar.login_button.setVisible(not is_authenticated)
        self.main_bar.logout_button.setVisible(is_authenticated)

    def on_scroll(self, value):
        scroll_bar = self.file_list_view.verticalScrollBar()
        threshold = scroll_bar.maximum() * 0.2
        if value >= scroll_bar.maximum() - threshold and not self.is_loading and not self.all_files_loaded:
            self.scroll_loading = True
            list_update.load_next_batch(self)

    def _show_scan_options(self):
        if self.local_scan_thread and self.local_scan_thread.isRunning():
            QMessageBox.warning(
                self, "Aviso", "Aguarde a conclusão do escaneamento local.")
            return

        dialog = OptionsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:

            selected_paths = dialog.get_selected_folders()
            settings = load_settings()
            settings['scan_paths'] = selected_paths
            save_settings(settings)

            self.current_view = 'local'
            self.current_folder_id = None
            list_update.clear_display(self)
            self.all_files_loaded = False
            self.current_page = 0

            if selected_paths:
                self._start_local_scan(selected_paths)
            else:
                self.indexer.clear_source('local')
                self.loading_label.setText("Nenhum arquivo encontrado.")
                self.loading_label.show()
                self.all_files_loaded = True

        list_update.load_next_batch(self)

    def force_rescan_local(self):
        if self.local_scan_thread and self.local_scan_thread.isRunning():
            QMessageBox.warning(
                self, "Aviso", "Aguarde a conclusão do escaneamento local.")
            return

        dialog = OptionsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_paths = dialog.get_selected_folders() if hasattr(
                dialog, 'get_selected_folders') else None
            settings = load_settings()
            settings['scan_paths'] = selected_paths
            save_settings(settings)

            self.current_view = 'local'
            self.current_folder_id = None
            list_update.clear_display(self)
            self.all_files_loaded = False
            self.current_page = 0

            if selected_paths:
                self._start_local_scan(selected_paths)
            else:
                self.indexer.clear_source('local')
                self.loading_label.setText("Nenhum arquivo encontrado.")
                self.loading_label.show()
                self.all_files_loaded = True

            list_update.load_next_batch(self)

    def _start_local_scan(self, paths_to_scan):
        from src.services.local_scan import LocalScan
        self.all_loaded_label.hide()

        self.local_scan_thread = QThread()
        self.local_scan_worker = LocalScan(self.indexer.db_name, paths_to_scan)
        self.local_scan_worker.moveToThread(self.local_scan_thread)

        self.local_scan_progress = QProgressDialog(
            "Escaneando arquivos locais...", "Cancelar", 0, 100, self)
        self.local_scan_progress.setWindowModality(self.windowModality())
        self.local_scan_progress.setAutoClose(True)
        self.local_scan_progress.setAutoReset(True)
        self.local_scan_progress.setFixedSize(400, 150)
        self.local_scan_progress.setStyleSheet("""
            QProgressBar { min-height: 25px; border: 1px solid #ccc; border-radius: 5px; text-align: center; }
            QProgressBar::chunk { background-color: #1976d2; border-radius: 5px; }
        """)

        self.total_files_to_process = 0

        def on_total_found(total):
            self.total_files_to_process = total
            print(f"DEBUG: Total de arquivos a processar: {total:,}")

        def update_progress(value):
            if self.total_files_to_process > 0:
                percent = min(
                    98, int((value / self.total_files_to_process) * 100))
            else:
                percent = min(98, int(value / 1000))

            self.local_scan_progress.setValue(percent)
            print(
                f"DEBUG: Progresso - {value:,}/{self.total_files_to_process:,} arquivos ({percent}%)")

        def update_status(msg):
            self.local_scan_progress.setLabelText(msg)
            self.status_bar.showMessage(msg, 2000)

        def on_finished():
            self.local_scan_progress.setValue(100)
            self.local_scan_progress.setLabelText("Escaneamento concluído.")
            self.local_scan_progress.close()
            self.on_local_scan_finished()

        self.local_scan_worker.total_files_found.connect(on_total_found)
        self.local_scan_worker.progress_update.connect(update_progress)
        self.local_scan_worker.update_status_signal.connect(update_status)
        self.local_scan_worker.finished.connect(on_finished)

        def cancel_scan():
            print("DEBUG: Botão cancelar pressionado")
            self.local_scan_worker.terminate()
            self.local_scan_progress.close()

        self.local_scan_progress.canceled.connect(cancel_scan)

        self.local_scan_thread.started.connect(self.local_scan_worker.run)

        self.local_scan_progress.show()
        self.local_scan_thread.start()

    def on_local_scan_finished(self):
        if self.local_scan_worker:
            try:
                self.local_scan_worker.finished.disconnect(
                    self.on_local_scan_finished)
            except TypeError:
                pass

        self.indexer = FileIndexer()
        self.search_engine = SearchEngine(self.indexer)
        try:
            file_count = self.indexer.get_file_count(source='local')
            self.tray_icon.showMessage("Sincronização Local Concluída",
                                       f"Escaneamento concluído. {file_count} arquivos locais indexados", QSystemTrayIcon.MessageIcon.Information, 3000)
        except Exception as e:
            print(f"Erro ao acessar banco em on_local_scan_finished: {e}")
            self.tray_icon.showMessage("Sincronização Local Concluída",
                                       "Escaneamento concluído.", QSystemTrayIcon.MessageIcon.Information, 3000)

        self.status_bar.showMessage("Escaneamento local concluído.", 5000)

        if self.local_scan_thread:
            self.local_scan_thread.quit()
            self.local_scan_thread.wait()

        self.local_scan_worker = None
        self.local_scan_thread = None
        self.local_scan_progress = None

        self.current_view = 'local'
        self.current_filter = "all"
        self.advanced_filters = {}
        self.current_page = 0
        self.all_files_loaded = False
        list_update.clear_display(self)
        self.main_bar.category_combo.setCurrentIndex(0)
        list_update.load_next_batch(self)
        if hasattr(self.search_engine, '_paged_cache'):
            self.search_engine._paged_cache.clear()

    def update_local_scan_progress(self, files_processed):
        self.status_bar.showMessage(
            f"Escaneando arquivos locais... {files_processed} arquivos processados.")

    def _start_auth(self, auto=False):
        if self.auth_thread and self.auth_thread.isRunning():
            self.status_bar.showMessage(
                "Processo de login já em andamento...", 5000)
            return

        if not auto:
            self.status_bar.showMessage(
                "Abrindo navegador para autenticação...", 5000)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.main_bar.login_button.setEnabled(False)
        else:
            self.status_bar.showMessage(
                "Verificando autenticação automática...", 5000)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.main_bar.login_button.setEnabled(False)

        self.auth_thread = QThread()
        self.auth_worker = AuthWorker()
        self.auth_worker.moveToThread(self.auth_thread)

        self.auth_worker.authenticated.connect(self.on_auth_success)
        self.auth_worker.auth_failed.connect(self.on_auth_fail)

        self.auth_thread.started.connect(self.auth_worker.run)
        self.auth_thread.start()

    def on_auth_success(self, service):
        self.progress_bar.setVisible(False)
        self.main_bar.login_button.setEnabled(True)
        self.status_bar.showMessage(
            "Login bem-sucedido.", 5000)
        self.service = service
        self.update_ui_for_auth_state(True)

        self.main_bar.update_profile(service)

        settings = load_settings()
        has_saved_config = bool(settings.get('scan_paths') and len(
            settings.get('scan_paths', [])) > 0)
        list_update.load_next_batch(self)

        self.auth_thread.quit()
        self.auth_thread.wait()

    def on_auth_fail(self, error_message):
        self.progress_bar.setVisible(False)
        self.main_bar.login_button.setEnabled(True)
        QMessageBox.critical(self, "Erro de Autenticação", error_message)
        self.status_bar.showMessage("Login falhou.", 5000)

        self.auth_thread.quit()
        self.auth_thread.wait()
        self.auth_worker.deleteLater()
        self.auth_thread.deleteLater()
        self.auth_worker = None
        self.auth_thread = None

    def handle_logout(self):
        try:
            if self.auth_worker:
                self.auth_worker.remove_token()
            self.status_bar.showMessage("Logout bem-sucedido.", 5000)
            self.service = None
            self.indexer.clear_source('drive')
            self.update_ui_for_auth_state(False)

            self.main_bar.reset_profile()

            self.current_view = 'local'
            self.current_folder_id = None
            list_update.load_next_batch(self)
        except Exception as e:
            print(f"Erro ao fazer logout: {e}")
            QMessageBox.warning(self, "Erro", f"Falha ao fazer logout: {e}")

    def _start_drive_sync(self):
        print("🔄 _start_drive_sync chamado pelo usuário")

        if self.drive_sync_running:
            print("⚠️ Drive sync já está em execução - ignorando nova solicitação")
            QMessageBox.information(
                self, "Aviso", "Sincronização do Drive já está em andamento.")
            return

        if not self.service:
            print("❌ Não autenticado no Google Drive")
            QMessageBox.warning(
                self, "Erro", "Não autenticado no Google Drive.")
            return

        self.drive_sync_running = True
        print("🚀 Iniciando nova sincronização do Drive...")

        start_drive_folder_processing(
            self, self.service, self.indexer, force_dialog=True)


    def _show_drive_folder_selection(self):
        if not self.service:
            QMessageBox.warning(
                self, "Erro", "Não autenticado no Google Drive.")
            return

        folder_dialog = DriveFolderDialog(self.service, self)

        if folder_dialog.exec() == QDialog.DialogCode.Accepted:
            folder_dialog.save_settings()
            QMessageBox.information(
                self, "Configuração Salva",
                "As configurações de pastas do Google Drive foram salvas.\n\n"
                "Use 'Selecionar Pastas do Drive' para sincronizar com as pastas selecionadas.")

    def on_drive_sync_finished(self):
        self.drive_sync_running = False
        print("✅ Drive sync finalizado - flag liberada")

        if self.drive_sync_running:
            print("⚠️ AVISO: Flag ainda está True após liberação!")

        prev_selected_id = None
        try:
            selected_indexes = self.file_list_view.selectedIndexes()
            if selected_indexes:
                current_item = self.file_list_model.data(
                    selected_indexes[0], Qt.ItemDataRole.UserRole)
                if current_item:
                    prev_selected_id = current_item.get(
                        'id') or current_item.get('path')
        except Exception:
            prev_selected_id = None

        self.status_bar.showMessage("Sincronização do Drive concluída.", 5000)
        self.progress_bar.setVisible(False)

        self.indexer = FileIndexer()
        self.search_engine = SearchEngine(self.indexer)

        if hasattr(self.indexer, '_paged_cache'):
            self.indexer._paged_cache.clear()
        if hasattr(self.indexer, '_count_cache'):
            self.indexer._count_cache.clear()
        if hasattr(self.search_engine, '_paged_cache'):
            self.search_engine._paged_cache.clear()

        self.current_page = 0
        self.all_files_loaded = False
        self.current_view = 'local'
        self.current_folder_id = None
        self.advanced_filters = {}

        list_update.clear_display(self)

        QTimer.singleShot(
            100, lambda: self._force_refresh_after_sync(prev_selected_id))

    def _force_refresh_after_sync(self, prev_selected_id=None):
        try:
            list_update.load_next_batch(self)

            if prev_selected_id:
                QTimer.singleShot(
                    200, lambda: self._reselect_and_refresh(prev_selected_id))

            selected_indexes = self.file_list_view.selectedIndexes()
            if selected_indexes:
                current_item = self.file_list_model.data(
                    selected_indexes[0], Qt.ItemDataRole.UserRole)
                if current_item:
                    file_id = current_item.get(
                        'id') or current_item.get('path')
                    if file_id:
                        QTimer.singleShot(
                            300, lambda: self._refresh_details_by_id(file_id))

            self.status_bar.showMessage(
                "Interface atualizada com novos metadados.", 3000)

        except Exception as e:
            print(f"Erro ao forçar atualização após sincronização: {e}")
            self.status_bar.showMessage("Erro ao atualizar interface.", 3000)

    def on_metadata_fusion_completed(self, fusion_count):
        try:
            print(
                f"[UI] Fusão de metadados concluída: {fusion_count} arquivos fusionados")

            if hasattr(self.search_engine, '_paged_cache'):
                self.search_engine._paged_cache.clear()

            if fusion_count > 0:
                self.status_bar.showMessage(
                    f"Metadados fusionados: {fusion_count} arquivos atualizados", 3000)

                selected_indexes = self.file_list_view.selectedIndexes()
                if selected_indexes:
                    current_item = self.file_list_model.data(
                        selected_indexes[0], Qt.ItemDataRole.UserRole)
                    if current_item:
                        file_id = current_item.get(
                            'id') or current_item.get('path')
                        if file_id:
                            self._update_file_in_model_and_details(file_id)

        except Exception as e:
            print(f"Erro no callback de fusão de metadados: {e}")

    def _update_file_in_model_and_details(self, file_id):
        try:
            self.indexer.ensure_conn()
            self.indexer.cursor.execute(
                """
                SELECT file_id, name, path, mimeType, source, description, thumbnailLink, thumbnailPath, size, modifiedTime, createdTime, parentId, starred
                FROM files WHERE file_id = ?
                """,
                (file_id,)
            )
            row = self.indexer.cursor.fetchone()
            if row:
                updated_item = {
                    'id': row[0],
                    'name': row[1],
                    'path': row[2],
                    'mimeType': row[3],
                    'source': row[4],
                    'description': row[5],
                    'thumbnailLink': row[6],
                    'thumbnailPath': row[7],
                    'size': row[8],
                    'modifiedTime': row[9],
                    'createdTime': row[10],
                    'parentId': row[11],
                    'starred': bool(row[12]) if len(row) > 12 else False,
                }

                self.file_list_model.updateFileById(file_id, updated_item)

                selected_indexes = self.file_list_view.selectedIndexes()
                if selected_indexes:
                    current_item = self.file_list_model.data(
                        selected_indexes[0], Qt.ItemDataRole.UserRole)
                    if current_item:
                        current_id = current_item.get(
                            'id') or current_item.get('path')
                        if current_id == file_id:
                            self.details_panel.update_details(updated_item)

        except Exception as e:
            print(f"Erro ao atualizar arquivo no modelo: {e}")

    def _refresh_details_by_id(self, file_id: str):
        try:
            if not file_id:
                return
            self.indexer.ensure_conn()
            self.indexer.cursor.execute(
                """
                SELECT file_id, name, path, mimeType, source, description, thumbnailLink, thumbnailPath, size, modifiedTime, createdTime, parentId, starred
                FROM files WHERE file_id = ?
                """,
                (file_id,)
            )
            row = self.indexer.cursor.fetchone()
            if not row:
                return
            updated_item = {
                'id': row[0],
                'name': row[1],
                'path': row[2],
                'mimeType': row[3],
                'source': row[4],
                'description': row[5],
                'thumbnailLink': row[6],
                'thumbnailPath': row[7],
                'size': row[8],
                'modifiedTime': row[9],
                'createdTime': row[10],
                'parentId': row[11],
                'starred': bool(row[12]) if len(row) > 12 else False,
            }
            self.details_panel.update_details(updated_item)
        except Exception as e:
            print(f"[UI] Falha ao atualizar detalhes pós-sync: {e}")

    def _find_model_index_by_id(self, file_id: str):
        try:
            if not file_id:
                return None
            model = self.file_list_model
            rows = model.rowCount()
            for row in range(rows):
                idx = model.index(row, 0)
                item = model.data(idx, Qt.ItemDataRole.UserRole)
                if not item:
                    continue
                item_id = item.get('id') or item.get('path')
                if item_id == file_id:
                    return idx
            return None
        except Exception:
            return None

    def _reselect_and_refresh(self, file_id: str):
        try:
            idx = self._find_model_index_by_id(file_id)
            if idx:
                sel_model = self.file_list_view.selectionModel()
                if sel_model:
                    sel_model.select(
                        idx, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows)
                    self.file_list_view.setCurrentIndex(idx)
                    self.file_list_view.scrollTo(idx)
                self._refresh_details_by_id(file_id)
                return
            self._refresh_details_by_id(file_id)
        except Exception as e:
            print(f"[UI] Falha ao re-selecionar/atualizar: {e}")

    def on_drive_sync_failed(self, error_message):
        self.drive_sync_running = False
        print(f"❌ Drive sync falhou - flag liberada: {error_message}")

        if self.drive_sync_running:
            print("⚠️ AVISO: Flag ainda está True após erro!")

        self.status_bar.showMessage(error_message, 5000)
        self.tray_icon.showMessage(
            "Erro de Sincronização", f"Falha na sincronização do Google Drive: {error_message}", QSystemTrayIcon.MessageIcon.Critical, 5000)
        self.progress_bar.setVisible(False)
        self.update_ui_for_auth_state(False)

    def update_drive_sync_progress(self, value, msg):
        self.status_bar.showMessage(msg)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)

    def update_drive_status_message(self, msg):
        self.status_bar.showMessage(msg)

    def debug_system_status(self):
        print(f"\n" + "="*60)
        print(f"🖥️ DEBUG STATUS DO SISTEMA")
        print(f"="*60)

        auth_status = "✅ Autenticado" if self.is_authenticated else "❌ Não autenticado"
        print(f"🔐 Google Drive: {auth_status}")

        local_scan_running = self.local_scan_thread and self.local_scan_thread.isRunning()
        print(
            f"🔄 Scan local: {'⏳ Executando' if local_scan_running else '✅ Parado'}")
        print("🔄 Sync Drive: ✅ Gerenciado pelo processing.py")

        try:
            local_count = self.indexer.get_file_count(source='local')
            drive_count = self.indexer.get_file_count(
                source='drive') if self.is_authenticated else 0
            total_count = self.indexer.get_file_count()

            print(f"📁 Arquivos locais: {local_count:,}")
            print(f"☁️ Arquivos Drive: {drive_count:,}")
            print(f"📊 Total geral: {total_count:,}")
        except Exception as e:
            print(f"❌ Erro ao contar arquivos: {e}")

        current_search = self.search_entry.text().strip()
        current_results = len(self.file_list_model._files) if hasattr(
            self.file_list_model, '_files') else 0
        print(
            f"🔍 Busca atual: '{current_search}' ({current_results} resultados)")

        print(f"\n💡 ATALHOS DE DEBUG:")
        print(f"   F10 - Testar amostras de acentos")
        print(f"   F11 - Status detalhado do banco")
        print(f"   F12 - Debug da busca atual (ou este status se vazio)")
        print(f"="*60)

    def debug_database_status(self):
        print(f"\n" + "="*60)
        print(f"💾 DEBUG STATUS DO BANCO DE DADOS")
        print(f"="*60)

        try:
            self.indexer.cursor.execute('SELECT COUNT(*) FROM files')
            files_count = self.indexer.cursor.fetchone()[0]

            self.indexer.cursor.execute('SELECT COUNT(*) FROM search_index')
            search_count = self.indexer.cursor.fetchone()[0]

            print(f"📋 Tabela 'files': {files_count:,} registros")
            print(f"🔍 Tabela 'search_index': {search_count:,} registros")

            consistent = files_count == search_count
            status = "✅ CONSISTENTE" if consistent else "⚠️ INCONSISTENTE"
            print(f"🎯 Consistência files ↔ search_index: {status}")

            self.indexer.cursor.execute(
                'SELECT source, COUNT(*) FROM files GROUP BY source')
            sources = self.indexer.cursor.fetchall()
            print(f"\n📂 Distribuição por fonte:")
            for source, count in sources:
                print(f"   {source}: {count:,} arquivos")

            self.indexer.cursor.execute('''
                SELECT name, normalized_name FROM search_index 
                WHERE name != normalized_name 
                LIMIT 5
            ''')
            accent_samples = self.indexer.cursor.fetchall()

            if accent_samples:
                print(f"\n📝 Amostras de normalização no índice:")
                for original, normalized in accent_samples:
                    print(f"   '{original}' → '{normalized}'")
            else:
                print(f"\n📝 Nenhum arquivo com acentos encontrado no índice")

        except Exception as e:
            print(f"❌ Erro ao acessar banco: {e}")

        print(f"="*60)

    def debug_test_accent_samples(self):
        print(f"\n" + "="*60)
        print(f"🧪 DEBUG TESTE DE AMOSTRAS COM ACENTOS")
        print(f"="*60)

        test_samples = [
            ("formação", "formacao"),
            ("ação", "acao"),
            ("coração", "coracao"),
            ("documentação", "documentacao"),
            ("expiação", "expiacao"),
            ("damião", "damiao"),
            ("são", "sao"),
            ("joão", "joao"),
            ("educação", "educacao"),
            ("informação", "informacao")
        ]

        print(f"🔍 Testando {len(test_samples)} termos com acentos...\n")

        total_tests = len(test_samples)
        passed_tests = 0

        for i, (original, expected_norm) in enumerate(test_samples, 1):
            actual_norm = self.search_engine.normalize_text(original)
            norm_ok = actual_norm == expected_norm

            try:
                results_with_accent = self.search_engine.load_files_paged(
                    source=None, page=0, page_size=3, search_term=original,
                    sort_by='name_asc', filter_type='all'
                )
                results_without_accent = self.search_engine.load_files_paged(
                    source=None, page=0, page_size=3, search_term=expected_norm,
                    sort_by='name_asc', filter_type='all'
                )

                search_ok = len(results_with_accent) == len(
                    results_without_accent)
                has_results = len(results_with_accent) > 0

                if norm_ok and search_ok:
                    passed_tests += 1
                    status = "✅" if has_results else "✓"
                else:
                    status = "❌"

                result_info = f"({len(results_with_accent)} resultados)" if has_results else "(sem resultados)"

                print(
                    f"{i:2d}. {status} '{original}' → '{actual_norm}' {result_info}")

                if has_results and i <= 3:
                    example = results_with_accent[0].get('name', 'N/A')[:50]
                    print(f"     Exemplo: {example}...")

            except Exception as e:
                print(f"{i:2d}. ❌ '{original}' → ERRO: {e}")

        success_rate = (passed_tests / total_tests) * 100
        print(f"\n📊 RESULTADO DO TESTE:")
        print(
            f"   ✅ Testes passaram: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(
            f"   🎯 Status geral: {'APROVADO' if success_rate >= 80 else 'PRECISA MELHORIAS'}")

        if success_rate < 100:
            print(
                f"\n💡 Dica: Se alguns testes falharam, execute a reconstrução do índice")
            print(f"   Comando: python -c \"from database import FileIndexer; FileIndexer().rebuild_search_index_with_normalization()\"")

        print(f"="*60)

    def _add_thumbnail_widgets(self, files_to_add):
        if self.current_page == 0:
            self.file_list_model.setFiles(files_to_add)
        else:
            self.file_list_model.addFiles(files_to_add)

    def on_file_selected(self, file_item):
        if file_item:
            self.details_panel.update_details(file_item)

    def on_double_click(self, file_item):
        if file_item and file_item.get('mimeType') in ['application/vnd.google-apps.folder', 'folder']:
            self.search_term = ""
            self.main_bar.search_entry.clear()
            self.current_page = 0
            self.all_files_loaded = False
            list_update.clear_display(self)
            self.current_folder_id = file_item['id']
            list_update.load_next_batch(self)
        elif file_item:
            if file_item.get('source') == 'local' and file_item.get('path'):
                try:
                    os.startfile(file_item['path'])
                except Exception as e:
                    pass
            elif file_item.get('source') == 'drive' and file_item.get('webViewLink'):
                webbrowser.open(file_item['webViewLink'])

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Backspace:
            if self.current_folder_id:
                self.go_to_parent_folder()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            selected_indexes = self.file_list_view.selectedIndexes()
            if selected_indexes:
                file_item = self.file_list_model.data(
                    selected_indexes[0], Qt.ItemDataRole.UserRole)
                self.on_double_click(file_item)
        elif event.key() == Qt.Key.Key_F12:
            current_search = self.main_bar.search_entry.text().strip()
            if current_search:
                self.search_engine.debug_search_normalization(current_search)
            else:
                self.debug_system_status()
        elif event.key() == Qt.Key.Key_F11:
            self.debug_database_status()
        elif event.key() == Qt.Key.Key_F10:
            self.debug_test_accent_samples()
        elif event.key() == Qt.Key.Key_F7:
            print("🔧 F7: Debug CPU Profile (não implementado)")
        elif event.key() == Qt.Key.Key_F8:
            print("📊 F8: Debug Memory Snapshot (não implementado)")
        elif event.key() == Qt.Key.Key_F9:
            print("💾 F9: Debug Memory Stats (não implementado)")
        elif event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            print("🔄 Atalho Ctrl+S - Iniciando sincronização do Google Drive...")
            self._start_drive_sync()
        else:
            super().keyPressEvent(event)

    def go_to_parent_folder(self):
        self.indexer.cursor.execute(
            "SELECT parentId FROM files WHERE file_id = ?", (self.current_folder_id,))
        row = self.indexer.cursor.fetchone()
        parent_id = row[0] if row else None
        self.navigate_to_folder(parent_id)


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
