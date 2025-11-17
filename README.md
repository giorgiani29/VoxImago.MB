# 📸 VoxImago.MB - Documentação

> Galeria de imagens com busca unificada Local + Google Drive

## 🚀 Instalação Rápida

### Pré-requisitos
- Python 3.8+
- Windows 10/11

### Passos
1. **Clone o repositório:**
   ```bash
   git clone https://github.com/giorgiani29/VoxImago.MB.git
   cd VoxImago.MB
   ```

2. **Instale dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Google Drive API:**
   - Copie `config/credentials.json.example` → `config/credentials.json`
   - Adicione suas credenciais da Google Cloud Console
   - Copie `config/settings.json.example` → `config/settings.json`
   - Configure seus caminhos de scan

4. **Execute:**
   ```bash
   python app.py
   ```

## 📋 Como Usar

### Primeira Execução

1. **Scan Local** - Configure pastas para monitoramento
2. **Login Google Drive** - Autorize acesso aos seus arquivos
3. **Sincronização** - Deixe o sistema indexar arquivos locais e Drive

### Funcionalidades Principais
- **🔍 Busca Unificada:** Encontre arquivos locais e do Drive simultaneamente
- **🖼️ Visualização:** Grid view com thumbnails inteligentes
- **📁 Filtros:** Por tipo, extensão, data, favoritos
- **⚡ Performance:** Algoritmo O(1) para matching de arquivos
- **🌙 Interface:** Tema escuro, system tray

### Atalhos Úteis
- **F10/F11/F12** - Ferramentas de debug e status
- **Ctrl+F** - Busca rápida
- **Duplo clique** - Abrir arquivo
- **Botão direito** - Menu contextual (Explorer, copiar caminho)

## ⚙️ Configuração

### Caminhos de Scan (`settings.json`)
```json
{
  "scan_paths": [
    "C:/Users/User/Pictures",
    "D:/Fotos"
  ],
  "drive_folders": [
    "root",
    "1ABC123..." 
  ]
}
```

### Formatos Suportados Por Enquanto
- **Imagens:** JPG, PNG, HEIC, RAW (ARW, CR2, etc.)
- **Vídeos:** MP4, AVI, MOV
- **Documentos:** PDF, DOCX (visualização limitada)

## 🔧 Troubleshooting

### Problemas Comuns
- **Token expirado:** Use menu Ferramentas > Logout/Login
- **Arquivos não aparecem:** Force rescan local no menu
- **Performance lenta:** Verifique índices do banco (F11)

### Logs
Arquivos de log em `app.log` para diagnóstico de problemas.

---

*Desenvolvido com PyQt6 e Google Drive API*