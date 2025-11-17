'''
 Diálogo de opções de escaneamento local
'''

import os
import platform
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QPushButton, QMessageBox, QDialog, QDialogButtonBox, QCheckBox, QFileDialog, QScrollArea, QHBoxLayout
)
from PyQt6.QtCore import Qt
from src.utils.utils import load_settings, save_settings


class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Opções de Escaneamento Local")
        self.setModal(True)
        self.setFixedSize(500, 400)

        self.main_layout = QVBoxLayout(self)

        self.label = QLabel("Selecione as pastas a serem escaneadas:")
        self.main_layout.addWidget(self.label)

        self.checkboxes = {}
        self.default_paths = self._get_default_folders()
        saved_settings = load_settings().get('scan_paths', [])

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)

        for name, path in self.default_paths.items():
            checkbox = QCheckBox(f"{name} ({path})")
            if path in saved_settings:
                checkbox.setChecked(True)
            self.checkboxes[name] = checkbox
            self.scroll_layout.addWidget(checkbox)

        self.custom_paths = saved_settings

        for path in saved_settings:
            if path not in self.default_paths.values():
                checkbox = QCheckBox(f"Customizada: {path}")
                checkbox.setChecked(True)
                self.checkboxes[path] = checkbox
                self.scroll_layout.insertWidget(
                    self.scroll_layout.count() - 1, checkbox)

        self.scroll_area.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll_area)

        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_folder_button = QPushButton("Adicionar Outra Pasta...")
        self.custom_folder_button.clicked.connect(self._add_custom_folder)
        bottom_layout.addWidget(self.custom_folder_button,
                                alignment=Qt.AlignmentFlag.AlignLeft)
        bottom_layout.addStretch()
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        bottom_layout.addWidget(
            self.button_box, alignment=Qt.AlignmentFlag.AlignRight)
        self.main_layout.addWidget(bottom_widget)

    def _get_default_folders(self):
        user_home = os.path.expanduser("~")
        from src.utils.utils import resolve_shared_folder_path
        folders = {}
        win_folders = [
            ("Documentos", "Documents"),
            ("Imagens", "Pictures"),
            ("Música", "Music"),
            ("Filmes", "Movies"),
            ("Vídeos", "Videos"),
            ("Downloads", "Downloads"),
            ("Desktop", "Desktop"),
        ]
        for pt, en in win_folders:
            pt_path = os.path.join(user_home, pt)
            en_path = os.path.join(user_home, en)
            if os.path.exists(pt_path):
                folders[pt] = pt_path
            elif os.path.exists(en_path):
                folders[pt] = en_path

        banco_path = resolve_shared_folder_path([
            "Banco de Imagens", "Image Bank"
        ])
        if banco_path:
            folders["Banco de Imagens"] = banco_path
        return folders

    def _add_custom_folder(self):
        folder_path = QFileDialog.getExistingDirectory(
            self, "Selecione a Pasta para Adicionar")
        if folder_path and folder_path not in self.custom_paths:
            self.custom_paths.append(folder_path)
            checkbox = QCheckBox(f"Customizada: {folder_path}")
            checkbox.setChecked(True)
            self.checkboxes[folder_path] = checkbox
            self.scroll_layout.addWidget(checkbox)

    def get_selected_folders(self):
        selected = []
        for name, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                if hasattr(self, 'default_paths') and name in self.default_paths:
                    selected.append(self.default_paths[name])
                else:
                    selected.append(name)
        return selected
