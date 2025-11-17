"""
Módulo drive_dialog

Este módulo define diálogos e interfaces relacionados à integração com o Google Drive
no VoxImago.MB. Fornece classes e funções para autenticação, seleção de pastas,
exibição de status de sincronização e interação do usuário com recursos do Drive.
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QMessageBox, QDialog, QDialogButtonBox, QCheckBox, QFileDialog, QScrollArea, QHBoxLayout
)
from PyQt6.QtCore import Qt
from src.utils.utils import load_settings, save_settings
from .drive_service import DriveService


class DriveFolderDialog(QDialog):
    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self.drive_service = DriveService(service)
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
        self.root_checkbox.setChecked(False)
        self.checkboxes_layout.addWidget(self.root_checkbox)

        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setWidgetResizable(True)
        self.main_layout.addWidget(self.scroll_area)

        self.refresh_button = QPushButton("🔄 Atualizar Lista de Pastas")
        self.refresh_button.clicked.connect(self._load_folders)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(
            self.refresh_button, alignment=Qt.AlignmentFlag.AlignLeft)
        buttons_layout.addStretch(1)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        buttons_layout.addWidget(self.button_box)
        self.main_layout.addLayout(buttons_layout)

        self.folders_data = {}
        self.checkboxes = {}

        self._load_saved_settings()
        self._load_folders()

    def _load_saved_settings(self):
        settings = load_settings()
        self.root_checkbox.setChecked(settings.get('sync_all_drive', False))

    def get_selected_folders(self):
        if self.root_checkbox.isChecked():
            return None
        selected = []
        for folder_id, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                selected.append(folder_id)
        return selected if selected else None

    def save_settings(self):
        settings = load_settings()
        selected_folders = self.get_selected_folders()
        if selected_folders is None:
            settings['sync_all_drive'] = True
            settings['drive_folders'] = []
        else:
            settings['sync_all_drive'] = False
            settings['drive_folders'] = selected_folders
        save_settings(settings)

    def _load_folders(self):
        try:
            self.refresh_button.setEnabled(False)
            self.refresh_button.setText("⏳ Carregando...")
            for checkbox in self.checkboxes.values():
                checkbox.setParent(None)
                checkbox.deleteLater()
            self.checkboxes.clear()
            self.folders_data.clear()

            personal_folders = []
            folders = self.drive_service.get_folders_in_drive()
            for folder in folders:
                folder_id = folder['id']
                folder_name = folder['name']
                self.folders_data[folder_id] = {
                    'name': folder_name,
                    'parents': folder.get('parents', []),
                    'shared': False,
                    'is_shared_drive': False,
                    'shared_drive_name': ''
                }
                personal_folders.append((folder_id, folder_name))
            shared_drive_roots = []
            shared_drive_folders = {}
            try:
                shared_drives = self.drive_service.get_shared_drives()
                print(f"🔍 Encontrados {len(shared_drives)} Shared Drives")
                for drive in shared_drives:
                    drive_id = drive['id']
                    drive_name = drive['name']
                    shared_drive_roots.append((drive_id, drive_name))
                    self.folders_data[drive_id] = {
                        'name': drive_name,
                        'parents': [],
                        'shared': False,
                        'is_drive_root': True,
                        'shared_drive_name': drive_name
                    }
                    try:
                        drive_folders = self.drive_service.get_folders_in_drive(
                            drive_id, drive_id)
                        for folder in drive_folders:
                            folder_id = folder['id']
                            folder_name = folder['name']
                            self.folders_data[folder_id] = {
                                'name': folder_name,
                                'parents': folder.get('parents', []),
                                'shared': False,
                                'is_shared_drive': True,
                                'shared_drive_name': drive_name
                            }
                            if drive_name not in shared_drive_folders:
                                shared_drive_folders[drive_name] = []
                            shared_drive_folders[drive_name].append(
                                (folder_id, folder_name))
                    except Exception as e:
                        print(
                            f"⚠️ Erro ao buscar pastas do Shared Drive '{drive_name}': {e}")
            except Exception as e:
                print(f"⚠️ Não foi possível listar Shared Drives: {e}")

            if personal_folders:
                personal_label = QLabel("📁 Driver pessoal:")
                personal_label.setStyleSheet(
                    "font-weight: bold; margin-top: 10px;")
                self.checkboxes_layout.addWidget(personal_label)
                mydrive_root_id = 'root'
                checkbox_root = QCheckBox("  📂 Meu Drive (completo)")
                saved_folders = load_settings().get('drive_folders', [])
                if mydrive_root_id in saved_folders:
                    checkbox_root.setChecked(True)
                self.checkboxes[mydrive_root_id] = checkbox_root
                self.checkboxes_layout.addWidget(checkbox_root)
                for folder_id, folder_name in sorted(personal_folders, key=lambda x: x[1].lower()):
                    checkbox = QCheckBox(f"  📂 {folder_name}")
                    if folder_id in saved_folders:
                        checkbox.setChecked(True)
                    self.checkboxes[folder_id] = checkbox
                    self.checkboxes_layout.addWidget(checkbox)

            if shared_drive_roots:
                team_drives_label = QLabel("🏢 Shared Drives (Equipes):")
                team_drives_label.setStyleSheet(
                    "font-weight: bold; margin-top: 10px; color: #1976D2;")
                self.checkboxes_layout.addWidget(team_drives_label)
                for drive_id, drive_name in sorted(shared_drive_roots, key=lambda x: x[1].lower()):
                    checkbox = QCheckBox(f"  🏢 {drive_name} (Drive completo)")
                    saved_folders = load_settings().get('drive_folders', [])
                    if drive_id in saved_folders:
                        checkbox.setChecked(True)
                    self.checkboxes[drive_id] = checkbox
                    self.checkboxes_layout.addWidget(checkbox)
                    if drive_name in shared_drive_folders:
                        drive_label = QLabel(f"  📂 Pastas em {drive_name}:")
                        drive_label.setStyleSheet(
                            "font-weight: bold; margin-left: 20px; margin-top: 5px; font-size: 11px;")
                        self.checkboxes_layout.addWidget(drive_label)
                        for folder_id, folder_name in sorted(shared_drive_folders[drive_name], key=lambda x: x[1].lower()):
                            checkbox = QCheckBox(f"    📂 {folder_name}")
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
