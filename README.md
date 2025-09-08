# VoxImago Beta

Busca unificada de arquivos locais e Google Drive com filtros avançados, favoritos, visualização de detalhes com miniatura ampliada, barra de rolagem, download e interface moderna em PyQt6.

## Funcionalidades

- Busca por nome, descrição, frases entre aspas, OR, e exclusão de termos (-palavra)
- Filtros por tipo, extensão, data de criação/modificação e favoritos
- Visualização de detalhes com thumbnail ampliada e barra de rolagem
- Download de arquivos do Google Drive
- Escaneamento de múltiplas pastas locais
- Interface moderna e responsiva

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
python app.py
```

3. Faça login no Google Drive para sincronizar arquivos.
4. Escolha pastas locais para escanear.
5. Use a barra de busca e filtros para encontrar arquivos.

## Observações

- Não compartilhe `credentials.json` ou `token.json` publicamente.
- O banco de dados (`file_index.db`) e a pasta de miniaturas (`thumbnails_cache/`) são gerados automaticamente.
- Para dúvidas ou sugestões, abra uma issue no GitHub.

## Licença

Este projeto é distribuído apenas para testes internos da equipe.
