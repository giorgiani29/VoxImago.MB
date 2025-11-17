import requests
import io
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class GoogleProfileWorker(QThread):
    profile_loaded = pyqtSignal(dict)
    profile_failed = pyqtSignal(str)
    
    def __init__(self, service):
        super().__init__()
        self.service = service
        
    def run(self):
        try:
            about = self.service.about().get(fields='user').execute()
            user_info = about.get('user', {})
            
            profile_data = {
                'displayName': user_info.get('displayName', 'Usuário'),
                'emailAddress': user_info.get('emailAddress', ''),
                'photoLink': user_info.get('photoLink', '')
            }
            
            self.profile_loaded.emit(profile_data)
            
        except Exception as e:
            self.profile_failed.emit(f"Erro ao buscar perfil: {e}")

class PhotoDownloadWorker(QThread):
    photo_downloaded = pyqtSignal(QPixmap)
    photo_failed = pyqtSignal(str)
    
    def __init__(self, photo_url, size=64):
        super().__init__()
        self.photo_url = photo_url
        self.size = size
        
    def run(self):
        try:
            if '=s' not in self.photo_url:
                self.photo_url += f"=s{self.size}"
            
            response = requests.get(self.photo_url, timeout=10)
            response.raise_for_status()
            
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(self.size, self.size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.photo_downloaded.emit(scaled_pixmap)
            else:
                self.photo_failed.emit("Falha ao carregar imagem")
                
        except Exception as e:
            self.photo_failed.emit(f"Erro ao baixar foto: {e}")

def make_circular_pixmap(pixmap):
    from PyQt6.QtGui import QPainter, QBrush, QPen
    from PyQt6.QtCore import Qt
    
    size = min(pixmap.width(), pixmap.height())
    circular_pixmap = QPixmap(size, size)
    circular_pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(circular_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
    painter.setPen(QPen(Qt.GlobalColor.transparent))
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    
    return circular_pixmap
