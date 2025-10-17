# Planejamento Semanal (15 a 21 de Outubro de 2025)

## ✅ Concluído (15-16/10)
- Logs detalhados do processo de fusão e sincronização
- Prints/logs para início/fim da fusão, progresso em lotes
- Tentativa de refatoração com `executemany` (não funcionou)
- Otimização de buscas SQL e índices no banco
- Benchmark: count_files = 0.10s, load_files_paged = 0.03s
- Tratamento de exceções nos slots PyQt6
- Logs de falhas de fusão e conflitos de metadados
- Padronização de nomes de arquivos de banco nos testes

---

## 🔴 HOJE - Quinta-feira (17/10) - CORREÇÃO DO ROLLBACK
### Prioridade Alta: Corrigir Mecanismo de Rollback

**Problema Identificado:**
- ✅ Testes executados revelaram falha no rollback de transações
- ❌ Arquivos permanecem salvos após rollback simulado (esperado: 0, atual: 2)
- ⚠️ Sistema está salvando dados mesmo após erro/exceção

**Tarefas:**
- [x] Investigar implementação atual do rollback em `src/database.py`
- [x] Identificar onde as transações estão sendo commitadas indevidamente
- [x] Implementar controle de transações adequado:
  - [x] `BEGIN TRANSACTION` no início de operações em lote
  - [x] `COMMIT` apenas em caso de sucesso completo
  - [x] `ROLLBACK` em caso de qualquer exceção
- [x] Adicionar context manager para garantir rollback automático
- [x] Testar com `test_transaction_rollback.py` até passar 100%
- [ ] Adicionar testes adicionais para cenários críticos:
  - [x] Rollback com múltiplos arquivos
  - [ ] Rollback durante fusão de metadados
  - [ ] Rollback em operações de delete em lote
- [ ] Documentar o mecanismo de transações no código
- [ ] Atualizar RELATORIO_TESTES.md com correções aplicadas

**ver o app log antes de começar segunda**

**Critério de Sucesso:**
- `test_transaction_rollback.py` deve passar com 0 arquivos após rollback
- Nenhum dado deve ser persistido em caso de erro durante operações em lote

---

## Segunda-feira (21/10)
- [ ] Adicionar testes automatizados adicionais para sistema de fusão
- [ ] Revisar dependências do requirements.txt
- [ ] Validar integridade de dados após correção do rollback
- [ ] Executar suite completa de testes e atualizar relatório

## Para a próxima semana (caso não finalize)
- [ ] Permitir configuração do critério de matching (nome, tamanho, hash).
- [ ] Adicionar opção de preservar metadados locais caso já existam.
- [ ] Implementar opção de "dry-run" para simular fusão sem alterar o banco.
- [ ] Explorar processamento paralelo ou uso de dicionários em memória para matching.
- [ ] Considerar internacionalização (i18n) se o app for usado por públicos diversos.
