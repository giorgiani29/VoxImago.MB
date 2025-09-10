# Vox Imago Beta

Busca unificada de arquivos locais e Google Drive com filtros avançados, favoritos, visualização de detalhes, download e interface moderna em PyQt6.

## Principais Mudanças

- **Refatoração e organização:** O código foi dividido em módulos especializados (`main.py`, `app.py`, `workers.py`, `database.py`, `utils.py`, `widgets.py`, `ui.py`), facilitando manutenção, testes e colaboração.
- **Novo ponto de entrada:** O aplicativo agora é iniciado pelo arquivo `main.py`, que centraliza a inicialização da interface gráfica.
- **Sincronização aprimorada:** Métodos de busca e sincronização foram revisados para maior eficiência e clareza, buscando separadamente seus arquivos do Google Drive e arquivos explicitamente compartilhados com você.
- **Performance:** Estrutura preparada para otimizações futuras, como commits em lote no banco de dados e redução de travamentos ao lidar com grandes volumes de arquivos.

## Funcionalidades

- Busca por nome, descrição, frases entre aspas, OR, e exclusão de termos (-palavra)
- Filtros por tipo, extensão, data de criação/modificação e favoritos
- Visualização de detalhes com thumbnail ampliada e barra de rolagem
- Download de arquivos do Google Drive
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
