

from PyQt6.QtCore import QObject, pyqtSignal
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import os

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_FILE = 'config/token.json'
CREDENTIALS_FILE = 'config/credentials.json'


class AuthWorker(QObject):
    authenticated = pyqtSignal(Credentials)
    auth_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def _check_initial_auth(self):
        creds = None
        if os.path.exists(TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(
                    TOKEN_FILE, SCOPES)
                if not creds or not creds.valid or not creds.refresh_token or not creds.client_id or not creds.client_secret:
                    raise ValueError("Token inválido ou incompleto.")
            except Exception as e:
                creds = None

        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                self.auth_failed.emit(
                    f"Erro: Arquivo {CREDENTIALS_FILE} não encontrado. Por favor, adicione-o.")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(
                    port=0, access_type='offline', prompt='consent')
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                self.auth_failed.emit(
                    f"Erro de autenticação: {e}. Verifique seu arquivo credentials.json.")
                return None

        return creds

    def run(self):
        creds = self._check_initial_auth()
        if creds:
            self.authenticated.emit(creds)
