# 🚀 VoxImago.MB - Guia Rápido do MVP

## ✅ MVP Funcional - O que você pode fazer AGORA:

### 📋 **Funcionalidades Principais**
1. **Busca Unificada**: Encontre arquivos locais e do Google Drive em um só lugar
2. **Interface Moderna**: Tema escuro elegante e intuitivo
3. **Filtros Avançados**: Por tipo, extensão, data, favoritos
4. **Miniaturas Inteligentes**: Visualização prévia de imagens e documentos
5. **Sincronização Drive**: Importa metadados do Google Drive
6. **Navegação Rápida**: System tray e atalhos de teclado

### 🏁 **Como começar (3 passos simples):**

#### 1️⃣ **Executar o aplicativo**
```bash
cd "C:\Users\user\Desktop\Rafael\VoxImago.MB-main"
python app.py
```

#### 2️⃣ **Configurar pastas locais**
- Clique em "🛠️ Ferramentas" → "Pastas Locais"
- Selecione as pastas que você quer indexar
- Aguarde o escaneamento (barra de progresso na parte inferior)

#### 3️⃣ **Fazer login no Google Drive (opcional)**
- Clique em "Login" (lado direito da barra)
- Autorize no navegador
- Aguarde a sincronização dos metadados

### 🔍 **Como usar as funcionalidades:**

#### **Busca Básica**
- Digite na barra de pesquisa (auto-complete ativo)
- Suporte a frases entre aspas: `"foto família"`
- Exclusão com hífen: `fotos -selfie`
- Operador OR: `férias OR viagem`

#### **Filtros Avançados**
- **Tipos**: Imagens, documentos, planilhas, apresentações, pastas
- **Extensão específica**: .jpg, .pdf, .docx, etc.
- **Datas**: Criado/modificado antes/depois de uma data
- **Favoritos**: Marque arquivos importantes com estrela

#### **Navegação**
- **Clique simples**: Visualiza detalhes no painel direito
- **Duplo clique**: Abre arquivo (local) ou Drive (online)
- **Backspace**: Volta para pasta anterior
- **Enter**: Abre item selecionado

#### **System Tray**
- **Ícone na bandeja**: Minimiza sem fechar
- **Duplo clique no ícone**: Mostra/esconde janela
- **Menu contextual**: Status, ferramentas, sair

### 📊 **Indicadores de Status**

#### **Barra de Status (inferior)**
- Progresso de operações (escaneamento, sincronização)
- Mensagens de feedback
- Contadores de arquivos

#### **Status dos Serviços**
- **Verde**: Funcionando
- **Vermelho**: Erro/não autenticado
- **Amarelo**: Em progresso

### 🎯 **Casos de Uso Típicos**

#### **1. Encontrar fotos de família**
```
Busca: família OR férias
Filtro: Imagens
Resultado: Todas as fotos com essas palavras
```

#### **2. Documentos importantes recentes**
```
Busca: contrato OR relatório  
Filtros: Documentos + Criado após: [última semana]
Resultado: Docs importantes recentes
```

#### **3. Arquivos grandes para limpeza**
```
Filtros: Tamanho > 100MB + Modificado antes: [6 meses]
Resultado: Arquivos antigos grandes
```

### ⚡ **Atalhos de Teclado**
- `Backspace`: Voltar pasta
- `Enter`: Abrir selecionado  
- `Ctrl+F`: Focar na busca
- `F5`: Atualizar lista

### 🔧 **Solução de Problemas Comuns**

#### **"Nenhum arquivo encontrado"**
- Verifique se configurou as pastas locais
- Aguarde o escaneamento terminar
- Tente uma busca mais ampla

#### **"Erro de autenticação Drive"**  
- Verifique se credentials.json está correto
- Reforce o login (Logout → Login)
- Verifique conectividade com internet

#### **"Miniaturas não aparecem"**
- Aguarde alguns segundos (carregamento assíncrono)
- Clique em "Ferramentas" → "Limpar Cache"
- Verifique permissões da pasta thumbnail_cache

### 📈 **Próximos Passos para Melhorias**

1. **Performance**: Otimizar para bibliotecas muito grandes
2. **Backup**: Sistema de backup automático de índices
3. **Sharing**: Compartilhamento direto de arquivos
4. **Analytics**: Relatórios de uso e estatísticas
5. **Cloud**: Suporte a outros provedores (OneDrive, Dropbox)

### 🎉 **Parabéns! Seu MVP está funcionando!**

O VoxImago.MB é um MVP completo e funcional que já oferece:
- ✅ Busca unificada poderosa
- ✅ Interface profissional  
- ✅ Integração Google Drive
- ✅ Performance otimizada
- ✅ Experiência de usuário moderna

**Comece a usar agora e veja como ele facilita o gerenciamento dos seus arquivos!** 🚀