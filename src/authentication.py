
from PyQt6.QtCore import QObject, pyqtSignal
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from src.utils import load_settings
import os

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_FILE = 'config/token.json'
CREDENTIALS_FILE = 'config/credentials.json'


class AuthWorker(QObject):
    authenticated = pyqtSignal(object)  # (service: Google Drive API)
    auth_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def _check_initial_auth(self):
        creds = None
        TOKEN_FILE = 'config/token.json'
        CREDENTIALS_FILE = 'config/credentials.json'
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
                self.auth_failed.emit(
                    "Arquivo credentials.json não encontrado.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

        if creds and creds.valid:
            service = build('drive', 'v3', credentials=creds)
            self.authenticated.emit(service)
            return service
        else:
            self.auth_failed.emit("Não Autenticado")
            return None

    def refresh_token(self):
        try:
            creds = None
            if os.path.exists(TOKEN_FILE):
                creds = Credentials.from_authorized_user_file(
                    TOKEN_FILE, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            if creds and creds.valid:
                service = build('drive', 'v3', credentials=creds)
                return service
        except Exception as e:
            print(f"Erro ao atualizar token: {e}")
        return None

    def run(self):
        self._check_initial_auth()

    def is_authenticated(self):
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(
                    TOKEN_FILE, SCOPES)
                return creds and creds.valid and creds.refresh_token and creds.client_id and creds.client_secret
            except Exception:
                return False
        return False

    def remove_token(self):
        token_path = os.path.abspath(TOKEN_FILE)
        print(f"Tentando remover token: {token_path}")
        if os.path.exists(token_path):
            os.remove(token_path)
            print(f"Token removido: {token_path}")
        else:
            print(f"Token não encontrado para remoção: {token_path}")
