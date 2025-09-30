# 🔧 GUIA DE DEBUG - VoxImago.MB

## 🚀 Como usar o sistema de debug

O VoxImago.MB tem um sistema de debug integrado que você pode usar enquanto o aplicativo está rodando. Aqui estão todas as funcionalidades disponíveis:

## ⌨️ ATALHOS DE DEBUG

### F12 - Debug de Busca / Status Geral
- **Com termo na busca**: Analisa detalhadamente a normalização de acentos
- **Sem termo na busca**: Mostra status geral do sistema

**Como usar:**
1. Digite um termo na caixa de busca (ex: "formação")
2. Pressione **F12**
3. Veja no terminal/console o relatório detalhado

### F11 - Status do Banco de Dados
- Mostra estatísticas detalhadas das tabelas
- Verifica consistência entre `files` e `search_index`
- Exibe amostras de normalização
- Mostra horários das últimas sincronizações

**Como usar:**
1. Pressione **F11** a qualquer momento
2. Veja no terminal/console o status completo do banco

### F10 - Teste de Amostras com Acentos
- Executa bateria de testes automáticos com 10 termos conhecidos
- Verifica normalização e busca bidirecional
- Calcula taxa de sucesso
- Mostra exemplos de resultados

**Como usar:**
1. Pressione **F10** a qualquer momento  
2. Aguarde o teste completo (alguns segundos)
3. Veja taxa de sucesso e exemplos no terminal

## 📊 INTERPRETANDO OS RESULTADOS

### ✅ Símbolos de Status
- `✅ CONSISTENTE` - Busca com/sem acentos retorna mesma quantidade
- `⚠️ INCONSISTENTE` - Diferença entre busca com/sem acentos
- `✓` - Teste passou mas sem resultados (normal)
- `❌` - Teste falhou ou erro

### 📈 Taxa de Sucesso (F10)
- **≥ 90%**: Excelente, normalização funcionando perfeitamente
- **80-89%**: Bom, algumas inconsistências menores
- **< 80%**: Precisa investigação, possível problema no índice

## 🔍 EXEMPLOS PRÁTICOS

### Testar Busca com Acentos:
1. Digite "formação" na busca
2. Pressione **F12**
3. Veja se retorna mesma quantidade que "formacao"

### Verificar Sistema:
1. Pressione **F12** (sem nada na busca)
2. Veja status de autenticação, workers, contadores

### Teste Rápido Completo:
1. Pressione **F10**
2. Aguarde resultado automático
3. Verifique se taxa ≥ 80%

## 🐛 SOLUCIONANDO PROBLEMAS

### ❌ "Erro ao acessar índice"
- Banco pode estar corrompido
- Execute reconstrução: `python rebuild_and_test.py`

### ❌ "0 registros no search_index"
- Índice vazio (bug grave)
- Execute: `python -c "from database import FileIndexer; FileIndexer().rebuild_search_index_with_normalization()"`

### ❌ Taxa de sucesso < 80%
- Índice pode estar desatualizado
- Execute reconstrução completa
- Verifique se há erros no terminal

### ⚠️ Resultados inconsistentes
- Normal em alguns casos (arquivos sem acentos)
- Se persistir, verifique implementação do `normalize_text()`

## 💡 DICAS AVANÇADAS

### Termos Recomendados para Teste:
- `formação` / `ação` / `coração` (acentos comuns)
- `são paulo` / `joão` / `damião` (nomes)
- `documentação` / `educação` (palavras longas)

### Verificação Pós-Sincronização:
1. Após sync local/Drive, execute **F11**
2. Verifique se contadores aumentaram
3. Execute **F10** para confirmar normalização

### Debug de Performance:
- Use **F12** durante buscas lentas
- Veja tempo de resposta no terminal
- Compare quantidade FTS5 direto vs. busca normal

## 🚨 LOGS IMPORTANTES

Todos os debugs aparecem no **terminal/console** de onde você executou o app:
```bash
# Para ver logs, execute assim:
python app.py

# Ou no VS Code, veja no terminal integrado
```

## 📞 SUPORTE

Se encontrar problemas:
1. Execute **F10** e anote a taxa de sucesso
2. Execute **F11** e copie as estatísticas
3. Execute **F12** com termo problemático
4. Compartilhe os logs para análise

---
**Versão:** 1.0 | **Data:** Setembro 2025