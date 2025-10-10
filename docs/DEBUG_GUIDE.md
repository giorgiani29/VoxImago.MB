# 🔧 Guia de Debug - VoxImago.MB

## ⌨️ Atalhos de Debug

### F12 - Debug de Busca / Status Geral
- **Com termo**: Analisa normalização de acentos
- **Sem termo**: Mostra status geral do sistema

### F11 - Status do Banco de Dados
- Estatísticas das tabelas files/search_index
- Verifica consistência entre tabelas
- Mostra horários das últimas sincronizações

### F10 - Teste de Amostras com Acentos
- Teste automático com 10 termos conhecidos
- Verifica normalização e busca bidirecional
- Calcula taxa de sucesso

## 📊 Interpretando Resultados

- ✅ **CONSISTENTE**: Busca com/sem acentos retorna mesma quantidade
- ❌ **INCONSISTENTE**: Diferenças entre buscas
- ✓ **Bom**: Teste passou mas sem resultados

## � Exemplos Práticos

### Testar Busca com Acentos:
1. Digite "formação" na busca
2. Pressione **F12**
3. Veja se retorna mesma quantidade que "formacao"

### Verificar Sistema:
1. Pressione **F12** (sem busca)
2. Veja status de autenticação e contadores

### Teste Completo:
1. Pressione **F10**
2. Aguarde resultado automático
3. Verifique se taxa ≥ 80%

## 🐛 Solução de Problemas

### ❌ "Erro ao acessar índice"
- Execute: `python rebuild_and_test.py`

### ❌ Taxa de sucesso < 80%
- Execute reconstrução do índice

### ⚠️ Resultados inconsistentes
- Verifique implementação do `normalize_text()`

**Versão:** 1.0 | **Data:** Outubro 2025
