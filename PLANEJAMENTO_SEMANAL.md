
# Planejamento Semanal (11 a 17 de Novembro de 2025)


## 🎯 Foco da Semana: Experiência do Usuário e Interface

- **🔍 PRIORITY: Melhorar clareza das mensagens de progresso durante sincronização Drive**
  - Usuário fica confuso com alternância entre duas mensagens diferentes
  - Solução: Unificar mensagens ou tornar transição mais clara
- Melhorar feedback visual e mensagens para o usuário
- Testar e validar melhorias de UX

---

## 🔄 Backlog e Futuras Sprints

### 🏗️ Refatoração Arquitetural (Nova Sprint)
- **Quebrar ui.py monolítico (1000+ linhas)** em componentes menores:
  - MainWindow, FileManager, AuthManager, SearchManager
- **Extrair lógica de negócio da UI** para service classes
- **Padronizar tratamento de erros** em todo o codebase
- **Adicionar testes unitários** básicos
- ✅ **Documentação consolidada** - criado docs/README.md focado no usuário

### Sincronização Híbrida e Incremental
- Monitorar criação/remoção local (watchdog)
- Implementar "soft delete" (is_present_local)
- Sincronizar mudanças da nuvem periodicamente

### Robustez e Rollback
- Implementar e testar rollback completo
- Adicionar testes automatizados para rollback
- Executar suite completa de testes

### Melhorias Futuras
- Configuração de critérios de matching
- Implementar "dry-run" para fusão
- Considerar internacionalização (i18n)

---

## 📊 Avaliação da Arquitetura (Análise Recente)

**Score Geral: 7/10** - Base sólida com oportunidades de melhoria

### Pontos Fortes
- ✅ Separação modular bem definida (database/, drive/, services/, ui/)
- ✅ Padrões PyQt6 adequados (threading, sinais/slots)
- ✅ Funcionalidades sofisticadas (matching O(1), search FTS5)

### Issues Identificadas  
- ⚠️ **ui.py monolítico** (1000+ linhas, múltiplas responsabilidades)
- ⚠️ **Lógica de negócio misturada com UI**
- ⚠️ **Documentação inconsistente** (português/inglês)

---

## ✅ Concluído recentemente

### Core Features
- Grid View e visualização organizada por data
- Otimização SQL e índices (benchmark: count_files = 0.10s)
- Sistema de thumbnails para RAW/HEIC e ícones padrão
- Busca híbrida com suporte a símbolos especiais
- Menu contextual (Explorer, copiar caminho)

### UX/UI Improvements  
- Feedback de autenticação Google Drive aprimorado
- Tooltips e ícones no menu Ferramentas
- Normalização de acentuação em buscas
- Padrão de data baseado em estrutura de pastas

### Technical
- Logs detalhados de fusão e sincronização
- Tratamento de exceções em slots PyQt6
- Modularização de eventos de seleção
- Limpeza de funções não utilizadas