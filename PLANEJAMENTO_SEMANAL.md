# Planejamento Semanal (20 a 26 de Outubro de 2025)

## ✅ Concluído (13-17/10)
- Logs detalhados do processo de fusão e sincronização
- Prints/logs para início/fim da fusão, progresso em lotes
- Tentativa de refatoração com `executemany` (não funcionou)
- Otimização de buscas SQL e índices no banco
- Benchmark: count_files = 0.10s, load_files_paged = 0.03s
- Tratamento de exceções nos slots PyQt6
- Logs de falhas de fusão e conflitos de metadados
- Padronização de nomes de arquivos de banco nos testes

---
### Prioridade Máxima: Melhorias na Visualização e Usabilidade

**Tarefas:**
 - [ ] Implementar visualização organizada por data (mais recente para mais antiga)
 - [ ] Melhorar qualidade e tamanho dos thumbnails (visualização maior e mais nítida)
 - [ ] Implementar Grid View para exibição dos arquivos
 - [ ] Testar experiência do usuário com vídeos do diário espiritual
 - [ ] Atualizar RELATORIO_TESTES.md com as melhorias aplicadas

**Critério de Sucesso:**
- Usuário consegue visualizar arquivos em grid, por data, com thumbnails de alta qualidade

---

## Segunda-feira (28/10) - Foco em Robustez e Rollback
- [ ] Implementar e testar rollback completo para operações críticas
- [ ] Adicionar testes automatizados para rollback durante fusão de metadados e deletes em lote
- [ ] Documentar o mecanismo de transações no código
- [ ] Validar integridade de dados após rollback
- [ ] Revisar dependências do requirements.txt
- [ ] Executar suite completa de testes e atualizar relatório

## Para a próxima semana (caso não finalize)

## Para as próximas semanas
- [ ] Permitir configuração do critério de matching (nome, tamanho, hash)
- [ ] Adicionar opção de preservar metadados locais caso já existam
- [ ] Implementar opção de "dry-run" para simular fusão sem alterar o banco
- [ ] Explorar processamento paralelo ou uso de dicionários em memória para matching
- [ ] Considerar internacionalização (i18n) se o app for usado por públicos diversos
