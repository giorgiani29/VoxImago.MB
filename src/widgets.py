# widgets.py - Componentes visuais customizados do Vox Imago
# Inclui FileItemWidget, OptionsDialog, ClickableLabel
# Use este arquivo para importar widgets personalizados na interface principal.

import os
import platform

from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QMessageBox, QDialog, QDialogButtonBox, QCheckBox, QFileDialog, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QRunnable



from .utils import load_settings

THUMBNAIL_CACHE_DIR = "assets/thumbnail_cache"


class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opções de Escaneamento Local")
        self.setModal(True)
        self.setFixedSize(400, 300)

        self.main_layout = QVBoxLayout(self)

        self.label = QLabel("Selecione as pastas a serem escaneadas:")
        self.main_layout.addWidget(self.label)

        self.checkboxes = {}
        self.default_paths = self._get_default_folders()

        saved_settings = load_settings().get('scan_paths', [])

        for name, path in self.default_paths.items():
            checkbox = QCheckBox(f"{name} ({path})")
            if path in saved_settings:
                checkbox.setChecked(True)
            self.checkboxes[name] = checkbox
            self.main_layout.addWidget(checkbox)

        self.custom_folder_button = QPushButton("Adicionar Outra Pasta...")
        self.custom_folder_button.clicked.connect(self._add_custom_folder)
        self.main_layout.addWidget(self.custom_folder_button)

        self.custom_paths = saved_settings

        for path in saved_settings:
            if path not in self.default_paths.values():
                checkbox = QCheckBox(f"Customizada: {path}")
                checkbox.setChecked(True)
                self.checkboxes[path] = checkbox
                self.main_layout.insertWidget(
                    self.main_layout.count() - 2, checkbox)

        settings = load_settings()
        show_drive_metadata = settings.get('show_drive_metadata', True)
        self.drive_metadata_checkbox = QCheckBox("Exibir metadados do Drive")
        self.drive_metadata_checkbox.setChecked(show_drive_metadata)
        self.main_layout.addWidget(self.drive_metadata_checkbox)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.main_layout.addWidget(self.button_box)

    def get_show_drive_metadata(self):
        return self.drive_metadata_checkbox.isChecked()

    def _get_default_folders(self):
        user_home = os.path.expanduser("~")
        if platform.system() == "Windows":
            return {
                "Documentos": os.path.join(user_home, "Documents"),
                "Imagens": os.path.join(user_home, "Pictures"),
                "Música": os.path.join(user_home, "Music"),
                "Vídeos": os.path.join(user_home, "Videos"),
                "Downloads": os.path.join(user_home, "Downloads"),
                "Desktop": os.path.join(user_home, "Desktop")
            }
        elif platform.system() == "Darwin":
            return {
                "Documentos": os.path.join(user_home, "Documents"),
                "Imagens": os.path.join(user_home, "Pictures"),
                "Música": os.path.join(user_home, "Music"),
                "Filmes": os.path.join(user_home, "Movies"),
                "Downloads": os.path.join(user_home, "Downloads"),
                "Desktop": os.path.join(user_home, "Desktop")
            }
        else:
            return {
                "Documentos": os.path.join(user_home, "Documents"),
                "Imagens": os.path.join(user_home, "Pictures"),
                "Música": os.path.join(user_home, "Music"),
                "Vídeos": os.path.join(user_home, "Videos"),
                "Downloads": os.path.join(user_home, "Downloads"),
                "Desktop": os.path.join(user_home, "Desktop")
            }

    def _add_custom_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Selecione a Pasta para Adicionar")
        if folder_path and folder_path not in self.custom_paths:
            self.custom_paths.append(folder_path)
            checkbox = QCheckBox(f"Customizada: {folder_path}")
            checkbox.setChecked(True)
            self.checkboxes[folder_path] = checkbox
            self.main_layout.insertWidget(
                self.main_layout.count() - 2, checkbox)

    def get_selected_paths(self):
        selected_paths = []
        for name, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                path = self.default_paths.get(name) or name
                selected_paths.append(path)
        return selected_paths


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class DriveFolderDialog(QDialog):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.setWindowTitle("Selecionar Pastas do Google Drive")
        self.setModal(True)
        self.setFixedSize(500, 400)

        self.main_layout = QVBoxLayout(self)

        self.label = QLabel(
            "Selecione as pastas do Google Drive a serem sincronizadas:")
        self.main_layout.addWidget(self.label)

        self.scroll_area = QScrollArea()
        self.scroll_widget = QWidget()
        self.checkboxes_layout = QVBoxLayout(self.scroll_widget)

        self.root_checkbox = QCheckBox(
            "🌐 Todos os Drives (Meu Drive + Compartilhados)")
        self.root_checkbox.setChecked(True)
        self.checkboxes_layout.addWidget(self.root_checkbox)

        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)

        self.refresh_button = QPushButton("🔄 Atualizar Lista de Pastas")
        self.refresh_button.clicked.connect(self._load_folders)
        self.main_layout.addWidget(self.refresh_button)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.main_layout.addWidget(self.button_box)

        self.folders_data = {}
        self.checkboxes = {}

        self._load_saved_settings()

        self._load_folders()

    def _load_folders(self):
        try:
            self.refresh_button.setEnabled(False)
            self.refresh_button.setText("⏳ Carregando...")

            for checkbox in self.checkboxes.values():
                checkbox.setParent(None)
                checkbox.deleteLater()
            self.checkboxes.clear()
            self.folders_data.clear()

            results = []
            page_token = None

            while True:
                response = self.service.files().list(
                    q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                    fields="nextPageToken, files(id, name, parents, shared, driveId)",
                    pageSize=100,
                    pageToken=page_token,
                    includeItemsFromAllDrives=True,
                    supportsAllDrives=True
                ).execute()

                results.extend(response.get('files', []))
                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            shared_drives = []
            try:
                drives_response = self.service.drives().list(
                    pageSize=100,
                    fields="nextPageToken, drives(id, name)"
                ).execute()
                shared_drives = drives_response.get('drives', [])
                print(f"🔍 Encontrados {len(shared_drives)} Shared Drives")
            except Exception as e:
                print(f"⚠️ Não foi possível listar Shared Drives: {e}")

            shared_drive_root_folders = []
            for drive in shared_drives:
                drive_id = drive['id']
                drive_name = drive['name']

                shared_drive_root_folders.append((drive_id, drive_name, True))

                try:
                    drive_response = self.service.files().list(
                        q=f"'{drive_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                        fields="files(id, name, parents)",
                        pageSize=50,
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        corpora='drive',
                        driveId=drive_id
                    ).execute()

                    drive_folders = drive_response.get('files', [])
                    for folder in drive_folders:
                        folder['shared_drive_name'] = drive_name
                        folder['is_shared_drive'] = True
                        results.append(folder)

                except Exception as e:
                    print(
                        f"⚠️ Erro ao buscar pastas do Shared Drive '{drive_name}': {e}")

            personal_folders = []
            shared_folders = []
            shared_drive_folders = []
            shared_drive_roots = []

            for folder in results:
                folder_id = folder['id']
                folder_name = folder['name']
                is_shared = folder.get('shared', False)
                is_shared_drive = folder.get('is_shared_drive', False)
                shared_drive_name = folder.get('shared_drive_name', '')

                self.folders_data[folder_id] = {
                    'name': folder_name,
                    'parents': folder.get('parents', []),
                    'shared': is_shared,
                    'is_shared_drive': is_shared_drive,
                    'shared_drive_name': shared_drive_name
                }

                if is_shared_drive:
                    shared_drive_folders.append(
                        (folder_id, folder_name, shared_drive_name))
                elif is_shared:
                    shared_folders.append((folder_id, folder_name))
                else:
                    personal_folders.append((folder_id, folder_name))

            for drive_id, drive_name, is_root in shared_drive_root_folders:
                shared_drive_roots.append((drive_id, drive_name))
                self.folders_data[drive_id] = {
                    'name': drive_name,
                    'parents': [],
                    'shared': False,
                    'is_shared_drive': True,
                    'shared_drive_name': drive_name,
                    'is_drive_root': True
                }

            if personal_folders:
                personal_label = QLabel("📁 Meu Drive:")
                personal_label.setStyleSheet(
                    "font-weight: bold; margin-top: 10px;")
                self.checkboxes_layout.addWidget(personal_label)

                for folder_id, folder_name in personal_folders[:20]:
                    checkbox = QCheckBox(f"  📂 {folder_name}")
                    saved_folders = load_settings().get('drive_folders', [])
                    if folder_id in saved_folders:
                        checkbox.setChecked(True)

                    self.checkboxes[folder_id] = checkbox
                    self.checkboxes_layout.addWidget(checkbox)

            if shared_folders:
                shared_label = QLabel("🌐 Arquivos Compartilhados:")
                shared_label.setStyleSheet(
                    "font-weight: bold; margin-top: 10px;")
                self.checkboxes_layout.addWidget(shared_label)

                for folder_id, folder_name in shared_folders[:20]:
                    checkbox = QCheckBox(f"  📂 {folder_name} (compartilhado)")
                    saved_folders = load_settings().get('drive_folders', [])
                    if folder_id in saved_folders:
                        checkbox.setChecked(True)

                    self.checkboxes[folder_id] = checkbox
                    self.checkboxes_layout.addWidget(checkbox)

            if shared_drive_roots or shared_drive_folders:
                team_drives_label = QLabel("🏢 Shared Drives (Equipes):")
                team_drives_label.setStyleSheet(
                    "font-weight: bold; margin-top: 10px; color: #1976D2;")
                self.checkboxes_layout.addWidget(team_drives_label)

                for drive_id, drive_name in shared_drive_roots:
                    checkbox = QCheckBox(f"  🏢 {drive_name} (Drive completo)")
                    saved_folders = load_settings().get('drive_folders', [])
                    if drive_id in saved_folders:
                        checkbox.setChecked(True)
                    self.checkboxes[drive_id] = checkbox
                    self.checkboxes_layout.addWidget(checkbox)

                drives_grouped = {}
                for folder_id, folder_name, drive_name in shared_drive_folders:
                    if drive_name not in drives_grouped:
                        drives_grouped[drive_name] = []
                    drives_grouped[drive_name].append((folder_id, folder_name))

                for drive_name, folders in drives_grouped.items():
                    drive_label = QLabel(f"  📂 Pastas em {drive_name}:")
                    drive_label.setStyleSheet(
                        "font-weight: bold; margin-left: 20px; margin-top: 5px; font-size: 11px;")
                    self.checkboxes_layout.addWidget(drive_label)

                    for folder_id, folder_name in folders[:10]:
                        checkbox = QCheckBox(f"    � {folder_name}")
                        saved_folders = load_settings().get('drive_folders', [])
                        if folder_id in saved_folders:
                            checkbox.setChecked(True)

                        self.checkboxes[folder_id] = checkbox
                        self.checkboxes_layout.addWidget(checkbox)

            self.refresh_button.setEnabled(True)
            self.refresh_button.setText("🔄 Atualizar Lista de Pastas")

        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Erro ao carregar pastas: {e}")
            self.refresh_button.setEnabled(True)
            self.refresh_button.setText("🔄 Atualizar Lista de Pastas")

    def _load_saved_settings(self):
        settings = load_settings()
        self.root_checkbox.setChecked(settings.get('sync_all_drive', True))

    def get_selected_folders(self):
        if self.root_checkbox.isChecked():
            return None

        selected = []
        for folder_id, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.append(folder_id)

        return selected if selected else None

    def save_settings(self):
        from .utils import save_settings
        settings = load_settings()

        selected_folders = self.get_selected_folders()
        if selected_folders is None:
            settings['sync_all_drive'] = True
            settings['drive_folders'] = []
        else:
            settings['sync_all_drive'] = False
            settings['drive_folders'] = selected_folders

        save_settings(settings)


class ThumbnailTask(QRunnable):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker

    def run(self):
        self.worker.run()
