# 🚀 Setup do Projeto VoxImago.MB

## 📦 Instalação Rápida

### 1. **Clone do Repositório**
```bash
git clone [URL_DO_SEU_REPO]
cd VoxImago.MB-main
```

### 2. **Criar Ambiente Virtual**
```bash
# Criar ambiente
python -m venv venv

# Ativar ambiente (Windows)
venv\Scripts\activate

# Ativar ambiente (Linux/Mac)  
source venv/bin/activate
```

### 3. **Instalar Dependências**
```bash
pip install -r requirements.txt
```

### 4. **Configurar Credenciais Google Drive** 

#### 4.1. Obter Credenciais OAuth2:
1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou selecione existente
3. Ative a **Google Drive API**
4. Vá em **Credenciais** → **Criar Credenciais** → **ID do cliente OAuth 2.0**
5. Escolha **"Aplicativo de desktop"**
6. Baixe o arquivo JSON

#### 4.2. Configurar no Projeto:
```bash
# Copie o arquivo baixado para:
cp downloads/client_secret_*.json config/credentials.json

# Ou use o exemplo:
cp config/credentials.json.example config/credentials.json
# Edite config/credentials.json com suas credenciais reais
```

### 5. **Executar o Aplicativo**
```bash
python app.py
```

### 6. **Primeiro Uso**
1. Clique em **"Login"** para autenticar com Google Drive  
2. Configure **pastas locais** em Ferramentas → Pastas Locais
3. Aguarde a sincronização inicial
4. Comece a buscar arquivos! 🎉

## 🔧 Estrutura de Arquivos Importantes

```
VoxImago.MB-main/
├── config/
│   ├── credentials.json     # ← VOCÊ DEVE CRIAR ESTE
│   ├── credentials.json.example  # Exemplo para guiar
│   ├── settings.json        # Criado automaticamente
│   └── settings.json.example    # Exemplo para referência
├── data/                    # Criado automaticamente
│   ├── file_index.db        # Banco de dados local
│   ├── last_sync.txt        # Timestamps
│   └── last_local_sync.txt  # Timestamps
└── venv/                    # Ambiente virtual (você cria)
```

## ⚡ Debug e Testes

### Atalhos de Debug no App:
- **F10**: Teste automático de normalização de acentos
- **F11**: Status completo do banco de dados  
- **F12**: Debug de busca e normalização

### Scripts de Teste:
```bash
# Teste completo do sistema
python tests/test_final.py

# Teste de casos extremos  
python tests/test_edge_cases.py

# Análise de qualidade do código
python analyze_code.py
```

## 🆘 Solução de Problemas

### ❌ "Erro de autenticação Drive"
1. Verifique se `config/credentials.json` existe e é válido
2. Delete `config/token.json` e faça login novamente
3. Confirme que a Google Drive API está ativa no projeto

### ❌ "Nenhum arquivo encontrado"  
1. Configure pastas locais: Ferramentas → Pastas Locais
2. Aguarde o escaneamento terminar (barra de progresso)
3. Verifique se há arquivos nas pastas selecionadas

### ❌ "Erro ao conectar banco"
1. Delete `data/file_index.db` e reinicie o app
2. Execute `python tests/test_final.py` para diagnóstico

## 📊 Status do Sistema

Use **F11** no app para ver:
- Quantidade de arquivos indexados
- Status da sincronização  
- Consistência do banco de dados
- Últimas operações

## 🎯 Funcionalidades Principais

✅ **Busca Unificada**: Local + Google Drive  
✅ **Acentos Inteligentes**: "formação" encontra "formacao"  
✅ **Filtros Avançados**: Tipo, extensão, data, favoritos  
✅ **System Tray**: Minimiza sem fechar  
✅ **Thumbnails**: Pré-visualização de imagens  
✅ **Debug Tools**: F10/F11/F12 para diagnóstico  

---

**🚀 Pronto! Seu VoxImago.MB está funcionando!** 

Para dúvidas, use os debug tools (F10/F11/F12) e consulte a documentação em `docs/`.