# Vox Imago Beta

Busca unificada de arquivos locais e Google Drive com filtros avançados, favoritos, visualização de detalhes e interface moderna em PyQt6.

## Mudanças Recentes (Setembro 2025)

- **Busca por descrição do Drive encontra arquivos locais idênticos:**
  - Agora, ao sincronizar o Drive, a descrição dos arquivos do Drive é copiada para o arquivo local idêntico (mesmo nome e tamanho). Assim, ao buscar por uma descrição, o arquivo local é encontrado mesmo que originalmente não tivesse metadados.
- **Remoção completa da lógica de download:**
  - Todas as funções, botões e classes relacionadas a download de arquivos do Google Drive foram removidas do código. O app agora utiliza apenas os metadados para busca e exibição.
- **Thumbnails reais apenas no painel de detalhes:**
  - Na lista principal, é exibido apenas o ícone genérico do tipo de arquivo. Miniaturas reais aparecem apenas no painel de detalhes.
- **Limpeza de código legado:**
  - Código antigo e funções não utilizadas foram removidos dos módulos principais, deixando o projeto mais limpo e fácil de manter.

## Principais Mudanças

- **Refatoração e organização:** O código foi dividido em módulos especializados (`main.py`, `app.py`, `workers.py`, `database.py`, `utils.py`, `widgets.py`, `ui.py`), facilitando manutenção, testes e colaboração.
- **Novo ponto de entrada:** O aplicativo agora é iniciado pelo arquivo `main.py`, que centraliza a inicialização da interface gráfica.
- **Sincronização aprimorada:** Métodos de busca e sincronização foram revisados para maior eficiência e clareza, buscando separadamente seus arquivos do Google Drive e arquivos explicitamente compartilhados com você.
- **Performance:** Estrutura preparada para otimizações futuras, como commits em lote no banco de dados e redução de travamentos ao lidar com grandes volumes de arquivos.
## Otimizações Implementadas

### 1. Índices e PRAGMA no SQLite
- Índices criados para os principais campos de busca e filtro (`source`, `parentId`, `mimeType`, `starred`, `name`).
- PRAGMA otimizados: `journal_mode=WAL`, `synchronous=NORMAL`, `temp_store=MEMORY`, `cache_size=5000`.

### 2. Conexões SQLite por Thread
- Cada worker/thread abre sua própria conexão SQLite, aplicando PRAGMA para performance.

### 3. Pool Controlado de Miniaturas
- Uso de `QThreadPool` com limite de threads para baixar miniaturas em paralelo de forma controlada.

### 4. Cache de Miniaturas por Hash
- Chave de cache baseada em `(path, mtime, size)` para arquivos locais e `(file_id, modifiedTime)` para arquivos do Google Drive.

---

## Otimizações Parcialmente Implementadas

### 1. Escaneamento Local em Batches
- Inserção em lote já ocorre, mas pode ser ajustada para batches de 500 registros e commit a cada lote.

### 2. Sincronização Incremental do Google Drive
- Sincronização considera o timestamp da última sync, mas precisa garantir busca apenas de arquivos modificados após esse ponto.

### 3. Melhorias de Autocomplete
- Sugestões de busca com debounce já presentes, mas precisam ser limitadas para textos com 3 ou mais caracteres.

### 4. Limpeza de Código Duplicado
- Algumas funções duplicadas ainda existem e precisam ser removidas.

---

## Otimizações Pendentes

- Migrar UI para `QListView` + `QAbstractListModel` para melhor escalabilidade.
- Implementar lazy loading de thumbnails (miniaturas apenas para itens visíveis).
- Adicionar logs de tempo e profiling (`cProfile`, `snakeviz`) para análise de performance.
## Funcionalidades

- Busca por nome, descrição, frases entre aspas, OR, e exclusão de termos (-palavra)
- Filtros por tipo, extensão, data de criação/modificação e favoritos
- Visualização de detalhes com thumbnail ampliada e barra de rolagem
- Escaneamento de múltiplas pastas locais
- Interface moderna e responsiva em PyQt6

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

## Como usar

1. Adicione seu arquivo `credentials.json` do Google Cloud na pasta do projeto.
2. Execute o aplicativo:

```sh
python main.py
```

3. Faça login no Google Drive para sincronizar arquivos.
4. Escolha pastas locais para escanear.
5. Use a barra de busca e filtros para encontrar arquivos.

## Observações Importantes

- Não compartilhe `credentials.json` ou `token.json` publicamente.
- O banco de dados (`file_index.db`) e a pasta de miniaturas (`thumbnails_cache/`) são gerados automaticamente.
- Para dúvidas ou sugestões, abra uma issue no GitHub.
- **Atenção:**  
  Para acessar arquivos do Google Drive, é obrigatório adicionar o arquivo `credentials.json` na pasta do aplicativo.  
  Este arquivo deve ser gerado no Google Cloud Console, ativando a API do Google Drive e criando credenciais do tipo "Aplicativo para área de trabalho".  
  Para testes internos, solicite o arquivo ao responsável pelo projeto.  
  Não compartilhe nem publique o `credentials.json` em locais públicos.

## Estrutura do Projeto

- `main.py`: Ponto de entrada principal do aplicativo.
- `app.py`: Inicialização da interface gráfica e janela principal.
- `workers.py`: Tarefas assíncronas (sincronização, escaneamento local, downloads).
- `database.py`: Manipulação do banco de dados SQLite, busca, filtros e favoritos.
- `utils.py`: Funções utilitárias usadas em várias partes do projeto.
- `widgets.py`: Componentes customizados da interface gráfica.
- `ui.py`: Interface gráfica principal e componentes visuais.
- `requirements.txt`: Lista de dependências.

## Licença

Este projeto é distribuído apenas para testes internos da equipe.
