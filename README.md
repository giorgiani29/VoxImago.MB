# Vox Imago

Busca unificada de arquivos locais e Google Drive com filtros avançados, favoritos, visualização de detalhes e interface moderna em PyQt6.

## Mudanças Recentes (Setembro 2025)

- **Novo ponto de entrada (`app.py`):**
  - O aplicativo agora é iniciado pelo arquivo `app.py` em vez de `main.py`.
- **Lista de arquivos otimizada com `QListView` + `QAbstractListModel`:**
  - Substitui `QTableWidget` antigo, garantindo escalabilidade e melhor performance.
- **Lazy loading paginado:**
  - Arquivos são carregados em lotes (`page_size`) enquanto o usuário rola a lista.
- **Filtros avançados completos:**
  - Filtragem por extensão, data de criação, data de modificação e favoritos.
- **Interface aprimorada:**
  - Tema escuro moderno via QSS.
  - Ícones genéricos na lista principal; miniaturas reais apenas no painel de detalhes.
- **Modo Explorer Local:**
  - Permite navegação dedicada apenas a arquivos locais.
- **Ícone de bandeja do sistema (SystemTray):**
  - Com menu de ferramentas e opções rápidas (mostrar janela, status dos serviços, sair).
- **Autocomplete de busca com debounce:**
  - Sugestões inteligentes de pesquisa com base no índice local e do Drive.
- **Remoção da lógica de download:**
  - O app agora usa exclusivamente metadados do Drive para busca e exibição.

---

## Principais Mudanças Anteriores

- **Busca por descrição do Drive encontra arquivos locais idênticos.**
- **Thumbnails reais apenas no painel de detalhes.**
- **Limpeza de código legado.**
- **Refatoração e organização em módulos:** (`app.py`, `workers.py`, `database.py`, `utils.py`, `widgets.py`, `ui.py`, `file_list_model.py`, `file_list_delegate.py`).

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

