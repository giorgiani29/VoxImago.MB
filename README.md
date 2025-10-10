# 🚀 VoxImago.MB - Busca Unificada de Arquivos

Sistema inteligente de busca que combina arquivos locais e Google Drive em uma interface moderna PyQt6.

## ⚡ Instalação Rápida

```bash
git clone https://github.com/giorgiani29/VoxImago.MB.git
cd VoxImago.MB
pip install -r requirements.txt
python app.py
```

## 🎯 Funcionalidades Principais

- **🔍 Busca Unificada**: Encontre arquivos locais e do Drive simultaneamente
- **🎨 Interface Moderna**: Tema escuro elegante com system tray
- **🏷️ Filtros Avançados**: Tipo, extensão, data, favoritos
- **🖼️ Miniaturas Inteligentes**: Visualização prévia otimizada
- **☁️ Sincronização Drive**: Metadados do Google Drive
- **🔄 Fusão Inteligente**: Descrições do Drive nos arquivos locais

## 📋 Como Usar

1. **Configure pastas locais**: Ferramentas → Pastas Locais
2. **Login Google Drive**: Clique em "Login" (opcional)
3. **Busque arquivos**: Use a barra de pesquisa com autocomplete
4. **Aplique filtros**: Tipo, extensão, datas, favoritos

## ⌨️ Atalhos

- `F10/F11/F12`: Debug integrado
- `Backspace`: Voltar pasta
- `Enter`: Abrir arquivo
- `Ctrl+F`: Focar busca

## 📊 Status do Projeto

- ✅ **107K+ arquivos** indexados com sucesso
- ✅ **Busca com acentos** funcionando perfeitamente
- ✅ **Performance otimizada** com lazy loading
- ✅ **Sistema de fusão** Drive↔Local ativo

## 🛠️ Requisitos

- Python 3.9+
- PyQt6, google-api-python-client, opencv-python, requests

## 📚 Documentação

- `docs/GUIA_MVP.md` - Guia rápido de uso
- `docs/DEBUG_GUIDE.md` - Sistema de debug
- `docs/README_OPTIMIZACAO.md` - Otimizações técnicas

---

## Otimizações Implementadas

### 1. Índices e PRAGMA no SQLite
- Índices criados para campos de busca e filtro (`source`, `parentId`, `mimeType`, `starred`, `name`).
- PRAGMA otimizados: `journal_mode=WAL`, `synchronous=NORMAL`, `temp_store=MEMORY`, `cache_size=5000`.

### 2. Conexões SQLite por Thread
- Cada worker abre sua própria conexão SQLite com PRAGMAs aplicados.

### 3. Pool Controlado de Miniaturas
- `QThreadPool` com limite de threads para controlar carregamento de miniaturas.

### 4. Cache de Miniaturas por Hash
- `(path, mtime, size)` para locais e `(file_id, modifiedTime)` para arquivos do Drive.

### 5. Lazy Loading de Arquivos
- Paginação com `page_size` + carregamento incremental conforme rolagem.

### 6. UI Escalável com `QListView`
- Substitui widgets menos performáticos.

---

## Otimizações Futuras

- Melhorar ainda mais a sincronização incremental do Drive (apenas arquivos alterados).  
- Limpeza final de funções duplicadas.  
- Adicionar logging detalhado e profiling (`cProfile`, `snakeviz`).  

---

## Funcionalidades

- Busca avançada: nome, descrição, frases entre aspas, `OR`, exclusão com `-palavra`.
- Filtros: tipo de arquivo, extensão, datas de criação/modificação, favoritos.
- Visualização de detalhes com thumbnail ampliada.
- Escaneamento de múltiplas pastas locais.
- Sincronização com Google Drive (somente metadados).
- Interface moderna em PyQt6 (tema escuro + SystemTray).

---

## Requisitos

- Python 3.9 ou superior
- PyQt6
- google-api-python-client
- google-auth-oauthlib
- opencv-python
- requests

Instale as dependências com:

```sh
pip install -r requirements.txt
```

---

## Como usar

1. Adicione seu arquivo `credentials.json` do Google Cloud na pasta do projeto.
2. Execute o aplicativo:

```sh
python app.py
```

3. Faça login no Google Drive para sincronizar metadados.
4. Escolha pastas locais para escanear.
5. Use a barra de busca e os filtros avançados para encontrar arquivos.

---

## Como funciona a sincronização de descrições do Drive para arquivos locais

Durante a sincronização, o sistema compara cada arquivo do Drive com os locais pelo nome e tamanho.  
Se encontrar um arquivo local idêntico, copia a descrição do Drive para o arquivo local e atualiza o índice.  
Assim, buscas por descrição encontram o arquivo local mesmo sem metadados próprios.

