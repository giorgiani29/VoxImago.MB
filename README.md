# VoxImago.MB

Um sistema de busca de arquivos que unifica seus arquivos locais e do Google Drive em uma única interface.

## Funcionalidades Principais

- **Busca Unificada**: Encontre arquivos no seu computador e no Google Drive de uma só vez.
- **Filtros Avançados**: Refine sua busca por tipo de arquivo, extensão, data e favoritos.
- **Sincronização Inteligente**: Conecte sua conta Google para que o sistema encontre descrições e tags dos seus arquivos na nuvem e as associe aos seus arquivos locais.
- **Interface Simples**: Um visual limpo e moderno com tema escuro.

## Requisitos

- Python 3.9 ou superior.

## Como Instalar e Usar

1. **Clone o repositório para o seu computador:**
   ```bash
   git clone https://github.com/giorgiani29/VoxImago.MB.git
   cd VoxImago.MB
   ```

2. **Instale as dependências necessárias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure suas credenciais do Google:**
   - Obtenha seu arquivo `credentials.json` no [Google Cloud Console](https://console.cloud.google.com/apis/credentials) e coloque-o na pasta `config/`.

4. **Execute o programa:**
   ```bash
   python app.py
   ```
- Na primeira vez que usar, o aplicativo pedirá para você fazer login na sua conta Google para sincronizar seus arquivos.
- Depois, basta escolher as pastas do seu computador que você deseja que o programa monitore.